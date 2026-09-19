"""One call, question to certified answer — Eq 1 through Eq 6.

WHY THIS FILE EXISTS
--------------------
Every piece of VINE was built and tested separately, and nothing joined them.
Running one question meant assembling six things by hand: retrieve Kq, parse
it into a spec, instantiate, check the problems, build five verifiers,
execute, check the trace, verbalize. That is thirty lines of glue written at
the exact moment you are also debugging a model for the first time.

    result = ask_vine("...", retriever=r, tables=t, kg=k, ask=ask)

is the same thing with the ordering guaranteed and the record kept.

THE ORDER IS THE POINT
----------------------
S3.4: "the language model does not independently decide the final answer
after retrieval. It verbalizes a decision that has already been established."

So the stages run in one order and cannot be reordered from outside:

    Kq = Retrieve(q, K)                 Eq 1
    Nq = Compile(q, Kq)                 Eq 1, and S3.1's two halves
    validate(Nq)                        S3.1, before anything executes
    execute under certificate gating    Eq 4
    a = f_LM(q, C*, Pi_q)               Eq 6, and ONLY after certification

If compilation is rejected, execution never starts. If execution leaves the
terminal unresolved, the answer is an abstention, not a hedge.

DRY RUN
-------
`dry_run=True` stops after validation. It compiles the network, records what
the parser produced, and spends no verifier calls at all. On a first run that
is what you want ten times before you let it execute once: the parser is the
component with the most freedom, and its output should be read by hand before
any aggregate is trusted.

WHAT IS RECORDED
----------------
S3.4 requires the execution trace to be directly auditable, so everything is
kept: the compiled spec, every certificate, every raw model reply, which
compiler path ran, how many repair attempts it took, and how long each stage
took. `VineResult.save()` writes it as one JSON file.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .answer import Answer, answer as verbalize_answer, supporting_certificates
from .calculator import make_calculator
from .certificate import Status
from .compile import CompileError, NetworkSpec, compile_section, instantiate
from .execute import ExecutionTrace, execute
from .model_verifiers import make_llm_verifier, make_vlm_verifier
from .network import Network
from .parser import ParseReport, make_semantic_parser
from .symbolic import make_rule_evaluator
from .table_data import Table
from .verifiers import make_cross_reference_resolver

__all__ = ["VineResult", "ask_vine", "make_ask", "build_verifiers"]


# --------------------------------------------------------------------------- #
# 1. The result
# --------------------------------------------------------------------------- #
@dataclass
class VineResult:
    question: str
    section_id: str = ""
    stage: str = ""                     # where it stopped
    spec: Optional[NetworkSpec] = None
    network: Optional[Network] = None
    report: Optional[ParseReport] = None
    trace: Optional[ExecutionTrace] = None
    answer: Optional[Answer] = None
    problems: List[str] = field(default_factory=list)
    evidence: Dict[str, int] = field(default_factory=dict)
    timings: Dict[str, float] = field(default_factory=dict)

    @property
    def status(self) -> Status:
        if self.answer is not None:
            return self.answer.status
        if self.trace is not None and self.trace.terminal is not None:
            return self.trace.terminal.status
        return Status.UNKNOWN

    @property
    def certified(self) -> bool:
        """S3.4: a definitive decision needs a valid terminal certificate."""
        return (self.trace is not None and self.trace.terminal is not None
                and self.trace.terminal.status is not Status.UNKNOWN
                and not self.trace.problems)

    def summary(self) -> str:
        parts = [f"{self.question[:70]}",
                 f"  stopped at   : {self.stage}",
                 f"  compiled by  : {self.report.source if self.report else '-'}"
                 + (f" ({self.report.attempts} attempts)"
                    if self.report and self.report.attempts > 1 else "")]
        if self.spec:
            parts.append(f"  obligations  : {len(self.spec.obligations)}"
                         f", merges {len(self.spec.merges)}")
        if self.network:
            from collections import Counter
            v = Counter(o.verifier for o in self.network.operations
                        if o.merge is None)
            parts.append(f"  verifiers    : {dict(v)}")
        if self.trace:
            parts.append(f"  execution    : {self.trace.operations_run} operations"
                         f", depth {self.trace.synchronization_depth}")
            if self.trace.skipped:
                parts.append(f"  skipped      : {self.trace.skipped}")
        if self.answer:
            parts.append(f"  decision     : {self.answer.status.value}"
                         f" (confidence {self.answer.confidence:.2f})")
            if self.answer.unresolved:
                parts.append(f"  unresolved   : {len(self.answer.unresolved)}")
        if self.problems:
            parts.append(f"  problems     : {self.problems}")
        parts.append(f"  time         : "
                     + ", ".join(f"{k} {v:.1f}s" for k, v in self.timings.items()))
        return "\n".join(parts)

    def as_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "question": self.question, "section_id": self.section_id,
            "stage": self.stage, "status": self.status.value,
            "certified": self.certified, "problems": self.problems,
            "evidence": self.evidence, "timings": self.timings,
        }
        if self.report:
            out["compile_report"] = self.report.as_dict()
            out["raw_parser_replies"] = self.report.raw
        if self.spec:
            out["spec"] = self.spec.as_dict()
        if self.trace:
            out["certificates"] = [c.as_dict() for c in self.trace.store.all()]
            out["waves"] = self.trace.waves
            out["skipped"] = self.trace.skipped
            out["unsupported_certification"] = self.trace.unsupported_certification()
            if self.network:
                out["supporting_certificates"] = [
                    c.as_dict() for c in
                    supporting_certificates(self.network, self.trace)]
        if self.answer:
            out["answer"] = self.answer.as_dict()
        return out

    def save(self, path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.as_dict(), indent=2, default=str))
        return p


# --------------------------------------------------------------------------- #
# 2. Wiring a model in
# --------------------------------------------------------------------------- #
def make_ask(vlm, max_tokens: int = 1024) -> Callable[[str, List[str]], str]:
    """Wrap a `mrag.vlm.VLM` as the `ask(prompt, images) -> str` callable.

    S3.3's model-agnosticism lives in this one function. Nothing else in VINE
    knows what a VLM is; swapping provider means passing a different callable,
    not editing a verifier.
    """
    def ask(prompt: str, images: Optional[Sequence[str]] = None) -> str:
        paths = list(images or [])
        if getattr(vlm, "provider", None) == "local" or hasattr(vlm, "_processor"):
            try:
                return vlm._answer_local(prompt, paths, max_tokens)
            except AttributeError:
                pass
        return vlm._answer_api(prompt, paths, max_tokens)
    return ask


def build_verifiers(tables: Sequence[Table] = (), kg=None, retriever=None,
                    ask: Optional[Callable] = None, query: str = "",
                    extra: Optional[Dict[str, Callable]] = None
                    ) -> Dict[str, Callable]:
    """Assemble the verifier dictionary from whatever is available.

    A verifier that cannot be built is left OUT rather than stubbed. The
    executor's own rule then applies: a missing verifier yields UNKNOWN, never
    FALSE. Substituting a placeholder that answers would be the one thing this
    architecture exists to prevent.
    """
    verifiers: Dict[str, Callable] = {}
    if tables:
        verifiers["calculator"] = make_calculator(list(tables))
        verifiers["symbolic"] = make_rule_evaluator(list(tables))
    if kg is not None:
        verifiers["cross_reference_resolver"] = make_cross_reference_resolver(kg)
    if ask is not None:
        verifiers["llm"] = make_llm_verifier(ask, retriever, query=query)
        verifiers["vlm"] = make_vlm_verifier(ask, retriever, query=query)
    if extra:
        verifiers.update(extra)
    return verifiers


# --------------------------------------------------------------------------- #
# 3. The entry point
# --------------------------------------------------------------------------- #
def ask_vine(question: str,
             *,
             chunks: Optional[Sequence[Dict[str, Any]]] = None,
             section_id: str = "",
             retriever=None,
             tables: Sequence[Table] = (),
             kg=None,
             ask: Optional[Callable[[str, List[str]], str]] = None,
             verifiers: Optional[Dict[str, Callable]] = None,
             dry_run: bool = False,
             use_semantic_parser: bool = True,
             fall_back_to_baseline: bool = True,
             max_parse_attempts: int = 3,
             top_k: Optional[int] = None,
             record_dir: Optional[str] = None,
             ) -> VineResult:
    """Run one question through VINE.

    chunks / retriever
        Kq. Pass `chunks` to work from material you already have, or a
        `retriever` to fetch it with `retrieve_for_compile`. Passing both uses
        the chunks and leaves the retriever for obligation-level retrieval
        during execution, which is Eq 5.
    section_id
        Needed for the baseline compiler and for its use as a fallback. Without
        it, a parser failure cannot fall back and is reported as a failure.
    ask
        `ask(prompt, images) -> str`. Without it there is no semantic parser
        and no llm/vlm verifier; the run uses the printed structure and the
        deterministic verifiers only, which is a legitimate and free mode.
    dry_run
        Compile and validate, then stop. No verifier is called.
    fall_back_to_baseline
        On by default, so a parser failure does not stop the pipeline. Turn it
        OFF when measuring the parser itself: a run padded with baseline
        networks would report the printed structure's accuracy as the
        parser's.
    """
    result = VineResult(question=question, section_id=section_id)
    clock = time.time

    # ---- Eq 1, first half: Kq -------------------------------------------
    t0 = clock()
    material = list(chunks or [])
    if not material and retriever is not None:
        try:
            got = retriever.retrieve_for_compile(question, top_k=top_k)
            material = list(got.chunks)
            result.evidence = {"chunks": len(got.chunks),
                               "figures": len(got.figures)}
        except Exception as e:                                # noqa: BLE001
            result.stage = "retrieval failed"
            result.problems = [f"retrieve_for_compile raised {e!r}"]
            return result
    result.evidence.setdefault("chunks", len(material))
    if not material:
        result.stage = "no evidence"
        result.problems = ["no chunks were supplied and none were retrieved"]
        return result
    if not section_id:
        seen = [c.get("section_id") for c in material if c.get("section_id")]
        section_id = result.section_id = (max(set(seen), key=seen.count)
                                          if seen else "")
    result.timings["retrieve"] = clock() - t0

    # ---- Eq 1, second half: Nq ------------------------------------------
    t0 = clock()
    if ask is not None and use_semantic_parser:
        parse = make_semantic_parser(
            ask, max_attempts=max_parse_attempts,
            fall_back_to_baseline=fall_back_to_baseline)
        spec, report = parse(question, material, section_id)
    else:
        # No model: the printed structure. Not a degraded mode -- it compiles
        # 915 of 953 sections and validates all of them.
        report = ParseReport(source="baseline", attempts=0)
        try:
            spec = compile_section(section_id, material, query=question)
        except CompileError as e:
            spec = None
            report.source = "failed"
            report.notes.append(str(e))
    result.spec, result.report = spec, report
    result.timings["compile"] = clock() - t0

    if spec is None:
        result.stage = "compilation failed"
        result.problems = [p for group in report.problems for p in group] or \
            list(report.notes)
        return result

    # ---- S3.1: checked BEFORE execution ----------------------------------
    net, problems = instantiate(spec)
    result.network, result.problems = net, list(problems)
    if problems:
        # "Networks containing unresolved references ... are rejected."
        result.stage = "network rejected"
        return result

    if dry_run:
        result.stage = "compiled (dry run)"
        if record_dir:
            result.save(Path(record_dir) / f"{_slug(question)}.json")
        return result

    # ---- Eq 4: execution under certificate gating ------------------------
    t0 = clock()
    vdict = verifiers if verifiers is not None else build_verifiers(
        tables=tables, kg=kg, retriever=retriever, ask=ask, query=question)
    result.trace = execute(net, vdict)
    result.timings["execute"] = clock() - t0
    if result.trace.problems:
        result.stage = "execution rejected"
        result.problems = list(result.trace.problems)
        return result

    # ---- Eq 6: only now -------------------------------------------------
    t0 = clock()
    result.answer = verbalize_answer(question, net, result.trace,
                                     verbalize=ask)
    result.timings["answer"] = clock() - t0
    result.stage = "answered"

    if record_dir:
        result.save(Path(record_dir) / f"{_slug(question)}.json")
    return result


def _slug(text: str, limit: int = 60) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return (s[:limit] or "query") + f"_{int(time.time())}"
