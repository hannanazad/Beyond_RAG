"""The fixes of 8 October 2026 (fix5), each found on the DEV cases:

  1. Given facts (Γ0q): the parser lists the facts the question states; the
     compiler puts them in the initial certificate store; every checker sees
     them, and never the question.
  2. Authority follows the evidence (Eq 3): a FALSE that rests on a provision
     printed under a stronger heading carries that heading, and a merge that
     comes out FALSE carries the strongest heading among the inputs that
     failed. Raised only, never lowered.
  3. A cross-reference claim is resolved exactly, then read against the
     manual by the text checker.
  4. The first input of an exception merge may not be an applicability check.

Everything here is made up for the test (ids, claims, provisions). No sample
question, gold answer or MUTCD text is used.
"""
import itertools
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

from mrag.vine import (Authority, Certificate, CertificateStore, Evidence, MergeType,
                       Network, NetworkSpec, Operation, Status, compose, execute,
                       instantiate, merge_authority)
from mrag.vine.experiments import (make_scenario, make_scenario_verifier,
                                   reference_terminal, run_sequential)
from mrag.vine.model_verifiers import build_prompt, make_llm_verifier
from mrag.vine.parser import (PARSER_CONTRACT, fact_problems, grounding_problems,
                              make_semantic_parser)
from mrag.vine.run import build_verifiers, resolve_then_read
import execution_check as ec

T, F, U, NA = Status.TRUE, Status.FALSE, Status.UNKNOWN, Status.NOT_APPLICABLE
S, G, O = Authority.STANDARD, Authority.GUIDANCE, Authority.OPTION
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")

QUESTION = ("A crew put up a blue panel 9 feet above a gravel lane near a park. "
            "The panel faces east. Does the made-up code allow it?")


def spec_of(obligations, merges=(), terminal="o1", facts=None, query=QUESTION):
    d = {"query": query, "terminal": terminal, "obligations": list(obligations),
         "merges": list(merges)}
    if facts is not None:
        d["facts"] = facts
    return NetworkSpec.from_dict(d)


# ---- 1. given facts in the IR and in Γ0q -----------------------------------------
sp = spec_of([{"id": "o1", "claim": "panel P is at least 7 feet high", "type": "numerical"}],
             facts=[{"id": "f1", "fact": "The panel is 9 feet above the lane."},
                    "The panel faces east."])
assert [f.id for f in sp.facts] == ["f1", "f2"], "a fact given as a string gets an id"
net, problems = instantiate(sp)
assert not problems, problems
given = [c for st in net.initial.states() for c in net.initial.get(st)]
assert [c.claim for c in given] == ["The panel is 9 feet above the lane.", "The panel faces east."]
assert all(c.status is T and c.verifier == "given" and c.normative_authority is Authority.SUPPORT
           and c.evidence == [Evidence("given", c.obligation_id)] for c in given)
assert sp.as_dict()["facts"][0] == {"id": "f1", "fact": "The panel is 9 feet above the lane."}
assert "facts" not in spec_of([{"id": "o1", "claim": "c"}]).as_dict(), \
    "a spec with no facts serialises exactly as before"
# the executor starts from them, and they are not steps
trace = execute(net, {k: (lambda op, st: Certificate(op.claim, T, [Evidence("chunk", "Z1")],
                                                     verifier="t")) for k in ALL})
assert trace.store.latest("given_f1").claim.startswith("The panel")
assert trace.terminal.status is T and trace.waves == [["o1"]]
print("1. facts become certificates in Γ0q; the executor starts from them")

# ---- 2. a fact is never a step, and ids stay unique --------------------------------
bad = spec_of([{"id": "o1", "claim": "c", "requires": ["f1"]}], facts=["x"])
assert any("'f1' is a fact, not a step" in p for p in bad.problems()), bad.problems()
assert not any("no obligation or merge produces" in p for p in bad.problems()), \
    "a misused fact gets one clear message, not two"
bad = spec_of([{"id": "o1", "claim": "c"}, {"id": "o2", "claim": "d"}],
              [{"id": "m1", "claim": "m", "kind": "conjunction", "inputs": ["o1", "f1"]}],
              terminal="m1", facts=["x"])
assert any("'f1' is a fact" in p for p in bad.problems())
bad = spec_of([{"id": "o1", "claim": "c", "guard": {"state": "f1", "status": "TRUE"},
                "requires": ["f1"]}], facts=["x"])
assert any("'f1' is a fact" in p for p in bad.problems())
bad = spec_of([{"id": "f1", "claim": "c"}], terminal="f1", facts=["x"])
assert any("duplicate ids" in p for p in bad.problems())
try:
    NetworkSpec.from_dict({"query": "q", "terminal": "o1", "facts": "not a list",
                           "obligations": [{"id": "o1", "claim": "c"}]})
    raise AssertionError("facts that are not a list must be refused")
except ValueError:
    pass
print("2. facts are never in requires, inputs, guards or the terminal; ids are unique")

# ---- 3. a fact is the question's own --------------------------------------------
sp = spec_of([{"id": "o1", "claim": "c"}], facts=[
    "The panel is 9 feet above the lane.",                 # fine
    "The panel is blue.",                                  # fine
    "The panel is 2 feet higher than 7 feet.",             # numbers worked out
    "Section 9Z.01 covers the panel.",                     # cites the manual
    "The panel violates the colour rule.",                 # a conclusion
    "The panel must be lit.",                              # a requirement
    "The panel is allowed."])                              # "allow" is in the question,
probs = fact_problems(sp)                                  #   "allowed" is not
by_fact = {}
for p in probs:
    by_fact[p.split(":")[0]] = by_fact.get(p.split(":")[0], "") + " | " + p
assert "f1" not in by_fact and "f2" not in by_fact, probs
assert "['2', '7']" in by_fact["f3"]
assert "9Z.01" in by_fact["f4"] and "Section" in by_fact["f4"]
assert "violates" in by_fact["f5"] and "must" in by_fact["f6"] and "allowed" in by_fact["f7"]
# the same words are fine when the question itself uses them
q2 = "Drivers must stop at the gate under Section 9Z.01, 1,200 feet ahead. Where may it go?"
assert fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q2, facts=[
    "Drivers must stop at the gate.", "The gate is 1200 feet ahead.",
    "The gate is under Section 9Z.01."])) == []
# a paraphrase may carry a conclusion: a fact is the question's own words
q6 = "A blue panel is 9 feet above a lane. Is it OK?"
flagged = {p_.split(":")[0] for p_ in fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q6, facts=[
    "The panel is good.", "The panel is too low.", "The panel is within the limits.",
    "The blue panel is nine feet above the lane.", "It is 9 feet above a lane."]))}
assert flagged == {"f1", "f2", "f3"}, flagged
# short forms do not end a sentence; "State Route" is not an ask
for q7 in ("The sign is 30 in. wide on a 45 mph road. Is it big enough?",
           "State Route 12 has a posted speed of 45 mph. What sign is needed?"):
    fact = q7.rsplit(". ", 1)[0] + "."
    assert fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q7, facts=[fact])) == [], q7
# grounding_problems reports them with everything else
assert any(p.startswith("f5:") for p in grounding_problems(sp, []))
# only what the question STATES counts, not what it asks
q3 = "A blue panel is 9 feet above a lane. Is this panel allowed?"
got = fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q3, facts=[
    "This panel is allowed.",                       # the ask, turned into a fact
    q3,                                             # the whole question
    "Is this panel allowed",                        # a question without its mark
    "A blue panel is nine feet above a lane.",      # fine: nine is 9
    "The panel is ten feet up."]))                  # ten is not in the question
by_fact = {}
for p_ in got:
    by_fact.setdefault(p_.split(":")[0], []).append(p_)
assert "allowed" in " ".join(by_fact["f1"])
assert any("is a question" in x for x in by_fact["f2"]) and any("is a question" in x for x in by_fact["f3"])
assert "f4" not in by_fact and "['10']" in " ".join(by_fact["f5"])
assert any("copies what the question asks" in x for x in fact_problems(spec_of(
    [{"id": "o1", "claim": "c"}], query=q3, facts=["Yes, is this panel allowed here."])))
# conclusion words, asks without a question mark, and two sentences in one fact
q4 = "A blue panel is 9 feet above a lane. Is it OK?"
flagged = {p_.split(":")[0] for p_ in fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q4, facts=[
    "The panel is OK.", "The placement is fine.", "A larger panel is needed.",
    "The exception applies to this panel.", "The panel fails the rule.",
    "The panel is consistent with the rule.", "A blue panel is 9 feet above a lane.",
    "A blue panel is 9 feet above a lane. It is blue."]))}
assert flagged == {"f1", "f2", "f3", "f4", "f5", "f6", "f8"}, flagged
for q5 in ("A blue panel is 9 feet above a lane. Determine whether this panel is allowed.",
           'A blue panel is 9 feet above a lane. "Is this panel allowed?"',
           "A blue panel is 9 feet above a lane. The crew wants to know if this panel is allowed"):
    flagged = {p_.split(":")[0] for p_ in fact_problems(spec_of([{"id": "o1", "claim": "c"}], query=q5,
               facts=["This panel is allowed.", q5, "A blue panel is 9 feet above a lane."]))}
    assert flagged == {"f1", "f2"}, (q5, flagged)
# a fact id is f1, f2, ...; a blank one is numbered
assert any("fact id 'x'" in p_ for p_ in spec_of([{"id": "o1", "claim": "c"}],
                                                facts=[{"id": "x", "fact": "a"}]).problems())
assert spec_of([{"id": "o1", "claim": "c"}], facts=[{"id": "  ", "fact": "a"}]).facts[0].id == "f1"
print("3. a fact may not add numbers, manual references or requirements to the question")

# ---- 4. the first input of an exception merge -----------------------------------
ex = spec_of([{"id": "o1", "claim": "rule R applies here", "type": "applicability"},
              {"id": "o2", "claim": "exception E covers this", "type": "exception"}],
             [{"id": "m1", "claim": "the case is acceptable", "kind": "exception",
               "inputs": ["o1", "o2"]}], terminal="m1")
assert any("m1: its first input 'o1' is an applicability check" in p
           for p in grounding_problems(ex, []))
ok = spec_of([{"id": "o1", "claim": "case C meets rule R", "type": "classification"},
              {"id": "o2", "claim": "exception E covers this", "type": "exception"}],
             [{"id": "m1", "claim": "the case is acceptable", "kind": "exception",
               "inputs": ["o1", "o2"]}], terminal="m1")
assert not any("applicability check" in p for p in grounding_problems(ok, []))
assert "never an\n  applicability or exception obligation" in PARSER_CONTRACT
assert '"facts": [' in PARSER_CONTRACT and "no checker is shown the question" in PARSER_CONTRACT


# the parser sends such a plan back, and takes the repaired one
def plan(base_type):
    return json.dumps({"terminal": "m1", "facts": [{"id": "f1", "fact": "The panel faces east."}],
                       "obligations": [
                           {"id": "o1", "claim": "panel P meets rule R", "type": base_type,
                            "authority": "STANDARD", "source_chunk": "Z1"},
                           {"id": "o2", "claim": "exception E covers the panel", "type": "exception",
                            "authority": "STANDARD", "source_chunk": "Z2"}],
                       "merges": [{"id": "m1", "claim": "panel P is acceptable",
                                   "kind": "exception", "inputs": ["o1", "o2"]}]})


replies = iter([plan("applicability"), plan("classification")])
prompts = []


def fake_parser_model(prompt, images):
    prompts.append(prompt)
    return next(replies)


KQ = [{"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard", "text": "rule R"},
      {"chunk_id": "Z2", "section_id": "9Z.01", "content_type": "Standard", "text": "exception E"}]
spec, report = make_semantic_parser(fake_parser_model, fall_back_to_baseline=False)(QUESTION, KQ)
assert spec is not None and report.attempts == 2, report.problems
assert "applicability check" in prompts[1] and "YOUR PREVIOUS PLAN WAS REJECTED" in prompts[1]
assert [f.text for f in spec.facts] == ["The panel faces east."]
print("4. an applicability check as the base of an exception merge is sent back for repair")

# ---- 5. what the checker is shown ---------------------------------------------------
CHUNKS = [
    {"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Guidance", "text": "the panel should be blue"},
    {"chunk_id": "Z2", "section_id": "9Z.02", "content_type": "Standard", "text": "a panel shall be lit"},
    {"chunk_id": "Z3", "section_id": "9Z.03", "content_type": "Standard", "text": "a note",
     "authority_inferred": True},
    {"chunk_id": "Z4", "section_id": "9Z.04", "content_type": "Support", "text": "background"},
]


class Retriever:
    def retrieve_for_obligation(self, query, obligation, certificates=None, top_k=None):
        self.query = query
        return SimpleNamespace(chunks=[dict(c) for c in CHUNKS], figures=[], debug={})


def checker(reply):
    seen = {}

    def ask(prompt, images):
        seen["prompt"] = prompt
        return json.dumps(reply)
    return ask, seen


def run_one(reply, authority="GUIDANCE", facts=("The panel faces east.",), status_word=None):
    sp = spec_of([{"id": "o1", "claim": "panel P meets the colour rule", "type": "classification",
                   "authority": authority, "source_chunk": "Z1"}], facts=list(facts))
    net, problems = instantiate(sp)
    assert not problems, problems
    ask, seen = checker(reply)
    v = make_llm_verifier(ask, Retriever(), query=QUESTION, use_pointers=False)
    trace = execute(net, {"llm": v})
    return trace, seen


trace, seen = run_one({"status": "TRUE", "evidence": ["Z1", "f1"], "basis": "Z1",
                       "confidence": 0.9, "reason": "r"})
p = seen["prompt"]
assert "GIVEN IN THE QUESTION" in p and "[f1] The panel faces east." in p
assert QUESTION not in p and "Does the made-up code allow it?" not in p, \
    "the checker is never shown the question"
assert "The panel faces east. => TRUE" not in p, "a fact is listed as given, not as a result"
assert '"basis": "<id>"' in p
c = trace.store.latest("s_o1")
assert c.status is T and Evidence("given", "f1") in c.evidence and Evidence("chunk", "Z1") in c.evidence
assert c.provenance["basis"] == "Z1" and c.provenance["given_facts_shown"] == ["f1"]
# a definite answer resting only on a fact of the case is not grounded in the manual
trace, _ = run_one({"status": "TRUE", "evidence": ["f1"], "confidence": 0.9, "reason": "r"})
c = trace.store.latest("s_o1")
assert c.status is U and "only facts from the question" in c.provenance["downgraded"]
# with no facts the block says so
trace, seen = run_one({"status": "UNKNOWN", "evidence": [], "reason": "r"}, facts=())
assert "GIVEN IN THE QUESTION" in seen["prompt"] and "(none)" in seen["prompt"]
print("5. the checker sees the given facts and may cite them, but they alone settle nothing; "
      "it never sees the question")

# ---- 6. authority follows the evidence a FALSE rests on -------------------------------
trace, _ = run_one({"status": "FALSE", "evidence": ["Z1", "Z2"], "basis": "Z2", "confidence": 0.9,
                    "reason": "a Standard requires it"})
c = trace.store.latest("s_o1")
assert c.status is F and c.normative_authority is S, c
assert c.provenance["authority_from"] == {"basis": "Z2", "printed_heading": "STANDARD",
                                          "declared": "GUIDANCE"}
assert not c.non_conformance() and c.refutes()
# a basis the checker was shown but did not cite as used raises nothing
trace, _ = run_one({"status": "FALSE", "evidence": ["Z1"], "basis": "Z2", "confidence": 0.9, "reason": "r"})
c = trace.store.latest("s_o1")
assert c.status is F and c.normative_authority is G and "authority_from" not in c.provenance
# TRUE does not change it
trace, _ = run_one({"status": "TRUE", "evidence": ["Z2"], "basis": "Z2", "confidence": 0.9, "reason": "r"})
assert trace.store.latest("s_o1").normative_authority is G
# never lowered
trace, _ = run_one({"status": "FALSE", "evidence": ["Z1"], "basis": "Z1", "confidence": 0.9, "reason": "r"},
                   authority="STANDARD")
assert trace.store.latest("s_o1").normative_authority is S
# only a PRINTED heading counts: inferred, Support, unsupplied or missing basis -> unchanged
for basis in ("Z3", "Z4", "NOT-SHOWN", None, "f1"):
    reply = {"status": "FALSE", "evidence": ["Z1", "Z3", "Z4", "f1"], "confidence": 0.9, "reason": "r"}
    if basis is not None:
        reply["basis"] = basis
    trace, _ = run_one(reply)
    c = trace.store.latest("s_o1")
    assert c.status is F and c.normative_authority is G and "authority_from" not in c.provenance, basis
print("6. a FALSE resting on a printed Standard is a Standard FALSE; never lowered; TRUE unchanged")

# ---- 7. the executor lets only that raise through -----------------------------------
op_net, _ = instantiate(spec_of([{"id": "o1", "claim": "c", "authority": "GUIDANCE"}]))


def returns(status, authority, prov=None, who="llm"):
    return lambda op, st: Certificate(op.claim, status, [Evidence("chunk", "Z")], verifier=who,
                                      normative_authority=authority, provenance=dict(prov or {}))


SHOWN = {"authority_from": {"basis": "Z", "printed_heading": "STANDARD"}}
for status, auth, prov, who, expect in [
        (F, S, SHOWN, "llm", S),                     # shown to rest on a printed Standard
        (F, S, SHOWN, "vlm", S),
        (F, S, {}, "llm", G),                        # claimed, not shown
        (F, S, {"authority_from": {"basis": "Z", "printed_heading": "OPTION"}}, "llm", G),
        (F, S, {"authority_from": "yes"}, "llm", G),  # not the record model_verifiers writes
        (F, S, SHOWN, "calculator", G),              # only the text and image checkers raise
        (T, S, SHOWN, "llm", G),                     # only a FALSE is raised
        (F, O, SHOWN, "llm", G)]:                    # never lowered
    t = execute(op_net, {k: returns(status, auth, prov, who) for k in ALL})
    c = t.store.latest("s_o1")
    assert c.normative_authority is expect, (status, auth, prov, who)
    assert ("authority_from" in c.provenance) == (expect is S), "a refused raise must not read as one"
print("7. the executor keeps a shown raise and resets every other change of authority")

# ---- 8. merge authority -------------------------------------------------------------
c_ = lambda oid, st, a: Certificate(oid, st, normative_authority=a, obligation_id=oid)
assert merge_authority(MergeType.CONJUNCTION, [c_("a", F, S), c_("b", T, G)], G, F) == (S, ["a"])
assert merge_authority(MergeType.CONJUNCTION, [c_("a", F, G), c_("b", T, G)], G, T) == (G, [])
assert merge_authority(MergeType.EXCEPTION, [c_("a", F, S), c_("b", F, O)], G, F) == (S, ["a"])
assert merge_authority(MergeType.ALTERNATIVE, [c_("a", F, G), c_("b", F, O)], O, F) == (G, ["a"])
assert merge_authority(MergeType.ALTERNATIVE, [c_("a", F, G), c_("b", F, O)], S, F) == (S, [])
assert merge_authority(MergeType.CONJUNCTION, [c_("a", F, S), c_("b", NA, S)], S, F) == (S, [])


def nested(a_status, inner="GUIDANCE"):
    sp = spec_of([{"id": "a", "claim": "a", "authority": "STANDARD"},
                  {"id": "b", "claim": "b", "authority": "GUIDANCE"},
                  {"id": "c", "claim": "c", "authority": "STANDARD"}],
                 [{"id": "m_in", "claim": "inner", "kind": "conjunction", "inputs": ["a", "b"],
                   "authority": inner},
                  {"id": "m_out", "claim": "outer", "kind": "conjunction", "inputs": ["m_in", "c"],
                   "authority": "STANDARD"}], terminal="m_out")
    net, problems = instantiate(sp)
    assert not problems, problems
    answers = {"a": a_status, "b": T, "c": T}
    return net, execute(net, {k: (lambda op, st: Certificate(op.claim, answers[op.id],
                                                             [Evidence("chunk", "Z")],
                                                             normative_authority=op.normative_authority))
                              for k in ALL})


net, t = nested(F)
inner = t.store.latest("s_m_in")
assert inner.status is F and inner.normative_authority is S, inner
assert inner.provenance["authority_from"] == {"failed_inputs": ["a"], "declared": "GUIDANCE"}
assert t.terminal.status is F, "a failed Standard inside a Guidance-labelled merge still fails the rule"
assert "non-conformance" not in compose(QUESTION, net, t).text.lower()
net, t = nested(T)
assert t.terminal.status is T and t.store.latest("s_m_in").normative_authority is G
print("8. a merge failing on a Standard carries STANDARD, so an enclosing merge cannot pass it")

# ---- 9. the reference evaluator and the sequential baseline agree ---------------------
def random_net(rng, n_ob=5, n_merge=3):
    obs = [{"id": f"o{i}", "claim": f"c{i}", "authority": rng.choice(["STANDARD", "GUIDANCE", "OPTION"])}
           for i in range(n_ob)]
    merges, pool = [], [o["id"] for o in obs]
    for j in range(n_merge):
        if len(pool) < 2:
            break
        k = rng.randint(2, min(3, len(pool)))
        ins = rng.sample(pool, k)
        merges.append({"id": f"m{j}", "claim": f"m{j}", "inputs": ins,
                       "kind": rng.choice(["conjunction", "alternative", "exception"]),
                       "authority": rng.choice(["STANDARD", "GUIDANCE", "OPTION"])})
        pool = [p for p in pool if p not in ins] + [f"m{j}"]
    rest = [p for p in pool if p != merges[-1]["id"]]
    if rest:
        merges.append({"id": "mt", "claim": "top", "kind": "conjunction",
                       "inputs": [merges[-1]["id"]] + rest, "authority": "STANDARD"})
    sp = spec_of(obs, merges, terminal=merges[-1]["id"])
    net, problems = instantiate(sp)
    assert not problems, problems
    return net


rng = random.Random(20261008)
agree = total = seq_agree = 0
for n in range(150):
    net = random_net(rng)
    for seed in range(6):
        sc = make_scenario(net, seed)
        got = execute(net, {k: make_scenario_verifier(sc) for k in ALL}).terminal.status
        ref = reference_terminal(net, sc)
        total += 1
        agree += got is ref
        seq_agree += run_sequential(net, sc).terminal is ref
assert agree == total, f"executor and reference disagree on {total - agree} of {total}"
print(f"9. executor and reference agree on {agree}/{total} random nested networks "
      f"(sequential baseline: {seq_agree}/{total})")

# ---- 10. cross-reference: resolve exactly, then read --------------------------------
calls = []


def resolver_says(status):
    def r(op, st):
        calls.append("resolver")
        return Certificate(op.claim, status, [Evidence("section", "9Z.01")],
                           verifier="cross_reference_resolver",
                           provenance={"resolved": ["Section 9Z.01"], "dangling": [],
                                       "reason": "no reference found" if status is U else ""})
    return r


def reader_says(status):
    def r(op, st):
        calls.append("reader")
        return Certificate(op.claim, status, [Evidence("chunk", "Z1")] if status is not U else [],
                           verifier="llm", provenance={"reason": "read it"})
    return r


xop = Operation("x1", "section 9Z.01 says the panel may be blue", "s_x1", [], "cross_reference_resolver")
calls.clear()
got = resolve_then_read(resolver_says(F), reader_says(T))(xop, CertificateStore())
assert got.status is F and calls == ["resolver"], "a dangling reference is a finding; nothing to read"
calls.clear()
got = resolve_then_read(resolver_says(T), reader_says(F))(xop, CertificateStore())
assert got.status is F and calls == ["resolver", "reader"], "the content is checked, not assumed"
assert got.provenance["handed_over_from"]["verifier"] == "cross_reference_resolver"
assert got.provenance["handed_over_from"]["status"] == "TRUE"
assert got.provenance["handed_over_from"]["resolved"] == ["Section 9Z.01"]
got = resolve_then_read(resolver_says(T), reader_says(U))(xop, CertificateStore())
assert got.status is U, "a resolved pointer whose claim nobody could check stays UNKNOWN"
got = resolve_then_read(resolver_says(U), reader_says(T))(xop, CertificateStore())
assert got.status is T and got.provenance["handed_over_from"]["status"] == "UNKNOWN"


def crashes(op, st):
    raise RuntimeError("graph not loaded")


got = resolve_then_read(crashes, reader_says(T))(xop, CertificateStore())
assert got.status is T and "graph not loaded" in got.provenance["handed_over_from"]["reason"]
got = resolve_then_read(resolver_says(T), reader_says(U))(xop, CertificateStore())
assert "could not decide" in got.provenance["handed_over_from"]["reason"]


class KG:
    def resolves(self, kind, ident):
        return ident == "9Z.01"

    def chunks_for_paragraph(self, sec, n):
        return ["Z1"]


vs = build_verifiers(kg=KG(), ask=lambda p, i: json.dumps({"status": "FALSE", "evidence": ["Z1"],
                                                           "confidence": 1, "reason": "r"}),
                     retriever=Retriever())
op = Operation("x1", "section 9Z.01 says it", "s_x1", [], "cross_reference_resolver",
               evidence_hint=[{"type": "section", "id": "9Z.01"}])
got = vs["cross_reference_resolver"](op, CertificateStore())
assert got.status is F and got.verifier == "llm", "build_verifiers chains the resolver to the reader"
vs = build_verifiers(kg=KG())
assert vs["cross_reference_resolver"](op, CertificateStore()).status is T, \
    "with no model, the resolver alone runs, as before"
print("10. a cross-reference is resolved exactly, then its claim is read against the manual")

# ---- 11. the execution record and summary -------------------------------------------
sp = spec_of([{"id": "o1", "claim": "panel P meets the colour rule", "type": "classification",
               "authority": "GUIDANCE", "source_chunk": "Z1"}], facts=["The panel faces east."])
net, _ = instantiate(sp)
ask, _ = checker({"status": "FALSE", "evidence": ["Z1", "Z2"], "basis": "Z2", "confidence": 0.9, "reason": "r"})
trace = execute(net, {"llm": make_llm_verifier(ask, Retriever(), use_pointers=False)})
rec = ec.make_exec_record("X1", QUESTION, sp, net, trace, compose(QUESTION, net, trace), [], 0.1)
kinds = {c["id"]: c["kind"] for c in rec["certificates"]}
assert kinds == {"f1": "given", "o1": "check"}, kinds
s = ec.summarize_execution([rec])
assert s["checks"] == 1 and s["given_facts"] == 1 and s["authority_raised"] == 1
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ec.print_execution(rec)
    ec.print_exec_summary(s)
out = buf.getvalue()
assert "[given         ] f1" in out and "raised  : GUIDANCE -> STANDARD (rests on Z2)" in out
ans = compose(QUESTION, net, trace)
assert all(c["type"] != "given" for c in ans.citations), "a fact from the question is not a citation"
# the sequential baselines start from Γ0q too
seq = run_sequential(net, make_scenario(net, 0))
assert seq.terminal is not None
print("11. given facts and raised authority show in the record and the summary")

print("\nALL CHECKER-FIX TESTS PASSED")
