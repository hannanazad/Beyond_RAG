"""The VINE graph as the pipeline's graph.

The retriever, the question router and the cross-reference verifier all call a
small set of graph methods (`sections_cited_by`, `chunks_for_section`,
`note_chunks_for`, `chunks_for_paragraph`, `query_entities`, ...). Until now
they were answered by the old GEMS-RAG graph (`graph.gpickle`, 12,115 nodes),
built from chunk-level metadata. This class answers the SAME methods from the
VINE graph (`vine_data/graph_cache.pkl`, ~19,700 nodes), which was built by
reading the manual sentence by sentence, with its figures and tables:

  cross-references   every "Section X", "Sections X and Y", "Sections X
                     through Y", "Paragraph N of Section X", and the
                     references inside list lead-ins
  exceptions         EXCEPTS links between the rule and the paragraph that
                     relaxes it
  notes              the notes printed with each figure and table
  tables             one node per printed row, each linked to the notes that
                     apply to it where the manual prints the note's mark
  figures            what each figure shows (the figure reading)

so `pipeline.kg` is now this graph, for the RAG baseline and for VINE alike
(the draft: one shared graph and retrieval backbone).

The interface is the old one, method for method, so no caller changes. `g` is
a networkx MultiDiGraph carrying the node attributes callers read directly
(chunk content_type and ordinal, figure image paths, sign-code names).

Inputs, all derived from the manual:
  graph_cache.pkl   (N, E, chunks) from graph_links.build + graph_enrich.enrich
  figures.jsonl     figure crops: image paths, pages, sheets, depicted signs
  sign_codes.json   sign names and categories read from the manual (optional)
  vine_items.jsonl  the table-row and figure-reading items in the vector store
                    (optional; built from the graph when absent)
"""
from __future__ import annotations

import json
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import networkx as nx

_MAX_SIBLING_ITEMS = 24
_DEFINED_TERM_RE = re.compile(
    r"^(?:\d{1,3}\.\s*)?([A-Z][A-Za-z0-9 ,()/&'\-]{2,60}?)\s*[‐-―-]{1,2}\s*[a-z(]")
# Relations followed when measuring how close a chunk is to something the
# question names. Hubs are left out on purpose: every sentence that uses the
# term "speed limit", or measures a height, or every row under "Freeway",
# would otherwise sit two steps from every other one.
_PROXIMITY_RELS = {"REFERS_TO", "EXCEPTS", "ITEM_OF", "NOTE_OF", "HAS_READING",
                   "ROW_OF", "HAS_ROW", "DEFINED_IN", "LISTED_IN", "PART_OF",
                   "has_sentence", "contains", "item_of", "depicts"}
_SECTION_ID = re.compile(r"^\d{1,2}[A-Z]\.\d{2}$")


def _chunk_of(node_id: str) -> Optional[str]:
    """sent:<chunk>#n and lead:<chunk> -> <chunk>."""
    if node_id.startswith("sent:"):
        return node_id[5:].split("#", 1)[0]
    if node_id.startswith("lead:"):
        return node_id[5:]
    if node_id.startswith("chunk:"):
        return node_id[6:]
    return None


def _base_figure(node_id: str) -> str:
    """figure:Table 2C-4#A (a chart of the table) -> figure:Table 2C-4."""
    return node_id.split("#", 1)[0] if node_id.startswith("figure:") else node_id


class VineKG:
    def __init__(self, graph_path, figures_path=None, sign_codes_path=None,
                 items_path=None, tables_path=None, table_rows_in_closure: int = 15) -> None:
        N, E, C = pickle.load(open(graph_path, "rb"))
        self.N, self.E = N, E
        self.chunks: List[Dict[str, Any]] = [c if isinstance(c, dict) else vars(c) for c in C]
        self.table_rows_in_closure = int(table_rows_in_closure)
        g = nx.MultiDiGraph()
        self.g = g

        # ---- chunks and sections, in manual order -------------------------
        self._chunk_order: Dict[str, int] = {}
        self._by_section: Dict[str, List[str]] = defaultdict(list)
        self._by_parent: Dict[str, List[str]] = defaultdict(list)
        self._chunk: Dict[str, Dict[str, Any]] = {}
        self._notes_of: Dict[str, List[str]] = defaultdict(list)    # figure id -> its note chunks
        for i, c in enumerate(self.chunks):
            if c.get("source") in ("figure_note", "table_note") and c.get("parent_id"):
                self._notes_of[c["parent_id"]].append(c["chunk_id"])
            cid, sec = c["chunk_id"], c.get("section_id") or ""
            self._chunk_order[cid] = i
            self._chunk[cid] = c
            self._by_section[sec].append(cid)
            if c.get("parent_id") and c.get("source") == "list_item":
                self._by_parent[c["parent_id"]].append(cid)
            snode = f"section:{sec}"
            if not g.has_node(snode):
                g.add_node(snode, kind="Section", id=sec, title=c.get("section_title"),
                           chapter=c.get("chapter"), part=c.get("part"),
                           page_pdf=c.get("page_pdf"), page_printed=c.get("page_printed"),
                           unresolved=False, resolved_section=True, cites_any_figure=False)
            g.add_node(f"chunk:{cid}", kind="Chunk", id=cid, section=sec,
                       content_type=c.get("content_type"), ordinal=c.get("ordinal"),
                       page_pdf=c.get("page_pdf"), page_printed=c.get("page_printed"),
                       source=c.get("source"), parent_id=c.get("parent_id"), item=c.get("item"))
            g.add_edge(snode, f"chunk:{cid}", label="contains")
        for sec in self._by_section:
            self._by_section[sec].sort(key=lambda x: (int(self._chunk[x].get("ordinal") or 0),
                                                      self._chunk_order[x]))

        # ---- the VINE graph itself -----------------------------------------
        for nid, v in N.items():
            if nid.startswith("section:") and g.has_node(nid):
                g.nodes[nid]["vine_text"] = v.text
                continue
            if nid.startswith("chunk:") and g.has_node(nid):
                continue
            g.add_node(nid, kind=v.kind, section=v.section, text=v.text,
                       authority=v.authority, pieces=tuple(v.pieces or ()))
            cid = _chunk_of(nid)
            if cid and f"chunk:{cid}" in g:
                g.add_edge(f"chunk:{cid}", nid, label="has_sentence")
        for e in E:
            if e.src in g and e.dst in g:
                g.add_edge(e.src, e.dst, label=e.rel, why=e.why)

        # ---- figures: attributes callers read, from figures.jsonl ----------
        self._figures: Dict[str, str] = {}
        recs: Dict[str, List[dict]] = defaultdict(list)
        if figures_path and Path(figures_path).exists():
            for l in open(figures_path):
                if l.strip():
                    f = json.loads(l)
                    recs[f["figure_id"]].append(f)
        cite_counts: Dict[str, Counter] = defaultdict(Counter)
        for e in E:
            if e.rel == "REFERS_TO" and e.dst.startswith("figure:"):
                sec = N[e.src].section if e.src in N else ""
                if sec:
                    cite_counts[_base_figure(e.dst)][sec] += 1
        for nid, v in N.items():
            if v.kind not in ("FIGURE", "TABLE"):
                continue
            fid = nid.split(":", 1)[1]                     # "Figure 2B-14"
            rs = sorted(recs.get(fid, []), key=lambda r: ((r.get("sheet") or 1), r.get("page_pdf") or 0))
            head = rs[0] if rs else {}
            canonical = fid.split(" ", 1)[1] if " " in fid else fid
            m_chap = re.match(r"(\d+[A-Z]?)", canonical)
            chapter = head.get("chapter") or (m_chap.group(1) if m_chap else "")
            secs = cite_counts.get(nid, Counter())
            in_chap = {s: n for s, n in secs.items() if chapter and s.upper().startswith(chapter.upper() + ".")}
            pool = in_chap or dict(secs)
            anchor = max(pool.items(), key=lambda kv: (kv[1], -self._sec_rank(kv[0])))[0] if pool else ""
            if not anchor:
                note_secs = [self._chunk[c].get("section_id") for c in self._notes_by_parent(fid)]
                anchor = next((s for s in note_secs if s), "")
            depicted = set(head.get("sign_codes_depicted") or ())
            g.nodes[nid].update(
                kind="Table" if v.kind == "TABLE" else "Figure", id=fid, canonical_id=canonical,
                chapter=chapter, anchor_section=anchor,
                page_pdf=head.get("page_pdf"), page_printed=head.get("page_printed"),
                caption=head.get("caption") or v.text, title=head.get("title") or v.text,
                image_path=head.get("image_path", ""),
                image_paths=tuple(r.get("image_path", "") for r in rs) or ("",),
                n_sheets=max(1, len(rs)), sign_codes=tuple(sorted(depicted)),
                unresolved=False)
            self._figures[fid.upper()] = nid
            self._figures.setdefault(canonical.upper(), nid)
            for sc in depicted:
                for sn in (f"signcode:{sc}", f"signcode:{sc.upper()}"):
                    if sn in g:
                        g.add_edge(nid, sn, label="depicts")
                        break
            if anchor:
                g.add_edge(nid, f"section:{anchor}", label="anchored_in")
            for sec in secs:
                g.add_edge(nid, f"section:{sec}", label="cited_in")
                if f"section:{sec}" in g:
                    g.nodes[f"section:{sec}"]["cites_any_figure"] = True

        # ---- sign codes: lookups by code, names for "STOP sign" -> R1-1 ----
        names: Dict[str, Dict[str, Any]] = {}
        if sign_codes_path and Path(sign_codes_path).exists():
            names = json.load(open(sign_codes_path))
        self._signs: Dict[str, str] = {}
        for nid, v in N.items():
            if v.kind != "SIGNCODE":
                continue
            code = nid.split(":", 1)[1]
            entry = names.get(code.upper()) or names.get(code) or {}
            name = entry.get("canonical_name") or next(
                (str(p).split("=", 1)[1] for p in (v.pieces or ()) if str(p).startswith("name=")), "")
            g.nodes[nid].update(kind="SignCode", id=code.upper(), canonical_name=name,
                                category=entry.get("category", ""), unresolved=False)
            self._signs.setdefault(code.upper(), nid)

        # ---- items in the vector store: table rows and figure readings ------
        self._items_of: Dict[str, List[str]] = defaultdict(list)   # graph node -> item chunk ids
        self._table_rows: Dict[str, int] = Counter()
        for nid, v in N.items():
            if v.kind == "TABLE_ROW":
                tab = next((str(p).split("=", 1)[1] for p in (v.pieces or ()) if str(p).startswith("table=")), "")
                self._table_rows[f"figure:{tab}"] += 1
        items = self._load_items(graph_path, items_path, tables_path)
        for it in items:
            iid, node = it["chunk_id"], it.get("graph_node", "")
            g.add_node(f"chunk:{iid}", kind="Chunk", id=iid, section=it.get("section_id", ""),
                       content_type=it.get("content_type"), ordinal=999, source="vine_graph")
            if node in g:
                g.add_edge(f"chunk:{iid}", node, label="item_of")
            self._items_of[node].append(iid)

        # ---- definitions (as the old graph computed them, from the text) ---
        terms: Dict[str, str] = {}
        for c in self.chunks:
            sec = c.get("section_id") or ""
            if not (sec.endswith(".02") or sec.endswith(".03")):
                continue
            m = _DEFINED_TERM_RE.match((c.get("text") or "")[:120])
            if m:
                terms.setdefault(m.group(1).strip().lower(), c["chunk_id"])
        g.graph["defined_terms"] = terms
        g.graph["_terms_by_length"] = sorted(terms, key=len, reverse=True)
        g.graph["source"] = str(graph_path)
        g.graph["build_stats"] = {"n_nodes": g.number_of_nodes(), "n_edges": g.number_of_edges(),
                                  "vine_nodes": len(N), "vine_edges": len(E), "items": len(items)}

        # ---- the graph proximity is measured on ----------------------------
        self._prox = nx.Graph()
        for u, v, d in g.edges(data=True):
            if d.get("label") in _PROXIMITY_RELS:
                self._prox.add_edge(u, v)
        self._dist_cache: Dict[str, Dict[str, int]] = {}

    # ------------------------------------------------------------------ helpers
    def _sec_rank(self, sec: str) -> int:
        ids = self._by_section.get(sec)
        return self._chunk_order.get(ids[0], 10 ** 6) if ids else 10 ** 6

    def _notes_by_parent(self, fid: str) -> List[str]:
        return list(self._notes_of.get(fid, []))

    @staticmethod
    def _load_items(graph_path, items_path, tables_path) -> List[Dict[str, Any]]:
        if items_path and Path(items_path).exists():
            return [json.loads(l) for l in open(items_path) if l.strip()]
        try:
            from .vine.vector_items import build_items
            return build_items(graph_path, tables_path)
        except Exception:                                   # noqa: BLE001
            return []

    def _chunk_sentences(self, cid: str) -> List[str]:
        node = f"chunk:{cid}"
        if node not in self.g:
            return []
        return [v for _u, v, d in self.g.out_edges(node, data=True) if d.get("label") == "has_sentence"]

    def _section_sentences(self, sec: str) -> List[str]:
        out: List[str] = []
        for cid in self._by_section.get(sec, []):
            out.extend(self._chunk_sentences(cid))
        return out

    # ------------------------------------------------------------------ lookups
    def sign(self, code: str) -> Optional[str]:
        return self._signs.get(str(code).upper())

    def figure(self, fid: str) -> Optional[str]:
        f = str(fid).strip()
        if f.lower().startswith("figure:"):
            f = f.split(":", 1)[1]
        return self._figures.get(f.upper())

    def section(self, sec_id: str) -> Optional[str]:
        n = f"section:{sec_id}"
        return n if n in self.g and self._by_section.get(sec_id) else None

    # ---------------------------------------------------------------- traversal
    def neighbors(self, node: str, n_hops: int = 1) -> Set[str]:
        if node not in self.g:
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
        """Figures and tables this chunk names, or the one it is a note of."""
        out: List[str] = []
        c = self._chunk.get(chunk_id)
        if c and c.get("source") in ("figure_note", "table_note") and c.get("parent_id"):
            if self.figure(c["parent_id"]):
                out.append(self.g.nodes[self.figure(c["parent_id"])]["id"])
        # A list item's figure is often named once, in the lead-in it shares
        # with its siblings ("... as follows (see Figure 2C-6):").
        sents = self._chunk_sentences(chunk_id)
        leads = [v for s in sents for _u, v, d in self.g.out_edges(s, data=True)
                 if d.get("label") == "ITEM_OF" and v.startswith("lead:")]
        for s in sents + leads:
            for _u, v, d in self.g.out_edges(s, data=True):
                if d.get("label") == "REFERS_TO" and v.startswith("figure:"):
                    b = _base_figure(v)
                    if b in self.g and self.g.nodes[b].get("id"):
                        out.append(self.g.nodes[b]["id"])
        node = f"chunk:{chunk_id}"
        if node in self.g:                                  # an item: its own figure or table
            for _u, v, d in self.g.out_edges(node, data=True):
                if d.get("label") == "item_of":
                    for _a, b, dd in self.g.out_edges(v, data=True):
                        if dd.get("label") == "ROW_OF" and b in self.g and self.g.nodes[b].get("id"):
                            out.append(self.g.nodes[b]["id"])
                    for a, _b, dd in self.g.in_edges(v, data=True):
                        if dd.get("label") == "HAS_READING" and self.g.nodes[a].get("id"):
                            out.append(self.g.nodes[a]["id"])
        return list(dict.fromkeys(out))

    def note_chunks_for(self, figure_or_table_id: str) -> List[str]:
        """Chunk ids of the notes printed with a figure or table."""
        node = self.figure(figure_or_table_id)
        if not node:
            return []
        out: List[str] = []
        heads = [node] + [u for u, _v, d in self.g.in_edges(node, data=True) if d.get("label") == "PART_OF"]
        for h in heads:
            for _u, v, d in self.g.out_edges(h, data=True):
                if d.get("label") == "NOTE_OF":
                    cid = _chunk_of(v)
                    if cid and cid in self._chunk:
                        out.append(cid)
        out.extend(self._notes_by_parent(self.g.nodes[node]["id"]))
        return sorted(dict.fromkeys(out), key=lambda c: self._chunk_order.get(c, 10 ** 6))

    def items_for_figure(self, figure_or_table_id: str) -> List[str]:
        """The vector-store items of a figure or table a provision names: its
        reading (what the figure shows), and -- when the table is small enough
        to read whole -- its rows. A provision citing Table 2C-4 is answered by
        Table 2C-4; one citing the 200-row Table 2B-1 needs one row, which the
        search finds by the sign's name."""
        node = self.figure(figure_or_table_id)
        if not node:
            return []
        out: List[str] = []
        for _u, v, d in self.g.out_edges(node, data=True):
            if d.get("label") == "HAS_READING":
                out.extend(self._items_of.get(v, []))
        if 0 < self._table_rows.get(node, 0) <= self.table_rows_in_closure:
            for u, _v, d in self.g.in_edges(node, data=True):
                if d.get("label") == "ROW_OF":
                    out.extend(self._items_of.get(u, []))
        return list(dict.fromkeys(out))

    def figures_for_section(self, section_id: str) -> List[str]:
        node = f"section:{section_id}"
        if node not in self.g:
            return []
        ranked = []
        for u, _v, d in self.g.in_edges(node, data=True):
            if not u.startswith("figure:"):
                continue
            if d.get("label") == "anchored_in":
                ranked.append((0, self.g.nodes[u].get("id")))
            elif d.get("label") == "cited_in":
                ranked.append((1, self.g.nodes[u].get("id")))
        ranked.sort()
        return list(dict.fromkeys(fid for _r, fid in ranked if fid))

    def chunks_for_section(self, section_id: str) -> List[str]:
        return list(self._by_section.get(section_id, []))

    def defined_terms(self) -> Dict[str, str]:
        return self.g.graph.get("defined_terms", {})

    def definition_chunk(self, term: str) -> Optional[str]:
        return self.defined_terms().get(str(term).strip().lower())

    def terms_defined_in(self, text: str, min_len: int = 6) -> List[str]:
        low = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
        out = []
        for term in self.g.graph.get("_terms_by_length", []):
            if len(term) < min_len:
                break
            if f" {term} " in low or f" {term}s " in low or f" {term}," in low:
                out.append(term)
        return out

    def notes_for_section(self, section_id: str) -> List[str]:
        out: List[str] = []
        for fid in self.figures_for_section(section_id):
            out.extend(self.note_chunks_for(fid))
        return list(dict.fromkeys(out))

    def paragraph_items(self, chunk_id: str) -> List[str]:
        c = self._chunk.get(chunk_id)
        if not c or c.get("source") != "list_item" or not c.get("parent_id"):
            return []
        out = [x for x in self._by_parent.get(c["parent_id"], []) if x != chunk_id]
        return [] if len(out) > _MAX_SIBLING_ITEMS else out

    def chunks_for_paragraph(self, section_id: str, ordinal: int) -> List[str]:
        try:
            o = int(ordinal)
        except (TypeError, ValueError):
            return []
        # A figure or table note carries its note number as an ordinal and sits
        # in the section that prints it; it is not that section's paragraph.
        return sorted(cid for cid in self._by_section.get(section_id, [])
                      if int(self._chunk[cid].get("ordinal") or -1) == o
                      and self._chunk[cid].get("source") not in ("figure_note", "table_note"))

    def chunk_for_paragraph(self, section_id: str, ordinal: int) -> Optional[str]:
        ids = self.chunks_for_paragraph(section_id, ordinal)
        if not ids:
            return None
        parents = {self._chunk[i].get("parent_id") for i in ids if self._chunk[i].get("source") == "list_item"}
        return next(iter(parents)) if len(parents) == 1 and len(ids) > 1 else ids[0]

    def resolves(self, kind: str, ident: str) -> bool:
        if kind == "section":
            return self.section(ident) is not None
        return bool(self.figure(ident))

    def sections_cited_by(self, section_id: str) -> List[str]:
        """Sections this one points to: "see Section X", "Sections X and Y",
        "Sections X through Y", "Paragraph N of Section X", and the paragraph a
        named exception sits in."""
        out: List[str] = []
        for s in self._section_sentences(section_id):
            for _u, v, d in self.g.out_edges(s, data=True):
                if d.get("label") not in ("REFERS_TO", "EXCEPTS"):
                    continue
                if v.startswith("section:"):
                    sec = v.split(":", 1)[1]
                elif v.startswith(("sent:", "lead:")):
                    sec = self.g.nodes[v].get("section", "")
                else:
                    continue
                if sec and sec != section_id and _SECTION_ID.match(sec) and self._by_section.get(sec):
                    out.append(sec)
        return list(dict.fromkeys(out))

    def references_of_chunk(self, chunk_id: str) -> Dict[str, List[str]]:
        """What a chunk names, read from the graph, in the payload's own form
        (bare ids: "2B-1", "4K.03"). Used to fill the vector-store payload, so
        the parser's "cites" line and the closure's by-name notes see every
        reference the graph found, including the plural and lead-in ones."""
        figs, tabs = [], []
        for fid in self.figures_for_chunk(chunk_id):
            kind, _, ident = fid.partition(" ")
            (tabs if kind == "Table" else figs).append(ident)
        own = (self._chunk.get(chunk_id) or {}).get("section_id", "")
        sents = self._chunk_sentences(chunk_id)
        leads = [v for s in sents for _u, v, d in self.g.out_edges(s, data=True)
                 if d.get("label") == "ITEM_OF" and v.startswith("lead:")]
        secs = []
        for s in sents + leads:
            for _u, v, d in self.g.out_edges(s, data=True):
                if d.get("label") not in ("REFERS_TO", "EXCEPTS"):
                    continue
                sec = (v.split(":", 1)[1] if v.startswith("section:") else
                       self.g.nodes[v].get("section", "") if v.startswith(("sent:", "lead:")) else "")
                if sec and sec != own and _SECTION_ID.match(sec):
                    secs.append(sec)
        return {"figure_refs": list(dict.fromkeys(figs)), "table_refs": list(dict.fromkeys(tabs)),
                "section_refs": list(dict.fromkeys(secs))}

    def section_cites_figures(self, section_id: str) -> bool:
        n = f"section:{section_id}"
        return bool(n in self.g and self.g.nodes[n].get("cites_any_figure"))

    def chunks_for_signcode(self, code: str) -> List[str]:
        node = self.sign(code)
        if not node:
            return []
        out = [_chunk_of(u) for u, _v, d in self.g.in_edges(node, data=True)
               if d.get("label") == "REFERS_TO" and _chunk_of(u)]
        return list(dict.fromkeys(c for c in out if c in self._chunk))

    # ---------------------------------------------------------------- query-time
    def query_entities(self, query: str) -> Set[str]:
        ents: Set[str] = set()
        q = (query or "").translate({0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-"})
        for m in re.finditer(r"\b(Figure|Table)\s+([0-9A-Z]+-[0-9]+[A-Za-z0-9]*)\b", q, re.IGNORECASE):
            n = self.figure(f"{m.group(1).title()} {m.group(2).upper()}")
            if n:
                ents.add(n)
        for m in re.finditer(r"\b(?:Section\s+)?([0-9]+[A-Z]\.[0-9]+)\b", q):
            n = self.section(m.group(1))
            if n:
                ents.add(n)
        for m in re.finditer(r"\b([RWDIMOE][A-Z]?\d{1,3}(?:-\d{1,3})?[a-zA-Z]?P?)\b", q):
            n = self.sign(m.group(1))
            if n:
                ents.add(n)
        return ents

    def _distances(self, ent: str) -> Dict[str, int]:
        if ent not in self._dist_cache:
            self._dist_cache[ent] = (nx.single_source_shortest_path_length(self._prox, ent, cutoff=6)
                                     if ent in self._prox else {})
            if len(self._dist_cache) > 512:
                self._dist_cache.pop(next(iter(self._dist_cache)))
        return self._dist_cache[ent]

    def proximity_score(self, query_ents: Set[str], chunk_id: str) -> float:
        if not query_ents:
            return 0.0
        node = f"chunk:{chunk_id}"
        best = min((self._distances(q).get(node, 10 ** 6) for q in query_ents), default=10 ** 6)
        return 1.0 / (1.0 + best) if best < 10 ** 6 else 0.0

    def is_known_citation(self, kind: str, idval: str) -> bool:
        kind = kind.lower()
        if kind == "section":
            return self.section(idval) is not None
        if kind in ("figure", "table"):
            return self.figure(f"{kind.title()} {str(idval).upper()}") is not None
        if kind in ("signcode", "sign"):
            return self.sign(idval) is not None
        return False
