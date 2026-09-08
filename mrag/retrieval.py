"""Retrieval pipeline.

  query
   │
   ├─ parse explicit ids / sign codes ────► direct lookups
   ├─ BGE-M3 dense+sparse hybrid (RRF) ───► top-K1 chunks
   ├─ +graph 1-hop expansion              ► augment candidate set
   ├─ apply scoring formula:
   │     S = α·dense + β·sparse + γ·hierarchy + δ·graph + ε·w(content_type)
   ├─ mxbai-rerank-large-v2 over top-K1 ──► top-K2 chunks
   ├─ ColQwen2 page retrieval (parallel) ─► top-K3 pages
   ├─ QUESTION ROUTER (v2) ───────────────► needs_figures? (see
   │     mrag/question_router.py). When NO, figure paths are skipped
   │     entirely and result.figures == [] — v1 attached ~4 figures to
   │     every answer regardless of need (measured precision 6%).
   └─ figures (only when the router says yes), merged from three paths:
       Path A — cross-linked from winning chunks via the KG (`see Figure 2B-1`),
                ordered by the rank of the citing chunk (best chunk first)
       Path C — ColQwen2 VISUAL retrieval over figure crops (added v5)
       Path B — caption-text similarity (off by default — was a major source
                of off-topic figures; toggle via CFG.use_caption_figure_fallback)
       Deduplicated and capped at CFG.top_k_figures_candidates. Optional
       VLM-based relevance filter (CFG.use_vlm_figure_filter) prunes to
       CFG.top_k_figures before display. Multi-sheet figures ship ALL their
       sheet images via payload["image_paths"].
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from .config import CFG
from .embeddings import TextEmbedder, ImageEmbedder, Reranker
from .kg import KG
from .question_router import decide_figures
from .vector_store import VectorStore

log = logging.getLogger("mrag.retrieval")


@dataclass
class RetrievalResult:
    chunks:  List[Dict[str, Any]] = field(default_factory=list)
    figures: List[Dict[str, Any]] = field(default_factory=list)
    pages:   List[Dict[str, Any]] = field(default_factory=list)
    debug:   Dict[str, Any]       = field(default_factory=dict)


class Retriever:
    def __init__(
        self,
        store: VectorStore,
        kg: KG,
        text_embedder: TextEmbedder,
        image_embedder: Optional[ImageEmbedder],
        reranker: Reranker,
    ) -> None:
        self.store = store
        self.kg = kg
        self.text = text_embedder
        self.img  = image_embedder
        self.rerank = reranker

    # ----- public entry point ----------------------------------------------

    def retrieve(self, query: str) -> RetrievalResult:
        result = RetrievalResult()
        result.debug["query"] = query

        # 1. Direct lookups -------------------------------------------------
        explicit = self.kg.query_entities(query)
        result.debug["query_entities"] = list(explicit)

        # 2. Hybrid chunk retrieval -----------------------------------------
        dense, sparse_list = self.text.encode_both([query])
        dense_q = dense[0]
        sparse_q = sparse_list[0]
        fused = self.store.search_chunks_hybrid(
            CFG.coll_chunks, dense_q, sparse_q, top_k=CFG.top_k_fused,
        )

        # 3. Graph expansion ------------------------------------------------
        candidate_ids: Set[int] = {h["id"] for h in fused}
        for ent_node in explicit:
            for nb in self.kg.neighbors(ent_node, n_hops=1):
                if not nb.startswith("chunk:"):
                    continue
                # Fetch this chunk by chunk_id from Qdrant via scroll (rare path).
                # In practice we just bump scoring for these in step 4.
                pass  # placeholder; scoring handles it.

        # 4. Apply the scoring formula --------------------------------------
        scored = []
        for hit in fused:
            payload = hit["payload"] or {}
            chunk_id = payload.get("chunk_id", "")
            base = float(hit.get("score", 0.0))
            s_graph = self.kg.proximity_score(explicit, chunk_id)
            s_rt = CFG.rule_type_weight(payload.get("content_type", "Support"))
            s_hier = _hierarchy_prior(query, payload)
            final = (
                CFG.w_dense   * base
                + CFG.w_graph * s_graph
                + CFG.w_ruletype * (s_rt - 1.0)            # center at 1.0
                + CFG.w_hierarchy * s_hier
            )
            scored.append((final, hit))
        scored.sort(key=lambda t: t[0], reverse=True)
        precursor = [h for _s, h in scored[: CFG.top_k_after_graph]]

        # 5. Cross-encoder rerank ------------------------------------------
        docs = [h["payload"].get("text", "")[:1500] for h in precursor]
        rerank_pairs = self.rerank.rank(query, docs, top_k=CFG.top_k_after_rerank)
        final_chunks = []
        for idx, score in rerank_pairs:
            hit = precursor[idx]
            payload = hit["payload"] or {}
            final_chunks.append({**payload, "score": score})
        result.chunks = final_chunks

        # 6. Figures — gated by the question router (v2), then three paths
        #    (A: KG cross-links, C: visual, B: caption fallback).
        figure_ids_seen: Set[str] = set()
        figs_out: List[Dict[str, Any]] = []
        candidate_cap = CFG.top_k_figures_candidates

        if getattr(CFG, "use_question_router", True):
            decision = decide_figures(
                query, kg=self.kg, top_chunks=final_chunks,
                soft_threshold=getattr(CFG, "router_soft_threshold", 0.5),
            )
            result.debug["figure_router"] = {
                "needs_figures": decision.needs_figures,
                "confidence": decision.confidence,
                "max_figures": decision.max_figures,
                "rules": decision.rules_fired,
                **decision.debug,
            }
            if not decision.needs_figures:
                result.figures = []
                # 7. ColPali page retrieval still runs (used for citations),
                #    handled below.
                return self._finish_pages(query, result)

        # Path 0: figures and tables the QUERY ITSELF names.
        # `explicit` comes from kg.query_entities(query) at step 1 but was only
        # ever used for proximity scoring on text chunks — so asking "what is in
        # Table 2B-1" could return every figure except Table 2B-1, whenever the
        # chunk that cites it fell outside the reranked top-k. Named evidence is
        # the strongest signal available; it goes first and cannot be crowded
        # out by the later paths.
        for node in sorted(explicit):
            if not node.startswith("figure:"):
                continue
            fid = node.split(":", 1)[1]
            if fid in figure_ids_seen:
                continue
            payload = _figure_payload_from_graph(self.kg, fid)
            if payload:
                figure_ids_seen.add(fid)
                payload["source"] = "explicit_query_id"
                figs_out.append(payload)
        if figs_out:
            log.info("Path 0: query named %d figure/table(s): %s",
                     len(figs_out), [f.get("figure_id") for f in figs_out])

        # Path A: figures the winning chunks explicitly cite via "see Figure X-Y"
        for ch in final_chunks:
            for fid in self.kg.figures_for_chunk(ch.get("chunk_id", "")):
                if fid in figure_ids_seen:
                    continue
                figure_ids_seen.add(fid)
                payload = _figure_payload_from_graph(self.kg, fid)
                if payload:
                    payload["source"] = "kg_link"
                    figs_out.append(payload)
                if len(figs_out) >= candidate_cap:
                    break
            if len(figs_out) >= candidate_cap:
                break

        # Path C: visual retrieval via ColPali on figure CROPS.
        # Only available if the image embedder loaded AND the visual
        # collection was populated by ingestion (v5+).
        if self.img is not None and len(figs_out) < candidate_cap:
            try:
                q_mv = self.img.encode_queries([query])[0]
                visual_hits = self.store.search_figures_visual(
                    CFG.coll_figures_visual, q_mv,
                    top_k=CFG.top_k_figures_visual,
                )
                for h in visual_hits:
                    payload = h.payload or {}
                    fid = payload.get("figure_id")
                    if fid and fid not in figure_ids_seen:
                        figure_ids_seen.add(fid)
                        figs_out.append({
                            **payload,
                            "score": float(getattr(h, "score", 0.0)),
                            "source": "visual",
                        })
                    if len(figs_out) >= candidate_cap:
                        break
            except Exception as e:
                log.warning("Visual figure retrieval failed: %r", e)

        # Path B: caption-text fallback (OFF by default in v5+). Was the
        # main contributor of off-topic figures in the previous design.
        if (CFG.use_caption_figure_fallback
                and len(figs_out) < candidate_cap):
            extra_hits = self.store.search_figures(
                CFG.coll_figures, dense_q, top_k=candidate_cap,
            )
            for h in extra_hits:
                payload = h.payload or {}
                fid = payload.get("figure_id")
                if fid and fid not in figure_ids_seen:
                    figure_ids_seen.add(fid)
                    figs_out.append({
                        **payload,
                        "score": float(h.score),
                        "source": "caption",
                    })
                if len(figs_out) >= candidate_cap:
                    break

        result.figures = figs_out
        return self._finish_pages(query, result)

    # ------------------------------------------------------------------
    # VINE entry point. SEPARATE from retrieve() on purpose: the RAG
    # baseline must keep behaving exactly as it did, or the Table 2
    # comparison compares two different systems.
    # ------------------------------------------------------------------

    def retrieve_for_obligation(
        self,
        query: str,
        obligation: str,
        certificates: Optional[Sequence[Dict[str, Any]]] = None,
        top_k: Optional[int] = None,
        follow_cross_references: bool = True,
    ) -> RetrievalResult:
        """Retrieve evidence for ONE obligation, conditioned on what is already
        established.

        `retrieve()` answers "what is relevant to this question" once and stops.
        This answers "what do I need to check THIS claim, given what I already
        know" — the paper's R_i = Retrieve(q, phi_i, Gamma_t, K).

        Three things differ from the one-shot path:

        1. The search text is the obligation, not the question. Verifying "the
           roadway is classified as a conventional road" should not retrieve
           whatever the original question was about.
        2. Sections already established by certificates are pulled WHOLE, by id,
           rather than hoping a vector search surfaces the right paragraphs.
           Their cross-referenced sections come too, one hop, because a
           provision's pointers are part of the provision.
        3. `top_k` is caller-controlled. The RAG default of 6 chunks is a page
           and a half of a standard; an obligation with a guard and an
           exception needs more.

        `certificates` follow Appendix A: each is a mapping with an "evidence"
        list of {"type": "section"|"figure"|"table", "id": "..."}. A bare list
        of section-id strings is also accepted.
        """
        result = RetrievalResult()
        result.debug["query"] = query
        result.debug["obligation"] = obligation

        # ---- 1. what do the certificates already establish? --------------
        established: List[str] = []
        for cert in certificates or []:
            if isinstance(cert, str):
                established.append(cert)
                continue
            for ev in (cert.get("evidence") or []):
                if isinstance(ev, str):
                    established.append(ev)
                elif ev.get("type") == "section" and ev.get("id"):
                    established.append(str(ev["id"]))
        established = list(dict.fromkeys(established))

        anchor_sections = list(established)
        if follow_cross_references:
            for sec in established:
                for ref in self.kg.sections_cited_by(sec):
                    if ref not in anchor_sections:
                        anchor_sections.append(ref)
        result.debug["established_sections"] = established
        result.debug["anchor_sections"] = anchor_sections

        # ---- 2. pull those sections whole, by id -------------------------
        anchor_chunk_ids: List[str] = []
        for sec in anchor_sections:
            anchor_chunk_ids.extend(self.kg.chunks_for_section(sec))
        anchor_hits = self.store.fetch_chunks_by_ids(
            CFG.coll_chunks, anchor_chunk_ids,
            default_score=float(getattr(CFG, "obligation_anchor_score", 0.015)),
        )
        result.debug["anchor_chunks"] = len(anchor_hits)

        # ---- 3. search on the OBLIGATION text ----------------------------
        explicit = self.kg.query_entities(f"{obligation} {query}")
        dense, sparse_list = self.text.encode_both([obligation])
        fused = self.store.search_chunks_hybrid(
            CFG.coll_chunks, dense[0], sparse_list[0], top_k=CFG.top_k_fused,
        )

        # ---- 4. merge, then score with the SAME formula as retrieve() ----
        merged, seen = [], set()
        for hit in anchor_hits + fused:          # anchors first: ties go to them
            cid = (hit["payload"] or {}).get("chunk_id", "")
            if cid and cid in seen:
                continue
            seen.add(cid)
            merged.append(hit)

        scored = []
        for hit in merged:
            payload = hit["payload"] or {}
            chunk_id = payload.get("chunk_id", "")
            base = float(hit.get("score", 0.0))
            s_graph = self.kg.proximity_score(explicit, chunk_id)
            s_rt = CFG.rule_type_weight(payload.get("content_type", "Support"))
            s_hier = _hierarchy_prior(obligation, payload)
            final = (
                CFG.w_dense * base
                + CFG.w_graph * s_graph
                + CFG.w_ruletype * (s_rt - 1.0)
                + CFG.w_hierarchy * s_hier
            )
            scored.append((final, hit))
        scored.sort(key=lambda t: t[0], reverse=True)
        precursor = [h for _s, h in scored[: CFG.top_k_after_graph]]

        # ---- 5. rerank against the obligation, not the question ----------
        k = int(top_k if top_k is not None
                else getattr(CFG, "top_k_obligation_chunks", 12))
        final_chunks = []
        if precursor:
            docs = [h["payload"].get("text", "")[:1500] for h in precursor]
            for idx, score in self.rerank.rank(obligation, docs, top_k=k):
                payload = precursor[idx]["payload"] or {}
                final_chunks.append({**payload, "score": score})
        result.chunks = final_chunks

        # ---- 6. figures ---------------------------------------------------
        # No router here: the compiler already decided this obligation needs
        # visual verification when it assigned the verifier. Figures named in
        # the obligation come first, then figures the winning chunks cite.
        figure_ids_seen: Set[str] = set()
        figs_out: List[Dict[str, Any]] = []
        cap = CFG.top_k_figures_candidates

        for node in sorted(explicit):
            if not node.startswith("figure:"):
                continue
            fid = node.split(":", 1)[1]
            if fid in figure_ids_seen:
                continue
            payload = _figure_payload_from_graph(self.kg, fid)
            if payload:
                figure_ids_seen.add(fid)
                payload["source"] = "explicit_obligation_id"
                figs_out.append(payload)

        for ch in final_chunks:
            if len(figs_out) >= cap:
                break
            for fid in self.kg.figures_for_chunk(ch.get("chunk_id", "")):
                if fid in figure_ids_seen or len(figs_out) >= cap:
                    continue
                payload = _figure_payload_from_graph(self.kg, fid)
                if payload:
                    figure_ids_seen.add(fid)
                    payload["source"] = "kg_link"
                    figs_out.append(payload)
        result.figures = figs_out

        result.debug["n_chunks"] = len(final_chunks)
        result.debug["n_figures"] = len(figs_out)
        return result

    def _finish_pages(self, query: str, result: RetrievalResult) -> RetrievalResult:
        """ColPali page retrieval (runs for every query, incl. no-figure ones)."""
        if self.img is not None:
            try:
                q_mv = self.img.encode_queries([query])[0]
                page_hits = self.store.search_pages(CFG.coll_pages, q_mv, top_k=CFG.top_k_pages)
                result.pages = [
                    {**(h.payload or {}), "score": float(h.score)}
                    for h in page_hits
                ]
            except Exception as e:
                log.warning("ColPali page retrieval failed: %r", e)
        return result


def _hierarchy_prior(query: str, payload: Dict[str, Any]) -> float:
    """Cheap prior on top of dense+sparse: if the query mentions Part N or
    Chapter NX, give chunks in that branch a small boost."""
    score = 0.0
    q = query.lower()
    part = (payload.get("part") or "").lower()
    chapter = (payload.get("chapter") or "").lower()
    m_part = re.search(r"\bpart\s+(\d+)\b", q)
    if m_part and f"part {m_part.group(1)}" in part:
        score += 0.6
    m_chap = re.search(r"\bchapter\s+([0-9a-z]+)\b", q)
    if m_chap and m_chap.group(1) in chapter:
        score += 0.6
    return score


def _figure_payload_from_graph(kg: KG, figure_id: str) -> Optional[Dict[str, Any]]:
    node = kg.figure(figure_id)
    if not node:
        return None
    data = kg.g.nodes[node]
    return {
        "figure_id":     data.get("id", figure_id),
        "canonical_id":  data.get("canonical_id", ""),
        "chapter":       data.get("chapter", ""),
        "anchor_section": data.get("anchor_section", ""),
        "page_pdf":      data.get("page_pdf"),
        "page_printed":  data.get("page_printed"),
        "caption":       data.get("caption", ""),
        "title":         data.get("title", ""),
        "image_path":    data.get("image_path", ""),
        "image_paths":   list(data.get("image_paths",
                                         (data.get("image_path", ""),))),
        "n_sheets":      data.get("n_sheets", 1),
        "sign_codes":    list(data.get("sign_codes", [])),
        "source":        "graph_link",
    }
