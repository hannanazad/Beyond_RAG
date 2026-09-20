"""Table 4 — fault containment under intermediate corruption (S4.5).

    "A verification architecture should not merely improve average accuracy;
     it should prevent a corrupted intermediate result from silently becoming
     a definitive terminal conclusion."

WHAT IS INJECTED
----------------
S4.5 lists five perturbations, and all five are corruptions of ONE branch's
output while the rest of the evidence is held fixed:

    removal of a required provision        -> that branch can no longer resolve
    withholding of a required figure       -> the same, on a visual branch
    modification of a numerical quantity   -> a CONFIDENT wrong answer
    insertion of a similar irrelevant rule -> a confident answer on wrong evidence
    reversal of an intermediate decision   -> True and False swapped

The first two remove evidence. The last three do not: they leave a branch that
looks exactly as healthy as a correct one. That distinction turns out to be
the whole result, and it is worth stating before the numbers rather than
after.

WHAT IS MEASURED
----------------
"The principal measure is whether the corrupted branch is contained through
certificate gating, contradiction, or abstention rather than propagated into
an unsupported terminal certificate."

So a fault is CONTAINED when the terminal either abstains, or still gives the
answer it would have given without the fault. It is PROPAGATED when the
terminal is definitive and differs from the uncorrupted one. Being unchanged
counts as containment because the corruption reached nothing that mattered --
which is a structural property, not luck.

WHICH CONFIGURATIONS ARE REPORTED
---------------------------------
VINE and Sequential-Verify are run for real, through the real executor.

The paper's table also has CoT and Self-Verify rows. Those are LLM behaviours
and cannot be measured without models, so they are NOT filled in here. What is
reported alongside is an "unconstrained chain": the same obligations composed
in one free-form step with no gating and no typed merge. It is the structural
stand-in for a reasoning trace, and it is labelled as that rather than as CoT,
because writing a number under a method that was never run is the exact
failure this project is about.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .certificate import Certificate, CertificateStore, Evidence, Status
from .execute import execute
from .experiments import (Result, Scenario, _all_verifiers, _compose_any_true,
                          _retype_merges, make_scenario, reference_terminal,
                          run_sequential)
from .network import MergeType, Network, Operation

__all__ = ["FaultKind", "Fault", "candidate_faults", "run_faulted",
           "containment_rate", "table4", "CONFIGURATIONS"]


class FaultKind(str, Enum):
    PROVISION_REMOVED = "provision removed"
    FIGURE_WITHHELD = "figure withheld"
    NUMERIC_CHANGED = "numeric changed"
    DISTRACTOR_INSERTED = "distractor inserted"
    DECISION_REVERSED = "decision reversed"


# Which modality column of Table 4 each fault belongs in.
MODALITY: Dict[FaultKind, str] = {
    FaultKind.PROVISION_REMOVED: "text",
    FaultKind.DISTRACTOR_INSERTED: "text",
    FaultKind.DECISION_REVERSED: "text",
    FaultKind.NUMERIC_CHANGED: "numeric",
    FaultKind.FIGURE_WITHHELD: "visual",
}

# A fault has to be injectable where that kind of evidence is actually used.
# Withholding a figure from a table lookup would not be a visual fault; it
# would be nothing at all.
_VERIFIER_FAULTS: Dict[str, Tuple[FaultKind, ...]] = {
    "calculator": (FaultKind.NUMERIC_CHANGED, FaultKind.PROVISION_REMOVED),
    "symbolic": (FaultKind.NUMERIC_CHANGED, FaultKind.DECISION_REVERSED),
    "vlm": (FaultKind.FIGURE_WITHHELD, FaultKind.DECISION_REVERSED),
    "llm": (FaultKind.PROVISION_REMOVED, FaultKind.DISTRACTOR_INSERTED,
            FaultKind.DECISION_REVERSED),
    "cross_reference_resolver": (FaultKind.PROVISION_REMOVED,
                                 FaultKind.DISTRACTOR_INSERTED),
}


@dataclass(frozen=True)
class Fault:
    kind: FaultKind
    target: str                  # the operation whose branch is corrupted

    @property
    def modality(self) -> str:
        return MODALITY[self.kind]

    def describe(self) -> str:
        return f"{self.kind.value} at {self.target}"


def candidate_faults(net: Network) -> List[Fault]:
    """Every fault that can be injected into this network.

    Only branches that FEED the terminal are worth corrupting. An obligation
    whose state nothing consumes -- the Option paragraphs the baseline
    compiler leaves out of the base -- can be corrupted freely without the
    answer changing, and counting those as contained would inflate every row
    in the table.
    """
    feeding = _states_feeding_terminal(net)
    out: List[Fault] = []
    for op in net.operations:
        if op.merge is not None or op.produces not in feeding:
            continue
        for kind in _VERIFIER_FAULTS.get(op.verifier, ()):
            out.append(Fault(kind, op.id))
    return out


def _states_feeding_terminal(net: Network) -> set:
    producer = {op.produces: op for op in net.operations}
    seen: set = set()
    stack = [net.terminal] if net.terminal else []
    while stack:
        state = stack.pop()
        if state in seen or state not in producer:
            continue
        seen.add(state)
        op = producer[state]
        stack.extend(op.merge_inputs or [])
        stack.extend(op.requires or [])
        stack.extend(op.guard_states or [])
    return seen


# --------------------------------------------------------------------------- #
# Injecting one fault
# --------------------------------------------------------------------------- #
_FLIP = {Status.TRUE: Status.FALSE, Status.FALSE: Status.TRUE,
         Status.UNKNOWN: Status.TRUE}


def _faulted_verifier(scenario: Scenario, fault: Fault) -> Callable:
    """The scenario verifier, with one branch corrupted.

    Note what the last three faults do to `confidence`: nothing. A branch
    whose number was altered, whose evidence was swapped for a lexically
    similar irrelevant rule, or whose decision was reversed reports itself as
    a clean, confident result. There is no signal in the certificate saying
    "this one is wrong" -- if there were, containing it would be trivial and
    the experiment would prove nothing.
    """
    def verify(op: Operation, store: CertificateStore) -> Certificate:
        status = scenario.of(op.id)
        note = ""
        evidence: List[Evidence] = [Evidence("section", f"{op.id}-evidence")]

        if op.requires:
            upstream = [store.latest(s) for s in op.requires]
            if any(c is None or c.status is Status.UNKNOWN for c in upstream):
                status, note = Status.UNKNOWN, "an upstream claim is unresolved"

        if op.id == fault.target:
            if fault.kind in (FaultKind.PROVISION_REMOVED,
                              FaultKind.FIGURE_WITHHELD):
                # the evidence is gone, so the check cannot be made
                status, evidence = Status.UNKNOWN, []
                note = f"injected: {fault.kind.value}"
            elif fault.kind is FaultKind.DISTRACTOR_INSERTED:
                # answered confidently, on evidence that does not govern it
                status = Status.TRUE
                evidence = [Evidence("section", "lexically-similar-irrelevant")]
                note = f"injected: {fault.kind.value}"
            else:
                # NUMERIC_CHANGED / DECISION_REVERSED: same shape, wrong answer
                status = _FLIP[status]
                note = f"injected: {fault.kind.value}"

        return Certificate(
            claim=op.claim, status=status, evidence=evidence,
            normative_authority=op.normative_authority,
            confidence=1.0 if status is not Status.UNKNOWN else 0.0,
            verifier=op.verifier, obligation_id=op.id,
            provenance={"note": note, "scenario": scenario.seed})
    return verify


# --------------------------------------------------------------------------- #
# The configurations
# --------------------------------------------------------------------------- #
CONFIGURATIONS: List[str] = ["Unconstrained chain", "Sequential-Verify",
                             "Sequential-Verify (permuted)", "VINE"]


def run_faulted(config: str, net: Network, scenario: Scenario,
                fault: Fault, order_seed: int = 0) -> Tuple[Status, Status]:
    """Return (terminal under the fault, terminal without it)."""
    clean = reference_terminal(net, scenario)
    verifier = _faulted_verifier(scenario, fault)

    if config == "VINE":
        trace = execute(net, _all_verifiers(verifier))
    elif config == "Sequential-Verify":
        trace = _sequential_trace(net, verifier)
    elif config == "Sequential-Verify (permuted)":
        # The compiled networks come out in an order that already respects
        # their dependencies, so a linear pass over them happens to reach
        # every prerequisite before it is needed -- it gets the benefit of
        # dependency-aware execution without having the mechanism. Permuting
        # the order removes that accident and leaves what a fixed linear chain
        # actually guarantees, which is nothing.
        trace = _sequential_trace(net, verifier, order_seed=order_seed)
    elif config == "Unconstrained chain":
        # no gating, and one free-form composition instead of typed merges
        used, fns = _retype_merges(net, _compose_any_true)
        for op in used.operations:
            op.guard, op.guard_desc = None, ""
        trace = execute(used, _all_verifiers(verifier), threshold_fns=fns)
    else:
        raise ValueError(f"unknown configuration {config!r}")

    got = trace.terminal.status if trace.terminal else Status.UNKNOWN
    return got, clean


def _sequential_trace(net: Network, verifier: Callable,
                      order_seed: Optional[int] = None):
    """A linear pass with no dependency gating."""
    import random
    from .execute import ExecutionTrace, merge_statuses
    chain = copy.deepcopy(net)
    store = CertificateStore()
    trace = ExecutionTrace(store=store)
    obligations = [o for o in chain.operations if o.merge is None]
    if order_seed is not None:
        random.Random(order_seed).shuffle(obligations)
    for op in obligations:
        store.add(op.produces, verifier(op, store))
        trace.waves.append([op.id])
    for op in [o for o in chain.operations if o.merge is not None]:
        inputs = [store.latest(s) for s in op.merge_inputs]
        status = (Status.UNKNOWN if any(c is None for c in inputs)
                  else merge_statuses(op.merge, inputs))
        store.add(op.produces, Certificate(
            claim=op.claim, status=status, verifier="merge",
            normative_authority=op.normative_authority, obligation_id=op.id))
        trace.waves.append([op.id])
    trace.terminal = store.latest(net.terminal) if net.terminal else None
    return trace


def contained(faulted: Status, clean: Status) -> bool:
    """Did the corruption fail to become a wrong definitive conclusion?

    Abstaining contains it. Giving the same answer as the clean run contains
    it -- the corruption reached nothing the decision depended on. Anything
    else is propagation.
    """
    if faulted is Status.UNKNOWN:
        return True
    return faulted is clean


def preserved(faulted: Status, clean: Status) -> bool:
    """Did the answer SURVIVE the corruption, rather than merely not lying?

    Containment on its own is gameable: a configuration that abstains on
    everything scores 100%. That is not a hypothetical. Permuting the
    sequential order makes operations run before their prerequisites exist,
    so more of them abstain, and the permuted chain scores HIGHER containment
    than VINE while being strictly worse at answering. Reporting containment
    without this column would have made the weaker configuration look better.
    """
    return clean is not Status.UNKNOWN and faulted is clean


# --------------------------------------------------------------------------- #
# The table
# --------------------------------------------------------------------------- #
def containment_rate(config: str, networks: Sequence[Network],
                     seeds: Sequence[int], kinds: Sequence[FaultKind] = ()
                     ) -> Tuple[float, float, int]:
    """(containment %, answer-preserved %, runs)."""
    hits = kept = total = 0
    for net in networks:
        faults = candidate_faults(net)
        if kinds:
            faults = [f for f in faults if f.kind in kinds]
        for seed in seeds:
            scenario = make_scenario(net, seed)
            for fault in faults:
                got, clean = run_faulted(config, net, scenario, fault,
                                         order_seed=seed + 10_000)
                total += 1
                hits += contained(got, clean)
                kept += preserved(got, clean)
    if not total:
        return 0.0, 0.0, 0
    return 100.0 * hits / total, 100.0 * kept / total, total


def table4(networks: Sequence[Network], seeds: Sequence[int] = range(10),
           by_kind: bool = False) -> List[Dict[str, Any]]:
    """Fault containment, by modality or by individual perturbation."""
    if by_kind:
        groups = [(k.value, (k,)) for k in FaultKind]
    else:
        groups = [(m, tuple(k for k, v in MODALITY.items() if v == m))
                  for m in ("text", "numeric", "visual")]

    rows: List[Dict[str, Any]] = []
    for config in CONFIGURATIONS:
        row: Dict[str, Any] = {"configuration": config}
        for label, kinds in groups:
            rate, _kept, n = containment_rate(config, networks, seeds, kinds)
            row[label] = rate if n else None
        _r, kept, n = containment_rate(config, networks, seeds)
        row["answer preserved"] = kept if n else None
        rows.append(row)
    # the two model-driven baselines the paper lists cannot be run without
    # models; they are named so the gap is visible rather than absent
    for config in ("CoT", "Self-Verify"):
        rows.insert(0, {"configuration": config,
                        **{label: None for label, _ in groups},
                        "answer preserved": None, "note": "needs models"})
    return rows
