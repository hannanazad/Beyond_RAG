"""Tests for the answer step — Eq 6.

The model is a stub throughout, so this runs at no cost. The point being
tested is not fluency: it is that the status, the citations and the
confidence come from the certificates and never from the prose.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import (Authority, Certificate, CertificateStore, Evidence,
                       MergeType, Network, Operation, Status, execute)
from mrag.vine.answer import (Answer, answer, build_answer_prompt, compose,
                              supporting_certificates)


def net_with_option():
    """gate -> a, b (both in the base) and opt (in the network, supporting
    nothing) -> conjunction."""
    net = Network(query="is a Curve sign required?", terminal="s_m")
    net.states = {"s_gate", "s_a", "s_b", "s_opt", "s_m"}
    net.operations = [
        Operation("gate", "Table 2C-4 indicates a sign is required", "s_gate",
                  [], "calculator"),
        Operation("a", "a Curve sign shall be used", "s_a", ["s_gate"], "llm"),
        Operation("b", "the layout matches Figure 2C-1", "s_b", ["s_gate"], "vlm",
                  normative_authority=Authority.GUIDANCE),
        Operation("opt", "a Winding Road sign may be used instead", "s_opt",
                  ["s_gate"], "llm", normative_authority=Authority.OPTION),
        Operation("m", "the requirements of 2C.07 are met", "s_m",
                  ["s_a", "s_b"], "merge", merge=MergeType.CONJUNCTION,
                  merge_inputs=["s_a", "s_b"]),
    ]
    return net


NET = net_with_option()
assert NET.validate() == [], NET.validate()
QUERY = "Is a Curve sign required in advance of this curve?"


def verifier(statuses, evidence=None):
    ev = evidence or {}

    def run(op, store):
        return Certificate(
            claim=op.claim, status=statuses.get(op.id, Status.TRUE),
            evidence=[Evidence(*e) for e in ev.get(op.id, [])],
            normative_authority=op.normative_authority,
            confidence=0.9, verifier=op.verifier, obligation_id=op.id)
    return run


EVID = {"gate": [("table", "Table 2C-4")],
        "a": [("chunk", "MUTCD11e_2C07_Standard_01")],
        "b": [("figure", "Figure 2C-1")],
        "opt": [("chunk", "MUTCD11e_2C07_Option_05")]}


def run(statuses):
    fn = verifier(statuses, EVID)
    return execute(NET, {k: fn for k in ("llm", "vlm", "calculator")})


# ---- 1. Pi_q is what the decision rests on, not the whole store -----------
trace = run({})
support = supporting_certificates(NET, trace)
ids = [c.obligation_id for c in support]
assert ids == ["gate", "a", "b", "m"], ids
assert "opt" not in ids           # certified, but supports nothing
assert len(trace.store.all()) == 5
print("1. the supporting subnetwork excludes an Option that nothing consumes")

# ---- 2. citations come from the certificates ------------------------------
a = compose(QUERY, NET, trace)
assert a.status is Status.TRUE
assert [c["id"] for c in a.citations] == [
    "Table 2C-4", "MUTCD11e_2C07_Standard_01", "Figure 2C-1"]
assert "MUTCD11e_2C07_Option_05" not in [c["id"] for c in a.citations]
print("2. citations are drawn from Pi_q, in first-use order")

# ---- 3. an inferred type is flagged in the citation -----------------------
def inferred_run(op, store):
    return Certificate(claim=op.claim, status=Status.TRUE,
                       evidence=[Evidence("chunk", "MUTCD11e_TBLNOTE_4C-1_03",
                                          inferred=True)],
                       normative_authority=op.normative_authority,
                       confidence=1.0, verifier=op.verifier, obligation_id=op.id)


t = execute(NET, {k: inferred_run for k in ("llm", "vlm", "calculator")})
cites = compose(QUERY, NET, t).citations
assert any(c.get("inferred") == "true" for c in cites)
print("3. a type derived from the verb is marked in the citation, not blurred "
      "with a printed heading")

# ---- 4. an unresolved branch produces an abstention, not a hedge ----------
trace = run({"b": Status.UNKNOWN})
a = compose(QUERY, NET, trace)
assert a.status is Status.UNKNOWN and a.abstained
assert a.confidence == 0.0 or a.confidence < 0.9
assert "cannot be answered" in a.text
assert "the layout matches Figure 2C-1" in a.text     # WHICH check was open
assert "probably" not in a.text.lower() and "likely" not in a.text.lower()
print("4. an unresolved check gives an abstention that names what was left "
      "open")

# ---- 5. Guidance that failed is reported, and does not refute -------------
trace = run({"b": Status.FALSE})
a = compose(QUERY, NET, trace)
assert a.status is Status.TRUE                        # GUIDANCE FALSE does not refute
assert a.non_conformances == ["the layout matches Figure 2C-1"]
assert "non-conformance" in a.text.lower()
print("5. a failed Guidance check is surfaced as non-conformance, and the "
      "decision still holds")

# ---- 6. a Standard that failed does refute --------------------------------
trace = run({"a": Status.FALSE})
a = compose(QUERY, NET, trace)
assert a.status is Status.FALSE and "does not hold" in a.text
print("6. a failed Standard refutes")

# ---- 7. the prompt states the decision and forbids re-deciding it ---------
trace = run({})
prompt = build_answer_prompt(QUERY, NET, trace)
assert QUERY in prompt and "DECISION\nTRUE" in prompt
assert "Do not re-decide it" in prompt
assert "MUTCD11e_2C07_Standard_01" in prompt
assert "MUTCD11e_2C07_Option_05" not in prompt        # not in Pi_q
assert "Cite nothing else" in prompt
print("7. the prompt supplies the decision and the evidence, and forbids "
      "re-deciding")

# ---- 8. the abstention prompt is different, on purpose --------------------
prompt = build_answer_prompt(QUERY, NET, run({"b": Status.UNKNOWN}))
assert "No decision was established" in prompt
assert "reads like a cautious yes is wrong" in prompt
assert "LEFT UNRESOLVED" in prompt
print("8. an abstention prompt tells the model not to write a cautious yes")

# ---- 9. the model writes the prose and nothing else ------------------------
trace = run({"b": Status.UNKNOWN})
said = {}


def stub(prompt, images):
    said["prompt"] = prompt
    # a model that ignores the instruction and answers anyway
    return "Yes, a Curve sign is definitely required here."


a = answer(QUERY, NET, trace, stub)
assert a.text.startswith("Yes, a Curve sign")          # the prose is used
assert a.status is Status.UNKNOWN                      # the status is NOT
assert a.abstained and a.provenance["verbalized"] is True
assert a.unresolved == ["the layout matches Figure 2C-1"]
print("9. a model that answers anyway changes the wording, never the status")

# ---- 10. a failed model leaves the decision answerable --------------------
def boom(prompt, images):
    raise RuntimeError("rate limited")


a = answer(QUERY, NET, run({}), boom)
assert a.status is Status.TRUE and a.text
assert "rate limited" in a.provenance["verbalization_error"]
assert answer(QUERY, NET, run({}), lambda p, i: "   ").provenance[
    "verbalization_error"]
print("10. a crashed or empty model falls back to the composed text rather "
      "than to no answer")

# ---- 11. a rejected network never yields an answer ------------------------
broken = Network(query="q", terminal="s_nowhere")
broken.states = {"s_x"}
broken.operations = [Operation("x", "a claim", "s_x", ["s_ghost"], "llm")]
t = execute(broken, {"llm": verifier({})})
assert t.problems
a = compose(QUERY, broken, t)
assert a.status is Status.UNKNOWN and "rejected before execution" in a.text
print("11. a rejected network reports the rejection instead of an answer")

# ---- 12. the answer carries the audit trail -------------------------------
a = compose(QUERY, NET, run({}))
assert a.provenance["supporting_certificates"] == 4
assert a.provenance["synchronization_depth"] == 3
assert a.as_dict()["status"] == "TRUE"
print("12. the answer carries depth, support count and a serialisable form")

print("\nALL ANSWER STEP TESTS PASSED")
