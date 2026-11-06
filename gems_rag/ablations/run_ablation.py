"""
Mechanical ablation sweep — one line per question, everything else to log file.

Fixes from v2:
  - proper dict-key fallbacks for chunks / pages / figures (v2 captured only figures)
  - _ensure_store_client_healthy baked in (Qdrant workaround from turn 16)
  - pipeline param so notebook can reuse already-initialized pipeline
  - per-question print in benchmark format: [N/M] RUN  <id> <qa_id> r1   OK <ms> ms — <preview>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

log = logging.getLogger("ablations.run")


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _completed_qa_ids(runs_path: Path) -> Set[str]:
    if not runs_path.exists():
        return set()
    return {row["qa_id"] for row in _load_jsonl(runs_path) if not row.get("error")}


def _errored_qa_ids(runs_path: Path) -> Set[str]:
    if not runs_path.exists():
        return set()
    return {row["qa_id"] for row in _load_jsonl(runs_path) if row.get("error")}


def _keep_only_successful(runs_path: Path) -> None:
    if not runs_path.exists():
        return
    tmp = runs_path.with_suffix(runs_path.suffix + ".tmp")
    with open(runs_path) as fin, open(tmp, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("error"):
                continue
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(runs_path)


def _load_config(config_path: Optional[Path]) -> Dict[str, Any]:
    if config_path is None:
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML not installed.")
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Robust extractors — mrag's ask() return shape is not documented, so try
# multiple key names for each field. Never fail on missing keys.
# ---------------------------------------------------------------------------

def _extract_field(r: Dict[str, Any], canonical: str, aliases: List[str]) -> Any:
    """Return the first non-empty value under any of (canonical, *aliases).
    Also checks under r["debug"] as a fallback."""
    for key in [canonical] + list(aliases):
        if key in r and r[key]:
            return r[key]
    debug = r.get("debug") or {}
    if isinstance(debug, dict):
        for key in [canonical] + list(aliases):
            if key in debug and debug[key]:
                return debug[key]
    return []


def _extract_chunks(r: Dict[str, Any]) -> Any:
    return _extract_field(r, "chunks_used", ["chunks", "retrieved_chunks", "text_chunks", "top_chunks"])


def _extract_pages(r: Dict[str, Any]) -> Any:
    return _extract_field(r, "pages_used", ["pages", "retrieved_pages", "colpali_pages", "visual_pages"])


def _extract_figures(r: Dict[str, Any]) -> Any:
    return _extract_field(r, "figures", ["figures_used", "figures_kept", "retrieved_figures"])


# ---------------------------------------------------------------------------
# Qdrant workaround (turn 16 — init_pipeline sometimes leaves client blind)
# ---------------------------------------------------------------------------

def _ensure_store_client_healthy(pipeline) -> None:
    from mrag.config import CFG
    if not (hasattr(pipeline, "store") and hasattr(pipeline.store, "_client")):
        return
    try:
        if pipeline.store._client.get_collections().collections:
            return
    except Exception:
        pass
    from qdrant_client import QdrantClient
    try:
        pipeline.store._client.close()
    except Exception:
        pass
    pipeline.store._client = QdrantClient(path=str(CFG.qdrant_dir))
    log.info("replaced pipeline.store._client with fresh QdrantClient")


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_ablation_sweep(ablation_id, gold_path, output_path,
                       vlm_alias="frontier_claude", prompt_style="fewshot",
                       limit=None, retrieval_only=False, pipeline=None):
    """Sweep one ablation over gold_qa.jsonl. Returns counters dict."""
    from mrag.config import CFG
    from mrag.ask import ask
    from ablations.ablation_shims import apply_ablation, verify_ablation_applied

    CFG.set_vlm_model(vlm_alias)
    CFG.set_answer_style(prompt_style)
    log.info("start ablation=%s vlm=%s prompt=%s retrieval_only=%s",
             ablation_id, vlm_alias, prompt_style, retrieval_only)

    if pipeline is None:
        try:
            from mrag.pipeline import init_pipeline
        except ImportError:
            from mrag.ask import init_pipeline
        pipeline = init_pipeline()

    _ensure_store_client_healthy(pipeline)

    undo = apply_ablation(pipeline, ablation_id)
    counters = {"total": 0, "already_done": 0, "ok": 0, "err": 0, "skipped": 0}

    try:
        checks = verify_ablation_applied(ablation_id, pipeline)
        log.info("ablation checks: %s", json.dumps(checks, default=str))
        if not checks.get("_all_ok", False):
            raise RuntimeError(f"Ablation {ablation_id} failed verification: {checks}")

        done = _completed_qa_ids(output_path)
        counters["already_done"] = len(done)
        log.info("resume: %d already completed", len(done))

        if _errored_qa_ids(output_path):
            _keep_only_successful(output_path)

        gold_records = list(_load_jsonl(gold_path))
        if limit:
            gold_records = gold_records[:limit]
        counters["total"] = len(gold_records)
        total = counters["total"]

        for i, qa in enumerate(gold_records, 1):
            qa_id = str(qa.get("qa_id") or qa.get("id") or qa.get("question_id") or qa.get("qid") or i)
            if qa_id in done:
                counters["skipped"] += 1
                continue
            question = qa.get("question") or qa.get("query") or qa.get("q") or qa.get("prompt")

            record = {
                "qa_id": qa_id, "ablation": ablation_id,
                "vlm_alias": vlm_alias, "prompt_style": prompt_style,
                "question": question,
            }

            t_start = time.time()
            try:
                if retrieval_only:
                    retriever = getattr(pipeline, "retriever", None)
                    r = retriever.retrieve(question) if retriever else ask(question)
                    record["answer"] = None
                    record["retrieval_only"] = True
                else:
                    r = ask(question)
                    record["answer"] = r.get("answer")
                    record["retrieval_only"] = False

                # Robust extraction — mrag return shape is not documented.
                record["chunks_used"] = _extract_chunks(r)
                record["pages_used"]  = _extract_pages(r)
                record["figures_used"] = _extract_figures(r)
                record["debug"] = r.get("debug", {})

                record["latency_s"] = time.time() - t_start
                record["error"] = None
                counters["ok"] += 1
            except Exception as e:
                record["latency_s"] = time.time() - t_start
                record["error"] = f"{type(e).__name__}: {e}"
                record["answer"] = None
                counters["err"] += 1
                log.exception("[%s] qa_id=%s failed", ablation_id, qa_id)

            _append_jsonl(output_path, record)

            # Per-question progress line (benchmark format)
            ms = int(record["latency_s"] * 1000)
            if record.get("error"):
                status, preview = "ERR", str(record["error"])
            else:
                status = "OK"
                preview = str(record.get("answer") or "").replace("\n", " ").replace("\r", " ").strip()
            if len(preview) > 80:
                preview = preview[:77] + "..."
            print(f"[{i}/{total}] RUN  {ablation_id} {qa_id} r1   {status} {ms} ms \u2014 {preview}", flush=True)

        log.info("done. total=%d ok=%d err=%d skipped=%d",
                 total, counters["ok"], counters["err"], counters["skipped"])

    finally:
        undo()

    return counters


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--ablation", type=str, default=None)
    p.add_argument("--gold", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--vlm", type=str, default=None)
    p.add_argument("--prompt-style", type=str, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--retrieval-only", action="store_true")
    args = p.parse_args()

    cfg = _load_config(args.config)
    ablation_id = args.ablation or cfg.get("ablation_id")
    if not ablation_id:
        p.error("--ablation required")

    gold = args.gold or Path(cfg.get("gold_path"))
    output = args.output or Path(cfg.get("output_path", f"ablations/results/runs_{ablation_id}.jsonl"))

    run_ablation_sweep(
        ablation_id=ablation_id, gold_path=gold, output_path=output,
        vlm_alias=args.vlm or cfg.get("vlm_alias", "frontier_claude"),
        prompt_style=args.prompt_style or cfg.get("prompt_style", "fewshot"),
        limit=args.limit,
        retrieval_only=args.retrieval_only or bool(cfg.get("retrieval_only", False)),
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
