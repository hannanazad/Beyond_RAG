"""The evidence a plan points to, fetched by id — for the checkers.

WHY
---
The parser writes, for every obligation, the provision it comes from
(`source_chunk`) and where its evidence is (`evidence_hint`: sections with an
optional paragraph, tables, figures). Its instructions say so: "Say where each
obligation's evidence is, in evidence_hint ... the obligation's type and hints
decide which checker runs."

The text and image checkers used to see only what a search on the claim's
words brought back (Eq 5, `retrieve_for_obligation`). That search can miss the
very paragraph the obligation was written from. The pointers are part of the
obligation, so the checker gets that evidence for certain, and the Eq 5
search adds to it.

No model is used here: everything is looked up by id in the graph and the
vector store. This file is apart from `mrag/retrieval.py` on purpose: the
retrieval code that builds Kq for the parser is not changed.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

__all__ = ["paragraph_numbers", "pointed_evidence"]


def paragraph_numbers(text: Any, most: int = 6) -> List[int]:
    """Paragraph numbers in a hint: "05" -> [5]; "3-5" -> [3, 4, 5];
    "2, 4" -> [2, 4]. A range is cut at `most` paragraphs."""
    out: List[int] = []
    for part in re.split(r"[,;]", str(text or "")):
        m = re.match(r"^\s*0*(\d{1,3})\s*(?:-|–|to|through)\s*0*(\d{1,3})\s*$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b:
                out.extend(range(a, min(b, a + most - 1) + 1))
            continue
        m = re.match(r"^\s*(?:¶|paragraph|para\.?)?\s*0*(\d{1,3})\s*$", part, re.I)
        if m:
            out.append(int(m.group(1)))
    return list(dict.fromkeys(out))[:most]


def pointed_evidence(retriever, source_chunk: str = "",
                     hints: Optional[Sequence[Dict[str, Any]]] = None,
                     max_chunks: int = 8, section_cap: int = 24,
                     collection: Optional[str] = None) -> Dict[str, Any]:
    """{"chunks": [...], "figures": [...], "debug": {...}} for one obligation.

    Order: the source provision, the hinted paragraphs, hinted sections (only
    when small enough to take whole, the same rule as `retrieve_for_obligation`),
    then the notes printed with a hinted table or figure. Hinted tables and
    figures come back as figures, so the image checker can be shown them.
    """
    from mrag.config import CFG
    from mrag.retrieval import _figure_payload_from_graph

    kg, store = retriever.kg, retriever.store
    want: List[str] = []

    def add(ids) -> None:
        for i in ids or ():
            if i and i not in want:
                want.append(i)

    add([source_chunk])
    sections, paragraphs, visuals = [], [], []
    for h in hints or ():
        kind = str(h.get("type", "")).lower()
        ident = str(h.get("id", "")).strip()
        if not ident:
            continue
        if kind == "section":
            para = str(h.get("paragraph", "") or "").strip()
            if para:
                paragraphs.append((ident, para))
            else:
                sections.append(ident)
        elif kind in ("table", "figure"):
            visuals.append(ident)

    for sec, para in paragraphs:
        for n in paragraph_numbers(para):
            add(kg.chunks_for_paragraph(sec, n))
    too_big = []
    for sec in sections:
        ids = kg.chunks_for_section(sec)
        if len(ids) > section_cap:
            too_big.append((sec, len(ids)))
            continue
        add(ids)
    for vid in visuals:
        add(kg.note_chunks_for(vid))

    kept = want[:max_chunks]
    hits = store.fetch_chunks_by_ids(collection or CFG.coll_chunks, kept)
    by_id = {(h.get("payload") or {}).get("chunk_id"): h for h in hits}
    chunks = [{**(by_id[i].get("payload") or {}),
               "score": float(by_id[i].get("score", 0.0)),
               "source": "obligation_pointer"}
              for i in kept if i in by_id]

    figures: List[Dict[str, Any]] = []
    seen = set()
    for vid in visuals:
        payload = _figure_payload_from_graph(kg, vid)
        if payload and payload["figure_id"] not in seen:
            seen.add(payload["figure_id"])
            payload["source"] = "obligation_pointer"
            figures.append(payload)

    return {"chunks": chunks, "figures": figures,
            "debug": {"pointed_chunks": kept,
                      "not_found": [i for i in kept if i not in by_id],
                      "dropped_over_cap": want[max_chunks:],
                      "sections_too_big_to_take_whole": too_big,
                      "pointed_figures": [f["figure_id"] for f in figures]}}
