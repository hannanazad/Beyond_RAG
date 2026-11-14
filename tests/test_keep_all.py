"""The 10 Nov 2026 instruction changes (made-up data): nothing that bears on the question is dropped.
1. The parser's instructions no longer tell it to cut, and tell it to keep every provision that bears.
2. The answer writer has no length limit, asks for every check, and is shown checks the decision
   does not rest on, marked as such."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import Certificate, NetworkSpec, Status, execute, instantiate
from mrag.vine.answer import build_answer_prompt
from mrag.vine.parser import PARSER_CONTRACT, build_parser_prompt

ok = 0
def check(c, what):
    global ok
    assert c, what
    ok += 1
    print("  ok ", what)

check("nothing more" not in PARSER_CONTRACT and "Leave those out" not in PARSER_CONTRACT,
      "the two cutting lines are gone")
check("Do not leave out\nany provision that bears on the question" in PARSER_CONTRACT
      and "Leave out only provisions that have\nnothing to do with it." in PARSER_CONTRACT,
      "the keep-everything-that-bears instruction is there")
check("The terminal depends on every obligation" not in PARSER_CONTRACT, "no rule that rewires the decision (review)")
p = build_parser_prompt("A made-up question?", [{"chunk_id": "X_Standard_01", "section_id": "9Z.01",
                        "content_type": "Standard", "text": "A made-up rule."}])
check("Find every provision shown that bears on the" in p and "A made-up question?" in p, "it reaches the prompt")

T, F = Status.TRUE, Status.FALSE
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")
def ob(i, claim, auth):
    return {"id": i, "claim": claim, "type": "applicability", "authority": auth, "requires": [],
            "evidence_hint": [], "source_chunk": "made_up"}
spec = NetworkSpec.from_dict({"query": "q", "terminal": "m", "obligations": [
    ob("a", "Device D is the required colour.", "STANDARD"),
    ob("b", "Device D is at the recommended height.", "GUIDANCE"),
    ob("c", "The manual allows a plaque below Device D here.", "OPTION")],
    "merges": [{"id": "m", "claim": "Device D meets the manual.", "kind": "conjunction",
                "inputs": ["a", "b"], "authority": "STANDARD"}]})
net, problems = instantiate(spec)
assert problems == [], problems
table = {"a": T, "b": F, "c": T}
def verify(op, store):
    return Certificate(claim=op.claim, status=table[op.id], normative_authority=op.normative_authority,
                       verifier=op.verifier, obligation_id=op.id, confidence=0.9,
                       provenance={"reason": "made-up reason " + op.id})
tr = execute(net, {v: verify for v in ALL})
prompt = build_answer_prompt("q", net, tr)
check("200 words" not in prompt and "There is no length limit: leave nothing out." in prompt, "no length limit")
check("each Option\nand what it allows" in prompt.replace(" and what it allows", "\nand what it allows")
      or "each Option and what it allows here" in prompt, "Options are asked for")
check("OTHER CHECKS MADE (the decision does not rest on them)\n- [TRUE] The manual allows a plaque below Device D here.  [OPTION]"
      in prompt, "a check the terminal does not depend on is still shown, marked")
check(prompt.count("Device D is the required colour.") == 1, "a check in the decision is not listed twice")
# an excused failure is marked; UNKNOWN branch mentions the other checks; skipped checks are listed
spec2 = NetworkSpec.from_dict({"query": "q", "terminal": "e", "obligations": [
    ob("r", "Device D meets the base rule.", "STANDARD"),
    {**ob("x", "An exception covers Device D here.", "OPTION"), "type": "exception"}],
    "merges": [{"id": "e", "claim": "Device D meets the rule or its exception.", "kind": "exception",
                "inputs": ["r", "x"], "authority": "STANDARD"}]})
net2, pr2 = instantiate(spec2); assert pr2 == [], pr2
table.update({"r": F, "x": T})
tr2 = execute(net2, {v: verify for v in ALL})
p2 = build_answer_prompt("q", net2, tr2)
check("DECISION\nTRUE" in p2 and "set aside: an exception or an alternative that holds covers it" in p2,
      "a base rule an exception covers is marked set aside")
table.update({"a": Status.UNKNOWN, "b": T})
tr3 = execute(net, {v: verify for v in ALL})
p3 = build_answer_prompt("q", net, tr3)
check("DECISION\nUNKNOWN" in p3 and "report the other checks listed as what was found" in p3,
      "the abstention prompt says how to report the other checks")
# an open Guidance under the Standard merge does not block it, and is still reported open
table.update({"a": T, "b": Status.UNKNOWN})
tr4 = execute(net, {v: verify for v in ALL})
p4 = build_answer_prompt("q", net, tr4)
check("DECISION\nTRUE" in p4 and "LEFT UNRESOLVED\n- Device D is at the recommended height." in p4,
      "an open Guidance does not block a Standard merge, and is listed as left unresolved")
print(f"ALL KEEP-ALL TESTS PASSED ({ok} checks)")
