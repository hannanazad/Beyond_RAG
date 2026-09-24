"""Give every table footnote a chunk a certificate can point at.

THE PROBLEM
-----------
A calculator certificate is supposed to cite the table AND the notes that
govern the value it returns, so that an obligation raised about one of those
notes can retrieve it. Two things stopped that from working.

First, 228 of the 230 footnotes in `mutcd_tables.jsonl` carry no `chunk_id`.
The note chunks the ingest produced exist for 50 of the 68 tables, but they
are table-level: one chunk holds several notes run together. A certificate
could therefore cite "the notes of Table 2C-3" but not "note 2", which is the
one that decides whether Condition A applies.

Second, six tables have footnotes with no note chunk ANYWHERE -- not in the
graph, not in the table records. The extractor never read them, because the
notes are printed inside the crop and these six crops did not yield text.
The list is worse than its length: it is 2C-6, 4C-1, 4C-2, 4C-3, 4C-4 and
4C-5, which between them hold Table 4C-1 note c and the 4C-4/4C-5 scope
notes -- the exact conditions the symbolic rule evaluator was written to
decide. The calculator can attach them, because it reads the transcription,
and the evaluator can decide them. What could not happen was retrieving them:
a condition raised as its own obligation had nothing to search for.

WHAT THIS DOES
--------------
1. Links each footnote to the existing note chunk that CONTAINS it. Measured:
   202 of 230 match by exact containment, so most of the work is linking, not
   creating.
2. Mints a note chunk for each footnote that no existing chunk contains, from
   the transcription text -- which is the better source anyway, since a human
   checked it against the page and the extractor's attempt is what failed.
3. Writes the updated table file and a separate file of NEW chunks only.

The new chunks are written separately rather than merged into chunks.jsonl,
so the append and the re-ingest are yours to run and to inspect first.

Run:
    python scripts/table_transcription/link_footnotes.py            # report only
    python scripts/table_transcription/link_footnotes.py --write
"""
from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _load_paths():
    """`paths.py` lives in scripts/table_transcription/, not beside this file.

    Inserting this script's own directory finds nothing and the import fails
    with `No module named 'paths'`, so point at the folder that actually has
    it. Every default below then comes from one place.
    """
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here / "table_transcription"))
    import paths as p
    return p


# --------------------------------------------------------------------------- #
def norm(text: str) -> str:
    """Compare on words only. The transcription and the extracted chunk differ
    in whitespace and in how superscript markers survived OCR, and neither
    difference means they are different notes."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


_GLYPHS = {"√": " sqrt ", "×": " x ", "÷": " / ", "−": "-", "–": "-", "—": "-",
           "’": "'", "“": '"', "”": '"', "≤": " <= ", "≥": " >= "}
_NOTE_PREFIX = re.compile(r"^\s*notes?\s*\d*\s*[.)]?\s*", re.I)


def loose(text: str) -> str:
    """The same comparison, with the differences a transcription introduces
    deliberately removed.

    Table 3G-1 Note 5 is printed "S=3(sqrt)R-50" with a radical glyph, and the
    transcription writes "S=3*sqrt(R-50)" so that a calculator can evaluate it.
    They are the same note. Matching on the strict form alone minted a second
    copy of a chunk that already existed, which would have put two near
    identical notes into the index and made retrieval choose between them.

    The leading "Notes 5." the extractor keeps is dropped for the same reason:
    it is the list marker, not part of the note.
    """
    for glyph, plain in _GLYPHS.items():
        text = (text or "").replace(glyph, plain)
    return norm(_NOTE_PREFIX.sub("", text or ""))


def authority_from_verb(text: str) -> str:
    """Section 1C.01, the same rule `parsing.py` uses. Anything derived this
    way is marked authority_inferred, because no heading is printed inside a
    crop and a certificate must not present a guess as a printed Standard."""
    low = text.lower()
    if re.search(r"\bshall\b", low):
        return "Standard"
    if re.search(r"\bshould\b", low):
        return "Guidance"
    if re.search(r"\bmay\b", low):
        return "Option"
    return "Support"


TABREF_RE = re.compile(r"\bTables?\s+((?:\d+[A-Z]-\d+[A-Za-z]?)"
                       r"(?:\s*(?:,|,?\s*or|,?\s*and)\s*\d+[A-Z]-\d+[A-Za-z]?)*)", re.I)
FIGREF_RE = re.compile(r"\bFigures?\s+((?:\d+[A-Z]-\d+[A-Za-z]?)"
                       r"(?:\s*(?:,|,?\s*or|,?\s*and)\s*\d+[A-Z]-\d+[A-Za-z]?)*)", re.I)
SECREF_RE = re.compile(r"\bSection\s+(\d+[A-Z]\.\d+)", re.I)
ID_RE = re.compile(r"\d+[A-Z]-\d+[A-Za-z]?", re.I)


def refs(text: str, rx: re.Pattern) -> List[str]:
    out: List[str] = []
    for m in rx.finditer(text):
        for ident in ID_RE.findall(m.group(1)):
            if ident not in out:
                out.append(ident)
    return out


# --------------------------------------------------------------------------- #
def table_metadata(graph, table_id: str, chunks: List[Dict[str, Any]],
                   canonical_hint: str = "") -> Dict[str, Any]:
    """Page and section for a table, read off the graph node the ingest built.

    Two tables -- 4C-4 and 4C-5 -- have no `anchor_section` on their node, so
    the notes minted for them would have landed with no section at all. A note
    with no section is invisible to the whole-section anchoring in
    `retrieve_for_obligation`, which is most of the reason for minting it. The
    fallback finds the section whose text cites the table, which is where the
    ingest would have anchored it had the anchor been recorded.
    """
    node = graph.nodes.get(f"figure:{table_id}") or {}
    canonical = (node.get("canonical_id") or canonical_hint
                 or table_id.replace("Table ", ""))
    section_id = node.get("anchor_section") or ""

    if not section_id:
        citing = [c for c in chunks if canonical in (c.get("table_refs") or [])]
        if citing:
            # the earliest citing paragraph, so a table cited in several
            # sections anchors where it is introduced
            citing.sort(key=lambda c: (_int(c.get("page_pdf")) or 10**6,
                                       _int(c.get("ordinal")) or 0))
            section_id = citing[0].get("section_id", "")

    if not section_id:
        # Nothing in the text names 4C-4 or 4C-5 -- the manual refers to them
        # by warrant rather than by number -- so no chunk cites them and the
        # citation fallback finds nothing. The ingest still recorded where
        # they were printed, as an `on_page_of` edge, and that is the section
        # the reader is in when they meet the table.
        for _u, target, data in graph.out_edges(f"figure:{table_id}", data=True):
            if data.get("label") == "on_page_of" and target.startswith("section:"):
                section_id = target.split(":", 1)[1]
                break

    if not section_id:
        page = _int(node.get("page_pdf"))
        same_page = sorted({c.get("section_id", "") for c in chunks
                            if _int(c.get("page_pdf")) == page and c.get("section_id")})
        if len(same_page) == 1:
            section_id = same_page[0]

    sec = graph.nodes.get(f"section:{section_id}") or {}
    return {
        "page_pdf": _int(node.get("page_pdf")),
        "page_printed": str(node.get("page_printed") or ""),
        "section_id": section_id,
        "section_title": sec.get("title", ""),
        "chapter": sec.get("chapter", ""),
        "part": sec.get("part", ""),
        "canonical": canonical,
    }


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def next_index(existing_ids: List[str], canonical: str) -> int:
    """Continue the ingest's own numbering rather than starting a new series."""
    highest = 0
    pattern = re.compile(rf"TBLNOTE_{re.escape(canonical)}_(\d+)$")
    for cid in existing_ids:
        m = pattern.search(cid)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def build_chunk(table_id: str, meta: Dict[str, Any], index: int,
                marker: str, text: str) -> Dict[str, Any]:
    return {
        "chunk_id": f"MUTCD11e_TBLNOTE_{meta['canonical']}_{index:02d}",
        "part": meta["part"], "chapter": meta["chapter"],
        "section_id": meta["section_id"], "section_title": meta["section_title"],
        "content_type": authority_from_verb(text),
        "ordinal": index,
        "page_pdf": meta["page_pdf"], "page_printed": meta["page_printed"],
        "text": text,
        "figure_refs": refs(text, FIGREF_RE),
        "table_refs": sorted({meta["canonical"], *refs(text, TABREF_RE)}),
        "section_refs": SECREF_RE.findall(text),
        "sign_codes": [],
        "modal_verbs": sorted({v for v in ("shall", "should", "may")
                               if re.search(rf"\b{v}\b", text.lower())}),
        "source": "table_note",
        "parent_id": table_id,
        "item": str(marker),
        # no heading is printed inside a crop, so the type was inferred
        "authority_inferred": True,
        "lead_in": f"{table_id}.",
        # NOTE: no extra keys. `parsing.Chunk` is a dataclass and
        # `read_chunks_jsonl` does Chunk(**d), so any field the dataclass does
        # not declare makes the whole ingest fail on load. An "origin" marker
        # was added here once and did exactly that. Which notes came from the
        # transcription is recoverable from mutcd_tables.jsonl anyway, since
        # every footnote there carries its chunk id.
    }


# --------------------------------------------------------------------------- #
def run(tables_path: Path, chunks_path: Path, graph_path: Path,
        out_tables: Path, out_chunks: Path, write: bool) -> Dict[str, Any]:
    records = [json.loads(line) for line in
               tables_path.read_text().splitlines() if line.strip()]
    chunks = [json.loads(line) for line in
              chunks_path.read_text().splitlines() if line.strip()]
    with graph_path.open("rb") as fh:
        graph = pickle.load(fh)

    by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for c in chunks:
        if c.get("source") == "table_note" and c.get("parent_id"):
            by_parent.setdefault(str(c["parent_id"]), []).append(c)
    all_ids = [c["chunk_id"] for c in chunks]

    linked = minted = already = loose_linked = 0
    new_chunks: List[Dict[str, Any]] = []
    # one note may appear in several records of the same table (sheets, parts),
    # and it must get the SAME chunk id in each
    minted_for: Dict[Tuple[str, str], str] = {}
    counters: Dict[str, int] = {}

    for rec in records:
        table_id = rec.get("table_id", "")
        meta = table_metadata(graph, table_id, chunks,
                              rec.get("canonical_id", ""))
        candidates = by_parent.get(table_id, [])
        note_ids: List[str] = list(rec.get("note_chunk_ids") or [])

        for fn in rec.get("footnotes") or []:
            text = (fn.get("text") or "").strip()
            if not text:
                continue
            if fn.get("chunk_id"):
                already += 1
                continue

            needle = norm(text)
            hit = next((c for c in candidates
                        if needle and needle in norm(c.get("text", ""))), None)
            if hit is None:
                soft = loose(text)
                hit = next((c for c in candidates
                            if soft and soft in loose(c.get("text", ""))), None)
                if hit is not None:
                    loose_linked += 1
            if hit is not None:
                fn["chunk_id"] = hit["chunk_id"]
                linked += 1
            else:
                key = (table_id, needle)
                if key not in minted_for:
                    if table_id not in counters:
                        counters[table_id] = next_index(
                            all_ids + [c["chunk_id"] for c in new_chunks],
                            meta["canonical"])
                    chunk = build_chunk(table_id, meta, counters[table_id],
                                        fn.get("marker", ""), text)
                    counters[table_id] += 1
                    new_chunks.append(chunk)
                    minted_for[key] = chunk["chunk_id"]
                    minted += 1
                fn["chunk_id"] = minted_for[key]

            if fn["chunk_id"] not in note_ids:
                note_ids.append(fn["chunk_id"])

        rec["note_chunk_ids"] = note_ids

    summary = {
        "records": len(records),
        "footnotes_already_linked": already,
        "linked_to_existing_chunk": linked,
        "of_those_matched_loosely": loose_linked,
        "new_chunks_minted": minted,
        "tables_touched": sorted({c["parent_id"] for c in new_chunks}),
    }

    if write:
        out_tables.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        out_chunks.write_text("\n".join(json.dumps(c) for c in new_chunks) + "\n")
        summary["wrote"] = [str(out_tables), str(out_chunks)]
    return summary


def main() -> None:
    p = _load_paths()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="write the files; omit for a dry run")
    ap.add_argument("--tables", type=Path, default=p.TABLES_OUT)
    ap.add_argument("--chunks", type=Path, default=getattr(p, "CHUNKS", None))
    ap.add_argument("--graph", type=Path, default=getattr(p, "GRAPH", None))
    ap.add_argument("--out-tables", type=Path, default=None)
    ap.add_argument("--out-chunks", type=Path, default=None)
    args = ap.parse_args()

    if args.chunks is None or args.graph is None:
        raise SystemExit("set CHUNKS and GRAPH in scripts/table_transcription/"
                         "paths.py, or pass --chunks and --graph")

    out_tables = args.out_tables or args.tables
    out_chunks = args.out_chunks or args.tables.with_name("table_notes_new.jsonl")

    summary = run(args.tables, args.chunks, args.graph, out_tables, out_chunks,
                  args.write)
    for key, value in summary.items():
        print(f"{key}: {value}")
    if not args.write:
        print("\ndry run; nothing written. Add --write.")


if __name__ == "__main__":
    main()
