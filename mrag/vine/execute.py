"""Certificate-gated execution — Eq 4, S3.2 and S3.4.

    o in A_t  <=>  [ for all s in Pre(o), Gamma_t(s) != empty ]  and  g_o(Gamma_t) = 1

Execution proceeds in waves: every enabled operation in a wave is independent
of the others, which is what S3.2 means by parallel verification and what
S4.4 measures as synchronization depth. Nothing here calls a model; verifiers
are injected, so the executor is testable on its own and model-agnostic in the
sense S3.3 requires.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .certificate import Authority, Certificate, CertificateStore, Status
from .network import MergeType, Network, Operation

log = logging.getLogger("mrag.vine.execute")

Verifier = Callable[[Operation, CertificateStore], Certificate]


# --------------------------------------------------------------------------- #
# Typed merges (S3.2)
# --------------------------------------------------------------------------- #
def _non_blocking(cert: Certificate) -> Status:
    """How one input counts where a FALSE would otherwise BLOCK the merge.

    A FALSE does not always mean the rule failed:

        STANDARD FALSE  ->  FALSE          refutes
        GUIDANCE FALSE  ->  TRUE           records non-conformance, does not refute
        OPTION   FALSE  ->  TRUE           the option was simply not taken

    This adjustment applies ONLY where FALSE blocks, i.e. inside a conjunction
    and to the base rule of an exception merge. It must NOT be applied to a
    branch that is meant to SATISFY something — an alternative, or the
    relaxing branch of an exception. Doing so let an exception that did not
    apply (OPTION, FALSE) rescue a rule whose mandatory threshold had failed,
    certifying a design as warranted when it was not.

    Derived from the normative_authority table in the annotation schema. The
    paper states what each authority means for a failed check but not the
    merge-level treatment, so this reading is recorded in the merged
    certificate's provenance.
    """
    if cert.status is Status.FALSE and cert.normative_authority is not Authority.STANDARD:
        return Status.TRUE
    return cert.status


def _kleene_and(states: Sequence[Status]) -> Status:
    if any(s is Status.FALSE for s in states):
        return Status.FALSE           # determined despite any UNKNOWN
    if any(s is Status.UNKNOWN for s in states):
        return Status.UNKNOWN
    return Status.TRUE


def _kleene_or(states: Sequence[Status]) -> Status:
    if any(s is Status.TRUE for s in states):
        return Status.TRUE
    if any(s is Status.UNKNOWN for s in states):
        return Status.UNKNOWN
    return Status.FALSE


def merge_statuses(kind: MergeType, inputs: Sequence[Certificate],
                   threshold_fn: Optional[Callable[[Sequence[Certificate]], Status]] = None
                   ) -> Status:
    if kind is MergeType.CONJUNCTION:
        # every branch must hold, so FALSE blocks -> adjust by authority
        return _kleene_and([_non_blocking(c) for c in inputs])
    if kind is MergeType.ALTERNATIVE:
        # a branch has to SATISFY; a recommendation not followed or an option
        # not taken satisfies nothing, so raw status is what counts
        return _kleene_or([c.status for c in inputs])
    if kind is MergeType.EXCEPTION:
        # inputs[0] is the base rule, inputs[1:] are relaxing branches.
        base = _non_blocking(inputs[0])
        if base is Status.TRUE:
            return Status.TRUE
        # only an exception that actually APPLIES relaxes the rule; an UNKNOWN
        # one cannot rescue a failed base, so the result stays unresolved
        return _kleene_or([base] + [c.status for c in inputs[1:]])
    if kind is MergeType.THRESHOLD:
        if threshold_fn is None:
            return Status.UNKNOWN     # no comparator supplied: unresolved, not False
        return threshold_fn(inputs)
    return Status.UNKNOWN


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
@dataclass
class ExecutionTrace:
    waves: List[List[str]] = field(default_factory=list)
    skipped: Dict[str, str] = field(default_factory=dict)   # op id -> why
    store: CertificateStore = field(default_factory=CertificateStore)
    terminal: Optional[Certificate] = None
    problems: List[str] = field(default_factory=list)

    @property
    def synchronization_depth(self) -> int:
        """S4.4: the critical path, not the number of operations."""
        return len(self.waves)

    @property
    def operations_run(self) -> int:
        return sum(len(w) for w in self.waves)

    def unsupported_certification(self) -> bool:
        """UCR (S4.5): a DEFINITIVE terminal decision — True or False — issued
        while a mandatory obligation never resolved. An UNKNOWN terminal is
        not unsupported certification; it is the abstention the architecture
        is supposed to produce.
        """
        if self.terminal is None or self.terminal.status is Status.UNKNOWN:
            return False
        unresolved_mandatory = [oid for oid, why in self.skipped.items()
                                if "optional" not in why]
        return bool(unresolved_mandatory)

    def unknown_certificates(self) -> List[str]:
        return [c.obligation_id or c.claim[:40] for c in self.store.all()
                if c.status is Status.UNKNOWN]

    def non_conformances(self) -> List[str]:
        """FALSE Guidance: recorded, not refuting."""
        return [c.obligation_id or c.claim[:40] for c in self.store.all()
                if c.non_conformance()]


def enabled(net: Network, store: CertificateStore, done: set) -> List[Operation]:
    """A_t in Eq 4."""
    out = []
    for o in net.operations:
        if o.id in done:
            continue
        if not all(store.marked(s) for s in o.requires):
            continue
        if o.guard is not None and not o.guard(store):
            continue
        out.append(o)
    return out


def execute(net: Network,
            verifiers: Dict[str, Verifier],
            max_waves: int = 50,
            threshold_fns: Optional[Dict[str, Callable]] = None) -> ExecutionTrace:
    """Run Nq to a terminal decision, or to exhaustion.

    `verifiers` maps a verifier name to a callable. A merge operation is run
    by the executor itself, never by a model: S3.2 makes merges typed
    precisely so the composition is not an LLM's free choice.
    """
    trace = ExecutionTrace(problems=net.validate())
    if trace.problems:
        log.error("network rejected: %s", trace.problems)
        return trace

    store = trace.store
    for state in net.initial.states():                # Gamma^0_q
        for cert in net.initial.get(state):
            store.add(state, cert)

    done: set = set()
    for _ in range(max_waves):
        wave = enabled(net, store, done)
        if not wave:
            break
        trace.waves.append([o.id for o in wave])
        for o in wave:                                 # independent: order irrelevant
            cert = (_run_merge(o, store, threshold_fns)
                    if o.merge is not None else _run_verifier(o, store, verifiers))
            store.add(o.produces, cert)
            done.add(o.id)
        if net.terminal and store.marked(net.terminal):
            break

    for o in net.operations:
        if o.id not in done:
            trace.skipped[o.id] = ("guard closed or prerequisites never established"
                                   if o.mandatory else "optional, not enabled")

    trace.terminal = store.latest(net.terminal) if net.terminal else None
    if net.terminal and trace.terminal is None:
        # S3.4: a definitive decision is issued only when the terminal state
        # carries a certificate. Returning None here would make "never
        # reached" indistinguishable from "not looked at" for the caller, so
        # the executor states the abstention explicitly instead. It is not a
        # verification result and says so: verifier="executor", UNKNOWN, with
        # the operations that never ran recorded.
        trace.terminal = Certificate(
            claim=f"terminal state {net.terminal!r} was never established",
            status=Status.UNKNOWN, normative_authority=Authority.STANDARD,
            verifier="executor", obligation_id="",
            provenance={"reason": "execution halted before the terminal state",
                        "unresolved_operations": sorted(trace.skipped),
                        "states_marked": sorted(store.states())},
        )
    return trace


def _run_verifier(op: Operation, store: CertificateStore,
                  verifiers: Dict[str, Verifier]) -> Certificate:
    fn = verifiers.get(op.verifier)
    if fn is None:
        # No verifier is UNKNOWN, never False: an absent tool has not refuted
        # anything, and S3.2 requires missing evidence to stay unresolved.
        return Certificate(claim=op.claim, status=Status.UNKNOWN,
                           normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id,
                           provenance={"error": f"no verifier registered for "
                                                f"{op.verifier!r}"})
    try:
        cert = fn(op, store)
    except Exception as e:                              # a crashed tool proves nothing
        return Certificate(claim=op.claim, status=Status.UNKNOWN,
                           normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id,
                           provenance={"error": repr(e)})
    cert.obligation_id = cert.obligation_id or op.id
    cert.dependencies = cert.dependencies or list(op.requires)
    # Normative authority is a property of the MANUAL — the printed Standard/
    # Guidance/Option heading — not of the tool that ran the check. Letting a
    # verifier return its own would let an LLM downgrade a Standard to
    # Guidance and turn a refutation into a note of non-conformance. The
    # operation's declared authority wins; any disagreement is recorded.
    if cert.normative_authority is not op.normative_authority:
        cert.provenance = dict(cert.provenance)
        cert.provenance["verifier_claimed_authority"] = cert.normative_authority.value
        cert.normative_authority = op.normative_authority
    return cert


def _run_merge(op: Operation, store: CertificateStore,
               threshold_fns: Optional[Dict[str, Callable]]) -> Certificate:
    inputs = [store.latest(s) for s in op.merge_inputs]
    missing = [s for s, c in zip(op.merge_inputs, inputs) if c is None]
    if missing:
        return Certificate(claim=op.claim, status=Status.UNKNOWN,
                           normative_authority=op.normative_authority,
                           verifier="merge", obligation_id=op.id,
                           provenance={"merge": op.merge.value, "missing": missing})
    fn = (threshold_fns or {}).get(op.id)
    status = merge_statuses(op.merge, inputs, threshold_fn=fn)

    evidence, seen = [], set()
    for c in inputs:
        for e in c.evidence:
            key = (e.type, e.id)
            if key not in seen:
                seen.add(key)
                evidence.append(e)
    confs = [c.confidence for c in inputs if c.confidence]
    return Certificate(
        claim=op.claim, status=status, evidence=evidence,
        normative_authority=op.normative_authority,
        confidence=min(confs) if confs else 0.0,    # a merge is as weak as its weakest input
        verifier="merge", obligation_id=op.id,
        dependencies=list(op.merge_inputs),
        provenance={
            "merge": op.merge.value,
            "inputs": {s: c.status.value for s, c in zip(op.merge_inputs, inputs)},
            "blocking_adjusted": {s: _non_blocking(c).value
                                  for s, c in zip(op.merge_inputs, inputs)},
            "non_conformance": [s for s, c in zip(op.merge_inputs, inputs)
                                if c.non_conformance()],
        },
    )
