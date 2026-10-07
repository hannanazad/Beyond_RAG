"""Tests for the semantic parser — the LLM half of Compile.

The model is a stub throughout, so this runs at no cost. What is tested is
not the quality of a decomposition; it is that nothing a model emits reaches
the executor without passing the same checks, and that a model which cannot
produce a valid spec cannot take the pipeline down.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import Authority, ObligationType, Status, execute
from mrag.vine.compile import CompileError, instantiate
from mrag.vine.parser import (ParseReport, build_parser_prompt,
                              make_semantic_parser, read_spec)

CHUNKS = [
    {"chunk_id": "c1", "section_id": "2C.07", "content_type": "Standard",
     "ordinal": 1, "text": "If Table 2C-4 indicates that a horizontal alignment "
                           "sign is required, the sign installed in advance of "
                           "the curve shall be a Curve (W1-2) sign.",
     "table_refs": ["2C-4"], "figure_refs": ["2C-1"]},
    {"chunk_id": "c2", "section_id": "2C.07", "content_type": "Guidance",
     "ordinal": 2, "text": "A Turn (W1-1) sign should be used instead of a Curve "
                           "sign where the advisory speed is 30 mph or less."},
    {"chunk_id": "c3", "section_id": "2C.07", "content_type": "Support",
     "ordinal": 4, "text": "Figure 2C-2 provides examples of warning signs."},
]
QUERY = "Which horizontal alignment sign is required on this curve?"

GOOD = {
    "terminal": "m1",
    "obligations": [
        {"id": "o1", "claim": "Table 2C-4 indicates a sign is required",
         "type": "numerical", "authority": "STANDARD", "requires": [],
         "evidence_hint": [{"type": "table", "id": "Table 2C-4"}],
         "source_chunk": "c1"},
        {"id": "o2", "claim": "the advisory speed is 30 mph or less",
         "type": "numerical", "authority": "GUIDANCE", "requires": ["o1"],
         "guard": {"state": "o1", "status": "TRUE"}, "source_chunk": "c2"},
        {"id": "o3", "claim": "a Curve (W1-2) sign is installed in advance",
         "type": "applicability", "authority": "STANDARD", "requires": ["o1"],
         "evidence_hint": [{"type": "figure", "id": "Figure 2C-1"}],
         "source_chunk": "c1"},
    ],
    "merges": [{"id": "m1", "claim": "the sign requirement is met",
                "kind": "conjunction", "inputs": ["o2", "o3"]}],
}


def say(payload):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return lambda prompt, images: text


def replies(*payloads):
    """A model whose answer changes on each call."""
    seq = [p if isinstance(p, str) else json.dumps(p) for p in payloads]
    box = {"i": 0}

    def ask(prompt, images):
        out = seq[min(box["i"], len(seq) - 1)]
        box["i"] += 1
        box["last_prompt"] = prompt
        return out
    ask.box = box
    return ask


# ---- 1. the prompt carries the provisions and marks Support ---------------
prompt = build_parser_prompt(QUERY, CHUNKS, "2C.07")
assert QUERY in prompt and "2C.07" in prompt
assert "[c1]" in prompt and "[c3]" in prompt
assert "information only; never an obligation" in prompt
assert "cites: Table 2C-4; Figure 2C-1" in prompt
assert "Do not name a checker" in prompt
assert "usual shape" not in prompt and "max(A, B)" not in prompt
print("1. the prompt lists the provisions, their citations, and marks Support")

# ---- 2. a good reply becomes a valid spec ---------------------------------
parse = make_semantic_parser(say(GOOD))
spec, report = parse(QUERY, CHUNKS, "2C.07")
assert report.source == "semantic_parser" and report.attempts == 1
assert spec.problems() == []
net, problems = instantiate(spec)
assert problems == []
assert [o.id for o in spec.obligations] == ["o1", "o2", "o3"]
print("2. a well-formed reply compiles and validates first time")

# ---- 3. the verifier is assigned by rule, not by the model ---------------
assert net.op("o1").verifier == "calculator"    # it cites a table
assert net.op("o3").verifier == "vlm"           # it cites a figure
assert net.op("o2").verifier == "symbolic"      # an atomic comparison
print("3. verifiers come from the rule: table -> calculator, figure -> vlm, "
      "comparison -> symbolic")

# ---- 4. a verifier the model names is discarded --------------------------
sneaky = json.loads(json.dumps(GOOD))
sneaky["obligations"][0]["verifier"] = "llm"    # route the table lookup to itself
spec, report = make_semantic_parser(say(sneaky))(QUERY, CHUNKS, "2C.07")
net, _ = instantiate(spec)
assert net.op("o1").verifier == "calculator"
assert any("proposed verifier was discarded" in n for n in report.notes)
print("4. a model trying to name its own verifier is overruled")

# ---- 5. an invented source_chunk is sent back for repair -----------------
fake = json.loads(json.dumps(GOOD))
fake["obligations"][1]["source_chunk"] = "c99"
ask = replies(fake, GOOD)
spec, report = make_semantic_parser(ask)(QUERY, CHUNKS, "2C.07")
assert report.source == "semantic_parser" and report.attempts == 2
assert any("'c99' is not one of the provisions shown" in p
           for group in report.problems for p in group)
assert "'c99'" in ask.box["last_prompt"]
print("5. provenance pointing at a chunk that was never supplied is sent back")

# ---- 6. the guard became a real function ---------------------------------
spec, report = make_semantic_parser(say(GOOD))(QUERY, CHUNKS, "2C.07")
net, _ = instantiate(spec)
assert net.op("o2").guard is not None
assert net.op("o2").guard_desc == "o1 is TRUE"
print("6. a guard in the reply becomes the function Eq 4 needs")

# ---- 7. a broken spec is repaired, not accepted --------------------------
broken = json.loads(json.dumps(GOOD))
broken["merges"][0]["inputs"] = ["o2", "o9"]     # o9 does not exist
ask = replies(broken, GOOD)
spec, report = make_semantic_parser(ask)(QUERY, CHUNKS, "2C.07")
assert report.attempts == 2 and report.source == "semantic_parser"
assert any("o9" in p for group in report.problems for p in group)
# the repair prompt must name the ids the model itself wrote
assert "YOUR PREVIOUS PLAN WAS REJECTED" in ask.box["last_prompt"]
assert "'o9'" in ask.box["last_prompt"]
assert "s_o9" not in ask.box["last_prompt"]      # not internal state names
print("7. a dangling reference is sent back with the id the model wrote, and "
      "the second attempt succeeds")

# ---- 8. a SUPPORT obligation is rejected ---------------------------------
support = json.loads(json.dumps(GOOD))
support["obligations"][2]["authority"] = "SUPPORT"
spec, report = make_semantic_parser(say(support), max_attempts=1)(
    QUERY, CHUNKS, "2C.07")
assert report.source == "baseline"
assert any("SUPPORT" in p for group in report.problems for p in group)
print("8. Support material offered as an obligation is rejected")

# ---- 9. an exception merge with the base in the wrong place --------------
wrong = {"terminal": "m1",
         "obligations": [
             {"id": "o1", "claim": "except where otherwise provided",
              "type": "exception", "authority": "STANDARD", "source_chunk": "c1"},
             {"id": "o2", "claim": "the sign shall be a Curve sign",
              "type": "applicability", "authority": "STANDARD",
              "source_chunk": "c1"}],
         "merges": [{"id": "m1", "claim": "the decision", "kind": "exception",
                     "inputs": ["o1", "o2"]}]}
spec, report = make_semantic_parser(say(wrong), max_attempts=1)(
    QUERY, CHUNKS, "2C.07")
assert any("itself an exception" in p for group in report.problems for p in group)
print("9. an exception merge whose first input is the exception is rejected")

# ---- 10. a cycle is caught ------------------------------------------------
cyc = {"terminal": "o1",
       "obligations": [
           {"id": "o1", "claim": "a", "authority": "STANDARD",
            "requires": ["o2"], "source_chunk": "c1"},
           {"id": "o2", "claim": "b", "authority": "STANDARD",
            "requires": ["o1"], "source_chunk": "c1"}],
       "merges": []}
spec, report = make_semantic_parser(say(cyc), max_attempts=1)(
    QUERY, CHUNKS, "2C.07")
assert any("cycle" in p for group in report.problems for p in group)
print("10. a dependency cycle is caught before execution")

# ---- 11. prose, and a crash, both fall back to the printed structure ------
for bad, why in [("I would check the table first, then the figure.", "prose"),
                 ("{ nope", "malformed")]:
    spec, report = make_semantic_parser(say(bad), max_attempts=2)(
        QUERY, CHUNKS, "2C.07")
    assert report.source == "baseline", why
    assert spec is not None and instantiate(spec)[1] == []


def boom(prompt, images):
    raise RuntimeError("rate limited")


spec, report = make_semantic_parser(boom)(QUERY, CHUNKS, "2C.07")
assert report.source == "baseline" and spec is not None
assert any("rate limited" in p for group in report.problems for p in group)
print("11. prose, malformed JSON and a crashed model all fall back to the "
      "printed structure")

# ---- 12. with no fallback, failure is reported as failure ----------------
spec, report = make_semantic_parser(say("nope"), max_attempts=1,
                                    fall_back_to_baseline=False)(
    QUERY, CHUNKS, "2C.07")
assert spec is None and report.source == "failed"
print("12. with the fallback off, a failure is a failure and says so")

# ---- 13. the compiled network runs --------------------------------------
spec, report = make_semantic_parser(say(GOOD))(QUERY, CHUNKS, "2C.07")
net, _ = instantiate(spec)
from mrag.vine import Certificate


def stub(op, store):
    return Certificate(claim=op.claim, status=Status.TRUE, confidence=0.9,
                       normative_authority=op.normative_authority)


trace = execute(net, {k: stub for k in
                      ("llm", "vlm", "calculator", "symbolic",
                       "cross_reference_resolver")})
assert trace.problems == [] and trace.terminal.status is Status.TRUE
assert trace.waves[0] == ["o1"]            # the gate runs alone
assert sorted(trace.waves[1]) == ["o2", "o3"]
print("13. the parsed network executes, gate first and the two branches "
      "together")

# ---- 14. the report is auditable ----------------------------------------
assert report.as_dict()["source"] == "semantic_parser"
assert isinstance(report.raw[0], str) and report.raw[0]
print("14. the report records the source, the attempts and the raw replies")

# ---- 15. a plan must point at the manual's real provisions ----------------
def one_problem(mutate, **kw):
    bad = json.loads(json.dumps(GOOD))
    mutate(bad)
    _spec, rep = make_semantic_parser(say(bad), max_attempts=1,
                                      fall_back_to_baseline=False, **kw)(
        QUERY, CHUNKS, "2C.07")
    assert rep.source == "failed", rep.as_dict()
    return [p for group in rep.problems for p in group]


probs = one_problem(lambda d: d["obligations"][2].update(source_chunk="c3"))
assert any("Support text" in p for p in probs), probs
probs = one_problem(lambda d: d["obligations"][1].update(authority="STANDARD"))
assert any("printed as Guidance" in p for p in probs), probs
probs = one_problem(lambda d: d["obligations"][2].update(source_chunk=""))
assert any("no source_chunk" in p for p in probs), probs
print("15. a source that is Support, missing, or a heading that is not the "
      "printed one, is sent back")

# ---- 16. hints must name things the manual has ---------------------------
known = {("table", "2C-4"), ("figure", "2C-1"), ("section", "2C.07")}
check = lambda kind, ident: (kind, ident) in known
spec, report = make_semantic_parser(say(GOOD), check_ref=check)(QUERY, CHUNKS, "2C.07")
assert report.source == "semantic_parser"
probs = one_problem(lambda d: d["obligations"][0]["evidence_hint"].__setitem__(
    0, {"type": "table", "id": "Table 9Z-9"}), check_ref=check)
assert any("'Table 9Z-9' in evidence_hint is not in the manual" in p for p in probs)
probs = one_problem(lambda d: d["obligations"][0]["evidence_hint"].__setitem__(
    0, {"type": "table", "id": "Figure 2C-1"}), check_ref=check)
assert any("use type 'figure'" in p for p in probs), probs
probs = one_problem(lambda d: d["merges"][0].update(kind="threshold"))
assert any("threshold merge" in p for p in probs), probs
print("16. a table, figure or section the manual does not have is sent back, "
      "and so is a threshold merge")

probs = one_problem(lambda d: d["obligations"][1].update(
    requires=[], guard={"not": {"state": "o1", "status": "TRUE"}}))
assert any("its guard reads ['o1'], which must also be in its requires" in p
           for p in probs), probs
print("16b. a guard that reads a result the item does not wait for is sent back")

# ---- 17. a column must be one the table prints ---------------------------
class FakeTable:
    def __init__(self, labels, part=None, sheet=None):
        self.column_labels, self.part, self.sheet = labels, part, sheet
    def column(self, frag):
        f = frag.strip().lower()
        return next((i for i, l in enumerate(self.column_labels) if f in l.lower()), None)

tabs = {"Table 2C-4": [FakeTable(["Roadway Type", "Required"], part="A"),
                       FakeTable(["Speed", "Recommended"], part="B")]}
ok = json.loads(json.dumps(GOOD))
ok["obligations"][0]["evidence_hint"] += [{"type": "column", "id": "required"},
                                          {"type": "part", "id": "A"}]
spec, report = make_semantic_parser(say(ok), tables=tabs)(QUERY, CHUNKS, "2C.07")
assert report.source == "semantic_parser", report.problems
probs = one_problem(lambda d: d["obligations"][0]["evidence_hint"].append(
    {"type": "column", "id": "Width"}), tables=tabs)
assert any("column 'Width' is not a column of Table 2C-4" in p for p in probs), probs
probs = one_problem(lambda d: d["obligations"][0]["evidence_hint"].append(
    {"type": "part", "id": "C"}), tables=tabs)
assert any("part 'C' is not a chart" in p for p in probs), probs
probs = one_problem(lambda d: d["obligations"][1].update(
    evidence_hint=[{"type": "column", "id": "Required"}]), tables=tabs)
assert any("needs a table hint" in p for p in probs), probs
print("17. a column, chart or sheet must be one the named table has")

# ---- 18. an unreadable reply is retried with a different prompt ----------
ask = replies("I think the sign is required.", GOOD)
spec, report = make_semantic_parser(ask)(QUERY, CHUNKS, "2C.07")
assert report.attempts == 2 and report.source == "semantic_parser"
assert "COULD NOT BE READ" in ask.box["last_prompt"]
print("18. a reply with no JSON is retried with a note, not the same prompt")

# ---- 19. table rows and figure descriptions are shown, labelled ----------
items = CHUNKS + [
    {"chunk_id": "vine:trow:Table 2C-4#s1r0", "section_id": "2C.07",
     "content_type": "TableRow", "table_refs": ["Table 2C-4"],
     "text": "Table 2C-4. Roadway Type: Freeways; Required: Yes"},
    {"chunk_id": "vine:reading:2C-1#1:Figure 2C-1", "section_id": "2C.07",
     "content_type": "FigureReading", "figure_refs": ["Figure 2C-1"],
     "text": "Figure 2C-1 shows curve signs."}]
p = build_parser_prompt(QUERY, items, figures=[{"figure_id": "Figure 2C-1",
                                               "caption": "Curve signs"}])
assert "TABLE ROW of Table 2C-4 -- printed table content, not a provision" in p
assert "FIGURE DESCRIPTION of Figure 2C-1 -- written by a reader" in p
assert "[Figure 2C-1] Curve signs" in p
assert p.index("PROVISIONS") < p.index("QUESTION") < p.index("HOW TO WRITE THE PLAN")
_s, rep = make_semantic_parser(say(dict(GOOD, obligations=[
    dict(GOOD["obligations"][0], source_chunk="vine:trow:Table 2C-4#s1r0")]
    + GOOD["obligations"][1:])), max_attempts=1, fall_back_to_baseline=False)(
    QUERY, items, "2C.07")
assert any("a TABLE ROW" in p for g in rep.problems for p in g), rep.problems
print("19. table rows and figure descriptions are shown and labelled; neither "
      "can be an obligation's source")

print("\nALL SEMANTIC PARSER TESTS PASSED")
