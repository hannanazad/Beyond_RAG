"""Tables 3 and 5 — execution structure, measured without a model.

WHAT THESE TWO TABLES ARE FOR
-----------------------------
S4.4: "Sequential-Verify and VINE use the same obligation decomposition and
the same verification operators; only the execution structure differs. This
provides a controlled test of whether the partial-order network itself
contributes beyond stepwise verification."

S4.6: the ablations ask "whether gains arise primarily from process
decomposition itself or from the stronger requirement that evidence be
explicitly verified, propagated, and composed before a terminal conclusion is
permitted."

Neither question is about answer quality. Both are about what the machinery
does with a given set of verifier outcomes. So both can be measured now, with
no model, no API key and no annotations — which is the whole reason these two
tables are the nearest wins.

WHAT IS AND IS NOT MEASURED HERE
--------------------------------
Verifier outcomes are SIMULATED from a seeded generator, not obtained from
models on MUTCD-150. That makes every number here a statement about execution
structure and nothing else. In particular `terminal_accuracy` is agreement
with the network's own declared logic, NOT the paper's "Full credit" column,
which needs real answers and stays TBD until the LLM and VLM verifiers exist.
Reporting the two as if they were the same number would be the exact error
this architecture is built to prevent.

THE EXECUTOR IS NEVER BYPASSED
------------------------------
Every configuration, ablations included, runs through the real `execute()`.
An ablation is expressed by changing what is GIVEN to it — the verifiers, the
guards on a copy of the network, the merge type — never by reimplementing
execution with the constraint removed. A harness that simulated the ablated
executor would only be measuring the harness.
"""
from __future__ import annotations

import copy
import random
import statistics as stats
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .certificate import Authority, Certificate, CertificateStore, Status
from .execute import (ExecutionTrace, _kleene_and, _kleene_or, _non_blocking,
                      execute, merge_statuses)
from .network import MergeType, Network, Operation

__all__ = ["Scenario", "Result", "make_scenario", "reference_terminal",
           "run_vine", "run_sequential", "ABLATIONS", "run_ablation",
           "table3", "table5", "format_table"]


# --------------------------------------------------------------------------- #
# 1. Simulated verifier outcomes
# --------------------------------------------------------------------------- #
@dataclass
class Scenario:
    """What each verifier would have concluded, fixed in advance and seeded.

    Holding these fixed across configurations is what makes the comparison
    controlled: every configuration sees identical verifier outcomes, so any
    difference in the terminal is caused by the machinery and nothing else.
    """
    statuses: Dict[str, Status]
    seed: int = 0

    def of(self, op_id: str) -> Status:
        return self.statuses.get(op_id, Status.UNKNOWN)


def make_scenario(net: Network, seed: int,
                  weights: Tuple[float, float, float] = (0.70, 0.15, 0.15)
                  ) -> Scenario:
    """Assign an outcome to every non-merge operation.

    The UNKNOWN share is the interesting one. A run in which every check
    resolves cannot distinguish any of these configurations — they only come
    apart when something is unresolved and the machinery has to decide whether
    to abstain or to press on.
    """
    rng = random.Random(seed)
    order = [Status.TRUE, Status.FALSE, Status.UNKNOWN]
    out: Dict[str, Status] = {}
    for op in net.operations:
        if op.merge is None:
            out[op.id] = rng.choices(order, weights=list(weights))[0]
    return Scenario(out, seed)


def make_scenario_verifier(scenario: Scenario, sees_store: bool = True,
                           always_answers: bool = False) -> Callable:
    """A verifier that reports its scenario outcome.

    `sees_store` models S3.3's obligation-conditioned retrieval: a verifier
    that can read the certificates established so far. Turn it off and an
    operation with prerequisites can no longer use them, so it abstains --
    which is what the "w/o obligation retrieval" ablation removes.

    `always_answers` models a single generative verifier standing in for the
    typed ones. A calculator that cannot find its input abstains; a model
    asked the same question produces an answer anyway. That difference, not
    accuracy, is what the "w/o typed verifiers" row is about.
    """
    def verify(op: Operation, store: CertificateStore) -> Certificate:
        status = scenario.of(op.id)
        reason = ""
        if op.requires:
            if not sees_store:
                status, reason = Status.UNKNOWN, "no access to upstream certificates"
            else:
                upstream = [store.latest(s) for s in op.requires]
                if any(c is None or c.status is Status.UNKNOWN for c in upstream):
                    status, reason = Status.UNKNOWN, "an upstream claim is unresolved"
        if always_answers and status is Status.UNKNOWN:
            status, reason = Status.TRUE, "guessed rather than abstained"
        return Certificate(
            claim=op.claim, status=status,
            normative_authority=op.normative_authority,
            confidence=1.0 if status is not Status.UNKNOWN else 0.0,
            verifier=op.verifier, obligation_id=op.id,
            provenance={"scenario": scenario.seed, "note": reason})
    return verify


# --------------------------------------------------------------------------- #
# 2. What the network's own logic says the answer is
# --------------------------------------------------------------------------- #
def reference_terminal(net: Network, scenario: Scenario) -> Status:
    """Evaluate the network declaratively, with no executor involved.

    This is the yardstick. It reads the dependency structure and the merge
    types straight off Nq and folds the scenario through them, so it shares
    no code with wave scheduling, guards, the certificate store or skipping —
    the machinery actually under test. Comparing the executor against itself
    would measure nothing.
    """
    producer: Dict[str, Operation] = {op.produces: op for op in net.operations}
    cache: Dict[str, Status] = {}
    visiting: set = set()

    def value_of(state: str) -> Status:
        if state in cache:
            return cache[state]
        op = producer.get(state)
        if op is None or state in visiting:
            return Status.UNKNOWN
        visiting.add(state)
        if op.merge is not None:
            inputs = [value_of(s) for s in op.merge_inputs]
            authorities = [_authority_of(producer.get(s)) for s in op.merge_inputs]
            result = _merge_plain(op.merge, inputs, authorities)
        else:
            result = scenario.of(op.id)
            # a check whose prerequisite never resolved cannot itself resolve
            if op.requires and any(value_of(s) is Status.UNKNOWN for s in op.requires):
                result = Status.UNKNOWN
        visiting.discard(state)
        cache[state] = result
        return result

    return value_of(net.terminal) if net.terminal else Status.UNKNOWN


def _authority_of(op: Optional[Operation]) -> Authority:
    return op.normative_authority if op is not None else Authority.STANDARD


def _blocking(status: Status, authority: Authority) -> Status:
    """The S3.2 reading, restated over bare statuses for the reference."""
    if status is Status.FALSE and authority is not Authority.STANDARD:
        return Status.TRUE
    return status


def _merge_plain(kind: MergeType, inputs: Sequence[Status],
                 authorities: Sequence[Authority]) -> Status:
    if kind is MergeType.CONJUNCTION:
        return _kleene_and([_blocking(s, a) for s, a in zip(inputs, authorities)])
    if kind is MergeType.ALTERNATIVE:
        return _kleene_or(list(inputs))
    if kind is MergeType.EXCEPTION:
        base = _blocking(inputs[0], authorities[0])
        if base is Status.TRUE:
            return Status.TRUE
        return _kleene_or([base] + list(inputs[1:]))
    return Status.UNKNOWN


# --------------------------------------------------------------------------- #
# 3. One measured run
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    config: str
    terminal: Status
    reference: Status
    calls: int
    latency: int                  # steps on the critical path
    correct: bool
    unsupported: bool             # a definitive answer the evidence does not support
    proof_completeness: float     # share of terminal-supporting states certified
    applicable: bool = True       # was there anything here to ablate?

    @staticmethod
    def of(config: str, net: Network, scenario: Scenario,
           trace: ExecutionTrace, latency: Optional[int] = None) -> "Result":
        ref = reference_terminal(net, scenario)
        got = trace.terminal.status if trace.terminal else Status.UNKNOWN
        return Result(
            config=config, terminal=got, reference=ref,
            calls=trace.operations_run,
            latency=trace.synchronization_depth if latency is None else latency,
            correct=(got is ref),
            # S4.5: the failure that matters is a DEFINITIVE conclusion the
            # evidence does not support. Abstaining when the reference also
            # abstains is the architecture working, not a miss.
            unsupported=(got is not Status.UNKNOWN and ref is Status.UNKNOWN),
            proof_completeness=_proof_completeness(net, trace))


def _proof_completeness(net: Network, trace: ExecutionTrace) -> float:
    """Of the states the terminal rests on, how many carry a certificate."""
    producer = {op.produces: op for op in net.operations}
    needed: set = set()
    stack = [net.terminal] if net.terminal else []
    while stack:
        state = stack.pop()
        if state in needed or state not in producer:
            continue
        needed.add(state)
        op = producer[state]
        stack.extend(op.merge_inputs or [])
        stack.extend(op.requires or [])
    if not needed:
        return 0.0
    have = sum(1 for s in needed if trace.store.latest(s) is not None)
    return have / len(needed)


def run_vine(net: Network, scenario: Scenario) -> Result:
    verifier = make_scenario_verifier(scenario)
    trace = execute(net, _all_verifiers(verifier))
    return Result.of("VINE", net, scenario, trace)


def _all_verifiers(fn: Callable) -> Dict[str, Callable]:
    return {name: fn for name in
            ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")}


# --------------------------------------------------------------------------- #
# 4. Table 3 — Sequential-Verify
# --------------------------------------------------------------------------- #
def run_sequential(net: Network, scenario: Scenario,
                   shuffle_seed: Optional[int] = None) -> Result:
    """The same obligations and verifiers, run in a fixed linear order.

    S4.4 is explicit that only the execution structure differs, so the
    obligations, the verifier outcomes and the typed merges are all held
    identical. What a linear chain does not have is a dependency structure:
    each step runs when its turn comes, whether or not what it depends on has
    been established.

    Latency is the number of steps, because a chain has no concurrency. This
    is the quantity S4.4 contrasts with the critical path.

    `shuffle_seed` reorders the obligations. The compiled networks happen to
    come out in an order that already respects their dependencies, so the
    document order flatters a linear chain; a permuted order shows what
    happens when it does not, and both are reported rather than only the one
    that makes the point.
    """
    chain = copy.deepcopy(net)
    obligations = [op for op in chain.operations if op.merge is None]
    merges = [op for op in chain.operations if op.merge is not None]
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(obligations)

    verifier = make_scenario_verifier(scenario)
    store = CertificateStore()
    trace = ExecutionTrace(store=store)

    for op in obligations:
        # no gating: a linear chain does not ask whether Pre(o) is established
        cert = verifier(op, store)
        store.add(op.produces, cert)
        trace.waves.append([op.id])
    for op in merges:
        inputs = [store.latest(s) for s in op.merge_inputs]
        if any(c is None for c in inputs):
            status = Status.UNKNOWN
        else:
            status = merge_statuses(op.merge, inputs)
        store.add(op.produces, Certificate(
            claim=op.claim, status=status, verifier="merge",
            normative_authority=op.normative_authority, obligation_id=op.id))
        trace.waves.append([op.id])

    trace.terminal = store.latest(net.terminal) if net.terminal else None
    return Result.of("Sequential-Verify", net, scenario, trace,
                     latency=len(trace.waves))


# --------------------------------------------------------------------------- #
# 5. Table 5 — the ablations
# --------------------------------------------------------------------------- #
def _strip_guards(net: Network) -> Network:
    out = copy.deepcopy(net)
    for op in out.operations:
        op.guard, op.guard_desc = None, ""
    return out


def _retype_merges(net: Network, fn: Callable[[Sequence[Certificate]], Status]
                   ) -> Tuple[Network, Dict[str, Callable]]:
    """Replace every typed merge with one free-form composition.

    THRESHOLD with a supplied comparator is the executor's own door for a
    composition it does not define, so an ablation can be expressed without
    touching the executor.
    """
    out = copy.deepcopy(net)
    fns: Dict[str, Callable] = {}
    for op in out.operations:
        if op.merge is not None:
            op.merge = MergeType.THRESHOLD
            fns[op.id] = fn
    return out, fns


def _compose_any_true(inputs: Sequence[Certificate]) -> Status:
    """An unconstrained final composition: something supported it, so yes."""
    return Status.TRUE if any(c.status is Status.TRUE for c in inputs) else Status.FALSE


def _compose_ignoring_status(inputs: Sequence[Certificate]) -> Status:
    """Certificates replaced by textual summaries.

    Without a machine-readable status there is nothing to gate on, so a
    downstream step sees that its inputs produced SOMETHING and proceeds.
    """
    return Status.TRUE


def _compose_dropping_unknown(inputs: Sequence[Certificate]) -> Status:
    """No evidence-completeness check: unresolved inputs are simply left out.

    This is the quiet one. Nothing looks wrong in the trace -- every input
    that reported is composed correctly -- and the conclusion is definitive
    because the unresolved branch was never counted.
    """
    resolved = [c for c in inputs if c.status is not Status.UNKNOWN]
    if not resolved:
        return Status.UNKNOWN
    return _kleene_and([_non_blocking(c) for c in resolved])


ABLATIONS: List[str] = [
    "VINE",
    "w/o certificates",
    "w/o guards",
    "w/o typed verifiers",
    "w/o obligation retrieval",
    "w/o completeness check",
    "w/o typed merge",
]


def run_ablation(name: str, net: Network, scenario: Scenario) -> Result:
    """Run one configuration of Table 5 through the real executor."""
    verifier = make_scenario_verifier(scenario)
    used, fns = net, None

    if name == "VINE":
        pass
    elif name == "w/o certificates":
        used, fns = _retype_merges(net, _compose_ignoring_status)
    elif name == "w/o guards":
        used = _strip_guards(net)
    elif name == "w/o typed verifiers":
        verifier = make_scenario_verifier(scenario, always_answers=True)
    elif name == "w/o obligation retrieval":
        verifier = make_scenario_verifier(scenario, sees_store=False)
    elif name == "w/o completeness check":
        used, fns = _retype_merges(net, _compose_dropping_unknown)
    elif name == "w/o typed merge":
        used, fns = _retype_merges(net, _compose_any_true)
    else:
        raise ValueError(f"unknown ablation {name!r}")

    trace = execute(used, _all_verifiers(verifier), threshold_fns=fns)
    # the reference is always the UNABLATED network's own logic: the question
    # is what each configuration does to a fixed correct answer
    result = Result.of(name, net, scenario, trace)
    if name == "w/o guards" and not any(op.guard for op in net.operations):
        # Removing something that is not there measures nothing. The baseline
        # parser reads printed structure, and the manual does not print
        # guarded branches, so every guard in the IR would have to come from
        # the semantic parser. Reporting 100% here would claim guards had been
        # shown not to matter, when they were never exercised.
        result.applicable = False
    return result


# --------------------------------------------------------------------------- #
# 6. The tables
# --------------------------------------------------------------------------- #
def _aggregate(rows: Sequence[Result], config: str) -> Dict[str, Any]:
    mine = [r for r in rows if r.config == config and r.applicable]
    if not mine:
        if any(r.config == config for r in rows):
            return {"configuration": config, "terminal_accuracy": None,
                    "UCR": None, "PC": None, "calls": None, "latency": None,
                    "runs": 0, "note": "not exercised by these networks"}
        return {}
    return {
        "configuration": config,
        "terminal_accuracy": 100.0 * sum(r.correct for r in mine) / len(mine),
        "UCR": 100.0 * sum(r.unsupported for r in mine) / len(mine),
        "PC": 100.0 * stats.mean(r.proof_completeness for r in mine),
        "calls": stats.mean(r.calls for r in mine),
        "latency": stats.mean(r.latency for r in mine),
        "runs": len(mine),
    }


def table3(networks: Sequence[Network], seeds: Sequence[int] = range(20),
           shuffle: bool = True) -> List[Dict[str, Any]]:
    """Linear versus dependency-aware verification."""
    rows: List[Result] = []
    for net in networks:
        for seed in seeds:
            scenario = make_scenario(net, seed)
            rows.append(run_vine(net, scenario))
            rows.append(run_sequential(net, scenario))
            if shuffle:
                r = run_sequential(net, scenario, shuffle_seed=seed + 10_000)
                r.config = "Sequential-Verify (permuted)"
                rows.append(r)
    names = ["Sequential-Verify"]
    if shuffle:
        names.append("Sequential-Verify (permuted)")
    names.append("VINE")
    return [t for t in (_aggregate(rows, n) for n in names) if t]


def table5(networks: Sequence[Network], seeds: Sequence[int] = range(20)
           ) -> List[Dict[str, Any]]:
    """Ablation of VINE execution mechanisms."""
    rows: List[Result] = []
    for net in networks:
        for seed in seeds:
            scenario = make_scenario(net, seed)
            for name in ABLATIONS:
                rows.append(run_ablation(name, net, scenario))
    return [t for t in (_aggregate(rows, n) for n in ABLATIONS) if t]


def format_table(rows: Sequence[Dict[str, Any]],
                 columns: Sequence[str] = ()) -> str:
    """A plain text table, for pasting into the paper or a log."""
    if not rows:
        return "(no rows)"
    cols = list(columns) or [c for c in rows[0] if c != "configuration"]
    width = max(len(str(r["configuration"])) for r in rows)
    head = "configuration".ljust(width) + "".join(f"  {c:>18s}" for c in cols)
    out = [head, "-" * len(head)]
    for r in rows:
        line = str(r["configuration"]).ljust(width)
        for c in cols:
            v = r.get(c)
            if v is None:
                line += f"  {'n/a':>18s}"
            else:
                line += (f"  {v:>18.1f}" if isinstance(v, float)
                         else f"  {str(v):>18s}")
        out.append(line)
    return "\n".join(out)
