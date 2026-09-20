"""MUTCD knowledge graph v2: deterministic, NetworkX-backed.

Changes vs v1
-------------
1. FIGURE ANCHORING — v1 linked figures to sections only by page co-location
   (first chunk on the same PDF page), which routinely attached a figure to
   the wrong section. v2 uses three evidence tiers, strongest first:
     T1 anchored_in     The section whose chunks CITE the figure ("see
                        Figure X-Y"). All citing sections get cited_in
                        edges; the anchor prefers a citing section in the
                        figure's own chapter, then the most-citing one.
     T2 belongs_to_chapter  The figure id encodes its chapter (2B-14 -> 2B):
                        layout-independent, always present.
     T3 on_page_of      v1's page co-location, kept only as a weak edge.
2. ONE NODE PER CANONICAL ID — multi-sheet figures (e.g. Figure 9E-12,
   Sheets 1–2) collapse into a single node carrying image_paths=(...); v1
   made the last sheet win and dropped the rest.
3. PREFIX-TOLERANT LOOKUPS — KG.figure() accepts "2B-14", "Figure 2B-14",
   and "figure:Figure 2B-14"; the prefix mismatch that broke the earlier
   gold-figure diagnostic cannot recur.
4. UNRESOLVED-REF ACCOUNTING — refs to entities that never materialised are
   counted in g.graph["build_stats"] and excluded from query results.
5. ROUTER SUPPORT — Section nodes carry cites_any_figure; KG exposes
   section_cites_figures() so the question router can use a KG prior for
   the "does this query need figures at all?" decision.

Node id forms                                   Edge labels
  part:Part 2                                   contains
  chapter:Chapter 2B. Regulatory Signs...       anchored_in    (Figure->Section)
  section:2B.04                                 cited_in       (Figure->Section)
  chunk:MUTCD11e_2B04_Standard_01               belongs_to_chapter (Figure->Chapter)
  figure:Figure 2B-14  /  figure:Table 2B-1     on_page_of     (Figure->Section, weak)
  signcode:R1-1                                 cites_figure / cites_table / cites_section
  category:Regulatory                           defines / mentions / depicts / kind_of
"""
from __future__ import annotations

import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

import networkx as nx

from .parsing import Chunk
from .figures import FigureRecord
from .figure_core import chapter_of
from .sign_codes import SignCodeEntry


# --------------------------------------------------------------------------- #
# Build                                                                       #
# --------------------------------------------------------------------------- #

def build(
    chunks: List[Chunk],
    figures: List[FigureRecord],
    sign_codes: Dict[str, SignCodeEntry],
) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    # v3: real Section nodes even when a section was cited before it was
    # parsed (252 used to stay as unresolved SectionRef stubs), plus
    # Paragraph nodes and the part_of_paragraph / note_on edges.
    # Defined-term index: {term -> chunk id}. Computed here because build()
    # has the chunk text and the graph does not store it.
    terms: Dict[str, str] = {}
    for c in chunks:
        if not (c.section_id.endswith(".02") or c.section_id.endswith(".03")):
            continue
        m = _DEFINED_TERM_RE.match(c.text[:120])
        if m:
            terms.setdefault(m.group(1).strip().lower(), c.chunk_id)
    g.graph["defined_terms"] = terms
    g.graph["_terms_by_length"] = sorted(terms, key=len, reverse=True)
    g.graph["build_stats"] = {**g.graph.get("build_stats", {}),
                              "defined_terms": len(terms)}

    g.graph["schema_version"] = 3

    # ---- 1. hierarchy: Part / Chapter / Section / Chunk ---------------------
    for c in chunks:
        part_id = (c.part or "Part ?").strip()
        chap_id = (c.chapter or "Chapter ?").strip()
        part_node, chap_node = f"part:{part_id}", f"chapter:{chap_id}"
        sec_node, chunk_node = f"section:{c.section_id}", f"chunk:{c.chunk_id}"

        if not g.has_node(part_node):
            g.add_node(part_node, kind="Part", title=part_id)
        if not g.has_node(chap_node):
            g.add_node(chap_node, kind="Chapter", title=chap_id, part=part_id)
            g.add_edge(part_node, chap_node, label="contains")
        # Write the real Section node even if a placeholder already exists.
        # The old `if not g.has_node(...)` guard meant any section cited before
        # it was parsed kept its SectionRef stub: 252 real sections ended up
        # with kind="SectionRef", unresolved=True, no title and no chapter edge.
        existing = g.nodes.get(sec_node, {})
        if not existing.get("resolved_section"):
            g.add_node(sec_node, kind="Section", id=c.section_id,
                       title=c.section_title, page_pdf=c.page_pdf,
                       page_printed=c.page_printed, chapter=chap_id,
                       part=part_id, unresolved=False, resolved_section=True,
                       cites_any_figure=existing.get("cites_any_figure", False))
        if not g.has_edge(chap_node, sec_node):
            g.add_edge(chap_node, sec_node, label="contains")
        g.add_node(chunk_node, kind="Chunk", id=c.chunk_id, section=c.section_id,
                   content_type=c.content_type, ordinal=c.ordinal,
                   page_pdf=c.page_pdf, page_printed=c.page_printed,
                   modal_verbs=tuple(c.modal_verbs))
        g.add_edge(sec_node, chunk_node, label="contains")

        def _ref(target: str, default_kind: str, label: str):
            if not g.has_node(target):
                g.add_node(target, kind=default_kind, unresolved=True)
            g.add_edge(chunk_node, target, label=label)

        for fid in c.figure_refs:
            _ref(f"figure:Figure {fid}", "FigureRef", "cites_figure")
        for tid in c.table_refs:
            _ref(f"figure:Table {tid}", "TableRef", "cites_table")
        for sid in c.section_refs:
            _ref(f"section:{sid}", "SectionRef", "cites_section")
        for sc in c.sign_codes:
            _ref(f"signcode:{sc.upper()}", "SignCodeRef", "mentions")
        # parent links added with list splitting and note chunks:
        #   list_item  -> the paragraph it was split out of
        #   note       -> the figure or table the note is printed inside
        parent = getattr(c, "parent_id", None)
        if parent:
            if getattr(c, "source", "") == "list_item":
                # The paragraph itself is no longer a chunk once it is split,
                # so give it a node of its own rather than a dangling edge.
                # It also gives "4C.05 Paragraph 4" something to resolve to.
                para_node = f"paragraph:{parent}"
                if not g.has_node(para_node):
                    g.add_node(para_node, kind="Paragraph", id=parent,
                               section=c.section_id, content_type=c.content_type,
                               ordinal=c.ordinal, page_pdf=c.page_pdf,
                               unresolved=False)
                    g.add_edge(sec_node, para_node, label="contains")
                g.add_edge(para_node, chunk_node, label="contains")
                g.add_edge(chunk_node, para_node, label="part_of_paragraph")
            elif getattr(c, "source", "") in ("figure_note", "table_note"):
                _ref(f"figure:{parent}", "FigureRef", "note_on")
        if c.figure_refs or c.table_refs:
            g.nodes[sec_node]["cites_any_figure"] = True

    # ---- 2. figures: ONE node per canonical id, sheets collapsed ------------
    by_canonical: Dict[str, List[FigureRecord]] = defaultdict(list)
    for f in figures:
        by_canonical[f.figure_id].append(f)

    page_to_section: Dict[int, str] = {}
    for c in chunks:
        page_to_section.setdefault(c.page_pdf, c.section_id)

    for figure_id, recs in by_canonical.items():
        recs = sorted(recs, key=lambda r: ((r.sheet or 1), r.page_pdf))
        head = recs[0]
        node = f"figure:{figure_id}"
        chapter_short = head.chapter or chapter_of(head.canonical_id)
        g.add_node(node, kind=head.kind, id=figure_id,
                   canonical_id=head.canonical_id,
                   chapter=chapter_short,
                   page_pdf=head.page_pdf, page_printed=head.page_printed,
                   caption=head.caption, title=head.title,
                   image_path=head.image_path,                      # back-compat
                   image_paths=tuple(r.image_path for r in recs),   # all sheets
                   n_sheets=len(recs),
                   sign_codes=tuple(head.sign_codes_depicted),
                   extraction_method=head.extraction_method,
                   unresolved=False)
        # T2: chapter edge straight from the id — layout-independent
        chap_node = _chapter_node(g, chapter_short)
        if chap_node:
            g.add_edge(node, chap_node, label="belongs_to_chapter")
        # T3: weak page co-location
        sec_id = page_to_section.get(head.page_pdf)
        if sec_id:
            g.add_edge(node, f"section:{sec_id}", label="on_page_of")
        for sc in head.sign_codes_depicted:
            g.add_edge(node, f"signcode:{sc.upper()}", label="depicts")

    # ---- 3. T1 citation-based anchoring --------------------------------------
    cite_counts: Dict[str, Counter] = defaultdict(Counter)
    for c in chunks:
        for fid in c.figure_refs:
            cite_counts[f"figure:Figure {fid}"][c.section_id] += 1
        for tid in c.table_refs:
            cite_counts[f"figure:Table {tid}"][c.section_id] += 1
    for fnode, secs in cite_counts.items():
        if not g.has_node(fnode) or g.nodes[fnode].get("unresolved"):
            continue
        for sec_id in secs:
            g.add_edge(fnode, f"section:{sec_id}", label="cited_in")
        anchor = _pick_anchor(g.nodes[fnode].get("chapter", ""), secs)
        g.add_edge(fnode, f"section:{anchor}", label="anchored_in")
        g.nodes[fnode]["anchor_section"] = anchor

    # ---- 4. sign codes & categories -------------------------------------------
    for code, entry in sign_codes.items():
        node = f"signcode:{code}"
        g.add_node(node, kind="SignCode", id=code, category=entry.category,
                   canonical_name=entry.canonical_name, unresolved=False)
        cat_node = f"category:{entry.category}"
        if not g.has_node(cat_node):
            g.add_node(cat_node, kind="Category", id=entry.category)
        g.add_edge(node, cat_node, label="kind_of")
        if entry.first_seen_section:
            g.add_edge(f"section:{entry.first_seen_section}", node, label="defines")

    # ---- 5. figure sign-code backfill (citing chunks + same-page chunks) -----
    page_to_chunk_nodes: Dict[int, List[str]] = defaultdict(list)
    for c in chunks:
        page_to_chunk_nodes[c.page_pdf].append(f"chunk:{c.chunk_id}")
    chunk_mentions: Dict[str, Set[str]] = defaultdict(set)
    for u, v, d in g.edges(data=True):
        if d.get("label") == "mentions" and u.startswith("chunk:"):
            chunk_mentions[u].add(v.split(":", 1)[1])
    for fnode in [n for n, d in g.nodes(data=True)
                  if n.startswith("figure:") and not d.get("unresolved")]:
        cand: Set[str] = set(g.nodes[fnode].get("sign_codes", ()))
        for u, _v, d in g.in_edges(fnode, data=True):
            if d.get("label") in ("cites_figure", "cites_table"):
                cand |= chunk_mentions.get(u, set())
        for cn in page_to_chunk_nodes.get(g.nodes[fnode].get("page_pdf"), []):
            cand |= chunk_mentions.get(cn, set())
        g.nodes[fnode]["sign_codes"] = tuple(sorted(cand))
        for sc in cand:
            g.add_edge(fnode, f"signcode:{sc.upper()}", label="depicts")

    # ---- 6. unresolved-ref accounting ------------------------------------------
    unresolved = [n for n, d in g.nodes(data=True) if d.get("unresolved")]
    g.graph["build_stats"] = {
        "n_nodes": g.number_of_nodes(),
        "n_edges": g.number_of_edges(),
        "n_figures": sum(1 for n, d in g.nodes(data=True)
                         if n.startswith("figure:") and not d.get("unresolved")),
        "n_unresolved_refs": len(unresolved),
        "unresolved_sample": sorted(unresolved)[:20],
        "n_anchored_figures": sum(1 for _n, d in g.nodes(data=True)
                                  if d.get("anchor_section")),
    }
    return g


def _chapter_node(g: nx.MultiDiGraph, chapter_short: str) -> Optional[str]:
    """'2B' -> the 'chapter:Chapter 2B. …' node created during chunk parsing."""
    if not chapter_short:
        return None
    pat = re.compile(rf"^chapter:Chapter\s+{re.escape(chapter_short)}\b",
                     re.IGNORECASE)
    for n in g.nodes:
        if n.startswith("chapter:") and pat.match(n):
            return n
    return None


def _pick_anchor(chapter_short: str, secs: Counter) -> str:
    """Most-citing section, preferring sections in the figure's own chapter
    (Section 2B.14 wins over 6F.03 for Figure 2B-*)."""
    in_chap = {s: n for s, n in secs.items()
               if chapter_short and s.upper().startswith(chapter_short.upper() + ".")}
    pool = in_chap or dict(secs)
    return max(pool.items(), key=lambda kv: kv[1])[0]


# --------------------------------------------------------------------------- #
# Persistence                                                                 #
# --------------------------------------------------------------------------- #

def write(g: nx.MultiDiGraph, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(g, f)


def read(path: Path) -> nx.MultiDiGraph:
    with open(path, "rb") as f:
        return pickle.load(f)


# --------------------------------------------------------------------------- #
# Query wrapper                                                               #
# --------------------------------------------------------------------------- #

# "119. Lane Reduction-a gradual narrowing ..." / "Accessible Pedestrian Signal-a device ..."
_MAX_SIBLING_ITEMS = 24
_DEFINED_TERM_RE = re.compile(r"^(?:\d{1,3}\.\s*)?([A-Z][A-Za-z0-9 ,()/&'\-]{2,60}?)\s*[\u2010-\u2015-]{1,2}\s*[a-z(]")


class KG:
    def __init__(self, g: nx.MultiDiGraph) -> None:
        self.g = g
        self._signs = {n.split(":", 1)[1]: n for n in g.nodes
                       if n.startswith("signcode:")}
        self._figures: Dict[str, str] = {}
        for n, d in g.nodes(data=True):
            if not n.startswith("figure:") or d.get("unresolved"):
                continue
            full = n.split(":", 1)[1]                  # "Figure 2B-14"
            self._figures[full.upper()] = n
            cid = d.get("canonical_id")
            if cid:                                     # "2B-14" also resolves
                self._figures.setdefault(cid.upper(), n)

    # ----- lookups (prefix-tolerant — fixes the v1 diagnostic bug) -----------

    def sign(self, code: str) -> Optional[str]:
        return self._signs.get(code.upper())

    def figure(self, fid: str) -> Optional[str]:
        f = fid.strip()
        if f.lower().startswith("figure:"):
            f = f.split(":", 1)[1]
        return self._figures.get(f.upper())

    def section(self, sec_id: str) -> Optional[str]:
        n = f"section:{sec_id}"
        return n if self.g.has_node(n) else None

    # ----- traversal ----------------------------------------------------------

    def neighbors(self, node: str, n_hops: int = 1) -> Set[str]:
        if not self.g.has_node(node):
            return set()
        out, frontier = {node}, {node}
        ug = self.g.to_undirected(as_view=True)
        for _ in range(n_hops):
            nxt: Set[str] = set()
            for n in frontier:
                nxt.update(ug.neighbors(n))
            out |= nxt
            frontier = nxt
        return out

    def figures_for_chunk(self, chunk_id: str) -> List[str]:
        node = f"chunk:{chunk_id}"
        if not self.g.has_node(node):
            return []
        out = []
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") in ("cites_figure", "cites_table"):
                vd = self.g.nodes.get(v, {})
                if not vd.get("unresolved"):
                    out.append(v.split(":", 1)[1])
        return out

    def note_chunks_for(self, figure_or_table_id: str) -> List[str]:
        """Chunk ids of the notes printed inside a figure or table.

        A table's numbers are meaningless without its notes: Table 6B-4's
        L/W/S key, Table 4C-7's definition of a high-occupancy bus, Table
        3G-1's "spacing should not exceed 300 feet". These are separate
        chunks joined to the figure/table by a `note_on` edge, so a
        calculator or visual obligation can pull the conditions attached to
        the value it is about to use.
        """
        fid = str(figure_or_table_id).strip()
        # accept "Table 6B-4", "6B-4", or a node id
        for node in (fid if fid.startswith("figure:") else f"figure:{fid}",
                     f"figure:Table {fid}", f"figure:Figure {fid}"):
            if self.g.has_node(node):
                return [u.split(":", 1)[1]
                        for u, _v, d in self.g.in_edges(node, data=True)
                        if d.get("label") == "note_on"]
        return []

    def figures_for_section(self, section_id: str) -> List[str]:
        """Figures anchored in (strong) then cited in (medium) this section."""
        node = f"section:{section_id}"
        if not self.g.has_node(node):
            return []
        ranked: List[tuple] = []
        for u, _v, d in self.g.in_edges(node, data=True):
            if not u.startswith("figure:") or self.g.nodes[u].get("unresolved"):
                continue
            lbl = d.get("label")
            if lbl == "anchored_in":
                ranked.append((0, u))
            elif lbl == "cited_in":
                ranked.append((1, u))
        ranked.sort()
        seen, out = set(), []
        for _r, u in ranked:
            fid = u.split(":", 1)[1]
            if fid not in seen:
                seen.add(fid)
                out.append(fid)
        return out

    def chunks_for_section(self, section_id: str) -> List[str]:
        """Every chunk of a section, in paragraph order.

        The graph has no way to ask this before now, so anything that knows it
        wants a whole provision — per-obligation retrieval, graph expansion,
        evidence completeness — had to hope a vector search would surface the
        right paragraphs. Median section is 4 chunks; the largest is 62.
        """
        node = f"section:{section_id}"
        if not self.g.has_node(node):
            return []
        out: List[tuple] = []
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") != "contains" or not v.startswith("chunk:"):
                continue
            vd = self.g.nodes.get(v, {})
            out.append((vd.get("ordinal", 0), v.split(":", 1)[1]))
        out.sort()
        seen, ids = set(), []
        for _o, cid in out:
            if cid not in seen:
                seen.add(cid)
                ids.append(cid)
        return ids

    def defined_terms(self) -> Dict[str, str]:
        """{lower-cased defined term -> chunk id of its definition}.

        Built at graph-build time (the graph stores no chunk text) and
        persisted in g.graph. A definitional obligation is one of the seven
        kinds in S3.1, and the compiler cannot raise one for a term whose
        definition never reached Kq.
        """
        return self.g.graph.get("defined_terms", {})

    def definition_chunk(self, term: str) -> Optional[str]:
        return self.defined_terms().get(str(term).strip().lower())

    def terms_defined_in(self, text: str, min_len: int = 6) -> List[str]:
        """Defined terms that occur in `text`, longest first.

        Longest-first matters: "conventional road" must win over "road".
        """
        low = " " + re.sub(r"\s+", " ", text.lower()) + " "
        out = []
        for term in self.g.graph.get("_terms_by_length", []):
            if len(term) < min_len:
                break
            if f" {term} " in low or f" {term}s " in low or f" {term}," in low:
                out.append(term)
        return out

    def notes_for_section(self, section_id: str) -> List[str]:
        """Note chunks of every figure/table this section cites or anchors.

        A table's number without its note is the failure mode this project
        keeps hitting: Table 6B-4's L/W/S key, Table 4C-7's definition of a
        high-occupancy bus, Table 3G-1's 300-foot cap.
        """
        out: List[str] = []
        for fid in self.figures_for_section(section_id):
            out.extend(self.note_chunks_for(fid))
        return list(dict.fromkeys(out))

    def paragraph_items(self, chunk_id: str) -> List[str]:
        """Sibling list items of the paragraph a chunk belongs to.

        Retrieval returns ONE item of a split list; its siblings are part of
        the same provision and often carry the exception.
        """
        node = f"chunk:{chunk_id}"
        if not self.g.has_node(node):
            return []
        out: List[str] = []
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") != "part_of_paragraph":
                continue
            for _p, w, dd in self.g.out_edges(v, data=True):
                if dd.get("label") == "contains" and w.startswith("chunk:"):
                    out.append(w.split(":", 1)[1])
        out = [c for c in dict.fromkeys(out) if c != chunk_id]
        # 1C.02 is one paragraph of 295 items. Its "siblings" are 294
        # unrelated definitions, so a big group is not a provision whose parts
        # belong together and pulling it in floods Kq.
        return [] if len(out) > _MAX_SIBLING_ITEMS else out

    def chunks_for_paragraph(self, section_id: str, ordinal: int) -> List[str]:
        """Every CHUNK making up paragraph `ordinal` of `section_id`.

        `chunk_for_paragraph` returns the paragraph NODE's id when a paragraph
        was split into lettered items -- and no chunk carries that bare id, so
        the reference resolved to nothing. Measured on the manual: 92 of its
        472 paragraph references, 19%, died that way, in the closure and in
        the cross-reference resolver alike.

        A split paragraph is one provision, so all of its items come back
        together. Returning one item would hand a verifier item A of a rule
        whose condition is in item C.
        """
        node = f"section:{section_id}"
        if not self.g.has_node(node):
            return []
        para_node = None
        for _u, v, d in self.g.out_edges(node, data=True):
            if (d.get("label") == "contains" and v.startswith("paragraph:")
                    and int(self.g.nodes[v].get("ordinal", -1)) == int(ordinal)):
                para_node = v
                break

        out: List[str] = []
        if para_node is not None:
            for u, _v, d in self.g.in_edges(para_node, data=True):
                if d.get("label") == "part_of_paragraph" and u.startswith("chunk:"):
                    out.append(u.split(":", 1)[1])
            if out:
                return sorted(out)
            # an unsplit paragraph: its own id IS the chunk id
            bare = para_node.split(":", 1)[1]
            if self.g.has_node(f"chunk:{bare}"):
                return [bare]

        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") != "contains" or not v.startswith("chunk:"):
                continue
            if int(self.g.nodes[v].get("ordinal", -1)) == int(ordinal):
                out.append(v.split(":", 1)[1])
        return sorted(out)

    def chunk_for_paragraph(self, section_id: str, ordinal: int) -> Optional[str]:
        """The chunk holding paragraph `ordinal` of `section_id`.

        The manual points at paragraphs, not sections: 4K.04 says "see
        Paragraph 6 in Section 4K.03". Resolving that to the whole section
        hands a verifier 25 chunks and asks it to guess which one was meant.
        """
        node = f"section:{section_id}"
        if not self.g.has_node(node):
            return None
        # Paragraph nodes FIRST. Where a paragraph was split into list items,
        # every item carries the PARENT's ordinal, so matching chunks first
        # returned item 1 of 295 for "Paragraph 3 of Section 1C.02" -- one
        # definition standing in for the whole provision.
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") == "contains" and v.startswith("paragraph:") \
                    and int(self.g.nodes[v].get("ordinal", -1)) == int(ordinal):
                return v.split(":", 1)[1]
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") != "contains" or not v.startswith("chunk:"):
                continue
            if int(self.g.nodes[v].get("ordinal", -1)) == int(ordinal):
                return v.split(":", 1)[1]
        return None

    def resolves(self, kind: str, ident: str) -> bool:
        """Does this reference point at something that actually exists?

        4 of the manual's own section references do not: 8B.05, 8C.05, 8E.10
        and 9D.10 appear in the text but not in its outline.
        """
        if kind == "section":
            node = f"section:{ident}"
            return self.g.has_node(node) and self.g.nodes[node].get("kind") == "Section"
        node = self.figure(ident)
        return bool(node) and not self.g.nodes[node].get("unresolved")

    def sections_cited_by(self, section_id: str) -> List[str]:
        """Sections this one cross-references, via its chunks' cites_section
        edges. `4K.04` -> `['4K.03']`, because paragraph 4 points there.

        Gold evidence lists the anchor section only, so a provision's pointers
        are invisible to anything scoring against the answer key alone.
        """
        out, seen = [], set()
        for cid in self.chunks_for_section(section_id):
            node = f"chunk:{cid}"
            if not self.g.has_node(node):
                continue
            for _u, v, d in self.g.out_edges(node, data=True):
                if d.get("label") == "cites_section" and v.startswith("section:"):
                    sec = v.split(":", 1)[1]
                    if sec != section_id and sec not in seen:
                        seen.add(sec)
                        out.append(sec)
        return out

    def section_cites_figures(self, section_id: str) -> bool:
        n = f"section:{section_id}"
        return bool(self.g.has_node(n)
                    and self.g.nodes[n].get("cites_any_figure"))

    def chunks_for_signcode(self, code: str) -> List[str]:
        node = self.sign(code)
        if not node:
            return []
        ug = self.g.to_undirected(as_view=True)
        return [n.split(":", 1)[1] for n in ug.neighbors(node)
                if n.startswith("chunk:")]

    # ----- query-time ----------------------------------------------------------

    def query_entities(self, query: str) -> Set[str]:
        ents: Set[str] = set()
        q = query.translate({0x2010: "-", 0x2011: "-", 0x2012: "-",
                             0x2013: "-", 0x2014: "-"})
        for m in re.finditer(r"\b(Figure|Table)\s+([0-9A-Z]+-[0-9]+[A-Za-z0-9]*)\b",
                             q, re.IGNORECASE):
            n = self.figure(f"{m.group(1).title()} {m.group(2).upper()}")
            if n:
                ents.add(n)
        for m in re.finditer(r"\b(?:Section\s+)?([0-9]+[A-Z]\.[0-9]+)\b", q):
            n = self.section(m.group(1))
            if n:
                ents.add(n)
        for m in re.finditer(r"\b([RWDIMOE][A-Z]?\d{1,3}(?:-\d{1,3})?[a-zA-Z]?P?)\b",
                             q):
            n = self.sign(m.group(1))
            if n:
                ents.add(n)
        return ents

    def proximity_score(self, query_ents: Set[str], chunk_id: str) -> float:
        if not query_ents:
            return 0.0
        node = f"chunk:{chunk_id}"
        if not self.g.has_node(node):
            return 0.0
        ug = self.g.to_undirected(as_view=True)
        best = float("inf")
        for qn in query_ents:
            if not ug.has_node(qn):
                continue
            try:
                best = min(best, nx.shortest_path_length(ug, qn, node))
            except nx.NetworkXNoPath:
                continue
        return 1.0 / (1.0 + best) if best != float("inf") else 0.0

    # ----- citation validation ---------------------------------------------------

    def is_known_citation(self, kind: str, idval: str) -> bool:
        kind = kind.lower()
        if kind == "section":
            return self.section(idval) is not None
        if kind in ("figure", "table"):
            return self.figure(f"{kind.title()} {idval.upper()}") is not None
        if kind in ("signcode", "sign"):
            return self.sign(idval) is not None
        return False
