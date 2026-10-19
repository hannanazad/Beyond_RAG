"""The structured parser (mrag/vine/structured_parser.py, 18 Oct 2026).

One call reads the question (facts, and what is asked: about the case or about
the manual); one call per group of sections decides every Standard, Guidance
and Option paragraph shown; code builds the structure.

Every section, paragraph and question here is made up (section numbers 9Z.xx,
"zorb" markers on "blip" lanes, "gadget" markings). None comes from a sample question, a gold
answer or the MUTCD. The model is a stand-in that returns fixed replies.

Run: python3 tests/test_structured_parser.py
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine import Certificate, Status, execute, instantiate
from mrag.vine import structured_parser as sp
from mrag.vine.compile import GivenFact
from mrag.vine.parser import _support

T, F, U, NA = Status.TRUE, Status.FALSE, Status.UNKNOWN, Status.NOT_APPLICABLE
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")
checks = 0


def ok(cond, msg=""):
    global checks
    assert cond, msg
    checks += 1


def ch(cid, sec, kind, n, text, title="Zorb Markers", **k):
    return {"chunk_id": cid, "section_id": sec, "section_title": title, "content_type": kind,
            "ordinal": n, "text": text, "figure_refs": [], "table_refs": [], "section_refs": [], **k}


KQ = [ch("W_S1", "9Z.01", "Standard", 1, "Zorb markers shall be spaced no more than 40 yards apart."),
      ch("W_O2", "9Z.01", "Option", 2, "Where a blip lane is narrower than 9 yards, zorb markers may be "
                                       "spaced up to 60 yards apart."),
      ch("W_G3", "9Z.01", "Guidance", 3, "Zorb markers should be orange."),
      ch("W_U4", "9Z.01", "Support", 4, "Zorb markers show where blip lanes run."),
      ch("G_S1", "9Z.02", "Standard", 1, "Gadget markings shall be white.", "Gadget Markings")]
Q = ("A city spaced zorb markers 50 yards apart along a blip lane that is 7 yards wide. "
     "Is that spacing acceptable?")
FACTS = {"facts": [{"id": "f1", "fact": "A city spaced zorb markers 50 yards apart along a blip lane that is 7 yards wide."}],
         "asked": [{"id": "a1", "ask": "Is that spacing acceptable?", "about": "case",
                    "claim": "The spacing of the zorb markers meets the manual."}]}


def to_decide(prompt):
    block = prompt.split("\nPARAGRAPHS TO DECIDE (")[1].split("\nHOW TO DECIDE")[0]
    return re.findall(r"^\[([^\]]+)\]", block, re.M)


def model(decisions, facts=FACTS, log=None):
    """A stand-in model: the facts reply, then for each section call one item
    per paragraph it is asked about (from `decisions`, else "does not bear")."""
    def ask(prompt, images=None):
        if log is not None:
            log.append(prompt)
        if "This step reads the QUESTION only" in prompt:
            return json.dumps(facts)
        out = []
        for i in to_decide(prompt):
            d = decisions.get(i)
            out.append({"id": i, **d} if d else {"id": i, "why": "about something else", "bears": False,
                                                 "checks": []})
        return json.dumps({"paragraphs": out})
    ask.last = None
    return ask


def check(claim, answers=("a1",), about="case", typ="classification", hints=()):
    return {"claim": claim, "about": about, "answers": list(answers), "type": typ,
            "evidence_hint": list(hints)}


def run(spec, table):
    net, problems = instantiate(spec)
    assert problems == [], problems

    def verify(op, store):
        return Certificate(claim=op.claim, status=table[op.id], normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id, confidence=0.9)
    trace = execute(net, {v: verify for v in ALL})
    return trace.terminal.status


def ids_for(spec, src):
    return [o.id for o in spec.obligations if o.source_chunk == src]


# --------------------------------------------------------------------------- #
# 1. The facts and the things asked
# --------------------------------------------------------------------------- #
def test_facts_step_reads_facts_and_asks():
    data, problems = sp.read_facts(json.dumps(FACTS), Q)
    ok(problems == [], problems)
    ok([f.id for f in data["facts"]] == ["f1"] and data["asked"][0]["about"] == "case")


def test_facts_step_finds_what_is_wrong():
    bad = {"facts": [{"id": "f1", "fact": "The markers are 50 yards apart, which meets the 40-yard rule."}],
           "asked": [{"id": "a1", "ask": "Is it acceptable?", "about": "maybe", "claim": "Is it acceptable?"}]}
    _d, problems = sp.read_facts(json.dumps(bad), Q)
    text = " | ".join(problems)
    ok("f1:" in text and "[\'40\']" in text, text)                     # a number the question does not state
    ok("about 'maybe'" in text and "the claim is a question" in text, text)
    two = Q + " Must they also be orange?"
    _d, problems = sp.read_facts(json.dumps(FACTS), two)
    ok(any("but the question has 2 questions" in p for p in problems), problems)
    d, problems = sp.read_facts("no json here", Q)
    ok(d is None and problems)


def test_a_bad_facts_reply_is_sent_back_and_the_repair_is_used():
    bad = {**FACTS, "asked": [{"id": "a1", "ask": "Is that spacing acceptable?", "about": "",
                               "claim": "The spacing meets the manual."}]}
    replies = [json.dumps(bad), json.dumps(FACTS)]
    seen = []
    inner = model({"W_S1": {"why": "height", "bears": True, "checks": [check("The zorb markers are spaced no more than 40 yards apart.")]}})

    def ask(prompt, images=None):
        seen.append(prompt)
        if "This step reads the QUESTION only" in prompt:
            return replies.pop(0)
        return inner(prompt)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is not None and rep.attempts == 2 and rep.steps == {"facts": 2, "section": 1}, rep.steps)
    ok("YOUR PREVIOUS REPLY WAS REJECTED" in seen[1] and "about ''" in seen[1])


def test_a_fact_still_wrong_after_the_repairs_is_left_out():
    bad = {"facts": FACTS["facts"] + [{"id": "f2", "fact": "The markers meet the 40-yard rule."}],
           "asked": FACTS["asked"]}
    seen = []
    inner = model({"W_S1": RULE})

    def ask(prompt, images=None):
        seen.append(prompt)
        return json.dumps(bad) if "This step reads the QUESTION only" in prompt else inner(prompt)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is not None and [f.id for f in spec.facts] == ["f1"], spec and spec.facts)
    ok(rep.steps["facts"] == 3 and any(p.startswith("facts: f2:") for p in rep.open_problems), rep.open_problems)
    ok(any("facts left out after the repairs: ['f2']" in n for n in rep.notes), rep.notes)
    ok("[f2]" not in seen[-1] and "[f1]" in seen[-1])                # the section call sees only f1


# --------------------------------------------------------------------------- #
# 2. Which paragraphs go to which call
# --------------------------------------------------------------------------- #
def test_small_sections_share_a_call_and_a_large_one_is_split():
    chunks = [ch(f"A{i}", "9Z.10", "Standard", i, f"made-up rule {i}") for i in range(1, 4)]
    chunks += [ch("A_sup", "9Z.10", "Support", 9, "made-up support")]
    chunks += [ch(f"B{i}", "9Z.11", "Guidance", i, f"made-up advice {i}") for i in range(1, 4)]
    chunks += [ch(f"C{i}", "9Z.12", "Option", i, f"made-up option {i}") for i in range(1, 21)]
    chunks += [ch("D_row", "9Z.13", "TableRow", 1, "a row", table_refs=["Table 9Z-1"])]
    chunks += [ch(f"E{i}", "9Z.14", "Standard", i, f"made-up rule {i}") for i in range(1, 3)]
    calls = sp.plan_calls(chunks, (), cap=8)
    ok([c.decide for c in calls][0] == ["A1", "A2", "A3", "B1", "B2", "B3"], calls[0].decide)
    ok([len(c.decide) for c in calls] == [6, 7, 7, 6, 2], [len(c.decide) for c in calls])
    ok({x for c in calls for x in c.decide} == {c["chunk_id"] for c in chunks
                                                if c["content_type"] in ("Standard", "Guidance", "Option")})
    ok(any(c["chunk_id"] == "A_sup" for c in calls[0].items))          # context goes with its section
    ok(any(c["chunk_id"] == "D_row" for c in calls[-1].items))         # a section with nothing to decide
    ok(sum(len(c.decide) for c in calls) == 28)                         # every paragraph once


def test_small_sections_that_would_pass_the_cap_get_calls_of_their_own():
    chunks = [ch(f"A{i}", "9Z.10", "Standard", i, f"made-up rule {i}") for i in range(1, 6)]
    chunks += [ch(f"B{i}", "9Z.11", "Guidance", i, f"made-up advice {i}") for i in range(1, 6)]
    calls = sp.plan_calls(chunks, (), cap=8)
    ok([c.decide for c in calls] == [[f"A{i}" for i in range(1, 6)], [f"B{i}" for i in range(1, 6)]],
       [c.decide for c in calls])


def test_only_a_few_rows_of_a_table_are_shown():
    rows = [ch(f"R{i}", "9Z.01", "TableRow", i, f"Table 9Z-1. Row {i}: width {i} ft", table_refs=["Table 9Z-1"])
            for i in range(1, 6)]
    call = sp.Call(items=KQ[:1] + rows, decide=["W_S1"])
    shown, left = sp.shown_items(call.items)
    ok([c["chunk_id"] for c in shown] == ["W_S1", "R1", "R2", "R3"] and left == {"Table 9Z-1": 2}, (shown, left))
    prompt = sp.build_section_prompt(Q, F1, ASKED, call, {}, {})
    ok("Row 3" in prompt and "Row 4" not in prompt and "2 more rows of Table 9Z-1" in prompt)


def test_the_graph_adds_named_exceptions_and_options_next_to_their_rule():
    record = {"X_O7": ch("X_O7", "9Z.01", "Option", 7, "On a one-way blip lane, the markers may be omitted."),
              "Y_S2": ch("Y_S2", "9Z.30", "Standard", 2, "Except on gadget roads, ...", "Other"),
              "W_O2": KQ[1]}
    added = sp._additions(KQ, exceptions_of=lambda c: ["Y_S2", "W_O2"] if c["chunk_id"] == "W_S1" else [],
                          options_of=lambda c: ["X_O7", "W_O2"] if c["section_id"] == "9Z.01" else [],
                          record_of=record.get)
    ok([a["chunk"]["chunk_id"] for a in added] == ["Y_S2", "X_O7"], added)   # W_O2 was retrieved already
    ok(added[0]["home"] == "W_S1" and "named as an exception" in added[0]["why"])
    calls = sp.plan_calls(KQ, added, cap=16)
    first = [c for c in calls if "W_S1" in c.decide][0]
    ok("Y_S2" in first.decide and "X_O7" in first.decide, first.decide)
    # with room for the rule's own section only, the additions still go with the rule
    calls = sp.plan_calls(KQ, added, cap=5)
    ok([c.decide for c in calls][0] == ["W_S1", "W_O2", "W_G3", "X_O7", "Y_S2"], [c.decide for c in calls])
    ok(sp._additions(KQ, None, None, None) == [])


# --------------------------------------------------------------------------- #
# 3. Reading a section reply
# --------------------------------------------------------------------------- #
ASKED = FACTS["asked"]
F1 = [GivenFact("f1", FACTS["facts"][0]["fact"])]


def read(items, call_chunks=KQ, asked=ASKED, facts=F1, known=(), check_ref=None):
    call = sp.Call(items=list(call_chunks),
                   decide=[c["chunk_id"] for c in call_chunks if c["content_type"] in ("Standard", "Guidance", "Option")])
    return sp.read_section(json.dumps({"paragraphs": items}), call, asked, facts, Q, set(known), check_ref)


def test_a_section_reply_must_decide_every_paragraph_once():
    _d, dec, problems, _n = read([{"id": "[W_S1]", "why": "x", "bears": False, "checks": []},
                                  {"id": "W_S1", "why": "x", "bears": False, "checks": []},
                                  {"id": "W_U4", "why": "x", "bears": False, "checks": []}])
    text = " | ".join(problems)
    ok("[W_S1] is listed twice" in text and "'W_U4' is not one of the paragraphs" in text, text)
    ok("no item for [W_O2], [W_G3], [G_S1]" in text, text)
    ok("W_S1" in dec)                                                    # "[W_S1]" read as W_S1


def test_a_check_for_an_ask_about_the_case_must_be_about_the_case():
    items = [{"id": "W_S1", "why": "x", "bears": True,
              "checks": [check("The manual requires zorb markers no more than 40 yards apart.", about="manual")]}]
    _d, dec, problems, _n = read(items)
    ok(any("asks whether the case meets the manual, but the claim is about the manual" in p for p in problems),
       problems)
    ok(dec["W_S1"]["bad_checks"] == [0])
    # an ask about the manual may be answered by a claim about the manual
    manual_ask = [{"id": "a1", "ask": "How far apart may they be?", "about": "manual",
                   "claim": "The manual states how far apart zorb markers may be."}]
    _d, dec, problems, _n = read(items, asked=manual_ask)
    ok(not [p for p in problems if "W_S1" in p], problems)


def test_other_check_problems_are_found():
    items = [{"id": "W_S1", "why": "x", "bears": True, "checks": [
                 check("The spacing is short enough?"),                                 # a question
                 check("The spacing is short enough.", answers=("a9",)),                # no such ask
                 check("The spacing is short enough.", answers=()),                     # answers nothing
                 check("The spacing is short enough.", typ="vibes"),                    # no such type
                 check("The markers meet the 40-yard rule.", hints=[{"type": "table", "id": "Table 9Z-9"}])]},
             {"id": "W_O2", "why": "x", "bears": True,
              "checks": [check("The narrow-lane exception covers the markers.", typ="exception")]},
             {"id": "W_G3", "why": "x", "bears": False, "checks": [check("The markers are orange.")]},
             {"id": "G_S1", "why": "x", "bears": True, "checks": []}]
    _d, dec, problems, _n = read(items, check_ref=lambda kind, ident: ident != "9Z-9")
    text = " | ".join(problems)
    for want in ("[W_S1] check 1: the claim is a question", "[W_S1] check 2: answers ['a9']",
                 "[W_S1] check 3 answers no ask", "[W_S1] check 4: type 'vibes'",
                 "[W_S1] check 5: table 'Table 9Z-9' in evidence_hint is not in the manual",
                 "[W_O2] check 1 is an exception check, but [W_O2] relaxes no paragraph",
                 "[W_G3]: it does not bear, but it has checks", "[G_S1]: it bears, but it has no check"):
        ok(want in text, (want, text))
    ok(sorted(dec["W_S1"]["bad_checks"]) == [0, 1, 2, 3], dec["W_S1"]["bad_checks"])
    ok(dec["W_S1"]["checks"][4]["evidence_hint"] == [])          # a bad hint is dropped, the check kept
    # an exception check is fine on a paragraph that relaxes another, or that the manual names
    items = [{"id": "W_O2", "why": "x", "bears": True, "relaxes": ["W_S1"],
              "checks": [check("The narrow-lane exception covers the markers.", typ="exception")]}]
    ok(not [p for p in read(items)[2] if "exception check" in p])
    items[0]["relaxes"] = []
    ok(not [p for p in read(items, known={"W_O2"})[2] if "exception check" in p])


def test_without_facts_a_check_cannot_be_about_the_case():
    asked = [{"id": "a1", "ask": "What colour are gadget markings?", "about": "manual",
              "claim": "The manual states the colour of gadget markings."}]
    items = [{"id": "G_S1", "why": "x", "bears": True,
              "checks": [check("Gadget markings here are white.", about="case")]}]
    problems = read(items, asked=asked, facts=[])[2]
    ok(any("states no facts about a case" in p for p in problems), problems)
    items = [{"id": "G_S1", "why": "x", "bears": True, "condition": "The road is a gadget road.",
              "checks": [check("The manual requires gadget markings to be white.", about="manual")]}]
    _d, dec, problems, _n = read(items, asked=asked, facts=[])
    ok(any("it has a condition, but the question states no facts" in p for p in problems), problems)
    ok(dec["G_S1"]["condition"] == "" and dec["G_S1"]["bad_checks"] == [])


def test_labelled_cases_must_be_named():
    facts = [GivenFact("f1", "Design A spaces the zorb markers 50 yards apart."),
             GivenFact("f2", "Design B spaces the zorb markers 30 yards apart.")]
    items = [{"id": "W_S1", "why": "x", "bears": True, "checks": [
        check("The zorb markers are no more than 40 yards apart."),
        check("For Design B, the zorb markers are no more than 40 yards apart.")]}]
    problems = read(items, facts=facts)[2]
    ok(any(p.startswith("[W_S1] check 1: the facts describe several") for p in problems), problems)
    ok(not any(p.startswith("[W_S1] check 2") for p in problems), problems)


# --------------------------------------------------------------------------- #
# 4. Code builds the plan
# --------------------------------------------------------------------------- #
RULE = {"why": "height", "bears": True,
        "checks": [check("The zorb markers spaced 50 yards apart are no more than 40 yards apart.")]}
EXC = {"why": "narrow lane", "bears": True, "relaxes": ["W_S1"],
       "condition": "The blip lane is narrower than 9 yards.",
       "checks": [check("Zorb markers 50 yards apart along a 7-yard blip lane are within what the paragraph allows.",
                        typ="exception")]}


def test_one_rule_and_its_exception_make_an_exception_merge():
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": EXC}))(Q, KQ)
    ok(spec is not None and rep.source == "semantic_parser" and rep.attempts == 1, rep.problems)
    ok(spec.source == "structured" and rep.open_problems == [], rep.open_problems)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    rule, = ids_for(spec, "W_S1")
    cond, exc = ids_for(spec, "W_O2")
    ok(term.kind == "exception" and term.inputs == [rule, exc] and term.authority == "STANDARD")
    by = {o.id: o for o in spec.obligations}
    ok(by[rule].authority == "STANDARD" and by[exc].authority == "OPTION")     # the printed headings
    ok(by[cond].type == "applicability" and by[cond].about == "case" and cond.startswith("c"))
    ok(by[exc].requires == [cond] and by[exc].guard.state == cond and by[exc].guard.status == "TRUE")
    ok(by[rule].about == "case" and spec.asked[0].answered_by == [spec.terminal])
    ok({p["id"]: p["bears"] for p in rep.paragraphs} ==
       {"W_S1": True, "W_O2": True, "W_G3": False, "G_S1": False}, rep.paragraphs)
    # executed: the rule fails, the exception covers the case -> met
    ok(run(spec, {rule: F, cond: T, exc: T}) is T)
    # the exception's condition does not hold -> it does not apply -> the rule decides
    ok(run(spec, {rule: F, cond: F, exc: T}) is F)
    ok(run(spec, {rule: T, cond: F, exc: F}) is T)


def test_the_manuals_own_link_makes_the_exception_without_relaxes():
    exc = {**EXC, "relaxes": []}
    graph = lambda c: ["W_O2"] if c["chunk_id"] == "W_S1" else []
    log = []
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": exc}, log=log),
                                          exceptions_of=graph)(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "exception" and term.inputs[0] == ids_for(spec, "W_S1")[0], term)
    ok("exceptions it names: [W_O2]" in log[1] and "named as an exception by [W_S1]" in log[1])


def test_an_exception_paragraph_is_used_only_with_its_rule():
    # the rule has no check for a2: the exception's check for a2 is not used on its own
    facts = {**FACTS, "asked": FACTS["asked"] + [{"id": "a2", "ask": "Are they the right colour?",
                                                  "about": "case",
                                                  "claim": "The colour of the zorb markers meets the manual."}]}
    q = Q + " Are they the right colour?"
    exc = {**EXC, "checks": EXC["checks"] + [check("The Option lets the markers be blue.",
                                                   answers=("a2",), typ="exception")]}
    adv = {"why": "colour", "bears": True,
           "checks": [check("The zorb markers are orange.", answers=("a2",))]}
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": exc, "W_G3": adv}, facts=facts))(q, KQ)
    ok(spec is not None, rep.problems)
    ok(any("has no check for a2; its checks for a2 are not used" in n for n in rep.notes), rep.notes)
    used = _support(spec)
    ok(all(o.id in used for o in spec.obligations), (used, [o.id for o in spec.obligations]))  # nothing unused
    ok(not any("be blue" in o.claim for o in spec.obligations))
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "conjunction" and len(term.inputs) == 2 and term.authority == "GUIDANCE")
    a2 = next(a for a in spec.asked if a.id == "a2")
    ok(a2.answered_by == ids_for(spec, "W_G3"))


def test_an_exception_check_without_a_rule_that_bears_is_not_used():
    # the rule it relaxes does not bear: the exception check would stand alone
    exc = {**EXC, "condition": ""}
    other = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.")]}
    spec, rep = sp.make_structured_parser(model({"W_O2": exc, "W_G3": other}))(Q, KQ)
    ok(spec is not None and ids_for(spec, "W_O2") == [] and ids_for(spec, "W_G3") != [], spec)
    ok(any("[W_O2]: its exception check(s) are not used" in n for n in rep.notes), rep.notes)
    # with only that paragraph, the ask is left with nothing that bears
    spec, rep = sp.make_structured_parser(model({"W_O2": exc}))(Q, KQ)
    ok(len(spec.obligations) == 1 and spec.obligations[0].source_chunk == "", spec.obligations)


def test_paragraphs_said_to_relax_each_other_are_rules_of_their_own():
    a = {**RULE, "relaxes": ["W_O2"]}
    b = {**EXC, "condition": "", "checks": [check("The markers meet the narrow-lane spacing.")]}
    spec, rep = sp.make_structured_parser(model({"W_S1": a, "W_O2": b}))(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "conjunction" and any("relax each other" in n for n in rep.notes), (term, rep.notes))


def test_a_paragraphs_checks_are_merged_at_its_heading():
    adv = {"why": "x", "bears": True, "join": "all",
           "checks": [check("The zorb markers are orange."), check("The zorb markers are clean.")]}
    spec, _r = sp.make_structured_parser(model({"W_G3": adv}))(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "conjunction" and term.authority == "GUIDANCE")
    one, two = ids_for(spec, "W_G3")
    ok(run(spec, {one: T, two: F}) is F)               # "this Guidance is followed": not followed
    alt = {**adv, "join": "any"}
    spec, _r = sp.make_structured_parser(model({"W_G3": alt}))(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "alternative" and term.authority == "GUIDANCE")
    one, two = ids_for(spec, "W_G3")
    ok(run(spec, {one: F, two: T}) is T)


def test_a_failed_guidance_beside_a_standard_is_a_non_conformance():
    adv = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.")]}
    spec, _r = sp.make_structured_parser(model({"W_S1": RULE, "W_G3": adv}))(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "conjunction" and term.authority == "STANDARD" and term.claim == FACTS["asked"][0]["claim"])
    rule, = ids_for(spec, "W_S1")
    g, = ids_for(spec, "W_G3")
    ok(run(spec, {rule: T, g: F}) is T and run(spec, {rule: F, g: T}) is F)


def test_an_ask_nothing_bears_on_is_checked_as_one_claim():
    spec, rep = sp.make_structured_parser(model({}))(Q, KQ)
    ok(spec is not None and len(spec.obligations) == 1 and spec.terminal == spec.obligations[0].id)
    o = spec.obligations[0]
    ok(o.claim == FACTS["asked"][0]["claim"] and o.source_chunk == "" and o.about == "case")
    ok(any("no paragraph shown bears on it" in p for p in rep.open_problems), rep.open_problems)
    ok(rep.source == "semantic_parser")


# --------------------------------------------------------------------------- #
# 4b. After the review of 18 Oct
# --------------------------------------------------------------------------- #
MANUAL = {"facts": FACTS["facts"],
          "asked": [{"id": "a1", "ask": "Where may the markers go?", "about": "manual",
                     "claim": "The manual states where zorb markers may go here."}]}


def test_two_asks_give_a_terminal_over_both():
    facts = {**FACTS, "asked": [
        {"id": "a1", "ask": "May the markers be omitted?", "about": "manual", "claim": "The manual allows the markers to be omitted here."},
        {"id": "a2", "ask": "May they be smaller?", "about": "manual", "claim": "The manual allows smaller markers here."}]}
    q = "A town has a blip lane. May the markers be omitted? May they be smaller?"
    o1 = {"why": "x", "bears": True, "checks": [check("The manual allows the markers to be omitted.", about="manual")]}
    o2 = {"why": "x", "bears": True,
          "checks": [check("The manual allows smaller markers.", answers=("a2",), about="manual")]}
    kq = [ch("V_O1", "9Z.40", "Option", 1, "Zorb markers may be omitted."),
          ch("V_O2", "9Z.40", "Option", 2, "Smaller zorb markers may be used.")]
    spec, rep = sp.make_structured_parser(model({"V_O1": o1, "V_O2": o2}, facts=facts))(q, kq)
    ok(spec is not None, (rep.problems, rep.notes))
    term = next(m for m in spec.merges if m.id == spec.terminal)
    by = {o.id: o for o in spec.obligations}
    n1, n2 = (next(a for a in spec.asked if a.id == x).answered_by[0] for x in ("a1", "a2"))
    ok(term.kind == "conjunction" and term.inputs == [n1, n2] and "; and " in term.claim)
    ok(by[n1].claim == facts["asked"][0]["claim"] and by[n1].requires == ids_for(spec, "V_O1"))
    ok(by[n1].evidence_hint == [{"type": "section", "id": "9Z.40", "paragraph": "1"}], by[n1].evidence_hint)
    ok(by[n1].about == "manual" and by[n1].source_chunk == "" and by[n1].authority == "STANDARD")
    a, b = ids_for(spec, "V_O1")[0], ids_for(spec, "V_O2")[0]
    ok(run(spec, {a: T, b: F, n1: T, n2: F}) is F)        # "may they be smaller?": no
    ok(run(spec, {a: T, b: F, n1: T, n2: T}) is T)        # the ask's own check decides


def test_an_ask_about_the_manual_is_one_check_over_its_statements():
    # a rule and the Option that relaxes it pull opposite ways for "may it ...?":
    # no merge of them is right, so they are statements the ask's own check reads
    rule = {"why": "x", "bears": True,
            "checks": [check("The manual requires zorb markers no more than 40 yards apart here.", about="manual")]}
    opt = {"why": "x", "bears": True, "relaxes": ["W_S1"],
           "checks": [check("The manual allows zorb markers up to 60 yards apart here.", about="manual",
                            typ="exception")]}
    spec, rep = sp.make_structured_parser(model({"W_S1": rule, "W_O2": opt}, facts=MANUAL))(Q, KQ)
    r, o = ids_for(spec, "W_S1")[0], ids_for(spec, "W_O2")[0]
    node = {x.id: x for x in spec.obligations}[spec.terminal]
    ok(spec.merges == [] and node.requires == [r, o] and node.claim == MANUAL["asked"][0]["claim"], spec.merges)
    ok([h["paragraph"] for h in node.evidence_hint] == ["1", "2"])
    for st_r, st_o in ((F, T), (T, F)):                    # whichever way they come out, the ask's check decides
        ok(run(spec, {r: st_r, o: st_o, node.id: T}) is T and run(spec, {r: st_r, o: st_o, node.id: F}) is F)
    ok(not any("is an exception obligation" in p for p in rep.open_problems), rep.open_problems)
    # an exception check with no rule that bears is still a statement for an ask about the manual
    spec, rep = sp.make_structured_parser(model({"W_O2": opt}, facts=MANUAL))(Q, KQ)
    node = {x.id: x for x in spec.obligations}[spec.terminal]
    ok(node.requires == ids_for(spec, "W_O2"), node)
    # a check about the case that also answers an ask about the manual is one more statement there
    facts = {"facts": FACTS["facts"], "asked": FACTS["asked"] + MANUAL["asked"]}
    both = {**RULE, "checks": [check("The zorb markers spaced 50 yards apart are no more than 40 yards apart.",
                                     answers=("a1", "a2"))]}
    spec, rep = sp.make_structured_parser(model({"W_S1": both}, facts=facts))(Q + " Where may the markers go?", KQ)
    a2 = {x.id: x for x in spec.obligations}[next(a for a in spec.asked if a.id == "a2").answered_by[0]]
    rule_id = ids_for(spec, "W_S1")[0]
    ok(a2.requires == [rule_id] and run(spec, {rule_id: F, a2.id: T}) is F)   # a1 fails; a2 is its own check


def test_the_ask_check_is_read_by_a_model_and_points_to_plain_paragraphs_first():
    facts = {"facts": FACTS["facts"], "asked": [{"id": "a1", "ask": "How far apart may they be?", "about": "manual",
                                                 "claim": "The spacing is at most 40 yards"}]}
    kq = KQ + [ch("L_A", "9Z.01", "Standard", 6, "item A", item="A", lead_in="Markers shall be:")]
    st = {"why": "x", "bears": True, "checks": [check("The manual requires markers no more than 40 yards apart.",
                                                      about="manual")]}
    spec, _r = sp.make_structured_parser(model({"L_A": st, "W_S1": st}, facts=facts))(Q, kq)
    net, _p = instantiate(spec)
    top = net.op(spec.terminal)
    ok(top.verifier == "llm", top.verifier)                 # a short comparison-like claim, still a model
    ok([h["paragraph"] for h in top.evidence_hint] == ["1", "6"], top.evidence_hint)   # the list last
    spec, _r = sp.make_structured_parser(model({}, facts=facts))(Q, KQ)                 # the fallback too
    ok(instantiate(spec)[0].op(spec.terminal).verifier == "llm")


def test_a_statement_about_the_manual_found_false_is_not_a_non_conformance():
    from mrag.vine.answer import _facts
    adv_m = {"why": "x", "bears": True,
             "checks": [check("The manual recommends that zorb markers be orange here.", about="manual")]}
    spec, _r = sp.make_structured_parser(model({"W_G3": adv_m}, facts=MANUAL))(Q, KQ)
    net, _p = instantiate(spec)
    g = ids_for(spec, "W_G3")[0]

    def verify(op, store):
        st = {g: F}.get(op.id, T)
        return Certificate(claim=op.claim, status=st, normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id, confidence=0.9)
    trace = execute(net, {v: verify for v in ALL})
    ok(_facts(net, trace)["non_conformances"] == [])
    # about the case, as before: a Guidance not followed is listed
    adv_c = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.")]}
    spec, _r = sp.make_structured_parser(model({"W_S1": RULE, "W_G3": adv_c}))(Q, KQ)
    net, _p = instantiate(spec)
    g = ids_for(spec, "W_G3")[0]
    trace = execute(net, {v: verify for v in ALL})
    ok(_facts(net, trace)["non_conformances"] == ["The zorb markers are orange."])


def test_an_ask_about_the_case_with_only_guidance_is_merged_at_guidance():
    a = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.")]}
    kq = KQ + [ch("W_G5", "9Z.01", "Guidance", 5, "Zorb markers should be round.")]
    b = {"why": "x", "bears": True, "checks": [check("The zorb markers are round.")]}
    spec, _r = sp.make_structured_parser(model({"W_G3": a, "W_G5": b}))(Q, kq)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.kind == "conjunction" and term.authority == "GUIDANCE", term)
    ok(run(spec, {ids_for(spec, "W_G3")[0]: T, ids_for(spec, "W_G5")[0]: F}) is F)   # "is it as recommended?": no


def test_a_definition_under_a_standard_does_not_hide_a_failed_guidance():
    # a Standard that only defines a term, beside the Guidance on the very thing
    # asked: the ask is decided at Guidance, so the failed Guidance is a "no"
    kq = KQ + [ch("W_S7", "9Z.01", "Standard", 7, "A zorb marker is a raised disc.")]
    defn = {"why": "x", "bears": True, "checks": [check("The zorb markers are raised discs.", typ="definitional")]}
    adv = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.")]}
    spec, _r = sp.make_structured_parser(model({"W_S7": defn, "W_G3": adv}))(Q, kq)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    d, g = ids_for(spec, "W_S7")[0], ids_for(spec, "W_G3")[0]
    ok(term.kind == "conjunction" and term.authority == "GUIDANCE", term)
    ok(run(spec, {d: T, g: F}) is F and run(spec, {d: F, g: T}) is F and run(spec, {d: T, g: T}) is T)
    # a Standard that states a practice keeps the rule: the Guidance not followed does not refute
    spec, _r = sp.make_structured_parser(model({"W_S1": RULE, "W_G3": adv}))(Q, KQ)
    term = next(m for m in spec.merges if m.id == spec.terminal)
    ok(term.authority == "STANDARD" and run(spec, {ids_for(spec, "W_S1")[0]: T, ids_for(spec, "W_G3")[0]: F}) is T)
    # only definitions: the rule over all of them, as before
    defn2 = {"why": "x", "bears": True, "checks": [check("The zorb markers are discs.", typ="definitional")]}
    spec, _r = sp.make_structured_parser(model({"W_S7": defn, "W_S1": defn2}))(Q, kq)
    ok(next(m for m in spec.merges if m.id == spec.terminal).authority == "STANDARD")


def test_an_exception_with_two_checks_raises_no_coverage_problem():
    exc = {**EXC, "condition": "", "checks": EXC["checks"] + [
        check("The blip lane is narrower than 9 yards, as the paragraph requires.", typ="exception")]}
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": exc}))(Q, KQ)
    ok(any(m.kind == "exception" for m in spec.merges) and rep.open_problems == [], rep.open_problems)


def test_one_asks_answer_does_not_change_with_another_ask_beside_it():
    facts = {**FACTS, "asked": FACTS["asked"] + [{"id": "a2", "ask": "Are they the right colour?", "about": "case",
                                                  "claim": "The colour of the zorb markers meets the manual."}]}
    adv = {"why": "x", "bears": True, "checks": [check("The zorb markers are orange.", answers=("a2",))]}
    rule = {**RULE, "checks": RULE["checks"]}
    both, _r = sp.make_structured_parser(model({"W_S1": rule, "W_G3": adv}, facts=facts))(Q + " Are they the right colour?", KQ)
    adv1 = {**adv, "checks": [check("The zorb markers are orange.", answers=("a1",))]}
    alone, _r = sp.make_structured_parser(model({"W_G3": adv1}, facts={**facts, "asked": facts["asked"][1:]}))(Q, KQ)
    g = ids_for(both, "W_G3")[0]
    ok(run(both, {ids_for(both, "W_S1")[0]: T, g: F}) is F)
    ok(run(alone, {ids_for(alone, "W_G3")[0]: F}) is F)


def test_a_cut_off_repair_does_not_replace_a_readable_reply():
    first = {"paragraphs": [{"id": "W_S1", **RULE}, {"id": "W_O2", "why": "x", "bears": "maybe", "checks": []},
                            {"id": "W_G3", "why": "x", "bears": False, "checks": []},
                            {"id": "G_S1", "why": "x", "bears": False, "checks": []}]}
    replies = [json.dumps(FACTS), json.dumps(first), '{"paragraphs": [{"id": "W_S1", "why": "he']

    def ask(prompt, images=None):
        return replies.pop(0)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is not None and ids_for(spec, "W_S1") != [], (spec, rep.problems))
    ok(rep.steps == {"facts": 1, "section": 2} and spec.obligations[0].source_chunk == "W_S1")


def test_a_failed_repair_call_keeps_the_first_reply():
    first = {"paragraphs": [{"id": "W_S1", **RULE}, {"id": "W_O2", "why": "x", "bears": "maybe", "checks": []}]}
    replies = [json.dumps(FACTS), json.dumps(first)]

    def ask(prompt, images=None):
        if not replies:
            raise RuntimeError("the API answered 400: PromptTooLong")
        return replies.pop(0)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is not None and rep.source == "semantic_parser" and ids_for(spec, "W_S1") != [])
    ok(any("the repair call failed" in p for p in rep.open_problems), rep.open_problems)
    # the facts step too
    replies = [json.dumps({**FACTS, "facts": FACTS["facts"] + [{"id": "f2", "fact": "It meets the 40-yard rule."}]})]
    inner = model({"W_S1": RULE})

    def ask2(prompt, images=None):
        if "This step reads the QUESTION only" in prompt:
            if not replies:
                raise RuntimeError("the server went away")
            return replies.pop(0)
        return inner(prompt)
    ask2.last = None
    spec, rep = sp.make_structured_parser(ask2)(Q, KQ)
    ok(spec is not None and [f.id for f in spec.facts] == ["f1"], rep.problems)
    ok(any("facts: the repair call failed" in p for p in rep.open_problems), rep.open_problems)


def test_the_facts_step_keeps_its_best_reply():
    good_but_one = {"facts": FACTS["facts"] + [{"id": "f2", "fact": "It meets the 40-yard rule."}],
                    "asked": FACTS["asked"]}
    worse = {"facts": [{"id": "f1", "fact": "It meets the 40-yard rule."}], "asked": []}
    replies = [json.dumps(good_but_one), json.dumps(worse), json.dumps(worse)]
    inner = model({"W_S1": RULE})

    def ask(prompt, images=None):
        return replies.pop(0) if "This step reads the QUESTION only" in prompt else inner(prompt)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is not None and [f.text for f in spec.facts] == [FACTS["facts"][0]["fact"]], rep.notes)
    ok(spec.asked[0].ask == FACTS["asked"][0]["ask"])


def test_ids_are_numbered_by_position():
    odd = {"facts": [{"id": "fact-1", "fact": FACTS["facts"][0]["fact"]}],
           "asked": [{"id": "Q1", **{k: v for k, v in FACTS["asked"][0].items() if k != "id"}}]}
    data, problems = sp.read_facts(json.dumps(odd), Q)
    ok(problems == [] and data["facts"][0].id == "f1" and data["asked"][0]["id"] == "a1", problems)


def test_with_no_facts_an_ask_about_the_case_is_read_as_about_the_manual():
    nofacts = {"facts": [], "asked": FACTS["asked"]}
    g = {"why": "x", "bears": True, "checks": [check("The manual requires gadget markings to be white.",
                                                     about="manual")]}
    spec, rep = sp.make_structured_parser(model({"G_S1": g}, facts=nofacts))("Must gadget markings be white?", KQ)
    ok(spec is not None and ids_for(spec, "G_S1") != [] and rep.asked[0]["about"] == "manual", rep.notes)
    ok(any("read as about the manual" in n for n in rep.notes))


def test_a_split_section_is_shown_whole_and_can_name_the_other_part():
    chunks = [ch(f"S{i}", "9Z.50", "Standard", i, f"made-up rule {i}") for i in range(1, 6)]
    chunks += [ch(f"O{i}", "9Z.50", "Option", i, f"made-up option {i}") for i in range(6, 11)]
    calls = sp.plan_calls(chunks, (), cap=6)
    ok([c.decide for c in calls] == [["S1", "S2", "S3", "S4", "S5"], ["O6", "O7", "O8", "O9", "O10"]])
    ok(all(len(c.items) == 10 for c in calls))
    prompt = sp.build_section_prompt("q?", F1, ASKED, calls[1], {}, {})
    ok("are decided in another call" in prompt and "[S1]" in prompt.split("are decided in another call")[0])
    items = [{"id": "O6", "why": "x", "bears": True, "relaxes": ["S1"],
              "checks": [check("The option covers the markers.", typ="exception")]},
             {"id": "S2", "why": "x", "bears": False, "checks": []}]
    _d, dec, problems, notes = sp.read_section(json.dumps({"paragraphs": items}), calls[1], ASKED, F1, Q, set())
    ok(dec["O6"]["relaxes"] == ["S1"] and "S2" not in dec, dec)
    ok(not any("S2" in p for p in problems) and any("[S2] was decided in this call" in n for n in notes))


def test_an_exception_to_an_exception_is_noted():
    e2 = {"why": "x", "bears": True, "relaxes": ["W_O2"],
          "checks": [check("The orange rule covers it.", typ="exception")]}
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": EXC, "W_G3": e2}))(Q, KQ)
    ok(any("an exception to an exception is not used" in n for n in rep.notes), rep.notes)
    ok(ids_for(spec, "W_G3") == [])


def test_the_graph_adds_whole_paragraphs():
    items = {f"L_{x}": ch(f"L_{x}", "9Z.01", "Option", 9, f"item {x}", item=x, lead_in="The markers may be:")
             for x in "ABCDE"}
    added = sp._additions(KQ, None, options_of=lambda c: list(items) if c["section_id"] == "9Z.01" else [],
                          record_of=items.get)
    ok(sorted(a["chunk"]["chunk_id"] for a in added) == sorted(items), added)   # one paragraph: all its items
    more = {**items, **{f"M{i}": ch(f"M{i}", "9Z.01", "Option", 10 + i, f"option {i}") for i in range(1, 5)}}
    added = sp._additions(KQ, None, options_of=lambda c: list(more) if c["section_id"] == "9Z.01" else [],
                          record_of=more.get)
    ok(len({(a["chunk"]["ordinal"]) for a in added}) == sp.OPTIONS_PER_SECTION, added)   # 3 paragraphs


def test_no_paragraph_retrieved_or_no_ask_gives_no_plan():
    spec, rep = sp.make_structured_parser(model({}))(Q, [KQ[3]])     # only Support
    ok(spec is None and rep.source == "failed" and "no Standard, Guidance or Option" in rep.notes[-1])
    noask = {"facts": FACTS["facts"], "asked": []}
    spec, rep = sp.make_structured_parser(model({}, facts=noask), fact_attempts=1)(Q, KQ)
    ok(spec is None and rep.source == "failed")


def test_a_failed_model_call_is_marked_for_another_try():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
    import vine_run as vr
    import parser_check as pc
    calls = []

    def ask(prompt, images=None):
        calls.append(prompt)
        if len(calls) == 2:
            raise ConnectionError("the server went away")
        return json.dumps(FACTS)
    ask.last = None
    spec, rep = sp.make_structured_parser(ask)(Q, KQ)
    ok(spec is None and rep.source == "failed")
    rec = pc.make_record("X", Q, {"chunks": KQ}, spec, rep)
    ok(rec["outcome"] == "failed" and vr.plan_needs_retry(rec, Q), rec["problems"])


def test_a_leftover_problem_drops_only_that_check():
    bad = {"why": "x", "bears": True, "checks": [
        check("The zorb markers are no more than 40 yards apart."),
        check("The manual requires 40 yards.", about="manual")]}            # wrong for an ask about the case
    log = []
    spec, rep = sp.make_structured_parser(model({"W_S1": bad}, log=log))(Q, KQ)
    ok(spec is not None and rep.attempts == 2 and len(log) == 3)          # facts, section, its repair
    ok(len(spec.obligations) == 1 and "40 yards apart" in spec.obligations[0].claim)
    ok(any("but the claim is about the manual" in p for p in rep.open_problems), rep.open_problems)
    para = next(p for p in rep.paragraphs if p["id"] == "W_S1")
    ok(para["checks"] == 1 and para["dropped_checks"] == 1)


def test_the_record_keeps_every_decision():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
    import parser_check as pc
    spec, rep = sp.make_structured_parser(model({"W_S1": RULE, "W_O2": EXC}))(Q, KQ)
    rec = pc.make_record("X", Q, {"chunks": KQ}, spec, rep)
    ok(rec["outcome"] == "valid first time" and len(rec["paragraphs"]) == 4)
    ok(rec["asked"][0]["claim"] == FACTS["asked"][0]["claim"] and rec["steps"] == {"facts": 1, "section": 1})
    ok(rec["spec"]["obligations"][0]["about"] == "case")
    json.dumps(rec)                                                       # it can be saved


# --------------------------------------------------------------------------- #
# 5. The "about" label: in the IR, and shown to the checker
# --------------------------------------------------------------------------- #
def test_about_is_kept_in_the_plan_and_an_old_plan_reads_as_before():
    from mrag.vine.compile import NetworkSpec
    old = {"query": "q", "terminal": "p1", "obligations": [
        {"id": "p1", "claim": "The made-up panel is blue.", "type": "classification",
         "authority": "STANDARD", "source_chunk": "Z1"}]}
    spec = NetworkSpec.from_dict(old)
    ok(spec.obligations[0].about == "" and "about" not in spec.as_dict()["obligations"][0])
    new = json.loads(json.dumps(old))
    new["obligations"][0]["about"] = " Case "
    spec = NetworkSpec.from_dict(new)
    ok(spec.obligations[0].about == "case" and spec.as_dict()["obligations"][0]["about"] == "case")
    ok(NetworkSpec.from_dict(spec.as_dict()).obligations[0].about == "case")
    net, problems = instantiate(spec)
    ok(problems == [] and net.op("p1").about == "case")
    new["obligations"][0]["about"] = "both"
    ok(any("about 'both'" in p for p in NetworkSpec.from_dict(new).problems()))


def test_the_checker_is_told_what_the_claim_is_about():
    from mrag.vine.model_verifiers import build_prompt
    from mrag.vine.network import Operation
    def prompt(about):
        op = Operation(id="o1", claim="The made-up panel is blue.", produces="s_o1", about=about)
        return build_prompt(op, [], [])[0]
    plain, case, manual = prompt(""), prompt("case"), prompt("manual")
    ok("WHAT THIS CLAIM IS ABOUT" not in plain)
    ok("WHAT THIS CLAIM IS ABOUT: THE CASE" in case and "WHAT THE MANUAL SAYS FOR THIS CASE" in manual)
    ok(case.replace(sp_about("case"), "").replace("\n\n\n", "\n") .count("CLAIM") ==
       plain.count("CLAIM"))
    # the block comes right after the claim, and nothing else changes
    ok(case.index("WHAT THIS CLAIM IS ABOUT") < case.index("GIVEN IN THE QUESTION"))
    ok(case.replace(sp_about("case") + "\n\n", "") == plain)
    ok(manual.replace(sp_about("manual") + "\n\n", "") == plain)


def sp_about(kind):
    from mrag.vine.model_verifiers import _ABOUT
    return _ABOUT[kind]


def test_the_instructions_hold_no_question():
    for name in ("FACTS_TASK", "SECTION_TASK", "SECTION_CONTRACT"):
        text = getattr(sp, name)
        ok(not any(w in text.lower() for w in ("zorb", "blip", "gadget")))
    ok(sp.INSTRUCTIONS.startswith(sp.VERSION))


if __name__ == "__main__":
    for _name, _f in sorted(globals().items()):
        if _name.startswith("test_") and callable(_f):
            _f()
            print("ok", _name)
    print(f"ALL STRUCTURED-PARSER TESTS PASSED ({checks} checks)")
