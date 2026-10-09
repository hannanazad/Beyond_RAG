"""What the checker sees of the manual, and how it looks further -- S3.3, Eq 5.

WHY
---
The checker used to see each piece of evidence as `[id] (2B.03 Standard)` and
its text. No section title, no paragraph number, and nothing about what the
piece points to. A traffic engineer never reads a provision that way: the
manual tells the reader where a rule's exceptions are ("Except as provided in
Section 2A.07", "Except as provided in Paragraphs 5 and 6 of this Section"),
that Option statements may modify a Standard in the same section (1C.01), and
that a table's notes go with the table (1A.04, Paragraph 5).

S3.3: "All verification remains grounded in the persistent knowledge graph",
and "Nq in turn issues obligation-specific requests back to the graph as
execution proceeds." This file is that, for the text and image checkers:

1. LABELS. Every piece is shown with where it sits (section number and title,
   paragraph, item, printed heading) and the links it carries in the graph:
   the exceptions it names, what else it refers to, the Option paragraphs of
   its section (for a Standard or Guidance), and the terms it uses that the
   manual defines. Only links that go OUT of the piece: the manual names a
   rule's exceptions in the rule itself.

2. LOOKUPS. Read-only tools the checker can call while it decides: open a
   section, open a paragraph with its neighbours, open a table or figure
   (notes, rows, what the figure shows), define a term, search the manual.
   Every call is logged, capped in number and in size. Nothing here writes to
   the graph or the store, and no model is called here. Search results are
   saved by query (when a folder is given), so a re-run sees the same pieces
   even on a different GPU.

3. NAMED EXCEPTIONS. The paragraphs a provision names as its exceptions, by
   id, so the checker can be handed them (`named_exception_ids`). A reference
   in parentheses ("(see definition in Section 1C.02)") is a reference, not an
   exception. A whole section named as an exception is handed over whole only
   when it is short; a long one is named, for the checker to open.

The structure of a piece (its kind, paragraph, heading, whether it is a note)
is always read from the graph's own record of it, never from a copy that an
earlier step may have re-tagged.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["ManualView", "Lookups", "Links", "TOOL_SPECS", "DEFAULT_MAX_LOOKUPS",
           "tools_digest"]

DEFAULT_MAX_LOOKUPS = 12
_SECTION_ID = re.compile(r"\b(\d{1,2}[A-Z]\.\d{2})\b")
_SECTION_ONLY = re.compile(r"^(?:\d{1,2}[A-Z]\.\d{2}|A\d)$")      # A1, A2: the appendix
_SECTION_RANGE = re.compile(r"\b(\d{1,2}[A-Z])\.(\d{2})\s+(?:through|to|-)\s+(\d{1,2}[A-Z])\.(\d{2})\b")
# The clause of a sentence that states an exception: from "except" or "unless"
# to the end of the clause. A dot inside a section number ("2A.07") and a comma
# inside a list of numbers ("Paragraphs 3, 5, and 6") do not end it.
_EXCEPTION_CLAUSE = re.compile(
    r"\b(?:except|unless)\b(?:[^.;:,]|\.(?=\d)|,(?=\s*(?:\d|and\b|or\b|through\b)))*", re.I)
_PARENS = re.compile(r"\([^()]*\)")
# An exception said to exist "otherwise", e.g. "except as otherwise provided in
# this Manual", "unless otherwise provided", "provided otherwise elsewhere".
_OTHERWISE = re.compile(
    r"\botherwise\s+(?:\w+\s+){0,2}?(?:provided|specified|designated|stated|noted|indicated|"
    r"prescribed|allowed|permitted|required|shown|described)\b|"
    r"\b(?:provided|specified|designated|stated|noted|indicated|prescribed|allowed|permitted|"
    r"required|shown|described)\s+otherwise\b", re.I)
# one clause can hold two exceptions: "unless otherwise provided in this Manual
# ... or as provided in Paragraph 19 of this Section"
_CLAUSE_PARTS = re.compile(r",?\s+(?:or|and)\s+(?=(?:as|unless|except|where|in)\b)", re.I)
_NAMES_A_PLACE = re.compile(
    r"\b(?:Sections?|Paragraphs?|Chapters?|Tables?|Figures?|Parts?)\s+[0-9A-Z]|"
    r"\b(?:this|that)\s+(?:Section|Chapter|Paragraph|Part|Table|Figure)\b", re.I)
_NOT_A_PROVISION = re.compile(r"\b(?:engineering|study|judgment|agency|jurisdiction|law|statute|"
                              r"ordinance|order)\b", re.I)
_PARA_SAME = re.compile(
    r"\bparagraphs?\s+((?:\d+)(?:\s*(?:,|,?\s*and|,?\s*or|through|-)\s*\d+)*)"
    r"\s+of\s+this\s+section", re.I)
_PARA_OTHER = re.compile(
    r"\bparagraphs?\s+((?:\d+)(?:\s*(?:,|,?\s*and|,?\s*or|through|-)\s*\d+)*)"
    r"\s+(?:of|in)\s+section\s+(\d+[A-Z]\.\d+)", re.I)
_NOTE_SOURCES = ("figure_note", "table_note")
_NORMATIVE = ("Standard", "Guidance", "Option")
# what the graph's record decides about a piece; a copy's re-tagging never wins
_STRUCTURE = ("source", "ordinal", "content_type", "parent_id", "item", "section_id",
              "section_title", "lead_in", "authority_inferred", "text")
_MAX_SECTION_PARAGRAPHS = 10       # per open_section call
_MAX_TABLE_ROWS = 20               # per open_table_or_figure call
_MAX_SEARCH_HITS = 6
_MAX_RESULT_CHARS = 12000          # per lookup result (about 3,000 tokens)
_SMALL_SECTION = 8                 # a section named as an exception is handed over whole up to this


def _numbers(spec: str) -> List[int]:
    """"5 and 6" -> [5, 6]; "3 through 5" -> [3, 4, 5]."""
    out: List[int] = []
    for a, b in re.findall(r"(\d+)\s*(?:through|-)\s*(\d+)", spec):
        if int(a) <= int(b) <= int(a) + 12:
            out.extend(range(int(a), int(b) + 1))
    out.extend(int(n) for n in re.findall(r"\d+", spec))
    return list(dict.fromkeys(out))


def _clean_ref(word: str, ident: str) -> str:
    ident = str(ident).strip()
    return ident if ident.lower().startswith(("table", "figure")) else f"{word} {ident}"


@dataclass
class Links:
    """What one piece of the manual points to (only links going out of it)."""
    exceptions: List[str] = field(default_factory=list)        # "Section 2A.07", "Section 2B.03 paragraph 5"
    exception_ids: List[str] = field(default_factory=list)     # chunk ids of those, when resolvable
    long_exception_sections: List[str] = field(default_factory=list)   # named whole, too long to hand over
    refers_to: List[str] = field(default_factory=list)          # sections, paragraphs, tables, figures
    options_here: List[int] = field(default_factory=list)       # Option paragraphs of the same section
    terms: List[str] = field(default_factory=list)              # used here and defined by the manual
    open_exception: str = ""                                    # the clause, when no place is named
    notes_of: List[str] = field(default_factory=list)           # tables/figures named here that have notes

    def line(self) -> str:
        parts = []
        if self.exceptions:
            parts.append("exceptions it names: " + ", ".join(self.exceptions))
        if self.open_exception:
            parts.append(f'says "{self.open_exception}" without naming where')
        if self.refers_to:
            parts.append("refers to: " + ", ".join(self.refers_to))
        if self.notes_of:
            parts.append("notes printed with: " + ", ".join(self.notes_of))
        if self.options_here:
            parts.append("Option paragraphs in this section: "
                         + ", ".join(str(n) for n in self.options_here))
        if self.terms:
            parts.append("terms the manual defines: " + ", ".join(f'"{t}"' for t in self.terms))
        return ("  links: " + " | ".join(parts)) if parts else ""


class ManualView:
    """Read-only access to the manual through the graph and the vector store.

    `kg` is the VINE graph (`mrag.kg_vine.VineKG`). `store` fetches payloads
    by id (`fetch_chunks_by_ids`) for the pieces the graph keeps no record of
    (table rows, figure descriptions). `search` is optional: a function
    `query -> [payload, ...]`.
    """

    def __init__(self, kg, store=None, collection: Optional[str] = None,
                 search: Optional[Callable[[str], List[Dict[str, Any]]]] = None) -> None:
        self.kg = kg
        self.store = store
        self.collection = collection
        self.search = search
        self._payloads: Dict[str, Dict[str, Any]] = {}
        self._links: Dict[str, Links] = {}

    @classmethod
    def from_retriever(cls, retriever, cache_dir: Optional[str] = None) -> Optional["ManualView"]:
        kg = getattr(retriever, "kg", None)
        if kg is None or not hasattr(kg, "_chunk_sentences"):
            return None                       # labels and lookups need the VINE graph
        try:
            from mrag.config import CFG
            collection = CFG.coll_chunks
        except Exception:                     # noqa: BLE001
            collection = None
        view = cls(kg, getattr(retriever, "store", None), collection)
        view.search = _make_search(retriever, collection, view, cache_dir)
        return view

    # ------------------------------------------------------------------ payloads
    def clean(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """The piece with its structure taken from the graph's own record."""
        cid = str(item.get("chunk_id") or "")
        rec = getattr(self.kg, "_chunk", {}).get(cid)
        if not rec:
            return dict(item)
        out = dict(item)
        for k in _STRUCTURE:
            if k in rec:
                out[k] = rec[k]
        for k in ("figure_refs", "table_refs", "section_refs"):
            out[k] = list(dict.fromkeys(list(item.get(k) or []) + list(rec.get(k) or [])))
        return out

    def remember(self, items: Sequence[Dict[str, Any]]) -> None:
        for it in items or ():
            cid = str(it.get("chunk_id") or "")
            if cid and cid not in self._payloads:
                self._payloads[cid] = self.clean(it)

    def payloads(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        """Payloads for these ids, in this order; unknown ids are skipped."""
        want = [i for i in dict.fromkeys(ids) if i]
        missing = [i for i in want if i not in self._payloads]
        if missing and self.store is not None and self.collection:
            try:
                for h in self.store.fetch_chunks_by_ids(self.collection, missing):
                    p = h.get("payload") or {}
                    if p.get("chunk_id") and p["chunk_id"] not in self._payloads:
                        self._payloads[p["chunk_id"]] = self.clean(p)
            except Exception:                 # noqa: BLE001
                pass
        for i in want:
            if i not in self._payloads and i in getattr(self.kg, "_chunk", {}):
                self._payloads[i] = dict(self.kg._chunk[i])
        return [self._payloads[i] for i in want if i in self._payloads]

    def section_title(self, sec: str) -> str:
        node = f"section:{sec}"
        g = self.kg.g
        return str(g.nodes[node].get("title") or "") if node in g else ""

    def _record(self, cid: str) -> Dict[str, Any]:
        return getattr(self.kg, "_chunk", {}).get(cid) or self._payloads.get(cid) or {}

    def _sections_between(self, a_ch: str, a_n: str, b_ch: str, b_n: str) -> List[str]:
        """"2F.12 through 2F.16" -> every section of that chapter in between."""
        if a_ch != b_ch:
            return [f"{a_ch}.{a_n}", f"{b_ch}.{b_n}"]
        lo, hi = int(a_n), int(b_n)
        if hi < lo or hi - lo > 30:
            return [f"{a_ch}.{a_n}", f"{b_ch}.{b_n}"]
        return [f"{a_ch}.{n:02d}" for n in range(lo, hi + 1) if self.kg.section(f"{a_ch}.{n:02d}")]

    def _section_ids_in(self, text: str) -> List[str]:
        out: List[str] = []
        for m in _SECTION_RANGE.finditer(text):
            out.extend(self._sections_between(*m.groups()))
        out.extend(_SECTION_ID.findall(_SECTION_RANGE.sub(" ", text)))
        return list(dict.fromkeys(out))

    # --------------------------------------------------------------------- links
    def links(self, item: Dict[str, Any]) -> Links:
        item = self.clean(item)
        cid = str(item.get("chunk_id") or "")
        if cid in self._links:
            return self._links[cid]
        kg, g = self.kg, self.kg.g
        own = str(item.get("section_id") or "")
        kind = str(item.get("content_type") or "")
        text = f"{item.get('lead_in') or ''} {item.get('text') or ''}".strip()
        out = Links()
        exc_refs: List[str] = []
        exc_ids: List[str] = []
        side_refs: List[str] = []                 # references in parentheses inside a clause

        # 1. exceptions the graph read from the text (EXCEPTS: rule -> exception)
        for s in kg._chunk_sentences(cid):
            for _u, v, d in g.out_edges(s, data=True):
                if d.get("label") != "EXCEPTS":
                    continue
                tcid = _chunk_of(v)
                rec = self._record(tcid) if tcid else {}
                if not rec:
                    continue
                sec = str(rec.get("section_id") or "")
                exc_ids.append(tcid)
                if rec.get("ordinal") not in (None, ""):
                    exc_refs.append(f"Section {sec} paragraph {rec.get('ordinal')}")
                else:
                    exc_refs.append(f"Section {sec}")

        # 2. exceptions the text names in an "except ..." / "unless ..." clause.
        #    What is in parentheses ("(see definition in Section 1C.02)") is a
        #    reference, not the exception.
        named_in_clause: List[str] = []
        for full in (m.group(0) for m in _EXCEPTION_CLAUSE.finditer(text)):
            for par in _PARENS.findall(full):
                for sec in self._section_ids_in(par):
                    side_refs.append(f"Section {sec}")
            cl = _PARENS.sub(" ", full)
            for m in _PARA_OTHER.finditer(cl):
                for n in _numbers(m.group(1)):
                    exc_refs.append(f"Section {m.group(2)} paragraph {n}")
                    exc_ids.extend(kg.chunks_for_paragraph(m.group(2), n))
            for m in _PARA_SAME.finditer(cl):
                for n in _numbers(m.group(1)):
                    if own:
                        exc_refs.append(f"Section {own} paragraph {n}")
                        exc_ids.extend(kg.chunks_for_paragraph(own, n))
            for sec in self._section_ids_in(_PARA_OTHER.sub(" ", cl)):
                if sec == own or not kg.section(sec):
                    continue
                exc_refs.append(f"Section {sec}")
                named_in_clause.append(sec)
                normative = self._normative_ids(sec)
                if len(normative) <= _SMALL_SECTION:
                    exc_ids.extend(normative)
                else:
                    out.long_exception_sections.append(sec)
            for m in re.finditer(r"\b(Table|Figure)\s+([0-9A-Z]+-[0-9]+[A-Za-z]?)", cl):
                exc_refs.append(f"{m.group(1)} {m.group(2)}")

            # 3. an exception said to exist "otherwise", with no place named
            for part in _CLAUSE_PARTS.split(cl):
                if (not out.open_exception and _OTHERWISE.search(part)
                        and not _NAMES_A_PLACE.search(part) and not _NOT_A_PROVISION.search(part)):
                    words = " ".join(part.split()).rstrip(" ,").lower()
                    if len(words) > 100:
                        words = words[:100].rsplit(" ", 1)[0] + " ..."
                    out.open_exception = words

        out.exceptions = list(dict.fromkeys(exc_refs))[:12]
        out.exception_ids = [i for i in dict.fromkeys(exc_ids) if i and i != cid]
        out.long_exception_sections = list(dict.fromkeys(out.long_exception_sections))

        # 4. everything else it refers to
        refs: List[str] = []
        for key, word in (("table_refs", "Table"), ("figure_refs", "Figure")):
            for x in item.get(key) or []:
                refs.append(_clean_ref(word, x))
        for s in item.get("section_refs") or []:
            if s != own and s not in named_in_clause:
                refs.append(f"Section {s}")
        refs.extend(r for r in side_refs if r != f"Section {own}")
        body = _EXCEPTION_CLAUSE.sub(" ", text)
        for m2 in _PARA_OTHER.finditer(body):
            for n in _numbers(m2.group(1)):
                refs.append(f"Section {m2.group(2)} paragraph {n}")
        for m2 in _PARA_SAME.finditer(body):
            for n in _numbers(m2.group(1)):
                if own:
                    refs.append(f"Section {own} paragraph {n}")
        parent = str(item.get("parent_id") or "")
        is_note = item.get("source") in _NOTE_SOURCES or kind == "TableRow"
        out.refers_to = [r for r in dict.fromkeys(refs)
                         if r not in out.exceptions
                         and not (is_note and r.lower() == parent.lower())][:10]

        # 5. the notes that go with a table or figure it names (1A.04 P5)
        for r in out.refers_to + out.exceptions:
            if r.lower().startswith(("table", "figure")) and kg.note_chunks_for(r):
                out.notes_of.append(r)
        if kind == "TableRow":
            ref = (item.get("table_refs") or item.get("figure_refs") or [parent])[0]
            ref = _clean_ref("Table", ref)
            if kg.note_chunks_for(ref) and ref not in out.notes_of:
                out.notes_of.append(ref)

        # 6. Option paragraphs of the same section: 1C.01 -- "Standard statements
        #    are sometimes modified by Option statements"; "Option statements
        #    sometimes contain allowable modifications to a Standard or Guidance
        #    statement."
        if kind in ("Standard", "Guidance") and own and item.get("source") not in _NOTE_SOURCES:
            mine = item.get("ordinal")
            opts = []
            for x in kg.chunks_for_section(own):
                r = self._record(x)
                if (r.get("content_type") == "Option" and r.get("source") not in _NOTE_SOURCES
                        and r.get("ordinal") not in (None, "", mine)):
                    opts.append(int(r["ordinal"]))
            out.options_here = sorted(set(opts))[:12]

        # 7. defined terms it uses (the graph's USES_TERM links)
        defined = kg.defined_terms() if hasattr(kg, "defined_terms") else {}
        terms = []
        for s in kg._chunk_sentences(cid):
            for _u, v, d in g.out_edges(s, data=True):
                if d.get("label") == "USES_TERM":
                    t = str(g.nodes[v].get("text") or "").lower()
                    if t and t in defined and defined[t] != cid:
                        terms.append(t)
        out.terms = list(dict.fromkeys(terms))[:5]

        self._links[cid] = out
        return out

    def _normative_ids(self, sec: str) -> List[str]:
        return [x for x in self.kg.chunks_for_section(sec)
                if self._record(x).get("content_type") in _NORMATIVE
                and self._record(x).get("source") not in _NOTE_SOURCES]

    def named_exception_ids(self, items: Sequence[Dict[str, Any]],
                            most: Optional[int] = None) -> List[str]:
        """The chunk ids of the exceptions these pieces name, in order."""
        out: List[str] = []
        for it in items:
            for x in self.links(it).exception_ids:
                if x not in out:
                    out.append(x)
        return out if most is None else out[:most]

    # --------------------------------------------------------------------- label
    def header(self, item: Dict[str, Any]) -> str:
        item = self.clean(item)
        cid = str(item.get("chunk_id") or "")
        kind = str(item.get("content_type") or "")
        sec = str(item.get("section_id") or "")
        title = item.get("section_title") or self.section_title(sec)
        where = f'Section {sec} "{title}"' if title else f"Section {sec}"
        parent = str(item.get("parent_id") or "")
        if kind == "TableRow":
            tab = _clean_ref("Table", (item.get("table_refs") or [parent or "table"])[0])
            return (f"[{cid}] TABLE ROW of {tab} -- printed table content, "
                    f"not a provision; read it with the table's notes")
        if kind == "FigureReading":
            fig = _clean_ref("Figure", (item.get("figure_refs") or [parent or "figure"])[0])
            return (f"[{cid}] FIGURE DESCRIPTION of {fig} -- written by a reader, not the "
                    f"manual's words; it may contain mistakes; not a provision")
        if item.get("source") in _NOTE_SOURCES or (parent.lower().startswith(("table ", "figure "))
                                                   and item.get("source") != "list_item"):
            note = f"note {item.get('item')} to {parent}" if item.get("item") else f"note to {parent}"
            head = f"[{cid}] {note} (printed in {where}) · {kind}"
        elif item.get("source") == "appendix":
            head = f"[{cid}] appendix · {kind}"
        else:
            pos = f" · paragraph {item.get('ordinal')}" if item.get("ordinal") not in (None, "") else ""
            if item.get("item"):
                pos += f", item {item.get('item')}"
            head = f"[{cid}] {where}{pos} · {kind}"
        if kind == "Support":
            head += " (information only)"
        if item.get("authority_inferred"):
            head += " (heading inferred from the verb; no printed heading)"
        return head

    def label(self, item: Dict[str, Any]) -> str:
        item = self.clean(item)
        lead = (item.get("lead_in") or "").strip()
        text = (item.get("text") or "").strip()
        body = f"{lead} {text}".strip() if lead and not text.startswith(lead) else text
        links = self.links(item).line() if item.get("content_type") not in ("FigureReading",) else ""
        return "\n".join(x for x in (self.header(item), body, links) if x)


def _chunk_of(node_id: str) -> Optional[str]:
    if node_id.startswith("sent:"):
        return node_id[5:].split("#", 1)[0]
    if node_id.startswith("lead:"):
        return node_id[5:]
    if node_id.startswith("chunk:"):
        return node_id[6:]
    return None


_ROW_NOTES = re.compile(r"\s*Notes that apply to this row:\s*(.*)$", re.S)


def _row_text(item: Dict[str, Any]) -> str:
    """A table row's text without the table caption it repeats. When the
    table's notes are printed with the rows, the shortened copies of them that
    a row carries are replaced by their marks."""
    text = str(item.get("text") or "")
    m = re.match(r"^\s*Table\s+[0-9A-Z]+-[0-9]+[A-Za-z]?\.[^.]*\.\s*", text)
    text = text[m.end():] if m else text
    n = _ROW_NOTES.search(text) if item.get("_notes_printed") else None
    if n:
        marks = re.findall(r"(?:^|;\s*)(Note\s+\d+|Note|[¹²³⁴⁵⁶⁷⁸⁹⁰]+|[ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ]+|\*+|\d+|[a-z])\b",
                           n.group(1))
        marks = list(dict.fromkeys(x.strip() for x in marks if x.strip()))
        if marks:
            text = (text[:n.start()] + f" Notes that apply to this row (printed above): "
                    f"{', '.join(marks)}.")
    return text


def _make_search(retriever, collection, view: "ManualView",
                 cache_dir: Optional[str] = None) -> Optional[Callable[[str], List[Dict[str, Any]]]]:
    """The pipeline's own hybrid search and reranker, as `query -> payloads`.

    With `cache_dir`, the ids found for each query are saved there, and a query
    asked again is answered from the saved ids: GPU arithmetic can rank two
    close pieces differently on another machine, and the checker's saved
    conversation must replay exactly."""
    text = getattr(retriever, "text", None)
    store = getattr(retriever, "store", None)
    rerank = getattr(retriever, "rerank", None)
    if text is None or store is None or not collection:
        return None
    folder = Path(cache_dir) / "lookup_search" if cache_dir else None
    tag = ""
    try:
        from mrag.config import CFG
        man = Path(CFG.base_dir) / "vine_data" / "text_store_manifest.json"
        tag = (hashlib.sha256(man.read_bytes()).hexdigest()[:12] if man.exists() else "nostore") \
            + "|" + str(getattr(CFG, "reranker_model", ""))
    except Exception:                         # noqa: BLE001
        tag = "unknown"

    def search(query: str) -> List[Dict[str, Any]]:
        path = None
        if folder is not None:
            key = hashlib.sha256(json.dumps({"collection": collection, "query": query,
                                             "k": _MAX_SEARCH_HITS, "store": tag}).encode()).hexdigest()
            path = folder / f"{key}.json"
            if path.exists():
                try:
                    ids = json.loads(path.read_text()).get("ids") or []
                    return view.payloads(ids)
                except (OSError, ValueError):
                    pass
        from mrag.config import CFG
        dense, sparse = text.encode_both([query])
        hits = store.search_chunks_hybrid(collection, dense[0], sparse[0],
                                          top_k=int(getattr(CFG, "top_k_fused", 30)))
        pool = [h.get("payload") or {} for h in hits]
        if rerank is not None and pool:
            docs = [p.get("text", "")[:1500] for p in pool]
            pool = [pool[i] for i, _s in rerank.rank(query, docs, top_k=_MAX_SEARCH_HITS)]
        found = pool[:_MAX_SEARCH_HITS]
        if path is not None:
            try:
                folder.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"query": query, "ids": [p.get("chunk_id") for p in found]}))
                tmp.replace(path)
            except OSError:
                pass
        return found
    return search


# --------------------------------------------------------------------------- #
# The lookups the checker may call
# --------------------------------------------------------------------------- #
TOOL_SPECS: List[Dict[str, Any]] = [
    {"name": "open_section",
     "description": ("Open a section of the manual: its title and its paragraphs in order, "
                     f"up to {_MAX_SECTION_PARAGRAPHS} paragraphs at a time. Use from_paragraph to "
                     "read on."),
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"section": {"type": "string", "description": "e.g. 2B.39"},
                                     "from_paragraph": {"type": "integer",
                                                        "description": "first paragraph to show (default 1)"}},
                      "required": ["section"]}},
    {"name": "open_paragraph",
     "description": ("Open one paragraph of a section (all its list items) with the paragraph "
                     "before and after it. For a paragraph with a very long list, use from_item "
                     "to read on."),
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"section": {"type": "string", "description": "e.g. 2B.03"},
                                     "paragraph": {"type": "integer"},
                                     "from_item": {"type": "integer",
                                                   "description": "first list item to show (default 1)"}},
                      "required": ["section", "paragraph"]}},
    {"name": "open_table_or_figure",
     "description": ("Open a table or figure: its caption, the notes printed with it, "
                     f"its rows ({_MAX_TABLE_ROWS} at a time; use from_row to read on, or "
                     "row_contains to get only the rows that contain some words, such as a "
                     "sign designation) and the written description of what a figure shows."),
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"id": {"type": "string", "description": "e.g. Table 2B-1 or Figure 2C-6"},
                                     "from_row": {"type": "integer",
                                                  "description": "first row to show (default 1)"},
                                     "row_contains": {"type": "string",
                                                      "description": "only rows containing this text, e.g. R2-10"}},
                      "required": ["id"]}},
    {"name": "define_term",
     "description": "The manual's own definition of a term (Section 1C.02 and the other definition sections).",
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"term": {"type": "string"}},
                      "required": ["term"]}},
    {"name": "search_manual",
     "description": (f"Search the whole manual. Returns the {_MAX_SEARCH_HITS} best-matching pieces. "
                     "Use words the manual would use, about the specific device or situation."),
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
]


class Lookups:
    """Runs the checker's lookups, logs them, and remembers what was shown.

    `shown` is every id the checker has seen in this conversation, so a piece
    returned twice is listed by id only, and so a reply may cite anything that
    was actually shown (rule 2 of `model_verifiers`)."""

    def __init__(self, view: ManualView, max_lookups: int = DEFAULT_MAX_LOOKUPS) -> None:
        self.view = view
        self.max_lookups = int(max_lookups)
        self.log: List[Dict[str, Any]] = []
        self.shown: Dict[str, Dict[str, Any]] = {}     # id -> payload, in order of showing

    @property
    def used(self) -> int:
        return len(self.log)

    def show(self, items: Sequence[Dict[str, Any]]) -> None:
        self.view.remember(items)
        for it in items:
            cid = str(it.get("chunk_id") or "")
            if cid and cid not in self.shown:
                self.shown[cid] = self.view.clean(it)

    def specs(self) -> List[Dict[str, Any]]:
        specs = [dict(s) for s in TOOL_SPECS]
        if self.view.search is None:
            specs = [s for s in specs if s["name"] != "search_manual"]
        return specs

    def render(self, items: Sequence[Dict[str, Any]], before: str = "",
               compact_rows: bool = False) -> str:
        """Labelled pieces; a piece already shown is listed by id only. With
        `compact_rows`, table rows are one line each under the table's own
        heading (which already says they are rows)."""
        lines = [before] if before else []
        fresh = []
        for it in items:
            cid = str(it.get("chunk_id") or "")
            if not cid:
                continue
            if cid in self.shown:
                lines.append(f"[{cid}] (already shown above)")
            elif compact_rows and it.get("content_type") == "TableRow":
                lines.append(f"[{cid}] {_row_text(it)}")
                fresh.append(it)
            else:
                lines.append(self.view.label(it))
                fresh.append(it)
        self.show(fresh)
        return "\n\n".join(lines) if lines else "(nothing)"

    # ------------------------------------------------------------------ dispatch
    def run(self, name: str, args: Dict[str, Any]) -> Tuple[str, bool]:
        """(text for the model, is_error). Never raises."""
        args = dict(args or {})
        entry: Dict[str, Any] = {"tool": name, "input": args}
        before = set(self.shown)
        items: List[Dict[str, Any]] = []
        try:
            fn = {"open_section": self._open_section, "open_paragraph": self._open_paragraph,
                  "open_table_or_figure": self._open_table_or_figure,
                  "define_term": self._define_term, "search_manual": self._search}.get(name)
            if fn is None:
                text, items, err = f"There is no tool named {name!r}.", [], True
            else:
                text, items, err = fn(**args)
            body = (self.render(items, text, compact_rows=(name == "open_table_or_figure"))
                    if items else text)
        except TypeError as e:
            body, items, err = f"The input does not fit this tool: {e}", [], True
        except Exception as e:                                # noqa: BLE001
            body, items, err = f"The lookup failed: {e!r}", [], True
        if name in ("open_section", "open_paragraph") and not err:
            entry["section"] = _norm_section(args.get("section"))
        entry["returned"] = [str(i.get("chunk_id")) for i in items if i.get("chunk_id")]
        entry["new"] = [x for x in entry["returned"] if x not in before]
        entry["error"] = bool(err)
        entry["chars"] = len(body)
        self.log.append(entry)
        return body, bool(err)

    # ------------------------------------------------------------------- helpers
    def _fits(self, items: Sequence[Dict[str, Any]], budget: int = _MAX_RESULT_CHARS) -> int:
        """How many of these pieces fit in the size budget (at least one)."""
        used, n = 0, 0
        for it in items:
            cid = str(it.get("chunk_id") or "")
            size = 40 if cid in self.shown else len(self.view.label(it)) + 2
            if n and used + size > budget:
                break
            used += size
            n += 1
        return n

    def _paragraph_pieces(self, sec: str, n: int) -> List[Dict[str, Any]]:
        ids = self.view.kg.chunks_for_paragraph(sec, n)
        recs = self.view.payloads(ids)
        recs.sort(key=lambda r: (_natural(str(r.get("item") or "")), str(r.get("chunk_id"))))
        return recs

    # --------------------------------------------------------------------- tools
    def _open_section(self, section: str, from_paragraph: int = 1):
        sec = _norm_section(section)
        if not _SECTION_ONLY.match(sec) or not self.view.kg.section(sec):
            return f"There is no Section {section!r} in the manual.", [], True
        ids = [x for x in self.view.kg.chunks_for_section(sec)
               if self.view._record(x).get("source") not in _NOTE_SOURCES]
        recs = self.view.payloads(ids)
        recs.sort(key=lambda r: (int(r.get("ordinal") or 0), _natural(str(r.get("item") or "")),
                                 str(r.get("chunk_id"))))
        ordinals = sorted({int(r.get("ordinal") or 0) for r in recs})
        start = max(1, int(from_paragraph or 1))
        keep = [o for o in ordinals if o >= start][:_MAX_SECTION_PARAGRAPHS]
        items = [r for r in recs if int(r.get("ordinal") or 0) in keep]
        n_fit = self._fits(items)
        cut = items[n_fit:]
        items = items[:n_fit]
        head = f'Section {sec} "{self.view.section_title(sec)}": {len(ordinals)} paragraphs'
        if not keep:
            return head + f"; there is no paragraph {start} or later", [], True
        last = int(items[-1].get("ordinal") or 0) if items else start
        head += f"; showing paragraphs {keep[0]} to {last}"
        if cut and int(cut[0].get("ordinal") or 0) == last:
            done = sum(1 for r in items if int(r.get("ordinal") or 0) == last)
            head += (f"; paragraph {last} is long and continues: open_paragraph "
                     f"(section {sec}, paragraph {last}, from_item={done + 1})")
        more = [o for o in ordinals if o > last]
        if more:
            head += f"; paragraphs {more[0]} to {more[-1]} not shown (from_paragraph={more[0]})"
        figs = self.view.kg.figures_for_section(sec)[:8]
        if figs:
            head += "; tables and figures for this section: " + ", ".join(figs)
        return head, items, False

    def _open_paragraph(self, section: str, paragraph: int, from_item: int = 1):
        sec = _norm_section(section)
        if not _SECTION_ONLY.match(sec) or not self.view.kg.section(sec):
            return f"There is no Section {section!r} in the manual.", [], True
        n = int(paragraph)
        main = self._paragraph_pieces(sec, n)
        if not main:
            return f"Section {sec} has no paragraph {n}.", [], True
        start = max(1, int(from_item or 1))
        if start > len(main):
            return (f"Section {sec} paragraph {n} has {len(main)} pieces; there is no item "
                    f"{start}."), [], True
        rest = main[start - 1:]
        n_fit = self._fits(rest)
        shown_main = rest[:n_fit]
        head = f'Section {sec} "{self.view.section_title(sec)}", paragraph {n}'
        if len(main) > 1:
            head += (f" ({len(main)} list items; showing {start} to {start - 1 + len(shown_main)}"
                     + (f"; from_item={start + len(shown_main)} for more" if n_fit < len(rest) else "")
                     + ")")
        before_p, after_p = [], []
        if start == 1 and n_fit == len(rest):
            def size(xs):
                return sum(40 if str(x.get("chunk_id")) in self.shown
                           else len(self.view.label(x)) + 2 for x in xs)
            room = _MAX_RESULT_CHARS - size(shown_main)
            prev = self._paragraph_pieces(sec, n - 1) if n > 1 else []
            nxt = self._paragraph_pieces(sec, n + 1)
            if prev and size(prev) <= room:
                before_p = prev
                room -= size(prev)
            if nxt and size(nxt) <= room:
                after_p = nxt
            head += (" with the paragraph before and after it" if before_p and after_p else
                     " with the paragraph before it" if before_p else
                     " with the paragraph after it" if after_p else "")
        return head, before_p + shown_main + after_p, False

    def _open_table_or_figure(self, id: str, from_row: int = 1,      # noqa: A002
                              row_contains: str = ""):
        kg = self.view.kg
        node = kg.figure(id)
        if not node:
            return f"There is no {id!r} in the manual.", [], True
        attrs = kg.g.nodes[node]
        fid = attrs.get("id") or id
        notes = self.view.payloads(kg.note_chunks_for(fid))
        rows_ids = [x for u, _v, d in kg.g.in_edges(node, data=True) if d.get("label") == "ROW_OF"
                    for x in kg._items_of.get(u, [])]
        reading_ids = [x for _u, v, d in kg.g.out_edges(node, data=True) if d.get("label") == "HAS_READING"
                       for x in kg._items_of.get(v, [])]
        head = f"{fid}: {attrs.get('caption') or attrs.get('title') or ''}".strip()
        if attrs.get("anchor_section"):
            head += f" (Section {attrs.get('anchor_section')})"
        head += f"; {len(notes)} notes"
        start = max(1, int(from_row or 1))
        want = str(row_contains or "").strip().lower()
        if want:
            pool = [r for r in self.view.payloads(rows_ids) if want in str(r.get("text") or "").lower()]
            what = f"{len(rows_ids)} rows, {len(pool)} contain {row_contains!r}"
        else:
            pool = self.view.payloads(rows_ids)
            what = f"{len(rows_ids)} rows"
        rows = pool[start - 1:start - 1 + _MAX_TABLE_ROWS]
        if notes:
            rows = [{**r, "_notes_printed": True} for r in rows]
        if rows:
            # notes always come (1A.04 P5); rows only as many as the size budget allows
            room = _MAX_RESULT_CHARS - sum(len(self.view.label(x)) + 2 for x in notes)
            keep, used = 0, 0
            for r in rows:
                size = 40 if str(r.get("chunk_id")) in self.shown else len(_row_text(r)) + 40
                if keep and used + size > room:
                    break
                used += size
                keep += 1
            rows = rows[:keep]
        if rows_ids:
            if not rows:
                head += f"; {what}; none from row {start} on"
            else:
                last = start - 1 + len(rows)
                head += f"; {what}, showing {start} to {last}"
                if last < len(pool):
                    head += f" (from_row={last + 1} for more" + \
                            (", or row_contains to find the rows you need)" if not want else ")")
        if int(attrs.get("n_sheets") or 1) > 1:
            head += f"; printed on {attrs.get('n_sheets')} sheets"
        if rows:
            head += ". Each row lists the table's columns as 'heading: value'"
        readings = self.view.payloads(reading_ids[:3])
        return head, notes + rows + readings, False

    def _define_term(self, term: str):
        kg = self.view.kg
        t = " ".join(str(term).strip().lower().split())
        cid = kg.definition_chunk(t) or (kg.definition_chunk(t[:-1]) if t.endswith("s") else None)
        if cid:
            return f'Definition of "{t}":', self.view.payloads([cid]), False
        close = [k for k in kg.defined_terms() if t and (t in k or k in t)][:8]
        if close:
            return (f'"{t}" is not a defined term. Defined terms close to it: '
                    + ", ".join(f'"{k}"' for k in close)), [], True
        return f'"{t}" is not a defined term in the manual.', [], True

    def _search(self, query: str):
        if self.view.search is None:
            return "Search is not available here.", [], True
        hits = self.view.search(str(query))
        self.view.remember(hits)
        return f"Search for {query!r}:", list(hits), False


def _norm_section(section: Any) -> str:
    """"Section 4F.08", "section 4f.08 " -> "4F.08"."""
    sec = re.sub(r"(?i)^\s*section\s+", "", str(section or "")).strip()
    return sec.upper() if re.match(r"(?i)^(?:\d{1,2}[a-z]\.\d{2}|a\d)$", sec) else sec


def _natural(s: str) -> Tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                 for p in re.split(r"(\d+)", s) if p)


def tools_digest(specs: Sequence[Dict[str, Any]]) -> str:
    """A short stable fingerprint of the tool definitions, for records."""
    return hashlib.sha256(json.dumps(list(specs), sort_keys=True).encode()).hexdigest()[:12]
