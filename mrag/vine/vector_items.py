"""What the VINE graph adds to the vector store, so retrieval can find it.

Retrieval searches the chunk collection in Qdrant. Everything in it came from
the manual's text layer: paragraphs, list items, figure notes, table notes.
Two kinds of knowledge in the VINE graph never reached it:

  FigureReading   what each figure SHOWS, written by looking at the page image
                  (358 readings over 485 figures). The text layer has only the
                  caption, so a question about something drawn in a figure had
                  nothing to match.
  TableRow        one row of a printed table with its column labels, e.g.
                  "Table 2C-4 (A) Roadway Type: Freeways and Expressways;
                  AADT Less than 1,000: Required; ...". The text layer has the
                  table's notes, never its cells.

Each becomes one item with the same payload keys ingest writes, so the
retriever, the reranker and the parser read it like any other chunk. The
graph node it came from travels in `graph_node`, so anything downstream can go
back to the graph for the item's edges.

AUTHORITY. A TableRow is the manual's own printed content. A FigureReading is
NOT the manual's words: it is a person's description of a drawing, and a check
of a sample against the pages found wrong details in some. Its payload says so
(`authority`), and nothing should treat it as a provision. It is there so that
retrieval finds the right figure; the figure itself (VLM) settles the claim.

No question and no answer is read here. The items come from the graph only.

    from mrag.vine.vector_items import build_items, write_items
    items = build_items("graph_cache.pkl")
    write_items(items, "vine_items.jsonl")
"""
from __future__ import annotations

import json
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

CONTENT_TYPES = ("FigureReading", "TableRow")
READING_AUTHORITY = "NOT NORMATIVE: a reading of the figure, not the manual's words"
ROW_AUTHORITY = "TABLE: printed in the manual"

_SEC = re.compile(r"^(\d{1,2})([A-Z])\.(\d{2})$")
_SEGMENT = re.compile(r"^\*\*(?:TA-(\d+)|(\d+[A-Z]?-\d+[a-z]?))\b", re.M)


def _section_key(sec: str):
    m = _SEC.match(sec or "")
    return (int(m.group(1)), m.group(2), int(m.group(3))) if m else (99, "Z", 99)


def _plain(text: str) -> str:
    """Markdown emphasis off, whitespace folded, the log's own correction notes
    dropped (they say what an entry USED to say). The words stay exactly."""
    t = re.sub(r"\*?\(Corrected \d{1,2} \w+ \d{4}[^)]*\)\*?", "", text or "")
    t = re.sub(r"\*\*|__|\*(?=\S)|(?<=\S)\*", "", t)
    t = re.sub(r"^\s*-\s+", "", t, flags=re.M)
    return re.sub(r"\s+", " ", t).strip()


def embed_text(item: Dict[str, Any]) -> str:
    """The exact form ingest embeds a chunk in (scripts/ingest_v3.py)."""
    return (f"[{item['content_type']}] Section {item['section_id']} — "
            f"{item['section_title']}. {item['text']}")


def build_items(graph_path, tables_path=None, max_chars: int = 2400) -> List[Dict[str, Any]]:
    """`tables_path` (mutcd_tables.jsonl) supplies clean table titles. Without
    it the caption read from the PDF is used, which on some tables runs on into
    the column headings."""
    N, E, C = pickle.load(open(graph_path, "rb"))
    table_title: Dict[str, str] = {}
    if tables_path and Path(tables_path).exists():
        for l in open(tables_path):
            if l.strip():
                t = json.loads(l)
                table_title.setdefault(t.get("table_id") or "",
                                       (t.get("title") or "").split("\u2014")[0].strip())
    out_e: Dict[str, List[Any]] = defaultdict(list)
    in_e: Dict[str, List[Any]] = defaultdict(list)
    for e in E:
        out_e[e.src].append(e)
        in_e[e.dst].append(e)

    titles = {v.section: v.text for v in N.values() if v.kind == "SECTION"}
    chunk_meta: Dict[str, Dict[str, Any]] = {}
    for c in C:
        get = (lambda k, c=c: getattr(c, k) if hasattr(c, k) else c.get(k))
        sid = get("section_id")
        if sid and sid not in chunk_meta:
            chunk_meta[sid] = {"part": get("part"), "chapter": get("chapter")}

    def citing_sections(fig: str) -> List[str]:
        """Sections whose sentences name this figure or table, most first."""
        n = Counter()
        for e in in_e.get(fig, []):
            if e.rel == "REFERS_TO" and e.src in N and N[e.src].section:
                n[N[e.src].section] += 1
        return [s for s, _ in sorted(n.items(), key=lambda kv: (-kv[1], _section_key(kv[0])))]

    def page_of(node) -> Optional[int]:
        for p in node.pieces or []:
            if str(p).startswith("pdf_page="):
                try:
                    return int(str(p).split("=", 1)[1])
                except ValueError:
                    return None
        return None

    def base(cid: str, ctype: str, sec: str, text: str, node_id: str) -> Dict[str, Any]:
        meta = chunk_meta.get(sec, {})
        return {
            "chunk_id": cid, "content_type": ctype,
            "section_id": sec, "section_title": titles.get(sec, ""),
            "part": meta.get("part"), "chapter": meta.get("chapter") or (sec.split(".")[0] if sec else ""),
            "ordinal": None, "page_pdf": None, "page_printed": None,
            "figure_refs": [], "table_refs": [], "section_refs": [], "sign_codes": [],
            "modal_verbs": [], "source": "vine_graph", "parent_id": None, "item": None,
            "authority_inferred": False, "lead_in": None,
            "text": text[:max_chars], "graph_node": node_id,
        }

    items: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------- readings
    for rid, r in N.items():
        if r.kind != "FIGURE_READING":
            continue
        figs = [e.src for e in in_e.get(rid, []) if e.rel == "HAS_READING"]
        if not figs:
            continue
        body = r.text or ""
        pieces: Dict[str, str] = {}                      # figure node -> its part of the body
        marks = list(_SEGMENT.finditer(body))
        if len(figs) > 1 and marks:
            preamble = body[:marks[0].start()].strip()
            for i, m in enumerate(marks):
                seg = body[m.start(): marks[i + 1].start() if i + 1 < len(marks) else len(body)]
                ident = f"6P-{m.group(1)}" if m.group(1) else m.group(2)
                for kind in ("Figure", "Table"):
                    key = f"figure:{kind} {ident}"
                    if key in figs:
                        pieces[key] = (pieces.get(key, "") + "\n" + seg).strip()
            if pieces and preamble:
                pieces = {k: f"{preamble}\n{v}" for k, v in pieces.items()}
        rest = [f for f in figs if f not in pieces]
        groups = [([f], txt) for f, txt in pieces.items()]
        if rest:
            groups.append((rest, body))                  # one shared item, not one copy per figure
        for fset, txt in groups:
            fig_nodes = [N[f] for f in fset if f in N]
            names = [f.split(":", 1)[1] for f in fset]
            caption = "; ".join(f"{n}. {fn.text}" for n, fn in zip(names, fig_nodes))
            secs = []
            for f in fset:
                for s in citing_sections(f):
                    if s not in secs:
                        secs.append(s)
            sec = secs[0] if secs else ""
            cid = f"vine:{rid}:" + "+".join(names)
            it = base(cid, "FigureReading", sec, f"{caption} — {_plain(txt)}", rid)
            it["figure_refs"] = [n for n in names if n.startswith("Figure")]
            it["table_refs"] = [n for n in names if n.startswith("Table")]
            it["section_refs"] = secs[:8]
            it["page_pdf"] = page_of(fig_nodes[0]) if fig_nodes else None
            it["parent_id"] = fset[0]
            it["authority"] = READING_AUTHORITY
            it["sign_codes"] = sorted(set(re.findall(r"\b[A-Z]{1,3}\d{1,3}-\d{1,3}[a-zA-Z]{0,2}P?\b", txt)))[:40]
            items.append(it)

    # -------------------------------------------------------------- table rows
    for tid, t in N.items():
        if t.kind != "TABLE_ROW":
            continue
        cells, table, sheet = [], "", ""
        for p in t.pieces or []:
            k, _, v = str(p).partition("=")
            if k == "table":
                table = v
            elif k == "sheet":
                sheet = v
            elif v:
                cells.append((k, v))
        tnode = N.get(f"figure:{table}")
        chart = next((N[e.dst].text for e in out_e.get(tid, [])
                      if e.rel == "ROW_OF" and N.get(e.dst) is not None and N[e.dst].kind == "SUBTABLE"), "")
        chart = chart.split("—", 1)[1].strip() if "—" in chart else ""
        row = "; ".join(f"{k}: {v}" + (" (the manual prints a dash here)" if v in ("—", "–", "-") else "")
                        for k, v in cells)
        head = table + (f" ({chart})" if chart else "") + (f", sheet {sheet}" if sheet and sheet != "1" else "")
        cap = table_title.get(table) or (tnode.text if tnode is not None else "").strip()[:90]
        sec = t.section or next(iter(citing_sections(f"figure:{table}")), "")
        notes = sorted({e.dst.split(":", 1)[1].split("#")[0] for e in out_e.get(tid, [])
                        if e.rel == "GOVERNED_BY"})
        it = base(f"vine:{tid}", "TableRow", sec, f"{head}. {cap}. {row}", tid)
        it["table_refs"] = [table] if table else []
        it["section_refs"] = citing_sections(f"figure:{table}")[:8]
        it["page_pdf"] = page_of(tnode) if tnode is not None else None
        it["parent_id"] = f"figure:{table}"
        it["sign_codes"] = sorted({e.src.split(":", 1)[1] for e in in_e.get(tid, []) if e.rel == "HAS_ROW"})
        it["note_chunk_ids"] = notes
        it["authority"] = ROW_AUTHORITY
        items.append(it)

    ids = [i["chunk_id"] for i in items]
    dup = [k for k, n in Counter(ids).items() if n > 1]
    if dup:
        raise ValueError(f"{len(dup)} duplicate item ids, e.g. {dup[:3]}")
    return items


def write_items(items: Iterable[Dict[str, Any]], path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return path


def read_items(path) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in open(path) if l.strip()]


def summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = Counter(i["content_type"] for i in items)
    no_sec = Counter(i["content_type"] for i in items if not i["section_id"])
    lens = sorted(len(i["text"]) for i in items)
    return {"items": len(items), "by_type": dict(by), "without_section": dict(no_sec),
            "median_chars": lens[len(lens) // 2] if lens else 0, "max_chars": lens[-1] if lens else 0}
