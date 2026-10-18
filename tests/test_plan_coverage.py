"""What a plan covers, and how applicability claims are read (17 Oct 2026).

S3.1 checks a plan's structure before it runs. Nothing checked that it covers
the question, and no checker can: each sees one claim, never the question or
the plan (S3.3). Four rules, read from the IR and the graph
(`parser.coverage_problems`):

  A. When the facts tell several cases of one kind apart by a label, every
     claim names its case, or says that it holds for each.
  B. When the provision a check rests on names an exception that was shown,
     a check rests on that exception too. The prompt marks it.
  C. "asked" (a new IR field): each thing the question asks, answered by a
     step the terminal depends on.
  D. An exception obligation is never an input of a conjunction.

They go back to the model for repair. A plan left with only these problems
is still used, and they are recorded.

And the checker: a claim that a provision applies is answered with the
provision's subject and conditions first ("scope"), and an exception for
something else does not put the thing the claim names outside the provision.

Everything here is made up (sections 9Z and 9Y; panels; designs). No sample
question, gold answer or MUTCD text is used.

Run: python3 tests/test_plan_coverage.py
"""
import json
import pickle
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation import parser_check as pc
from mrag.kg_vine import VineKG
from mrag.vine import NetworkSpec, Operation, Status, execute, instantiate
from mrag.vine.model_verifiers import (READING_RULES, build_prompt, is_scope_claim,
                                       make_llm_verifier, parse_model_reply)
from mrag.vine.network import ObligationType
from mrag.vine.parser import (GROUNDING_RULES, PARSER_CONTRACT, build_parser_prompt,
                              case_labels, coverage_problems, exceptions_from_graph,
                              make_semantic_parser, named_exceptions_shown)

checks = 0


def check(cond, what):
    global checks
    assert cond, what
    checks += 1
    print(f"  ok  {what}")


def ob(i, claim, type_="classification", src="Z1", **kw):
    return {"id": i, "claim": claim, "type": type_, "authority": kw.pop("authority", "STANDARD"),
            "requires": kw.pop("requires", []), "source_chunk": src, **kw}


def spec_of(obligations, merges=(), terminal=None, facts=(), asked=None,
            query="A blue panel is on a lane. Is the panel allowed?"):
    d = {"query": query, "terminal": terminal or obligations[0]["id"],
         "facts": [{"id": f"f{k}", "fact": t} for k, t in enumerate(facts, 1)],
         "obligations": list(obligations), "merges": list(merges)}
    if asked is not None:
        d["asked"] = asked
    return NetworkSpec.from_dict(d)


def kinds(problems):
    out = []
    for p in problems:
        out.append("C" if p.startswith('"asked"') or p.startswith("asked ") else
                   "D" if "is an exception obligation, but" in p else
                   "B" if "names its exception" in p else
                   "A" if "several of one kind" in p else "?")
    return out


ASK1 = [{"id": "a1", "ask": "Is the panel allowed", "answered_by": ["o1"]}]

# --------------------------------------------------------------------------- #
print("1. Case labels")
check(case_labels("Design A has a 7-foot panel and Design B a 5-foot panel.") == {"design": ["A", "B"]},
      "two designs told apart by a letter")
check(case_labels("Designs A and B are proposed; Option 1, 2 or 3.") == {"design": ["A", "B"],
                                                                        "option": ["1", "2", "3"]},
      "lists of labels after a plural")
check(case_labels("Lane 1 and Lane 2 are open.") == {"lane": ["1", "2"]}, "numbered lanes")
check(case_labels("Designs A, B, and C are proposed.") == {"design": ["A", "B", "C"]}, "a list with ', and'")
check(case_labels("Sign 1 in the median is red; Sign 2 is blue.") == {"sign": ["1", "2"]},
      "the word 'in' after a label is not inches")
check(case_labels("a lane 12 feet wide and a sign 30 feet away") == {},
      "a size after a noun is not a label")
check(case_labels("Lane 12 feet wide. Zone 50 feet long. Ramp 2 lanes.") == {},
      "a size after a capitalised word is not a label either")
check(case_labels("a W9-9 sign and a ZZ1-1 panel") == {}, "a sign code is not a label")
check(case_labels("Approach 2.5 miles out") == {}, "a decimal is not a label")

# --------------------------------------------------------------------------- #
print("2. Rule A: several labelled cases, and a claim that names none")
FACTS2 = ["Design A puts a blue panel 7 feet above the lane.", "Design B puts it 5 feet above the lane."]
s = spec_of([ob("o1", "The blue panel is at least 6 feet above the lane."),
             ob("o2", "In Design A, the blue panel is at least 6 feet above the lane."),
             ob("o3", "In each design, the panel faces east."),
             ob("o4", "A blue panel is a panel of the kind defined in 9Z.01.", "definitional"),
             ob("o5", "Designs A and B both use a blue panel.")],
            [{"id": "m1", "claim": "the designs are acceptable", "kind": "conjunction",
              "inputs": ["o5", "o3", "o2", "o1"]}], terminal="m1", facts=FACTS2,
            asked=[{"id": "a1", "ask": "Is each design allowed", "answered_by": ["m1"]}])
pa = coverage_problems(s)
check([p.split(":")[0] for p in pa if "several of one kind" in p] == ["o1"],
      "only the claim naming no design is flagged (not 'In Design A', 'each design', a definition)")
check("Design A" in pa[0] and "Design B" in pa[0] and 'for Design A' in pa[0], "the problem names the cases")
FACTS2b = ["Sign 1 is 7 feet high.", "Sign 2 is 5 feet high."]
s2 = spec_of([ob("o1", "For sign 1, the height is at least 6 feet."),
              ob("o2", "Signs 1 and 2 are at least 4 feet high."),
              ob("o3", "The height is at least 6 feet.")],
             [{"id": "m1", "claim": "the signs are acceptable", "kind": "conjunction",
               "inputs": ["o3", "o2", "o1"]}], terminal="m1", facts=FACTS2b,
             asked=[{"id": "a1", "ask": "Are the signs allowed", "answered_by": ["m1"]}])
p2 = coverage_problems(s2)
check([p.split(":")[0] for p in p2] == ["o3"] and 'for Sign 1' in p2[0],
      "the label as the hint writes it ('for sign 1', in lower case) clears the problem")
s1 = spec_of([ob("o1", "The blue panel is at least 6 feet above the lane.")],
             facts=["Design A puts a blue panel 7 feet above the lane."], asked=ASK1)
check(coverage_problems(s1) == [], "one labelled case only: nothing to tell apart")

# --------------------------------------------------------------------------- #
print("3. Rule B: a rule's named exception that was shown")
KQ = [{"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard", "ordinal": 1,
       "text": "Except as provided in Paragraph 3 of this Section, a blue panel shall face east."},
      {"chunk_id": "Z2", "section_id": "9Z.01", "content_type": "Support", "ordinal": 2,
       "text": "Blue panels are made up."},
      {"chunk_id": "Z3", "section_id": "9Z.01", "content_type": "Option", "ordinal": 3,
       "text": "A blue panel may face west near a park."},
      {"chunk_id": "Z4", "section_id": "9Z.01", "content_type": "Standard", "ordinal": 4,
       "text": "A blue panel shall be square."}]
names = {"Z1": ["Z3", "Z2", "Y9"], "Z4": []}
shown = named_exceptions_shown(KQ, lambda c: names.get(c["chunk_id"], []))
check(shown == {"Z1": ["Z3"]}, "only exceptions that were shown, and only Standard/Guidance/Option ones")
base_only = spec_of([ob("o1", "The blue panel faces east.")], asked=ASK1)
pb = coverage_problems(base_only, KQ, shown)
check(kinds(pb) == ["B"] and "'Z3'" in pb[0] and pb[0].startswith("o1:"), "the rule alone: flagged, naming Z3")
with_exc = spec_of([ob("o1", "The blue panel faces east."),
                    ob("o2", "The park exception covers the blue panel.", "exception", "Z3",
                       authority="OPTION")],
                   [{"id": "m1", "claim": "the panel may face as it does", "kind": "exception",
                     "inputs": ["o1", "o2"]}], terminal="m1",
                   asked=[{"id": "a1", "ask": "Is the panel allowed", "answered_by": ["m1"]}])
check(coverage_problems(with_exc, KQ, shown) == [], "the exception checked in an exception merge: no problem")
loose = spec_of([ob("o1", "The blue panel faces east."),
                 ob("o2", "The park exception covers the blue panel.", "exception", "Z3",
                    authority="OPTION")], asked=ASK1)
check(kinds(coverage_problems(loose, KQ, shown)) == ["B"],
      "an exception check the terminal does not depend on does not count")
other = spec_of([ob("o1", "The blue panel is square.", src="Z4")], asked=ASK1)
check(coverage_problems(other, KQ, shown) == [], "a rule that names no exception: nothing to add")
check(coverage_problems(base_only, KQ, None) == [], "without the graph, rule B is skipped")
scope_only = spec_of([ob("o1", "Section 9Z.01 applies to the blue panel.", "applicability")], asked=ASK1)
check(coverage_problems(scope_only, KQ, shown) == [],
      "an applicability check is not the rule an exception relaxes: not flagged")

# from the graph, as the checkers read it: the clause and the EXCEPTS links
CH = [dict(c, section_title="Blue Panels", source="paragraph", parent_id=None, item=None,
           lead_in=None, authority_inferred=False, figure_refs=[], table_refs=[], section_refs=[])
      for c in KQ] + [
      {"chunk_id": "Z5", "section_id": "9Z.01", "section_title": "Blue Panels", "content_type": "Standard",
       "ordinal": 5, "text": "A blue panel shall be lit.", "source": "paragraph", "parent_id": None,
       "item": None, "lead_in": None, "authority_inferred": False, "figure_refs": [], "table_refs": [],
       "section_refs": []},
      {"chunk_id": "Z6", "section_id": "9Z.01", "section_title": "Blue Panels", "content_type": "Option",
       "ordinal": 6, "text": "A blue panel may be dark by day.", "source": "paragraph", "parent_id": None,
       "item": None, "lead_in": None, "authority_inferred": False, "figure_refs": [], "table_refs": [],
       "section_refs": []}]
N = {f"sent:{c['chunk_id']}#0": SimpleNamespace(kind="SENTENCE", section="9Z.01", text=c["text"],
                                                 authority=None, pieces=()) for c in CH}
N["section:9Z.01"] = SimpleNamespace(kind="SECTION", section="9Z.01", text="Blue Panels",
                                     authority=None, pieces=())
E = [SimpleNamespace(src="sent:Z5#0", rel="EXCEPTS", dst="sent:Z6#0", why="made up")]
TMP = Path(tempfile.mkdtemp())
pickle.dump((N, E, CH), open(TMP / "g.pkl", "wb"))
(TMP / "items.jsonl").write_text("")
kg = VineKG(TMP / "g.pkl", items_path=TMP / "items.jsonl")
from_graph = named_exceptions_shown(CH, exceptions_from_graph(kg))
check(from_graph == {"Z1": ["Z3"], "Z5": ["Z6"]},
      "the graph gives Z1 -> Z3 (its 'Except as provided in Paragraph 3') and Z5 -> Z6 (an EXCEPTS link)")
check(exceptions_from_graph(None) is None and exceptions_from_graph(object()) is None,
      "no VINE graph: no exception reader")

# the prompt marks them
prompt = build_parser_prompt("A blue panel faces west. Is it allowed?", CH, exceptions=from_graph)
z1 = prompt[prompt.index("[Z1]"):prompt.index("[Z2]")]
check("exceptions it names: [Z3]" in z1, "the parser is shown Z1's exception, by id")
check("exceptions it names: [" not in build_parser_prompt("A blue panel. Is it allowed?", CH),
      "without the map, the prompt is as before")

# --------------------------------------------------------------------------- #
print("4. Rule C: every thing asked has a check the terminal depends on")
Q2 = "A blue panel is on a lane. Is the panel allowed? Where should it face?"
two = [ob("o1", "The blue panel is allowed on the lane."), ob("o2", "The blue panel should face east."),
       ob("o3", "The blue panel is square.")]
m = [{"id": "m1", "claim": "the panel is allowed and faces east", "kind": "conjunction",
      "inputs": ["o1", "o2"]}]
good = [{"id": "a1", "ask": "Is the panel allowed", "answered_by": ["o1"]},
        {"id": "a2", "ask": "Where should it face", "answered_by": ["o2"]}]
check(coverage_problems(spec_of(two, m, "m1", query=Q2, asked=good)) == [], "each ask answered: no problem")
pc_ = coverage_problems(spec_of(two, m, "m1", query=Q2))
check(len(pc_) == 1 and pc_[0].startswith('"asked" is missing'), "no asked list: flagged")
pc_ = coverage_problems(spec_of(two, m, "m1", query=Q2, asked=good[:1]))
check(len(pc_) == 1 and "1 item(s)" in pc_[0] and "2 questions" in pc_[0], "fewer items than questions")
for q in ("A blue panel is on a lane. Is the panel allowed? Explain your answer.",
          "The crew has not decided whether to paint it. Is the panel allowed?",
          "A blue panel is on a lane. Is the panel allowed? Why?"):
    check(coverage_problems(spec_of(two, m, "m1", query=q, asked=good[:1])) == [],
          f"only real questions are counted: {q.split('. ')[-1][:40]!r}")
bad = [{"id": "a1", "ask": "Is the panel allowed", "answered_by": ["o1"]},
       {"id": "a2", "ask": "Where should it face", "answered_by": ["o3"]},
       {"id": "o2", "ask": "Is it square", "answered_by": ["o9", "f1"]},
       {"id": "a4", "ask": "Is it lit", "answered_by": []}]
pc_ = coverage_problems(spec_of(two, m, "m1", query=Q2, asked=bad, facts=["A blue panel is on a lane."]))
check(any("a2" in p and "does not depend on them" in p for p in pc_), "a step the terminal does not read")
check(any("'o2'" in p and "already used" in p for p in pc_), "an item id that is a step's id")
check(any("['o9', 'f1']" in p and "not obligations or merges" in p for p in pc_),
      "an unknown id and a fact id are not answers")
check(any("a4" in p and "no obligation or merge answers it" in p for p in pc_), "an item with no answer")
top = [{"id": "a1", "ask": "Is the panel allowed", "answered_by": ["m1"]},
       {"id": "a2", "ask": "Where should it face", "answered_by": ["m1"]}]
check(coverage_problems(spec_of(two, m, "m1", query=Q2, asked=top)) == [],
      "two parts both answered by the top merge: allowed (a 'Why?' has the same checks)")
check(coverage_problems(spec_of(two, m, "m1", asked=[{"id": "a1", "ask": "Is the panel allowed",
                                                       "answered_by": ["m1"]}])) == [],
      "one part answered by the terminal: fine")

# --------------------------------------------------------------------------- #
print("5. Rule D: an exception obligation is not a conjunction input")
d_obs = [ob("o1", "The blue panel faces east."),
         ob("o2", "The park exception covers the blue panel.", "exception", "Z3", authority="OPTION")]
pd = coverage_problems(spec_of(d_obs, [{"id": "m1", "claim": "acceptable", "kind": "conjunction",
                                        "inputs": ["o1", "o2"]}], "m1", asked=[
    {"id": "a1", "ask": "Is the panel allowed", "answered_by": ["m1"]}]))
check(kinds(pd) == ["D"] and pd[0].startswith("m1: 'o2'"), "in a conjunction: flagged")
for kind in ("exception", "alternative"):
    check(coverage_problems(spec_of(d_obs, [{"id": "m1", "claim": "acceptable", "kind": kind,
                                             "inputs": ["o1", "o2"]}], "m1", asked=[
        {"id": "a1", "ask": "Is the panel allowed", "answered_by": ["m1"]}])) == [],
        f"in an {kind} merge: fine")

# --------------------------------------------------------------------------- #
print("6. The repair loop: coverage problems go back; a plan is never lost over them alone")
Q6 = "A blue panel faces west near a park. Is it allowed?"
EXC = {"Z1": ["Z3"]}


def plan(obligations, merges=(), terminal="o1", asked=True):
    d = {"terminal": terminal, "facts": [{"id": "f1", "fact": "A blue panel faces west near a park."}],
         "obligations": obligations, "merges": list(merges)}
    if asked:
        d["asked"] = [{"id": "a1", "ask": "Is it allowed", "answered_by": [terminal]}]
    return json.dumps(d)


RULE_ONLY = plan([ob("o1", "The blue panel faces east.")])                       # rule B open
NO_ASKED = plan([ob("o1", "The blue panel faces east.")], asked=False)            # rules B and C open
FIXED = plan([ob("o1", "The blue panel faces east."),
              ob("o2", "The park exception covers the blue panel.", "exception", "Z3", authority="OPTION")],
             [{"id": "m1", "claim": "the panel may face west", "kind": "exception", "inputs": ["o1", "o2"]}],
             terminal="m1")
HARD = plan([ob("o1", "The blue panel faces east.", src="Z2")])                   # a Support source


def model(*replies):
    seq = list(replies)
    seen = []

    def ask(prompt, images):
        seen.append(prompt)
        return seq[min(len(seen) - 1, len(seq) - 1)]
    ask.seen = seen
    return ask


names_of = lambda c: EXC.get(c["chunk_id"], [])                                   # noqa: E731
a = model(RULE_ONLY, FIXED)
spec, rep = make_semantic_parser(a, fall_back_to_baseline=False, exceptions_of=names_of)(Q6, KQ)
check(spec is not None and rep.attempts == 2 and rep.used_attempt == 2 and rep.open_problems == [],
      "rule B open, then repaired: the repaired plan, nothing left open")
check("names its exception" in a.seen[1] and "YOUR PREVIOUS PLAN WAS REJECTED" in a.seen[1]
      and "exceptions it names: [Z3]" in a.seen[0], "the repair request carries the problem; the prompt the mark")
check(any("exception merge whose first input is the rule" in r for r in GROUNDING_RULES)
      and all(r in a.seen[1] for r in GROUNDING_RULES[-4:]), "the new rules go with every repair")

a = model(NO_ASKED, RULE_ONLY, RULE_ONLY)
spec, rep = make_semantic_parser(a, fall_back_to_baseline=False, exceptions_of=names_of)(Q6, KQ)
check(spec is not None and rep.source == "semantic_parser" and rep.attempts == 3,
      "never cleared: the plan is still used")
check(rep.used_attempt == 3 and len(rep.open_problems) == 1 and "names its exception" in rep.open_problems[0],
      "the one with the fewest open problems wins, the later on a tie; what is left is recorded")
check(any("coverage problem(s) were not cleared" in n for n in rep.notes), "and said so in the notes")

a = model(RULE_ONLY, HARD, HARD)
spec, rep = make_semantic_parser(a, fall_back_to_baseline=False, exceptions_of=names_of)(Q6, KQ)
check(spec is not None and rep.used_attempt == 1 and [o.source_chunk for o in spec.obligations] == ["Z1"],
      "a later plan with a problem about the manual never replaces a usable one")
a = model(HARD, HARD, HARD)
spec, rep = make_semantic_parser(a, fall_back_to_baseline=False, exceptions_of=names_of)(Q6, KQ)
check(spec is None and rep.source == "failed" and rep.open_problems == [],
      "a plan with a problem about the manual is never used")

rec = pc.make_record("X1", Q6, {"chunks": KQ}, *make_semantic_parser(
    model(RULE_ONLY), max_attempts=1, fall_back_to_baseline=False, exceptions_of=names_of)(Q6, KQ))
check(rec["outcome"] == "valid, open problems" and len(rec["open_problems"]) == 1 and rec["used_attempt"] == 1,
      "the plan record says so")
summ = pc.summarize([rec])
check(summ["open_problems"] == 1 and summ["outcome"] == {"valid, open problems": 1}
      and "mean_obligations" in summ, "and the summary counts it as a valid plan with problems left")

# --------------------------------------------------------------------------- #
print("7. The IR: 'asked' is kept, read leniently, and never executed")
d = json.loads(FIXED)
s = NetworkSpec.from_dict({**d, "query": Q6})
check(s.as_dict()["asked"] == [{"id": "a1", "ask": "Is it allowed", "answered_by": ["m1"]}]
      and NetworkSpec.from_dict(s.as_dict()).as_dict() == s.as_dict(), "kept and read back the same")
d.pop("asked")
check("asked" not in NetworkSpec.from_dict({**d, "query": Q6}).as_dict(),
      "a plan without it is written exactly as before")
lenient = NetworkSpec.from_dict({**d, "query": Q6, "asked": [{"ask": ""}, 7, "Is it allowed",
                                                             {"text": "Where", "checks": "o1"}]})
check([(x.id, x.ask, x.answered_by) for x in lenient.asked] == [("a3", "Is it allowed", []),
                                                               ("a4", "Where", ["o1"])],
      "items without text are left out; other spellings are read")
check(NetworkSpec.from_dict({**d, "query": Q6, "asked": "a1"}).asked == [], "not a list: left out")
n1, p1 = instantiate(s)
n2, p2 = instantiate(NetworkSpec.from_dict({**d, "query": Q6}))
check(p1 == p2 == [] and sorted(o.id for o in n1.operations) == sorted(o.id for o in n2.operations),
      "the network is the same with or without it")

# --------------------------------------------------------------------------- #
print("8. The instructions")
for line in ('"asked": [', "Step 5. What is asked.", "every claim names the one",
             "use the fact's own words", "write\n    one claim per item",
             "exceptions it names", "Not whether the case obeys the provision",
             "Do not put every check of the plan behind one check that a\n    Section applies",
             "An exception obligation is never an input of a conjunction."):
    check(line in PARSER_CONTRACT, f"the contract says: {line[:50]!r}")

# --------------------------------------------------------------------------- #
print("9. The checker: a claim that a provision applies")


def op(claim, type_):
    return Operation(id="o1", claim=claim, produces="s_o1",
                     obligation_type=ObligationType(type_) if type_ else None)


CH9 = [{"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard",
        "text": "A blue panel shall face east."}]
check(is_scope_claim(op("Section 9Z.01 governs the panel.", "applicability")), "an applicability obligation")
check(not is_scope_claim(op("The panel meets the applicable height rule.", "classification")),
      "not a compliance claim that says 'applicable'")
check(not is_scope_claim(op("The park exception covers the panel, so 9Z.01 does not apply to it.",
                            "exception")), "not an exception obligation")
check(not is_scope_claim(op("The panel is 7 feet high.", "numerical")), "not a plain comparison")
p_app, _ = build_prompt(op("Section 9Z.01 applies to the blue panel.", "applicability"), CH9, [])
p_num, _ = build_prompt(op("The panel is 7 feet high.", "numerical"), CH9, [])
check('"scope"' in p_app and "THIS CLAIM IS ABOUT WHETHER A PROVISION APPLIES" in p_app
      and p_app.index("THIS CLAIM IS ABOUT") < p_app.index("THE CLAIM AGAIN"), "the scope field is asked for")
check('"scope"' not in p_num and "THIS CLAIM IS ABOUT" not in p_num, "and only there")
check("An exception for something else (another item, or\n  only a part of the thing the claim names)"
      in READING_RULES and "does not put the thing itself\n  outside P" in READING_RULES,
      "the reading rule: an exception for a part does not put the whole outside")
r = parse_model_reply(json.dumps({"scope": "covers blue panels; the case is a blue panel", "status": "TRUE",
                                  "evidence": ["Z1"], "basis": "Z1", "confidence": 0.8, "reason": "r"}), ["Z1"])
check(r.scope.startswith("covers blue panels") and r.status is Status.TRUE, "the scope is read")
r = parse_model_reply(json.dumps({"scope": {"subject": "blue panels"}, "status": "FALSE",
                                  "evidence": ["Z1"], "confidence": 0.8, "reason": "r"}), ["Z1"])
check(json.loads(r.scope) == {"subject": "blue panels"}, "a scope written as an object is kept as JSON")


class Retriever:
    def retrieve_for_obligation(self, query, obligation, certificates=None, top_k=None):
        return SimpleNamespace(chunks=[dict(c) for c in CH9], figures=[], debug={})


sp = NetworkSpec.from_dict({"query": "made-up", "terminal": "o1",
                            "facts": [{"id": "f1", "fact": "A blue panel is on a lane."}],
                            "obligations": [ob("o1", "Section 9Z.01 applies to the blue panel.",
                                               "applicability")]})
net, probs = instantiate(sp)
reply = {"scope": "9Z.01 covers blue panels; f1 says the item is a blue panel", "status": "TRUE",
         "evidence": ["Z1", "f1"], "basis": "Z1", "confidence": 0.9, "reason": "it is a blue panel"}
v = make_llm_verifier(lambda p, i: json.dumps(reply), Retriever(), query="made-up", use_pointers=False)
c = execute(net, {"llm": v}).terminal
check(c.status is Status.TRUE and c.provenance["scope"].startswith("9Z.01 covers blue panels"),
      "the certificate keeps what the checker said the provision covers")

# --------------------------------------------------------------------------- #
print("10. An id copied with its square brackets; a condition the facts are silent on")
BR = json.loads(FIXED)
BR["obligations"][0]["source_chunk"] = "[Z1]"
BR["obligations"][1]["source_chunk"] = " [ Z3 ] "
spec, rep = make_semantic_parser(model(json.dumps(BR)), fall_back_to_baseline=False,
                                 exceptions_of=names_of)(Q6, KQ)
check(spec is not None and rep.attempts == 1 and [o.source_chunk for o in spec.obligations] == ["Z1", "Z3"],
      "'[Z1]' names the provision Z1: valid first time, no repair spent on it")
check(any("'[Z1]' was read as 'Z1'" in n for n in rep.notes), "and the reading is noted")
BR["obligations"][0]["source_chunk"] = "[Z9]"
spec, rep = make_semantic_parser(model(json.dumps(BR)), max_attempts=1, fall_back_to_baseline=False,
                                 exceptions_of=names_of)(Q6, KQ)
check(spec is None and any("'Z9' is not one of the provisions shown" in p for g in rep.problems for p in g),
      "a bracketed id that was not shown is still refused")
for line in ("that the facts say something about", "write the condition into the claim",
             "A claim never states something about the case that the facts do not\n    say."):
    check(line in PARSER_CONTRACT, f"the contract says: {line[:50]!r}")

print(f"\nALL PLAN-COVERAGE TESTS PASSED ({checks} checks)")
