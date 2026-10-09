"""Does retrieval find the right part of the manual when the question is worded freely?

Runs every case in evaluation/retrieval_dev/manual_cases_v2.jsonl through
`retrieve_for_compile` -- what VINE's parser reads (search + cross-reference
expansion + closure over notes, definitions, cited sections and paragraphs) --
and records where the target section and paragraph landed.
(`with_rag=True` also runs the older `retrieve(q)` top 6; it is off by default.)

The cases are written from the MUTCD itself: random provisions, each worded
three ways (the manual's own words, plain words, a short scenario), plus
questions that need two sections. No test question and no gold answer is used.
manual_cases_v2 (9 October 2026) corrects 9 cases found, on an audit against
their own sections, to describe a situation the provision does not cover (for
example Section 8A.12, which is only about circular intersections near a grade
crossing, written as an ordinary intersection). Each corrected case keeps its id
and carries "previous_text" and "revised" (the reason). v1 is kept unchanged:
the retrieval test of 7 October 2026 was run on it.

WHAT IS MEASURED, PER CASE
  search_rank     1-based rank of the first SEARCHED chunk from each target
                  section (searched = ranked by the retriever, before any
                  expansion). None if the section is not among them.
  in_kq           the target section appears anywhere in what the parser
                  would read (searched + expanded + closure)
  chunk_in_kq     the exact source paragraph is in what the parser would read
  rag_rank        rank of the target section in the RAG top 6, or None
                  (only with with_rag=True)

WITH THE PROVISION FINDER (mrag/find_provisions.py), ALSO
  targets         for each target paragraph: was it among the candidates
                  (in_pool), which ways of looking brought it in (found_by:
                  question, sentence n, term: X, heading: 2C.46), its rank in
                  each view of the question (view_ranks), its rank among the
                  searched slots (searched_rank) and whether it reached Kq
  section_found_by  the same "found_by", per target section
  find            sentences used, manual terms found, heading sections, pool size
  rankings        every view's full ranking of the pool (for reading a run
                  afterwards without running it again)

passes(r): every target section is in Kq and, when the case names its source
paragraph, that paragraph is too. This is the number the 7 October 2026 run
missed on 17 of 154.

Nothing in this file changes the pipeline. It only reads.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_CASES = Path(__file__).resolve().parent / "retrieval_dev" / "manual_cases_v2.jsonl"
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


def run_case(retriever, case: Dict[str, Any], with_rag: bool = False) -> Dict[str, Any]:
    """One case through retrieve_for_compile (and retrieve() if with_rag).
    Never raises: a crash is recorded."""
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
        # what kind of item filled the parser's input -- so items added from
        # the VINE graph (TableRow, FigureReading) can be seen crowding or not
        out["kq_types"] = dict(_count(c.get("content_type", "?") for c in chunks))
        out["searched_types"] = dict(_count(c.get("content_type", "?") for c in searched))
        find = (getattr(res, "debug", None) or {}).get("find")
        if find is not None:
            out.update(_find_record(find, case, chunks, searched))
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


def _find_record(find: Dict[str, Any], case: Dict[str, Any], chunks: List[Dict[str, Any]],
                 searched: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Where each target came from, and how each view of the question ranked it."""
    pool_ids = list(find.get("pool_ids") or [])
    sources = find.get("sources") or {}
    rankings = find.get("rankings") or {}
    pos = {v: {cid: i for i, cid in enumerate(lst, 1)} for v, lst in rankings.items()}
    searched_ids = [c.get("chunk_id", "") for c in searched]
    all_ids = {c.get("chunk_id", "") for c in chunks}
    targets = {}
    for cid in case.get("target_chunk_ids") or []:
        targets[cid] = {
            "in_pool": cid in pool_ids,
            "found_by": list(sources.get(cid, [])),
            "view_ranks": {v: p.get(cid) for v, p in pos.items()},
            "searched_rank": (searched_ids.index(cid) + 1) if cid in searched_ids else None,
            "in_kq": cid in all_ids,
        }
    pool_secs = list(find.get("pool_sections") or [""] * len(pool_ids))
    by_section: Dict[str, List[str]] = {}
    for t in case["target_sections"]:
        ways: List[str] = []
        for cid, sec in zip(pool_ids, pool_secs):
            if sec == t:
                for w in sources.get(cid, []):
                    if w not in ways:
                        ways.append(w)
        by_section[t] = ways
    return {
        "targets": targets,
        "section_found_by": by_section,
        "find": {"sentences": len(find.get("sentences") or []),
                 "terms": [t.get("term") + (f" -> {t['see']}" if t.get("see") else "")
                           for t in find.get("terms") or []],
                 "headings": [h.get("section") for h in find.get("headings") or []],
                 "pool": find.get("pool")},
        "rankings": rankings,
    }


def passes(r: Dict[str, Any]) -> Optional[bool]:
    """Every target section is in Kq, and the source paragraph too when the
    case names one. None when the case crashed."""
    if "in_kq" not in r:
        return None
    return all(r["in_kq"].values()) and r.get("chunk_in_kq") is not False


def gate(now: List[Dict[str, Any]], before: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The same cases before and after: how many pass, which were gained and
    which were lost. `ok` is True when no fewer cases pass than before."""
    b = {r["case_id"]: r for r in before}
    common = [r for r in now if r["case_id"] in b]
    gained = [r["case_id"] for r in common if passes(r) and not passes(b[r["case_id"]])]
    lost = [r["case_id"] for r in common if passes(b[r["case_id"]]) and not passes(r)]
    n_now = sum(1 for r in common if passes(r))
    n_before = sum(1 for r in common if passes(b[r["case_id"]]))
    errors = [r["case_id"] for r in common if passes(r) is None]
    return {"n": len(common), "pass_before": n_before, "pass_now": n_now,
            "gained": gained, "lost": lost, "errors": errors,
            "ok": n_now >= n_before and not errors}


def print_gate(g: Dict[str, Any]) -> None:
    print(f"\n  cases compared        : {g['n']}")
    print(f"  target reaches Kq     : {g['pass_before']} before -> {g['pass_now']} now")
    print(f"  gained                : {g['gained'] or 'none'}")
    print(f"  lost                  : {g['lost'] or 'none'}")
    if g["errors"]:
        print(f"  CRASHED               : {g['errors']}")


def print_targets(results: List[Dict[str, Any]], case_ids: Iterable[str]) -> None:
    """For the named cases: where each target came from and how each view ranked it."""
    want = set(case_ids)
    for r in results:
        if r["case_id"] not in want:
            continue
        print(f"  {r['case_id']:26s} passes {passes(r)} | Kq {r.get('kq_size')} | "
              f"terms {(r.get('find') or {}).get('terms')} | headings {(r.get('find') or {}).get('headings')}")
        for sec, ways in (r.get("section_found_by") or {}).items():
            print(f"      section {sec:7s} in Kq {r['in_kq'].get(sec)} | found by {ways or 'nothing'}")
        for cid, t in (r.get("targets") or {}).items():
            print(f"      {cid:36s} pool {t['in_pool']} | searched rank {t['searched_rank']} | "
                  f"in Kq {t['in_kq']} | found by {t['found_by'] or 'nothing'} | view ranks {t['view_ranks']}")


def _count(items: Iterable[str]) -> Dict[str, int]:
    d: Dict[str, int] = defaultdict(int)
    for x in items:
        d[x] += 1
    return d


def run_all(retriever, cases: List[Dict[str, Any]], with_rag: bool = False,
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


def _found(r: Dict[str, Any], k: int = 5) -> Optional[bool]:
    if "search_rank" not in r:
        return None
    return all(v is not None and v <= k for v in r["search_rank"].values())


def compare(before: List[Dict[str, Any]], after: List[Dict[str, Any]], k: int = 5) -> Dict[str, Any]:
    """The same cases, two runs: what got better, what got worse.

    `before` and `after` are the `results` lists that CELL 7 saves. Only cases
    present in both are compared. Nothing is tuned from this: it reports."""
    b = {r["case_id"]: r for r in before}
    a = {r["case_id"]: r for r in after}
    common = [cid for cid in a if cid in b]
    rows = defaultdict(lambda: {"n": 0, "top_before": 0, "top_after": 0,
                                "kq_before": 0, "kq_after": 0, "rag_before": 0, "rag_after": 0})
    gained, lost = [], []
    for cid in common:
        rb, ra = b[cid], a[cid]
        row = rows[ra["style"]]
        row["n"] += 1
        fb, fa = bool(_found(rb, k)), bool(_found(ra, k))
        row["top_before"] += fb
        row["top_after"] += fa
        row["kq_before"] += all(rb.get("in_kq", {}).values()) if "in_kq" in rb else 0
        row["kq_after"] += all(ra.get("in_kq", {}).values()) if "in_kq" in ra else 0
        row["rag_before"] += all(v is not None for v in rb.get("rag_rank", {"_": None}).values())
        row["rag_after"] += all(v is not None for v in ra.get("rag_rank", {"_": None}).values())
        if fa and not fb:
            gained.append(cid)
        if fb and not fa:
            lost.append(cid)
    vine_share = [sum(v for t, v in (r.get("searched_types") or {}).items()
                      if t in ("TableRow", "FigureReading")) for r in after]
    return {"by_style": dict(rows), "gained": gained, "lost": lost, "k": k,
            "median_vine_items_in_searched": sorted(vine_share)[len(vine_share) // 2] if vine_share else 0}


def print_compare(c: Dict[str, Any]) -> None:
    k = c["k"]
    print(f"\n  {'style':22s} {'n':>3s}   {'search@'+str(k):>17s}   {'in Kq':>15s}   {'RAG top6':>15s}")
    for style in STYLE_ORDER + sorted(set(c["by_style"]) - set(STYLE_ORDER)):
        r = c["by_style"].get(style)
        if not r:
            continue
        n = r["n"]
        print(f"  {style:22s} {n:>3d}   {_pct(r['top_before'], n)} -> {_pct(r['top_after'], n)}"
              f"   {_pct(r['kq_before'], n)} -> {_pct(r['kq_after'], n)}"
              f"   {_pct(r['rag_before'], n)} -> {_pct(r['rag_after'], n)}")
    print(f"\n  now found in the searched top {k}: {c['gained'] or 'none'}")
    print(f"  no longer found in the top {k}  : {c['lost'] or 'none'}")
    print(f"  median number of TableRow/FigureReading items among the searched chunks: "
          f"{c['median_vine_items_in_searched']}")


def misses(results: List[Dict[str, Any]], styles=("plain_words", "scenario",
                                                     "two_section_linked",
                                                     "two_section_unlinked")) -> List[Dict[str, Any]]:
    """Cases where a target section never reached what the parser reads."""
    return [r for r in results if r["style"] in styles
            and ("search_rank" not in r or not all(r["in_kq"].values()))]
