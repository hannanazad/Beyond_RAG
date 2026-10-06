"""Does retrieval find the right part of the manual when the question is worded freely?

Runs every case in evaluation/retrieval_dev/manual_cases_v1.jsonl through the
two retrieval entry points and records where the target section landed.

  retrieve_for_compile(q)   what VINE's parser reads (search + cross-reference
                            expansion + closure over notes, definitions, cited
                            sections and paragraphs)
  retrieve(q)               the RAG baseline, top 6 after reranking

The cases are written from the MUTCD itself: random provisions, each worded
three ways (the manual's own words, plain words, a short scenario), plus
questions that need two sections. No test question and no gold answer is used.

WHAT IS MEASURED, PER CASE
  search_rank     1-based rank of the first SEARCHED chunk from each target
                  section (searched = ranked by the retriever, before any
                  expansion). None if the section is not among them.
  in_kq           the target section appears anywhere in what the parser
                  would read (searched + expanded + closure)
  chunk_in_kq     the exact source paragraph is in what the parser would read
  rag_rank        rank of the target section in the RAG top 6, or None

Nothing in this file changes the pipeline. It only reads.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_CASES = Path(__file__).resolve().parent / "retrieval_dev" / "manual_cases_v1.jsonl"
CUTS = (1, 3, 5, 10)


def load_cases(path: Optional[str] = None) -> List[Dict[str, Any]]:
    p = Path(path) if path else DEFAULT_CASES
    cases = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids in " + str(p))
    return cases


def _first_rank(sections: List[str], target: str) -> Optional[int]:
    for i, s in enumerate(sections, 1):
        if s == target:
            return i
    return None


def run_case(retriever, case: Dict[str, Any], with_rag: bool = True) -> Dict[str, Any]:
    """One case through both entry points. Never raises: a crash is recorded."""
    out: Dict[str, Any] = {k: case[k] for k in ("case_id", "style", "part", "target_sections")}
    t0 = time.time()
    try:
        res = retriever.retrieve_for_compile(case["text"])
        chunks = list(res.chunks or [])
        searched = [c for c in chunks if c.get("source") == "searched"]
        searched_secs = [c.get("section_id", "") for c in searched]
        all_secs = {c.get("section_id", "") for c in chunks}
        all_ids = {c.get("chunk_id", "") for c in chunks}
        out["search_rank"] = {t: _first_rank(searched_secs, t) for t in case["target_sections"]}
        out["in_kq"] = {t: (t in all_secs) for t in case["target_sections"]}
        out["chunk_in_kq"] = (all(cid in all_ids for cid in case["target_chunk_ids"])
                              if case.get("target_chunk_ids") else None)
        out["kq_size"] = len(chunks)
        out["searched_top5"] = searched_secs[:5]
        out["kq_sources"] = dict(_count(c.get("source", "?") for c in chunks))
    except Exception as e:                                     # noqa: BLE001
        out["error_compile"] = repr(e)
    if with_rag:
        try:
            rag = retriever.retrieve(case["text"])
            rag_secs = [c.get("section_id", "") for c in (rag.chunks or [])]
            out["rag_rank"] = {t: _first_rank(rag_secs, t) for t in case["target_sections"]}
            out["rag_top"] = rag_secs
        except Exception as e:                                 # noqa: BLE001
            out["error_rag"] = repr(e)
    out["seconds"] = round(time.time() - t0, 2)
    return out


def _count(items: Iterable[str]) -> Dict[str, int]:
    d: Dict[str, int] = defaultdict(int)
    for x in items:
        d[x] += 1
    return d


def run_all(retriever, cases: List[Dict[str, Any]], with_rag: bool = True,
            progress: bool = True) -> List[Dict[str, Any]]:
    results = []
    t0 = time.time()
    for i, c in enumerate(cases, 1):
        results.append(run_case(retriever, c, with_rag=with_rag))
        if progress and (i % 10 == 0 or i == len(cases)):
            print(f"  {i}/{len(cases)} cases, {time.time() - t0:.0f}s")
    return results


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def _pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:5.1f}%" if d else "   - "


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per style. A two-section case counts as found only if BOTH are found."""
    by_style: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in results:
        by_style[r["style"]].append(r)
    table: Dict[str, Dict[str, Any]] = {}
    for style, rows in by_style.items():
        ok = [r for r in rows if "search_rank" in r]
        n = len(ok)
        row: Dict[str, Any] = {"n": len(rows), "errors": len(rows) - n}
        for k in CUTS:
            row[f"search_top{k}"] = sum(
                1 for r in ok if all(v is not None and v <= k for v in r["search_rank"].values()))
        row["in_kq"] = sum(1 for r in ok if all(r["in_kq"].values()))
        chunk_rows = [r for r in ok if r.get("chunk_in_kq") is not None]
        row["chunk_in_kq"] = sum(1 for r in chunk_rows if r["chunk_in_kq"])
        row["chunk_n"] = len(chunk_rows)
        rag = [r for r in rows if "rag_rank" in r]
        row["rag_n"] = len(rag)
        row["rag_top6"] = sum(1 for r in rag if all(v is not None for v in r["rag_rank"].values()))
        row["median_kq"] = (sorted(r["kq_size"] for r in ok)[n // 2] if n else None)
        table[style] = row
    return table


STYLE_ORDER = ["manual_words", "plain_words", "scenario",
               "two_section_linked", "two_section_unlinked"]


def print_summary(table: Dict[str, Dict[str, Any]]) -> None:
    print(f"\n  {'style':22s} {'n':>3s}   {'search@1':>8s} {'@3':>7s} {'@5':>7s} {'@10':>7s}"
          f"   {'in Kq':>7s} {'para in Kq':>10s}   {'RAG top6':>8s}  {'Kq size':>7s}")
    for style in STYLE_ORDER + sorted(set(table) - set(STYLE_ORDER)):
        if style not in table:
            continue
        r = table[style]
        n = r["n"] - r["errors"]
        print(f"  {style:22s} {r['n']:>3d}   {_pct(r['search_top1'], n):>8s} {_pct(r['search_top3'], n):>7s}"
              f" {_pct(r['search_top5'], n):>7s} {_pct(r['search_top10'], n):>7s}"
              f"   {_pct(r['in_kq'], n):>7s} {_pct(r['chunk_in_kq'], r['chunk_n']):>10s}"
              f"   {_pct(r['rag_top6'], r['rag_n']):>8s}  {str(r['median_kq']):>7s}"
              + (f"   ERRORS {r['errors']}" if r["errors"] else ""))
    print("\n  search@k : every target section has a searched chunk at rank <= k")
    print("  in Kq    : every target section is somewhere in what the parser would read")
    print("  para     : the exact source paragraph is in what the parser would read")


def by_part(results: List[Dict[str, Any]], style: str = "scenario") -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = defaultdict(lambda: {"n": 0, "top5": 0, "in_kq": 0})
    for r in results:
        if r["style"] != style or "search_rank" not in r:
            continue
        p = out[r["part"]]
        p["n"] += 1
        p["top5"] += all(v is not None and v <= 5 for v in r["search_rank"].values())
        p["in_kq"] += all(r["in_kq"].values())
    return dict(sorted(out.items()))


def misses(results: List[Dict[str, Any]], styles=("plain_words", "scenario",
                                                     "two_section_linked",
                                                     "two_section_unlinked")) -> List[Dict[str, Any]]:
    """Cases where a target section never reached what the parser reads."""
    return [r for r in results if r["style"] in styles
            and ("search_rank" not in r or not all(r["in_kq"].values()))]
