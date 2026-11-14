"""Evidence made of whole pages: everything VINE's store holds on the pages
another retriever chose (13 Nov 2026: VisRAG's top pages, read by VINE's parser).

Only the place the evidence comes from changes. The pieces are the store's own
records (paragraphs, list items, table and figure notes, table rows, figure
descriptions), unchanged, so the parser, the checkers and the answer writer
read them exactly as they read Kq.

Which page a piece is on:
  - text pieces (paragraphs, list items, notes): the page they start on
    (`page_pdf`). A paragraph that starts on the page before is not shown.
  - a table row: the page of its own sheet of the table (figures.jsonl gives
    each sheet's page; the row's id "trow:Table 2B-1#s3r18" gives the sheet),
    or every page of the table when the sheet is not known. The store's own
    `page_pdf` of a row is the table's first page, or empty (14 Nov review).
  - a figure description: every page of the figures it describes.
  - a figure or table is listed when any of its sheets is on a chosen page.

The pages file is the retriever's own output (compare40/visrag_retrieve.py:
retrieval.jsonl), one line per question:
    {"question_id": ..., "question_sha256": ..., "top_pages": [{"rank", "page_pdf", "page_printed", "score"}, ...]}
It holds the question's hash and page numbers only. Any other field stops the
run: nothing but the question may reach retrieval or the parser.

No question and no answer is read here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ROW_KEYS = {"question_id", "question_sha256", "top_pages"}
PAGE_KEYS = {"rank", "page_pdf", "page_printed", "score"}
SOURCE = "visrag_page"
_SEC = re.compile(r"^(\d{1,2})([A-Z])\.(\d{2})$")


class PagesFileError(ValueError):
    """The pages file does not fit the questions of this run."""


def page_number(value: Any) -> Optional[int]:
    """A PDF page number (1 = the first page), or None. "213" and "213.0" are 213."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() and f >= 1 else None


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pages_file(path, questions: Dict[str, str], k: int) -> Dict[str, List[Dict[str, Any]]]:
    """{question id: its top `k` pages, best first}, for every question of the run.

    Stops (PagesFileError) when a question is missing, when its text is not the
    text the pages were chosen for (sha256 of the UTF-8 text), when a question
    has fewer than `k` pages, when a page appears twice, or when a line holds
    any field other than the question id, its hash and the ranked pages."""
    if not 1 <= int(k) <= 1000:
        raise PagesFileError(f"pages per question must be at least 1 (got {k})")
    rows: Dict[str, Dict[str, Any]] = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        extra = set(r) - ROW_KEYS
        if extra:
            raise PagesFileError(f"line {n}: fields other than the question id, its hash and the pages: {sorted(extra)}")
        qid = str(r.get("question_id") or "")
        if not qid:
            raise PagesFileError(f"line {n}: no question_id")
        if qid in rows:
            raise PagesFileError(f"line {n}: {qid} appears twice")
        for p in r.get("top_pages") or []:
            extra = set(p) - PAGE_KEYS
            if extra:
                raise PagesFileError(f"line {n} ({qid}): page fields other than {sorted(PAGE_KEYS)}: {sorted(extra)}")
        rows[qid] = r
    out: Dict[str, List[Dict[str, Any]]] = {}
    missing = [q for q in questions if q not in rows]
    if missing:
        raise PagesFileError(f"{len(missing)} questions have no pages in {Path(path).name}: {missing[:5]}")
    for qid, text in questions.items():
        r = rows[qid]
        want = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if r.get("question_sha256") != want:
            raise PagesFileError(f"{qid}: the pages were chosen for a different question text")
        ranked = sorted(r.get("top_pages") or [], key=lambda p: int(p.get("rank") or 0))
        if len(ranked) < k:
            raise PagesFileError(f"{qid}: {len(ranked)} pages saved, {k} asked for")
        top, seen = [], set()
        for p in ranked[:k]:
            pg = page_number(p.get("page_pdf"))
            if pg is None:
                raise PagesFileError(f"{qid}: page {p.get('page_pdf')!r} is not a page number")
            if pg in seen:
                raise PagesFileError(f"{qid}: page {pg} appears twice")
            seen.add(pg)
            top.append({"rank": int(p["rank"]), "page_pdf": pg, "page_printed": p.get("page_printed"),
                        "score": p.get("score")})
        if [p["rank"] for p in top] != list(range(1, k + 1)):
            raise PagesFileError(f"{qid}: the ranks are not 1 to {k}")
        out[qid] = top
    return out


def scroll_payloads(client, collection: str, batch: int = 512) -> List[Dict[str, Any]]:
    """Every record's payload in a Qdrant collection (no vectors)."""
    out: List[Dict[str, Any]] = []
    offset = None
    while True:
        points, offset = client.scroll(collection_name=collection, limit=batch, offset=offset,
                                       with_payload=True, with_vectors=False)
        out.extend(dict(p.payload or {}) for p in points)
        if offset is None:
            return out


def sheet_pages(figure_records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[int, int]]:
    """{figure or table id: {sheet: page}}, from figures.jsonl. When every record
    of a figure has its own sheet number, those are used; otherwise (28 figures and
    tables over several pages have no sheet numbers) the sheets are numbered in page
    order, which is how the tables file numbers them (Table 1D-2: sheet 2 is page 78)."""
    recs: Dict[str, List[Tuple[Optional[int], int]]] = {}
    for r in figure_records:
        fid = str(r.get("figure_id") or "")
        pg = page_number(r.get("page_pdf"))
        if fid and pg is not None:
            recs.setdefault(fid, []).append((page_number(r.get("sheet")), pg))
    out: Dict[str, Dict[int, int]] = {}
    for fid, rs in recs.items():
        sheets = [s for s, _ in rs]
        if all(s is not None for s in sheets) and len(set(sheets)) == len(sheets):
            out[fid] = {s: pg for s, pg in sorted(rs)}
        else:
            out[fid] = {i: pg for i, pg in enumerate(sorted({pg for _, pg in rs}), 1)}
    return out


def _as_list(v: Any) -> List[str]:
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    s = str(v or "").strip()
    if s.startswith("["):
        try:
            return [str(x) for x in json.loads(s.replace("'", '"'))]
        except ValueError:
            return []
    return [s] if s else []


_ROW_SHEET = re.compile(r"#s(\d+)r\d+$")


def pages_of(piece: Dict[str, Any], sheets: Dict[str, Dict[int, int]]) -> List[int]:
    """The pages a piece is on (see the top of this file)."""
    kind = str(piece.get("content_type") or "")
    own = page_number(piece.get("page_pdf"))
    if kind == "TableRow":
        table = _parent_figure(piece)
        of_table = sheets.get(table, {})
        m = _ROW_SHEET.search(str(piece.get("graph_node") or piece.get("chunk_id") or ""))
        if m and int(m.group(1)) in of_table:
            return [of_table[int(m.group(1))]]
        if of_table:
            return sorted(set(of_table.values()))
    elif kind == "FigureReading":
        names = _as_list(piece.get("figure_refs")) + _as_list(piece.get("table_refs"))
        parent = _parent_figure(piece)
        if parent and parent not in names:
            names.append(parent)
        found = sorted({pg for n in names for pg in sheets.get(n, {}).values()})
        if found:
            return found
    return [own] if own is not None else []


def by_page(payloads: Iterable[Dict[str, Any]],
            sheets: Optional[Dict[str, Dict[int, int]]] = None) -> Tuple[Dict[int, List[Dict[str, Any]]], int]:
    """{page: the store's pieces on it}, and how many pieces are on no page."""
    pages: Dict[int, List[Dict[str, Any]]] = {}
    seen, no_page = set(), 0
    for p in payloads:
        cid = str(p.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        on = pages_of(p, sheets or {})
        if not on:
            no_page += 1
            continue
        for pg in on:
            pages.setdefault(pg, []).append(p)
    return pages, no_page


def _section_key(sec: str):
    m = _SEC.match(str(sec or ""))
    return (0, int(m.group(1)), m.group(2), int(m.group(3))) if m else (1, 0, str(sec or ""), 0)


def figures_by_page(sheets: Dict[str, Dict[int, int]]) -> Dict[int, List[str]]:
    """{page: ids of the figures and tables with a sheet on it}."""
    out: Dict[int, List[str]] = {}
    for fid in sorted(sheets):
        for pg in sorted(set(sheets[fid].values())):
            out.setdefault(pg, []).append(fid)
    return out


def _parent_figure(c: Dict[str, Any]) -> str:
    """The figure or table a note, row or description belongs to ("Table 2C-4"), or ""."""
    parent = str(c.get("parent_id") or "")
    if parent.lower().startswith("figure:"):
        parent = parent.split(":", 1)[1]
    return parent if parent.lower().startswith(("figure ", "table ")) else ""


def evidence_for_pages(pages: Sequence[Dict[str, Any]], pieces_by_page: Dict[int, List[Dict[str, Any]]],
                       figure_ids_by_page: Dict[int, List[str]],
                       figure_payload: Callable[[str], Optional[Dict[str, Any]]],
                       sort_key: Callable[[Dict[str, Any]], Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(pieces, figures) for one question: every piece the store holds on its
    pages, best page first and each page in the manual's order; and the figures
    and tables on those pages, plus the ones whose notes, rows or descriptions
    are on them. `sort_key` is the parser's own order within a section."""
    chunks: List[Dict[str, Any]] = []
    seen = set()
    fig_ids: List[str] = []
    for p in pages:
        pg, rank = p["page_pdf"], p["rank"]
        rows = sorted(pieces_by_page.get(pg, []),
                      key=lambda c: (_section_key(c.get("section_id")), sort_key(c)))
        for c in rows:
            cid = str(c.get("chunk_id"))
            if cid in seen:
                continue
            seen.add(cid)
            chunks.append({**c, "score": p.get("score"), "source": SOURCE, "page_rank": rank})
            parent = _parent_figure(c)
            if parent and parent not in fig_ids:
                fig_ids.append(parent)
        for fid in figure_ids_by_page.get(pg, []):
            if fid not in fig_ids:
                fig_ids.append(fid)
    figures: List[Dict[str, Any]] = []
    shown = set()
    for fid in fig_ids:
        f = figure_payload(fid)
        if not f:
            continue
        key = str(f.get("figure_id") or fid)
        if key in shown:
            continue
        shown.add(key)
        figures.append({**f, "source": SOURCE})
    return chunks, figures


NORMATIVE = ("Standard", "Guidance", "Option")


def counts(chunks: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Pieces by kind, and the Standards, Guidance and Options the parser must account for."""
    out: Dict[str, int] = {}
    for c in chunks:
        k = str(c.get("content_type") or "")
        out[k] = out.get(k, 0) + 1
    out["normative"] = sum(out.get(k, 0) for k in NORMATIVE)
    return out
