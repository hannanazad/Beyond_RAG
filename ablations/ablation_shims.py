"""
Runtime ablation shims for MRAG_stp2.

Pipeline attribute layout (confirmed):
  pipeline.rerank              → Reranker object (mxbai-rerank-large-v2)
  pipeline.retriever.rerank    → same object, aliased at construction (ask.py:62)

Reranker interface (from retrieval.py:117):
  self.rerank.rank(query, docs, top_k=CFG.top_k_after_rerank)
  returns [(idx, score), ...] iterated as `for idx, score in rerank_pairs`

No GPT calls anywhere.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

log = logging.getLogger(__name__)


class NoOpReranker:
    """Passes candidates through in original order — matches Reranker.rank()."""

    def rank(self, query, docs, top_k=None, **kwargs):
        n = len(docs)
        if top_k is not None:
            n = min(n, top_k)
        return [(i, 1.0 - i * 1e-6) for i in range(n)]

    def load(self):
        return self

    def __getattr__(self, name):
        def _stub(*args, **kwargs):
            log.warning("NoOpReranker: unexpected call to %r", name)
            return None
        return _stub


@dataclass
class Ablation:
    id: str
    description: str
    cfg_patches: Dict[str, Any] = field(default_factory=dict)
    swap_reranker: bool = False


ABLATIONS: Dict[str, Ablation] = {
    "baseline":         Ablation("baseline",         "Production defaults."),
    "A1_no_router":     Ablation("A1_no_router",     "Disable question router.",     cfg_patches={"use_question_router": False}),
    "A2_no_vlm_filter": Ablation("A2_no_vlm_filter", "Disable VLM figure filter.",   cfg_patches={"use_vlm_figure_filter": False}),
    "A3_no_graph":      Ablation("A3_no_graph",      "Zero graph proximity.",        cfg_patches={"w_graph": 0.0}),
    "A4_no_rule_type":  Ablation("A4_no_rule_type",  "Zero rule-type weight.",       cfg_patches={"w_ruletype": 0.0}),
    "A5_no_hierarchy":  Ablation("A5_no_hierarchy",  "Zero hierarchy prior.",        cfg_patches={"w_hierarchy": 0.0}),
    "A6_no_reranker":   Ablation("A6_no_reranker",   "Swap reranker for NoOp.",      swap_reranker=True),
}


def _get_cfg():
    from mrag.config import CFG
    return CFG


def apply_ablation(pipeline, ablation_id: str) -> Callable[[], None]:
    """Apply the named ablation. Returns undo() closure."""
    if ablation_id not in ABLATIONS:
        raise KeyError(f"Unknown ablation {ablation_id!r}. Known: {sorted(ABLATIONS.keys())}")

    ablation = ABLATIONS[ablation_id]
    cfg = _get_cfg()

    cfg_snapshot: Dict[str, Any] = {}
    for key, new_value in ablation.cfg_patches.items():
        if not hasattr(cfg, key):
            log.warning("CFG has no attribute %r — ablation %s may not affect the pipeline.", key, ablation_id)
        cfg_snapshot[key] = getattr(cfg, key, None)
        setattr(cfg, key, new_value)
        log.info("[%s] CFG.%s: %r -> %r", ablation_id, key, cfg_snapshot[key], new_value)

    pipeline_rerank_snap = None
    retriever_rerank_snap = None
    if ablation.swap_reranker:
        noop = NoOpReranker()
        if hasattr(pipeline, "rerank"):
            pipeline_rerank_snap = pipeline.rerank
            pipeline.rerank = noop
            log.info("[%s] pipeline.rerank -> NoOpReranker", ablation_id)
        if hasattr(pipeline, "retriever") and hasattr(pipeline.retriever, "rerank"):
            retriever_rerank_snap = pipeline.retriever.rerank
            pipeline.retriever.rerank = noop
            log.info("[%s] pipeline.retriever.rerank -> NoOpReranker", ablation_id)
        if pipeline_rerank_snap is None and retriever_rerank_snap is None:
            log.error("[%s] no rerank attribute found on pipeline or pipeline.retriever", ablation_id)

    def undo():
        for key, old_value in cfg_snapshot.items():
            setattr(cfg, key, old_value)
        if pipeline_rerank_snap is not None:
            pipeline.rerank = pipeline_rerank_snap
        if retriever_rerank_snap is not None:
            pipeline.retriever.rerank = retriever_rerank_snap
        log.info("[%s] undone", ablation_id)

    return undo


def list_ablations() -> List[Dict[str, str]]:
    return [{"id": a.id, "description": a.description} for a in ABLATIONS.values()]


def verify_ablation_applied(ablation_id: str, pipeline) -> Dict[str, Any]:
    ablation = ABLATIONS[ablation_id]
    cfg = _get_cfg()
    checks: Dict[str, Any] = {}
    for key, expected in ablation.cfg_patches.items():
        actual = getattr(cfg, key, "<missing>")
        checks[f"CFG.{key}"] = {"expected": expected, "actual": actual, "ok": actual == expected}
    if ablation.swap_reranker:
        pr = getattr(pipeline, "rerank", None)
        rr = getattr(getattr(pipeline, "retriever", None), "rerank", None)
        ok = isinstance(pr, NoOpReranker) or isinstance(rr, NoOpReranker)
        checks["rerank_swapped"] = {
            "expected": "NoOpReranker on pipeline.rerank / pipeline.retriever.rerank",
            "pipeline.rerank": type(pr).__name__,
            "pipeline.retriever.rerank": type(rr).__name__,
            "ok": ok,
        }
    checks["_all_ok"] = all(c.get("ok", True) for c in checks.values() if isinstance(c, dict))
    return checks
