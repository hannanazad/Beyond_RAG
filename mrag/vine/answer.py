"""From a certified decision to an answer — Eq 6 and S3.4.

    a = f_LM(q, C*, Pi_q)

WHAT THE PAPER ASKS FOR, AND WHAT IT FORBIDS
--------------------------------------------
S3.4: "This ordering is important: the language model does not independently
decide the final answer after retrieval. It verbalizes a decision that has
already been established through execution of the verification network. The
supporting evidence, normative authority, confidence, and provenance remain
attached to the decision, making the execution trace directly auditable."

So the model's job here is the opposite of its job in a verifier. A verifier
DECIDES one claim and must answer in constrained fields. This step decides
nothing and writes prose. The status, the citations and the confidence are
all fixed before the model is called, and none of them is read back out of
what it writes.

That is why the reply is not parsed. There is nothing in it to parse: every
machine-readable field of the answer already exists in the certificates.

ABSTENTION IS AN ANSWER
-----------------------
S3.4: execution runs "until the terminal proposition is either established,
refuted, or CANNOT BE RESOLVED from the available evidence. A definitive
standards decision is issued only when the terminal state has a valid
decision certificate."

An UNKNOWN terminal therefore does not get a hedged answer; it gets an
answer that says what was not established and which obligation left it open.
The abstract lists evidence-aware abstention as a contribution, and an
abstention that reads like a weak yes is not one.

WITHOUT A MODEL
---------------
`verbalize` is optional. With no model the answer is composed from the
certificates alone -- less fluent, entirely faithful, and testable at no
cost. It is also the honest floor: if the deterministic version already says
everything true, the model is adding fluency and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from .certificate import Authority, Certificate, Status
from .execute import ExecutionTrace, _failed_inputs
from .network import MergeType, Network

__all__ = ["Answer", "supporting_certificates", "build_answer_prompt",
           "compose", "answer"]


# --------------------------------------------------------------------------- #
# 1. Pi_q — the certificates the decision rests on
# --------------------------------------------------------------------------- #
def supporting_certificates(net: Network, trace: ExecutionTrace
                            ) -> List[Certificate]:
    """The executed certificate subnetwork behind the terminal, leaves first.

    Eq 6 takes Pi_q, not the whole store. The difference is real: the baseline
    compiler leaves Option paragraphs out of the base merge, so their
    certificates exist and are certified but support nothing. Quoting them in
    the answer would attribute the decision to evidence it did not rest on.
    """
    producer = {op.produces: op for op in net.operations}
    order: List[str] = []
    seen: Set[str] = set()

    def walk(state: str) -> None:
        if state in seen or state not in producer:
            return
        seen.add(state)
        op = producer[state]
        for upstream in (list(op.merge_inputs or []) + list(op.requires or [])
                         + list(op.guard_states or [])):
            walk(upstream)
        order.append(state)

    if net.terminal:
        walk(net.terminal)

    out: List[Certificate] = []
    for state in order:
        cert = trace.store.latest(state)
        if cert is not None:
            out.append(cert)
    return out


def _citations(support: Sequence[Certificate]) -> List[Dict[str, str]]:
    """Every distinct piece of evidence behind the decision, in first-use order."""
    out: List[Dict[str, str]] = []
    seen: Set[tuple] = set()
    for cert in support:
        for ev in cert.evidence:
            key = (ev.type, ev.id)
            if key in seen or ev.type == "given":
                # a fact from the question is what the case is, not a source
                continue
            seen.add(key)
            item = {"type": ev.type, "id": ev.id}
            if ev.inferred:
                # S3.3 grounds verification in the graph; a type this project
                # derived from a verb is not the same as one the manual
                # printed, and a citation should not blur the two.
                item["inferred"] = "true"
            out.append(item)
    return out


# --------------------------------------------------------------------------- #
# 2. The answer
# --------------------------------------------------------------------------- #
@dataclass
class Answer:
    text: str
    status: Status
    confidence: float
    citations: List[Dict[str, str]] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)      # claims left open
    non_conformances: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        return self.status is Status.UNKNOWN

    def as_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "status": self.status.value,
                "confidence": self.confidence, "citations": self.citations,
                "unresolved": self.unresolved,
                "non_conformances": self.non_conformances,
                "provenance": self.provenance}


def _terminal_op(net: Network) -> str:
    """The id of the operation that produces the terminal state."""
    op = next((o for o in net.operations if o.produces == net.terminal), None)
    return op.id if op else ""


def _found_false(net: Network, trace: ExecutionTrace) -> List[Certificate]:
    """The checks a FALSE decision rests on.

    Walk down from the terminal through the inputs that made each merge FALSE,
    read the way the executor read them (`_failed_inputs`: in a conjunction
    only an input that blocks at the merge's own heading), down to the checks
    themselves. For an exception that came out FALSE, the exceptions that were
    not available are walked too: they are why the failed base was not saved.
    Without this an answer said only that the final claim "does not hold",
    and a reader could not tell which requirement failed.
    """
    producer = {op.produces: op for op in net.operations}
    out: List[Certificate] = []
    seen: Set[str] = set()

    def walk(state: str) -> None:
        if state in seen:
            return
        seen.add(state)
        op, cert = producer.get(state), trace.store.latest(state)
        if op is None or cert is None or cert.status is not Status.FALSE:
            return
        if op.merge is None:
            out.append(cert)
            return
        inputs = [trace.store.latest(s) for s in op.merge_inputs]
        if any(c is None for c in inputs):
            return
        failed = {id(c) for c in _failed_inputs(op.merge, inputs, op.normative_authority)}
        if op.merge is MergeType.EXCEPTION:
            failed |= {id(c) for c in inputs[1:] if c.status is Status.FALSE}
        if not failed:          # a threshold merge: every input that failed
            failed = {id(c) for c in inputs if c.status is Status.FALSE}
        for s, c in zip(op.merge_inputs, inputs):
            if id(c) in failed:
                walk(s)

    if net.terminal:
        walk(net.terminal)
    return out


def _excused(net: Network, trace: ExecutionTrace) -> Set[str]:
    """States whose failure the network itself set aside: the base of an
    exception that applied, and the inputs of an alternative that was met
    another way. A Guidance item under them was not departed from -- the
    manual's exception or alternative covers it -- so it is not reported as
    a non-conformance."""
    producer = {op.produces: op for op in net.operations}
    out: Set[str] = set()

    def under(state: str) -> None:
        if state in out:
            return
        out.add(state)
        op = producer.get(state)
        if op is not None and op.merge is not None:
            for s in op.merge_inputs:
                under(s)

    for op in net.operations:
        cert = trace.store.latest(op.produces)
        if op.merge is None or not op.merge_inputs or cert is None or cert.status is not Status.TRUE:
            continue
        if op.merge is MergeType.EXCEPTION:
            base = trace.store.latest(op.merge_inputs[0])
            if base is not None and base.status is Status.FALSE:
                under(op.merge_inputs[0])
        elif op.merge is MergeType.ALTERNATIVE:
            for s in op.merge_inputs:
                c = trace.store.latest(s)
                if c is not None and c.status is Status.FALSE:
                    under(s)
    return out


def _heading(cert: Certificate) -> str:
    return cert.normative_authority.value.capitalize()


def _bare(claim: str) -> str:
    """A claim without its closing full stop, to be listed inside a sentence."""
    return str(claim or "").strip().rstrip(".").strip()


def _facts(net: Network, trace: ExecutionTrace) -> Dict[str, Any]:
    terminal = trace.terminal
    support = supporting_certificates(net, trace)
    # The terminal's own certificate is excluded: that it is unresolved is the
    # headline, and repeating it as a "check left open" makes an abstention
    # read as though two things failed when one did. What a reader needs is
    # the UPSTREAM check that left it open.
    upstream = [c for c in support if c.obligation_id != _terminal_op(net)]
    unresolved = [c.claim for c in upstream if c.status is Status.UNKNOWN]
    producer = {op.produces: op for op in net.operations}
    check_ids = {op.id for op in net.operations if op.merge is None}
    state_of = {op.id: op.produces for op in net.operations}
    # Why a FALSE decision does not hold: the checks it rests on.
    found_false = (_found_false(net, trace)
                   if terminal is not None and terminal.status is Status.FALSE else [])
    # What still holds of a decision that does not: the parts of the final
    # conjunction that came out TRUE. A question with several parts gets one
    # final claim joining them, and "does not hold" alone hid that most of
    # them did.
    still_true: List[str] = []
    top = producer.get(net.terminal) if net.terminal else None
    if found_false and top is not None and top.merge is MergeType.CONJUNCTION:
        for s in top.merge_inputs:
            c = trace.store.latest(s)
            if c is not None and c.status is Status.TRUE:
                still_true.append(c.claim)
    # A Guidance check that failed is NOT a refutation -- the executor lets it
    # pass a conjunction -- but it is a finding, and an answer that dropped it
    # would be complete only by omission. Checks only: a Guidance merge that
    # failed repeats the item that failed in it, in vaguer words. Not one the
    # network set aside (an exception or an alternative covered it), and not
    # one already listed as a reason the decision fails.
    excused = _excused(net, trace)
    listed = {c.obligation_id for c in found_false}
    # A claim ABOUT THE MANUAL ("the manual recommends X here") found not true is
    # not a recommendation the case failed to follow (compile.Obligation.about,
    # 18 Oct 2026); a plan that does not say what its claims are about reads as before.
    about_manual = {op.id for op in net.operations if getattr(op, "about", "") == "manual"}
    non_conf = [c.claim for c in upstream
                if c.non_conformance() and c.obligation_id in check_ids
                and c.obligation_id not in about_manual
                and state_of.get(c.obligation_id) not in excused
                and c.obligation_id not in listed]
    # Checks found not to apply, and the established results that decided
    # that. Leaving them out would hide why part of the rule was not used.
    not_applicable = [c.claim for c in upstream
                      if c.status is Status.NOT_APPLICABLE]
    deciding: List[str] = []
    for c in support:
        if c.status is not Status.NOT_APPLICABLE:
            continue
        for state, value in (c.provenance.get("decided_by") or {}).items():
            src = trace.store.latest(state)
            # only results actually established (TRUE or FALSE) decided it
            if src is None or src.status not in (Status.TRUE, Status.FALSE):
                continue
            line = f"{src.claim} ({value})"
            if line not in deciding:
                deciding.append(line)
    return {
        "terminal": terminal, "support": support,
        "unresolved": unresolved, "non_conformances": non_conf,
        "found_false": found_false, "still_true": still_true,
        "not_applicable": not_applicable, "deciding": deciding,
        "citations": _citations(support),
        # A merge is as weak as its weakest input, and the terminal already
        # carries that. But an UNKNOWN terminal is not a weak decision, it is
        # no decision, and the merge's confidence is the minimum over inputs
        # that DID resolve -- so an abstention was coming out at 0.9. A number
        # that high next to "cannot be answered" invites a reader to treat the
        # abstention as a near miss.
        "confidence": (terminal.confidence
                       if terminal and terminal.status is not Status.UNKNOWN
                       else 0.0),
    }


def compose(query: str, net: Network, trace: ExecutionTrace) -> Answer:
    """The answer with no model at all. Faithful, not fluent."""
    f = _facts(net, trace)
    terminal: Optional[Certificate] = f["terminal"]
    status = terminal.status if terminal else Status.UNKNOWN

    if trace.problems:
        text = ("The verification network was rejected before execution, so "
                "no decision was reached: " + "; ".join(trace.problems))
    elif status is Status.UNKNOWN:
        opened = f["unresolved"] or ["the terminal proposition"]
        text = ("This cannot be answered from the evidence available. "
                + str(len(opened)) + " required check"
                + ("s were" if len(opened) != 1 else " was")
                + " left unresolved: " + "; ".join(opened[:4])
                + ("." if len(opened) <= 4 else ", and others."))
    elif status is Status.NOT_APPLICABLE:
        # Not a yes and not a no: the provisions checked do not reach this
        # situation, and the answer says which established results decided it.
        text = (f"{terminal.claim} — this does not apply to the situation "
                "described.")
        if f["deciding"]:
            text += (" Decided by: " + "; ".join(f["deciding"][:4])
                     + ("." if len(f["deciding"]) <= 4 else ", and others."))
    else:
        verdict = "holds" if status is Status.TRUE else "does not hold"
        text = f"{terminal.claim} — this {verdict}."
        # Each claim is written as a statement that would make the check pass,
        # so it is named as found NOT true; printed bare it read as if it held.
        # A one-check plan's check is the final claim itself: not repeated.
        why = [c for c in f["found_false"] if _bare(c.claim) != _bare(terminal.claim)]
        if why:
            items = [f"{_bare(c.claim)} ({_heading(c)})" for c in why]
            text += (" It does not hold because these were found not true: "
                     + "; ".join(items[:6]) + ("." if len(items) <= 6 else "; and others."))
        if f["still_true"]:
            text += (" These parts do hold: " + "; ".join(_bare(c) for c in f["still_true"][:4]) + ".")
        if f["non_conformances"]:
            # "does not refute" only makes sense next to a decision that holds;
            # beside one that does not, it read as if the Guidance item were
            # the reason for the decision, or excused it.
            lead = (" Recorded as non-conformance with Guidance, which does "
                    "not refute the decision (found not true): " if status is Status.TRUE
                    else " Also recorded as non-conformance with Guidance (found not true): ")
            text += lead + "; ".join(_bare(c) for c in f["non_conformances"][:3]) + "."
        if f["not_applicable"]:
            text += (" Not applicable here: "
                     + "; ".join(f["not_applicable"][:3])
                     + ("." if len(f["not_applicable"]) <= 3 else ", and others."))

    return Answer(text=text, status=status, confidence=f["confidence"],
                  citations=f["citations"], unresolved=f["unresolved"],
                  non_conformances=f["non_conformances"],
                  provenance={"query": query, "verbalized": False,
                              "found_false": [c.obligation_id for c in f["found_false"]],
                              "supporting_certificates": len(f["support"]),
                              "synchronization_depth": trace.synchronization_depth,
                              "operations_run": trace.operations_run})


def build_answer_prompt(query: str, net: Network, trace: ExecutionTrace) -> str:
    """The prompt for Eq 6. It states the decision; it does not ask for one."""
    f = _facts(net, trace)
    terminal: Optional[Certificate] = f["terminal"]
    status = (terminal.status if terminal else Status.UNKNOWN).value

    lines: List[str] = []
    for cert in f["support"]:
        ids = ", ".join(e.id for e in cert.evidence if e.type != "given") or "no evidence"
        facts = [e.id for e in cert.evidence if e.type == "given"]
        lines.append(f"- [{cert.status.value}] {cert.claim}\n"
                     f"  authority: {cert.normative_authority.value}"
                     f"  verifier: {cert.verifier}"
                     f"  confidence: {cert.confidence:.2f}\n"
                     f"  evidence: {ids}"
                     + (f"\n  facts from the question it used: {', '.join(facts)}"
                        if facts else ""))

    if status == "UNKNOWN":
        guidance = (
            "No decision was established. Say plainly that the question cannot "
            "be answered from the available evidence, name the checks that were "
            "left unresolved, and do not offer a likely answer or a guess. An "
            "abstention that reads like a cautious yes is wrong.")
    elif status == Status.NOT_APPLICABLE.value:
        guidance = (
            "The decision above has already been established by executing a "
            "verification network: the provisions checked do not apply to the "
            "situation described. Say so plainly and name the established "
            "results that decided it. Do not say that the situation meets or "
            "breaks the provisions, and do not add reasoning of your own.")
    else:
        guidance = (
            "The decision above has already been established by executing a "
            "verification network. Do not re-decide it, do not soften it, and "
            "do not add reasoning of your own. Write the answer a reader needs, "
            "using only the claims, reasons and evidence listed: the decision "
            "first; if it does not hold, which checks were found not true and "
            "what the manual requires there, as their reasons state; the parts "
            "that do hold; and any Guidance not followed, named as a "
            "recommendation rather than a requirement. Each claim listed is "
            "written as the statement that was checked, so a claim found not "
            "true must be reported as not true. Plain prose, no headings, at "
            "most 200 words.")

    def reason(cert: Certificate) -> str:
        r = str(cert.provenance.get("reason") or "").strip()
        return f"\n  the checker's reason: {r[:600]}" if r else ""

    parts = [
        f"QUESTION\n{query}",
        "",
        f"DECISION\n{status}"
        + (f" — {terminal.claim}" if terminal else ""),
        "",
        "SUPPORTING CERTIFICATES\n" + ("\n".join(lines) or "(none)"),
    ]
    if f["found_false"]:
        parts += ["", "WHY IT DOES NOT HOLD (each of these was found NOT true)\n"
                  + "\n".join(f"- {c.claim}  [{c.normative_authority.value}]" + reason(c)
                              for c in f["found_false"])]
    if f["still_true"]:
        parts += ["", "PARTS THAT DO HOLD\n"
                  + "\n".join(f"- {c}" for c in f["still_true"])]
    if f["unresolved"]:
        parts += ["", "LEFT UNRESOLVED\n"
                  + "\n".join(f"- {c}" for c in f["unresolved"])]
    if f["non_conformances"]:
        nc = {c.claim: c for c in f["support"] if c.non_conformance()}
        parts += ["", "NON-CONFORMANCE WITH GUIDANCE (found NOT true; does not refute)\n"
                  + "\n".join(f"- {c}" + (reason(nc[c]) if c in nc else "")
                              for c in f["non_conformances"])]
    if f["not_applicable"]:
        parts += ["", "FOUND NOT TO APPLY HERE\n"
                  + "\n".join(f"- {c}" for c in f["not_applicable"])]
    if f["deciding"]:
        parts += ["", "DECIDED BY (established results)\n"
                  + "\n".join(f"- {c}" for c in f["deciding"])]
    parts += ["", guidance, "",
              "Cite evidence by the ids shown. Cite nothing else."]
    return "\n".join(parts)


def answer(query: str, net: Network, trace: ExecutionTrace,
           verbalize: Optional[Callable[[str, List[str]], str]] = None,
           ) -> Answer:
    """Eq 6. Compose the answer, optionally having a model write the prose.

    The status, citations and confidence come from the certificates either
    way. If the model is unavailable or returns nothing, the deterministic
    text stands: an answer step that failed must not turn a certified
    decision into no answer at all.
    """
    base = compose(query, net, trace)
    if verbalize is None:
        return base

    prompt = build_answer_prompt(query, net, trace)
    # the composed text is kept beside the model's, so the two can be read
    # side by side and the model's prose checked against the certificates
    base.provenance["template_text"] = base.text
    try:
        text = (verbalize(prompt, []) or "").strip()
    except Exception as e:                                    # noqa: BLE001
        base.provenance["verbalization_error"] = repr(e)
        return base
    if not text:
        base.provenance["verbalization_error"] = "the model returned nothing"
        return base

    base.text = text
    base.provenance["verbalized"] = True
    base.provenance["prompt_chars"] = len(prompt)
    # The status is NOT re-read from the prose. S3.4 is explicit that the
    # model verbalizes a decision already established; reading a status back
    # out of what it wrote would hand the decision to it after all.
    return base
