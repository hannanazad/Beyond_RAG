"""Certificate-gated execution — Eq 4, S3.2 and S3.4.

    o in A_t  <=>  [ for all s in Pre(o), Gamma_t(s) != empty ]  and  g_o(Gamma_t) = 1

Execution proceeds in waves: every enabled operation in a wave is independent
of the others, which is what S3.2 means by parallel verification and what
S4.4 measures as synchronization depth. Nothing here calls a model; verifiers
are injected, so the executor is testable on its own and model-agnostic in the
sense S3.3 requires.

BRANCHES THAT DO NOT APPLY
--------------------------
S3.2: "conditional guards determine which branches are relevant after earlier
facts become known". A branch found NOT relevant used to simply never run. A
merge that listed it then waited for ever, and the decision came out UNKNOWN
even when every fact it needed was known -- a rule for night work left a
daytime question unanswered.

The fix is the one workflow engines use for the same problem, dead-path
elimination (WS-BPEL 2.0; Voelzer 2010, "if all inputs are false, all outputs
are false as well"): a branch that is skipped hands on a result saying so,
instead of nothing.

    S3.2's rule for merges -- "if a mandatory predecessor remains Unknown
    and the conclusion cannot otherwise be determined, the merged result also
    remains Unknown" -- is applied to guards and prerequisites as well: each
    decides only what it would decide however every UNKNOWN result turns out.

    guard open however the UNKNOWN results it reads
      turn out                                         -> the item runs
    guard closed however they turn out                 -> NOT_APPLICABLE
    open for some outcomes, closed for others          -> UNKNOWN, marked
                                                          "applicability
                                                          unknown"
    every prerequisite does not apply                  -> NOT_APPLICABLE
    every prerequisite does not apply or may not,
      and one may not                                  -> UNKNOWN, marked
                                                          "applicability
                                                          unknown"
    one prerequisite or more applies                   -> the item runs, and
                                                          its checker sees
                                                          which did not
    merge: inputs that do not apply are left out; if none is left, the merge
    does not apply; an exception that does not apply leaves the base rule to
    decide; a base rule that does not apply makes the whole exception merge
    not apply. An input of unknown applicability is tried both ways, and the
    merge is definite only if both give the same result.

These results are SETTLED by the executor itself, from certificates already
in the store. No verifier runs, so they are not operations run and add no
wave to the synchronization depth.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Sequence

from .certificate import Authority, Certificate, CertificateStore, Evidence, Status
from .network import Gate, MergeType, Network, Operation

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


def _applies(cert: Certificate) -> bool:
    return cert.status is not Status.NOT_APPLICABLE


def _merge_once(kind: MergeType, inputs: Sequence[Certificate],
                threshold_fn: Optional[Callable[[Sequence[Certificate]], Status]] = None
                ) -> Status:
    """A typed merge (S3.2) over inputs taken as they are. Inputs that do not
    apply are left out: a branch that is not relevant neither satisfies a rule
    nor breaks it."""
    if kind is MergeType.EXCEPTION:
        # inputs[0] is the base rule, inputs[1:] are relaxing branches. An
        # exception relaxes a rule; if the rule itself does not apply there is
        # nothing to relax, and the merge does not apply either.
        if not inputs or not _applies(inputs[0]):
            return Status.NOT_APPLICABLE
        base = _non_blocking(inputs[0])
        if base is Status.TRUE:
            return Status.TRUE
        # only an exception that actually APPLIES relaxes the rule; an UNKNOWN
        # one cannot rescue a failed base, so the result stays unresolved. One
        # that does not apply is left out, so with none left the base decides.
        return _kleene_or([base] + [c.status for c in inputs[1:] if _applies(c)])

    live = [c for c in inputs if _applies(c)]
    if not live:
        return Status.NOT_APPLICABLE
    if kind is MergeType.CONJUNCTION:
        # every branch must hold, so FALSE blocks -> adjust by authority
        return _kleene_and([_non_blocking(c) for c in live])
    if kind is MergeType.ALTERNATIVE:
        # a branch has to SATISFY; a recommendation not followed or an option
        # not taken satisfies nothing, so raw status is what counts
        return _kleene_or([c.status for c in live])
    if kind is MergeType.THRESHOLD:
        if threshold_fn is None:
            return Status.UNKNOWN     # no comparator supplied: unresolved, not False
        return threshold_fn(live)
    return Status.UNKNOWN


_MAX_UNCERTAIN_MERGE_INPUTS = 10


def merge_outcomes(kind: MergeType, inputs: Sequence[Certificate],
                   threshold_fn: Optional[Callable[[Sequence[Certificate]], Status]] = None
                   ) -> set:
    """Every result the merge could have had, had it been known whether each
    input of unknown applicability applies. Such an input is UNKNOWN if it
    applies (and three-valued logic already covers TRUE and FALSE), or
    NOT_APPLICABLE if it does not, so both are tried."""
    unsure = [i for i, c in enumerate(inputs) if c.applicability_unknown()]
    if len(unsure) > _MAX_UNCERTAIN_MERGE_INPUTS:
        return {Status.UNKNOWN, Status.NOT_APPLICABLE}
    out = set()
    for mask in product((False, True), repeat=len(unsure)):
        trial = list(inputs)
        for i, dead in zip(unsure, mask):
            if dead:
                trial[i] = replace(inputs[i], status=Status.NOT_APPLICABLE)
        out.add(_merge_once(kind, trial, threshold_fn))
    return out


def merge_statuses(kind: MergeType, inputs: Sequence[Certificate],
                   threshold_fn: Optional[Callable[[Sequence[Certificate]], Status]] = None
                   ) -> Status:
    """The merge's result: definite only if it is the same however every
    input of unknown applicability turns out (S3.2), else UNKNOWN."""
    outcomes = merge_outcomes(kind, inputs, threshold_fn)
    return next(iter(outcomes)) if len(outcomes) == 1 else Status.UNKNOWN


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
    # Settled by the executor without running a verifier (see the module
    # docstring). op id -> why. Neither is "skipped": each has a certificate.
    not_applicable: Dict[str, str] = field(default_factory=dict)
    undecided: Dict[str, str] = field(default_factory=dict)

    @property
    def synchronization_depth(self) -> int:
        """S4.4: the critical path, not the number of operations."""
        return len(self.waves)

    @property
    def operations_run(self) -> int:
        return sum(len(w) for w in self.waves)

    def unsupported_certification(self) -> bool:
        """UCR (S4.5): a DEFINITIVE terminal decision issued while a mandatory
        obligation never resolved. An UNKNOWN terminal is not unsupported
        certification; it is the abstention the architecture is supposed to
        produce. An obligation found NOT to apply is resolved: that was
        decided from established results and is recorded in the store.
        """
        if self.terminal is None or self.terminal.status is Status.UNKNOWN:
            return False
        unresolved_mandatory = [oid for oid, why in self.skipped.items()
                                if "optional" not in why]
        return bool(unresolved_mandatory)

    def unknown_certificates(self) -> List[str]:
        return [c.obligation_id or c.claim[:40] for c in self.store.all()
                if c.status is Status.UNKNOWN]

    def not_applicable_certificates(self) -> List[str]:
        return [c.obligation_id or c.claim[:40] for c in self.store.all()
                if c.status is Status.NOT_APPLICABLE]

    def non_conformances(self) -> List[str]:
        """FALSE Guidance: recorded, not refuting."""
        return [c.obligation_id or c.claim[:40] for c in self.store.all()
                if c.non_conformance()]


def _gate(o: Operation, store: CertificateStore) -> Gate:
    """Where o's guard stands. A bare predicate (a hand-built network with no
    `guard_eval`) says only open or not, never why, so "not open" is read as
    "not yet": it can never switch a branch off."""
    if o.guard_eval is not None:
        return o.guard_eval(store)
    if o.guard is not None:
        return Gate.OPEN if o.guard(store) else Gate.PENDING
    return Gate.OPEN


def _all_prerequisites_dead(o: Operation, store: CertificateStore) -> bool:
    """Dead-path elimination: a step whose every input does not apply does not
    apply either. One live input is enough to keep it: it then runs, and its
    checker sees which inputs did not apply."""
    if not o.requires:
        return False
    certs = [store.latest(s) for s in o.requires]
    return all(c is not None and c.status is Status.NOT_APPLICABLE for c in certs)


def _prerequisites_undecided(o: Operation, store: CertificateStore) -> bool:
    """Every prerequisite either does not apply or may not apply, and at
    least one may: then whether this step applies is unknown too, so it is
    not run (it would be checking something that may not apply)."""
    if not o.requires or o.merge is not None:
        # a merge works this out itself, input by input (merge_outcomes)
        return False
    certs = [store.latest(s) for s in o.requires]
    if any(c is None for c in certs):
        return False
    return (all(c.status is Status.NOT_APPLICABLE or c.applicability_unknown()
                for c in certs)
            and any(c.applicability_unknown() for c in certs))


def enabled(net: Network, store: CertificateStore, done: set) -> List[Operation]:
    """A_t in Eq 4: every prerequisite marked, and the guard open."""
    out = []
    for o in net.operations:
        if o.id in done:
            continue
        if not all(store.marked(s) for s in o.requires):
            continue
        if _all_prerequisites_dead(o, store) or _prerequisites_undecided(o, store):
            continue
        if _gate(o, store) is not Gate.OPEN:
            continue
        out.append(o)
    return out


def _read(store: CertificateStore, states: Sequence[str]) -> List[tuple]:
    return [(s, store.latest(s)) for s in dict.fromkeys(states)
            if store.latest(s) is not None]


def _executor_certificate(o: Operation, status: Status, reason: str,
                          read: List[tuple]) -> Certificate:
    """A result the executor settles itself, from certificates already in the
    store. It carries the evidence of the results that decided it, so the
    audit trail (S3.4) shows WHY a check was found not to apply."""
    # Only results that were actually established can explain a decision; an
    # UNKNOWN one the guard also read did not decide anything.
    deciding = [(s, c) for s, c in read if c.status is not Status.UNKNOWN]
    evidence: List[Evidence] = []
    seen: set = set()
    for _s, c in deciding:
        for e in c.evidence:
            if (e.type, e.id) not in seen:
                seen.add((e.type, e.id))
                evidence.append(e)
    confs = [c.confidence for _s, c in deciding if c.confidence]
    return Certificate(
        claim=o.claim, status=status,
        evidence=evidence if status is Status.NOT_APPLICABLE else [],
        normative_authority=o.normative_authority,
        confidence=(min(confs) if confs and status is Status.NOT_APPLICABLE else 0.0),
        verifier="executor", obligation_id=o.id,
        dependencies=[s for s, _c in read],
        provenance={"reason": reason,
                    "guard": o.guard_desc,
                    "decided_by": {s: c.status.value for s, c in read},
                    **({"applicability": "unknown"}
                       if status is Status.UNKNOWN else {})})


def _settle(net: Network, store: CertificateStore, done: set,
            trace: ExecutionTrace) -> None:
    """Give a result to every item whose fate is already decided without a
    verifier: it does not apply, or whether it applies is unknown. Repeats
    until nothing changes, because one such result can decide the next."""
    changed = True
    while changed:
        changed = False
        for o in net.operations:
            if o.id in done:
                continue
            if not all(store.marked(s) for s in o.requires):
                continue
            if _all_prerequisites_dead(o, store):
                why = "none of its prerequisites applies"
                cert = _executor_certificate(o, Status.NOT_APPLICABLE, why,
                                             _read(store, o.requires))
                trace.not_applicable[o.id] = why
            elif _prerequisites_undecided(o, store):
                why = ("whether it applies is unknown: its prerequisites "
                       "either do not apply or may not apply")
                cert = _executor_certificate(o, Status.UNKNOWN, why,
                                             _read(store, o.requires))
                trace.undecided[o.id] = why
            else:
                gate = _gate(o, store)
                if gate is Gate.CLOSED:
                    why = (f"its guard ({o.guard_desc}) is closed however "
                           f"the results it reads turn out")
                    cert = _executor_certificate(o, Status.NOT_APPLICABLE, why,
                                                 _read(store, o.guard_states))
                    trace.not_applicable[o.id] = why
                elif gate is Gate.UNDECIDED:
                    why = (f"whether it applies is unknown: its guard "
                           f"({o.guard_desc}) depends on a result that is "
                           f"UNKNOWN")
                    cert = _executor_certificate(o, Status.UNKNOWN, why,
                                                 _read(store, o.guard_states))
                    trace.undecided[o.id] = why
                else:
                    continue
            store.add(o.produces, cert)
            done.add(o.id)
            changed = True


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
        _settle(net, store, done, trace)
        if net.terminal and store.marked(net.terminal):
            break
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
    # one last pass: an item that does not feed the terminal may still be
    # settled as not applicable, and must not be reported as never resolved
    _settle(net, store, done, trace)

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
    if "applicability" in (cert.provenance or {}):
        # whether a check applies is the executor's call, not the checker's
        cert.provenance = {k: v for k, v in cert.provenance.items()
                           if k != "applicability"}
    if cert.status is Status.NOT_APPLICABLE:
        # Only the executor decides that a check does not apply, and only from
        # guards over established results. A checker that says so has not
        # checked the claim, so the claim stays unresolved.
        cert.provenance = dict(cert.provenance)
        cert.provenance["verifier_claimed_status"] = Status.NOT_APPLICABLE.value
        cert.status = Status.UNKNOWN
        cert.confidence = 0.0
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
    outcomes = merge_outcomes(op.merge, inputs, threshold_fn=fn)
    status = next(iter(outcomes)) if len(outcomes) == 1 else Status.UNKNOWN

    # The decision rests on the inputs that apply. Those that do not are
    # named in the provenance; their evidence is cited only when nothing
    # applied, because then it is the evidence for "does not apply".
    used = [c for c in inputs if _applies(c)] or list(inputs)
    evidence, seen = [], set()
    for c in used:
        for e in c.evidence:
            key = (e.type, e.id)
            if key not in seen:
                seen.add(key)
                evidence.append(e)
    confs = [c.confidence for c in used if c.confidence]
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
            "not_applicable": [s for s, c in zip(op.merge_inputs, inputs)
                               if not _applies(c)],
            **({"applicability": "unknown"}
               if status is Status.UNKNOWN and Status.NOT_APPLICABLE in outcomes
               else {}),
        },
    )
