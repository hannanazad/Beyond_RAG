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
from .execute import ExecutionTrace
from .network import Network

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
            if key in seen:
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


def _facts(net: Network, trace: ExecutionTrace) -> Dict[str, Any]:
    terminal = trace.terminal
    support = supporting_certificates(net, trace)
    # The terminal's own certificate is excluded: that it is unresolved is the
    # headline, and repeating it as a "check left open" makes an abstention
    # read as though two things failed when one did. What a reader needs is
    # the UPSTREAM check that left it open.
    upstream = [c for c in support if c.obligation_id != _terminal_op(net)]
    unresolved = [c.claim for c in upstream if c.status is Status.UNKNOWN]
    # A Guidance check that failed is NOT a refutation -- the executor lets it
    # pass a conjunction -- but it is a finding, and an answer that dropped it
    # would be complete only by omission.
    non_conf = [c.claim for c in upstream if c.non_conformance()]
    return {
        "terminal": terminal, "support": support,
        "unresolved": unresolved, "non_conformances": non_conf,
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
    else:
        verdict = "holds" if status is Status.TRUE else "does not hold"
        text = f"{terminal.claim} — this {verdict}."
        if f["non_conformances"]:
            text += (" Recorded as non-conformance with Guidance, which does "
                     "not refute the decision: "
                     + "; ".join(f["non_conformances"][:3]) + ".")

    return Answer(text=text, status=status, confidence=f["confidence"],
                  citations=f["citations"], unresolved=f["unresolved"],
                  non_conformances=f["non_conformances"],
                  provenance={"query": query, "verbalized": False,
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
        ids = ", ".join(e.id for e in cert.evidence) or "no evidence"
        lines.append(f"- [{cert.status.value}] {cert.claim}\n"
                     f"  authority: {cert.normative_authority.value}"
                     f"  verifier: {cert.verifier}"
                     f"  confidence: {cert.confidence:.2f}\n"
                     f"  evidence: {ids}")

    guidance = (
        "The decision above has already been established by executing a "
        "verification network. Do not re-decide it, do not soften it, and do "
        "not add reasoning of your own. Write the answer a reader needs, "
        "using only the claims and evidence listed."
        if status != "UNKNOWN" else
        "No decision was established. Say plainly that the question cannot be "
        "answered from the available evidence, name the checks that were left "
        "unresolved, and do not offer a likely answer or a guess. An "
        "abstention that reads like a cautious yes is wrong."
    )

    parts = [
        f"QUESTION\n{query}",
        "",
        f"DECISION\n{status}"
        + (f" — {terminal.claim}" if terminal else ""),
        "",
        "SUPPORTING CERTIFICATES\n" + ("\n".join(lines) or "(none)"),
    ]
    if f["unresolved"]:
        parts += ["", "LEFT UNRESOLVED\n"
                  + "\n".join(f"- {c}" for c in f["unresolved"])]
    if f["non_conformances"]:
        parts += ["", "NON-CONFORMANCE WITH GUIDANCE (does not refute)\n"
                  + "\n".join(f"- {c}" for c in f["non_conformances"])]
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
