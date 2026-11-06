"""
Backfill missing retrieval traces on existing runs_<id>.jsonl files.

Why: v2 of run_ablation.py captured `r.get("chunks_used", [])` and
`r.get("pages_used", [])`, but mrag's ask() actually returns those fields
under different keys. Result: 4 completed ablations (A2-A5, A6) have empty
chunks_used and pages_used in their record, blocking retrieval-metric
scoring (Recall@5, MRR, nDCG@6, context_precision, evidence_sufficiency,
retrieval_points_25, full 97-point score).

Fix: for each completed record, re-call `pipeline.retriever.retrieve(question)`
with the SAME ablation applied (so we get the same retrieval trace the
original run would have produced). Merge chunks + pages back into the record.
Generation is not re-run — fast (~200 ms/Q vs ~28 s/Q for full ask()).

No GPT calls. No re-generation. Just retrieval trace recovery.

Usage:
    from ablations.postprocess_retrieval import postprocess_ablation
    postprocess_ablation(
        ablation_id="A3_no_graph",
        runs_path=Path("/content/ablation_results/runs_A3_no_graph.jsonl"),
        pipeline=pipeline,
    )
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("ablations.postprocess")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _probe_retriever_return(r: Dict[str, Any]) -> Dict[str, str]:
    """First-call diagnostic: report what keys the retriever.retrieve() returns
    so we know how to extract chunks/pages/figures. Called once per ablation."""
    top_keys = list(r.keys()) if isinstance(r, dict) else [type(r).__name__]
    debug_keys = []
    if isinstance(r, dict) and isinstance(r.get("debug"), dict):
        debug_keys = list(r["debug"].keys())
    return {"top_level": top_keys, "debug": debug_keys}


def _extract(r: Dict[str, Any], canonical: str, aliases: List[str]) -> Any:
    """Try multiple key names; fall through to r['debug'] if present."""
    if not isinstance(r, dict):
        return []
    for key in [canonical] + list(aliases):
        if key in r and r[key]:
            return r[key]
    debug = r.get("debug") or {}
    if isinstance(debug, dict):
        for key in [canonical] + list(aliases):
            if key in debug and debug[key]:
                return debug[key]
    return []


def _extract_chunks(r):
    return _extract(r, "chunks_used", ["chunks", "retrieved_chunks", "text_chunks", "top_chunks"])


def _extract_pages(r):
    return _extract(r, "pages_used", ["pages", "retrieved_pages", "colpali_pages", "visual_pages"])


def _extract_figures(r):
    return _extract(r, "figures", ["figures_used", "figures_kept", "retrieved_figures"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def postprocess_ablation(
    ablation_id: str,
    runs_path: Path,
    pipeline,
    force: bool = False,
    verbose: bool = True,
) -> Dict[str, int]:
    """
    Backfill chunks_used + pages_used + figures_used on every non-errored
    record in `runs_path` by re-calling pipeline.retriever.retrieve(question)
    with the ablation applied.

    force=True re-fills even records that already have chunks/pages populated.

    Returns counters. Does not call any GPT / VLM code path.
    """
    from ablations.ablation_shims import apply_ablation

    records = _load_jsonl(runs_path)
    if not records:
        log.warning("No records in %s — nothing to post-process", runs_path)
        return {"total": 0, "filled": 0, "skipped": 0, "err": 0}

    log.info("[%s] post-processing %d records in %s", ablation_id, len(records), runs_path.name)

    undo = apply_ablation(pipeline, ablation_id)
    counters = {"total": len(records), "filled": 0, "skipped": 0, "err": 0}
    probed = False

    try:
        retriever = getattr(pipeline, "retriever", None)
        if retriever is None or not hasattr(retriever, "retrieve"):
            log.error("pipeline has no retriever.retrieve() — cannot post-process")
            return counters

        for i, rec in enumerate(records, 1):
            qa_id = rec.get("qa_id", str(i))
            if rec.get("error"):
                counters["skipped"] += 1
                continue
            if not force and (rec.get("chunks_used") or rec.get("pages_used")):
                counters["skipped"] += 1
                continue
            question = rec.get("question")
            if not question:
                counters["skipped"] += 1
                continue

            t_start = time.time()
            try:
                r = retriever.retrieve(question)

                # One-shot probe on first successful call — print return schema
                # so the user (and next Claude session) know what keys mrag exposes.
                if not probed and verbose:
                    probe = _probe_retriever_return(r)
                    print(f"[{ablation_id}] retriever.retrieve() return schema:")
                    print(f"  top-level keys: {probe['top_level']}")
                    print(f"  debug keys    : {probe['debug']}")
                    probed = True

                rec["chunks_used"]  = _extract_chunks(r)
                rec["pages_used"]   = _extract_pages(r)
                # only overwrite figures if we have something better
                new_figures = _extract_figures(r)
                if new_figures:
                    rec["figures_used"] = new_figures
                rec["postprocess_latency_s"] = time.time() - t_start
                rec["postprocessed"] = True
                counters["filled"] += 1
            except Exception as e:
                rec["postprocess_error"] = f"{type(e).__name__}: {e}"
                counters["err"] += 1
                log.exception("[%s] qa_id=%s post-process failed", ablation_id, qa_id)

            if verbose and (i % 25 == 0 or i == counters["total"]):
                print(f"  [{ablation_id}] {i}/{counters['total']}  filled={counters['filled']} skipped={counters['skipped']} err={counters['err']}",
                      flush=True)

        _write_jsonl(runs_path, records)
        log.info("[%s] wrote back %d records to %s", ablation_id, len(records), runs_path.name)

    finally:
        undo()

    return counters


def postprocess_all(
    ablations_dir: Path,
    pipeline,
    ablation_ids: Optional[List[str]] = None,
    force: bool = False,
    verbose: bool = True,
) -> Dict[str, Dict[str, int]]:
    """
    Run postprocess_ablation for every runs_<id>.jsonl in ablations_dir.
    Optionally restrict to `ablation_ids`.
    """
    from ablations.ablation_shims import ABLATIONS
    known = set(ABLATIONS.keys())

    ablations_dir = Path(ablations_dir)
    results: Dict[str, Dict[str, int]] = {}

    if ablation_ids is None:
        # Auto-detect from files
        ablation_ids = []
        for p in sorted(ablations_dir.glob("runs_*.jsonl")):
            stem = p.stem  # runs_A1_no_router
            aid = stem[len("runs_"):]
            if aid in known:
                ablation_ids.append(aid)

    for aid in ablation_ids:
        runs_path = ablations_dir / f"runs_{aid}.jsonl"
        if not runs_path.exists():
            log.warning("skip %s: %s not found", aid, runs_path)
            continue
        print(f"\n=== post-processing {aid} ===")
        results[aid] = postprocess_ablation(aid, runs_path, pipeline, force=force, verbose=verbose)
        print(f"  → {results[aid]}")

    return results
