"""Comparisons over the facts of the case are decided by arithmetic (17 Oct 2026).

1. The symbolic evaluator reads a comparison the claim states itself, when the
   value it names is also stated by a fact given in the question: "The flow of
   900 units is 500 units or more" with the fact "The flow is 900 units". S3.3
   prefers a deterministic operator "whenever the obligation admits a more
   constrained verification mechanism". Before, given facts were not read at all
   (only measurements from earlier results), so such checks went to the
   language model.
2. It decides only when that is unambiguous: one comparison phrase; one other
   number in the claim, confirmed by a fact; no fraction; no multiplier
   ("3 times the width"); units of the same kind (feet against inches is
   converted; feet against seconds is not decided).
3. The language-model checker: a reply that names a supplied manual provision as
   its basis, but lists only the question's facts as evidence, is read as citing
   that basis (the prompt asks for the basis to be listed under evidence).
   Before, such a correct answer was turned into UNKNOWN. A reply whose basis is
   a fact, or which names no basis, is still downgraded.

Everything here is made up (units, panels, made-up sections). No sample
question, gold answer or MUTCD text is used.

Run: python3 tests/test_stated_comparison.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine import Evidence, NetworkSpec, Status, execute, instantiate
from mrag.vine.model_verifiers import make_llm_verifier
from mrag.vine.symbolic import make_rule_evaluator, stated_comparison

T, F, U = Status.TRUE, Status.FALSE, Status.UNKNOWN
checks = 0


def check(cond, what):
    global checks
    assert cond, what
    checks += 1
    print(f"  ok  {what}")


G = [("f1", "The made-up strip has a 30-foot clear zone."),
     ("f2", "The panel flow is 1,250 units per hour."),
     ("f3", "The lamp gives 52 flashes per minute."),
     ("f4", "The strip is 2 miles long and has 3 lanes.")]


def decide(claim, given=G):
    r = stated_comparison(claim, given)
    return None if r is None else r["status"]


print("1. A comparison the claim states, its value given in the question")
check(decide("The 30-foot clear zone is 30 feet or more.") is T, "30 ft is 30 ft or more: TRUE (inclusive bound)")
check(decide("The 30-foot clear zone is at least 36 feet.") is F, "30 ft is at least 36 ft: FALSE")
check(decide("The flow of 1,250 units per hour is 1,000 units per hour or greater.") is T,
      "a thousands separator is read as one number")
check(decide("The flow of 1,250 units per hour is not more than 1,200 units per hour.") is F,
      "'not more than' is at most")
check(decide("The rate of 52 flashes per minute is in excess of 60 flashes per minute.") is F,
      "'in excess of' is greater than")
check(decide("The 30-foot clear zone is not less than 300 inches.") is T, "feet against inches: converted (360 in)")
r = stated_comparison("The 30-foot clear zone is 30 feet or more.", G)
check(r["facts"] == ["f1"] and r["comparator"] == ">=" and r["bound"] == 30.0,
      "the fact that states the value is recorded")

print("2. Anything ambiguous is left to the interpreting checker")
check(decide("The 30-foot clear zone is at most 3 times the panel height.") is None, "a multiplier")
check(decide("The 2-mile strip with 3 lanes is at least 1 mile long.") is None,
      "two other numbers in the claim: which one is compared is not clear")
check(decide("The clear zone is at least 3/4 of the strip.") is None, "a fraction")
check(decide("The 30-foot clear zone is at least 20 seconds.") is None, "units of different kinds")
check(decide("The 40-foot clear zone is 30 feet or more.") is None,
      "the value is not stated by any fact of the case (the claim cannot invent it)")
check(decide("The 30-foot clear zone is at least 20 feet and at most 40 feet.") is None,
      "two comparisons in one claim")
check(decide("Section 9Z.04 paragraph 2 requires a 30-foot clear zone.") is None, "no comparison phrase")
for c in ("The 30-foot clear zone is no wider than 20 feet.", "The 30-foot clear zone is not at least 36 feet.",
          "The 30-foot clear zone is not in excess of 20 feet.", "The 30-foot clear zone isn't more than 20 feet.",
          "The 30-foot clear zone does not have more than 20 feet."):
    check(decide(c) is None, f"a 'not' outside the phrase turns it round: left open ({c[24:52]!r})")
check(decide("The 3 lanes are no fewer than 2 lanes.", [("f1", "The strip has 3 lanes.")]) is T,
      "'no fewer than' is at least")
G2 = [("f1", "The ZZ1-1 panel on the post is 48 inches wide."), ("f2", "There are 2 panels.")]
check(decide("The ZZ1-1 panel is at least 36 inches wide.", G2) is None,
      "a number inside a code is not the case's value")
check(decide("The 48-inch ZZ1-1 panel is at least 36 inches wide.", G2) is T, "the value beside the code is")
check(decide("Both of the 2 panels are at least 36 inches wide.", G2) is None,
      "a count is not compared with a width")
check(decide("The 30-foot clear zone is at least 0.01 mi.") is F, "miles converted (0.01 mi is 52.8 ft)")
check(decide("The 30-foot clear zone is at least 20.") is None and decide("The zone, 30, is at least 20 feet.") is None,
      "a number with no unit is not compared")
check(decide("The 3 lanes are at least 2 vehicles.", [("f1", "The strip has 3 lanes.")]) is None,
      "two different count words: not compared")

print("3. In a network: the symbolic checker decides it, with the fact and the source paragraph")


def net_with(claim, facts):
    spec = NetworkSpec.from_dict({
        "query": "made-up", "terminal": "o1",
        "facts": [{"id": f"f{i + 1}", "fact": t} for i, t in enumerate(facts)],
        "obligations": [{"id": "o1", "claim": claim, "type": "numerical", "authority": "STANDARD",
                         "requires": [], "evidence_hint": [], "source_chunk": "MUTCD11e_9Z04_Standard_02",
                         "verifier": "symbolic"}]})
    net, problems = instantiate(spec)
    assert problems == [], problems
    return net


net = net_with("The 30-foot clear zone is 30 feet or more.", ["The made-up strip has a 30-foot clear zone."])
tr = execute(net, {"symbolic": make_rule_evaluator()})
c = tr.terminal
check(c.status is T and c.verifier == "symbolic", "decided TRUE by the symbolic checker, no model")
check(Evidence("given", "f1") in c.evidence and Evidence("chunk", "MUTCD11e_9Z04_Standard_02") in c.evidence,
      "its evidence is the given fact and the paragraph the bound comes from")
check(c.provenance["stated_comparison"]["phrase"] == "30 feet or more", "the phrase it read is recorded")
net = net_with("The 30-foot clear zone is 30 feet or more.", ["The made-up strip is gravel."])
tr = execute(net, {"symbolic": make_rule_evaluator()})
check(tr.terminal.status is U and "interpreting verifier" in tr.terminal.provenance["reason"],
      "no fact states the value: UNKNOWN, handed on as before")

print("4. The language-model checker: a named manual basis counts as cited")
CHUNKS = [{"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard",
           "text": "the clear zone shall be 30 feet or more"}]


class Retriever:
    def retrieve_for_obligation(self, query, obligation, certificates=None, top_k=None):
        return SimpleNamespace(chunks=[dict(c) for c in CHUNKS], figures=[], debug={})


def run_reply(reply):
    spec = NetworkSpec.from_dict({
        "query": "made-up", "terminal": "o1",
        "facts": [{"id": "f1", "fact": "The made-up strip has a 30-foot clear zone."}],
        "obligations": [{"id": "o1", "type": "classification",
                         "claim": "The strip's clear zone meets the clear-zone rule.", "authority": "STANDARD", "requires": [],
                         "evidence_hint": [], "source_chunk": "Z1"}]})
    net, problems = instantiate(spec)
    assert not problems, problems
    v = make_llm_verifier(lambda p, i: json.dumps(reply), Retriever(), query="made-up", use_pointers=False)
    return execute(net, {"llm": v}).terminal


c = run_reply({"status": "TRUE", "evidence": ["f1"], "basis": "Z1", "confidence": 0.9, "reason": "30 >= 30"})
check(c.status is T and Evidence("chunk", "Z1") in c.evidence and c.provenance["basis_counted_as_evidence"] == "Z1",
      "basis Z1 named, only f1 listed: TRUE, and Z1 is cited (it was turned into UNKNOWN)")
c = run_reply({"status": "TRUE", "evidence": ["f1"], "basis": "f1", "confidence": 0.9, "reason": "r"})
check(c.status is U and "only facts" in c.provenance["downgraded"], "the basis is a fact: still downgraded")
c = run_reply({"status": "TRUE", "evidence": ["f1"], "confidence": 0.9, "reason": "r"})
check(c.status is U and "only facts" in c.provenance["downgraded"], "no basis: still downgraded")
c = run_reply({"status": "TRUE", "evidence": ["f1"], "basis": "Z9", "confidence": 0.9, "reason": "r"})
check(c.status is U, "a basis that was never supplied is dropped, and the answer is still downgraded")

print(f"\nALL STATED-COMPARISON TESTS PASSED ({checks} checks)")
