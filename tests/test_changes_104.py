"""changes_104 (12 Nov 2026): the fixes after the keepall run.

1. A checker reply the code cannot read is asked again (at most twice) before
   it is given up as UNKNOWN (SAMPLE019: two JSON objects; SAMPLE030: a
   missing quote mark).
2. Each part of the question is answered from its own results. The terminal
   that only joins the parts is read at face value: a FALSE Guidance or
   Option answer to one part is not turned into TRUE by the bundle's
   Standard heading (Rule B), and the answer writer is told why a check was
   left open.
3. The checker reads a claim worded like a rule as a statement about the
   case, judges only what the claim says, writes the facts first ("case"),
   and sees earlier results with their confidence, as findings that can be
   wrong.
4. The parser accounts for every Standard, Guidance and Option shown
   ("provisions", rule E); a claim is about one case only; and a provision
   still unaccounted for after the last attempt gets a plain check in its own
   words, added by the code.

Every model call is a stub: no API key, no GPU, no cost. Made-up provisions
(section 9Z) are used, never the test questions or their answers.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import Authority, Certificate, CertificateStore, Status, execute
from mrag.vine.answer import build_answer_prompt, parts_of_question, why_open, answer
from mrag.vine.compile import NetworkSpec, instantiate
from mrag.vine.execute import ExecutionTrace
from mrag.vine.model_verifiers import (READING_RULES, build_prompt, make_llm_verifier,
                                       parse_model_reply, reask_if_unreadable, _contract)
from mrag.vine.network import Operation
from mrag.vine.parser import (PARSER_CONTRACT, GROUNDING_RULES, add_checks_for_unaccounted,
                              coverage_problems, make_semantic_parser, provision_problems,
                              unaccounted_provisions)

n_checks = 0


def check(cond, what):
    global n_checks
    assert cond, what
    n_checks += 1
    print("  ok ", what)


GOOD = json.dumps({"status": "TRUE", "evidence": ["Z1"], "basis": "Z1", "confidence": 0.9,
                   "reason": "The panel faces east, as the rule requires."})
MISSING_QUOTE = ('{"status":"TRUE","evidence":["Z1"],"basis":"Z1","confidence":0.9,'
                 '"reason":"The panel faces east.}')
TWO_OBJECTS = (json.dumps({"status": "FALSE", "evidence": ["Z1"], "basis": "Z1", "confidence": 0.9,
                           "reason": "first try"})
               + "\n\nWait, that was wrong. Corrected answer:\n\n" + GOOD)

# --------------------------------------------------------------------------- #
print("1. An unreadable checker reply is asked again")
rec = {}
note = reask_if_unreadable(MISSING_QUOTE, ["Z1"], rec)
check(note is not None and "could not be read" in note and "Close every string" in note,
      "a missing quote mark: asked again, with the problem named")
check(rec["count"] == 1 and rec["replies"][0]["problem"].startswith("malformed JSON"),
      "the unreadable reply and why are kept")
rec2 = {}
check(reask_if_unreadable(TWO_OBJECTS, ["Z1"], rec2) is not None
      and "Extra data" in rec2["replies"][0]["problem"], "two JSON objects in one reply: asked again")
check(reask_if_unreadable(GOOD, ["Z1"], {}) is None, "a readable reply is not asked again")
check(reask_if_unreadable("I think it is fine.", ["Z1"], {}) is not None, "no JSON at all: asked again")
rec3 = {"count": 2}
check(reask_if_unreadable(MISSING_QUOTE, ["Z1"], rec3) is None, "at most twice")
check(reask_if_unreadable('{"status":"MAYBE","evidence":[],"confidence":0.5,"reason":"x"}', [], {}) is not None,
      "a status word that is not TRUE, FALSE or UNKNOWN: asked again")

ZCHUNK = {"chunk_id": "Z1", "section_id": "9Z.01", "content_type": "Standard", "ordinal": 1,
          "text": "A blue panel shall face east."}


class FakeRetriever:
    def retrieve_for_obligation(self, query, obligation, certificates=None, top_k=None, **kw):
        class R:
            pass
        r = R()
        r.chunks, r.figures, r.debug = [dict(ZCHUNK)], [], {}
        return r


def stub(*replies):
    seq, box = list(replies), {"i": 0, "prompts": []}

    def ask(prompt, images):
        box["prompts"].append(prompt)
        out = seq[min(box["i"], len(seq) - 1)]
        box["i"] += 1
        return out
    ask.box = box
    return ask


def run_one(ask):
    op = Operation(id="o1", claim="The blue panel faces east.", produces="s_o1", verifier="llm",
                   normative_authority=Authority.STANDARD, source_chunk="Z1")
    v = make_llm_verifier(ask, retriever=FakeRetriever(), labels=False, use_pointers=False)
    return v(op, CertificateStore())


ask = stub(MISSING_QUOTE, GOOD)
cert = run_one(ask)
check(cert.status is Status.TRUE and ask.box["i"] == 2,
      "the answer given again in a readable form is used (two calls)")
check(cert.provenance["asked_again_unreadable"]["count"] == 1
      and "YOUR EARLIER REPLY" in ask.box["prompts"][1], "the certificate records the re-ask")
ask = stub(TWO_OBJECTS, GOOD)
check(run_one(ask).status is Status.TRUE, "two objects, then one: the one is used")
ask = stub(MISSING_QUOTE, MISSING_QUOTE, MISSING_QUOTE, GOOD)
cert = run_one(ask)
check(cert.status is Status.UNKNOWN and ask.box["i"] == 3,
      "still unreadable after two re-asks: UNKNOWN (never FALSE), three calls in all")
ask = stub(GOOD)
cert = run_one(ask)
check(cert.status is Status.TRUE and ask.box["i"] == 1 and "asked_again_unreadable" not in cert.provenance,
      "a readable first reply: one call, as before")

# --------------------------------------------------------------------------- #
print("2. Each part of the question on its own; the bundle of parts at face value")


def spec(asked, terminal="m_all", guidance_status_claim="The recommended panel is blue."):
    return NetworkSpec.from_dict({
        "query": "Is a panel required, and what colour is recommended?", "terminal": terminal,
        "obligations": [
            {"id": "o_req", "claim": "A panel is required here.", "type": "classification",
             "authority": "STANDARD", "source_chunk": "Z1"},
            {"id": "o_col", "claim": guidance_status_claim, "type": "classification",
             "authority": "GUIDANCE", "source_chunk": "Z2"}],
        "merges": [{"id": "m_all", "claim": "A panel is required and the recommended panel is blue.",
                    "kind": "conjunction", "inputs": ["o_req", "o_col"], "authority": "STANDARD"}],
        "asked": asked})


TWO_PARTS = [{"id": "a1", "ask": "Is a panel required?", "answered_by": ["o_req"]},
             {"id": "a2", "ask": "What colour is recommended?", "answered_by": ["o_col"]}]
ONE_PART = [{"id": "a1", "ask": "Does the panel meet the rule?", "answered_by": ["m_all"]}]


def fixed(results):
    """A verifier that returns the given status for each obligation id."""
    def v(op, store):
        st, prov = results[op.id]
        return Certificate(claim=op.claim, status=st, normative_authority=op.normative_authority,
                           confidence=0.0 if st is Status.UNKNOWN else 0.9, verifier="llm",
                           obligation_id=op.id, provenance=prov)
    return {"llm": v}


net, probs = instantiate(spec(TWO_PARTS))
check(not probs and net.op("m_all").face_value and len(net.asked) == 2,
      "two parts, and the terminal answers neither: it only joins them, read at face value")
tr = execute(net, fixed({"o_req": (Status.TRUE, {}), "o_col": (Status.FALSE, {})}))
check(tr.terminal.status is Status.FALSE
      and tr.terminal.provenance.get("read_at_face_value") is True,
      "a Guidance answer found FALSE is not turned into TRUE by the bundle's Standard heading")
net1, _ = instantiate(spec(ONE_PART))
check(not net1.op("m_all").face_value, "one part answered by the terminal itself: read at its heading")
tr1 = execute(net1, fixed({"o_req": (Status.TRUE, {}), "o_col": (Status.FALSE, {})}))
check(tr1.terminal.status is Status.TRUE, "and there Rule B still holds: a Guidance not followed breaks no Standard")

parts = parts_of_question(net, tr)
check([p["id"] for p in parts] == ["a1", "a2"]
      and parts[0]["results"][0]["status"] == "TRUE" and parts[1]["results"][0]["status"] == "FALSE",
      "each part with its own result")
prompt = build_answer_prompt("Is a panel required, and what colour is recommended?", net, tr)
check("PARTS OF THE QUESTION" in prompt and "part by part" in prompt
      and "ALL PARTS TOGETHER" in prompt and "\nDECISION\n" not in prompt,
      "the answer is written part by part; the bundle is shown as such, not as the decision")

unread = {"problem": "malformed JSON: Unterminated string starting at: line 1 column 159 (char 158)",
          "reason": ""}
tr2 = execute(net, fixed({"o_req": (Status.TRUE, {}), "o_col": (Status.UNKNOWN, unread)}))
prompt2 = build_answer_prompt("Is a panel required, and what colour is recommended?", net, tr2)
check(tr2.terminal.status is Status.UNKNOWN and "cannot be answered from the available evidence" not in prompt2
      and "does not stop the other parts" in prompt2,
      "one part left open does not stop the other parts from being answered")
check("not decided: the checker's reply could not be read" in prompt2,
      "and the open part says why: the reply could not be read, not 'no evidence was found'")
check(why_open(None, "o9", ExecutionTrace(skipped={"o9": "its guard is closed"})).startswith("it was not run"),
      "a check that did not run says so")
a = answer("Is a panel required, and what colour is recommended?", net, tr2)
check([p["id"] for p in a.provenance["parts"]] == ["a1", "a2"]
      and a.provenance["parts"][1]["results"][0]["status"] == "UNKNOWN",
      "the parts and their results are kept with the answer")
prompt1 = build_answer_prompt("Does the panel meet the rule?", net1, tr1)
check("\nDECISION\nTRUE" in prompt1 and "PARTS OF THE QUESTION" not in prompt1,
      "a question with one part reads as before")

# --------------------------------------------------------------------------- #
print("3. The checker reads the claim as being about the case")
check("still says what the\n  case does" in READING_RULES and "Judge only what the claim says" in READING_RULES,
      "a claim worded like a rule is about the case; judge only what the claim says")
c_plain, c_scope = _contract(False), _contract(False, scope=True)
check('"case":' in c_plain and c_plain.index('"case"') < c_plain.index('"status"')
      and '"case":' not in c_scope and '"scope"' in c_scope,
      "the facts come first in the reply (\"case\"); a scope claim keeps its own first field")
earlier = Certificate(claim="The island is raised.", status=Status.FALSE,
                      normative_authority=Authority.STANDARD, confidence=0.55, verifier="llm",
                      obligation_id="o0")
op = Operation(id="o1", claim="The blue panel faces east.", produces="s_o1")
p, _allowed = build_prompt(op, [ZCHUNK], [], [earlier], [])
check("EARLIER RESULTS" in p and "can be wrong" in p and "(confidence 0.55)" in p
      and "ALREADY ESTABLISHED" not in p, "earlier results come with their confidence, as findings that can be wrong")
r = parse_model_reply(json.dumps({"case": "The panel faces west (f1).", "status": "FALSE",
                                  "evidence": ["Z1"], "basis": "Z1", "confidence": 0.9,
                                  "reason": "It faces west."}), ["Z1"])
check(r.status is Status.FALSE and r.case.startswith("The panel faces west"), "the case field is read and kept")

# --------------------------------------------------------------------------- #
print("4. The parser accounts for every provision; one case per claim")
KQ = [ZCHUNK,
      {"chunk_id": "Z2", "section_id": "9Z.01", "content_type": "Guidance", "ordinal": 2,
       "text": "The panel should be blue."},
      {"chunk_id": "Z3", "section_id": "9Z.01", "content_type": "Support", "ordinal": 3,
       "text": "Panels are made up."},
      {"chunk_id": "Z4", "section_id": "9Z.02", "content_type": "Option", "ordinal": 4,
       "lead_in": "Near a park:", "text": "the panel may face west."},
      {"chunk_id": "Z5", "section_id": "9Z.03", "content_type": "Standard", "ordinal": 1,
       "text": "A panel shall be square."}]
s = spec(TWO_PARTS)
pp = provision_problems(s, KQ)
check(len(pp) == 1 and "leaves out 4 of the 4" in pp[0] and "'Z3'" not in pp[0],
      "no account at all: the four Standards, Guidance and Options are named (Support is not)")
s.provisions = [{"id": "Z1", "checked_by": ["o_req"]}, {"id": "Z2", "checked_by": ["o_col"]},
                {"id": "Z4", "not_related": "no park in this question"},
                {"id": "Z5", "checked_by": ["o_req"]}]
pp = provision_problems(s, KQ)
check(len(pp) == 1 and "'Z5'" in pp[0] and "rests on it" in pp[0],
      "checked_by an obligation that does not rest on it: sent back")
s.obligations[0].evidence_hint = [{"type": "section", "id": "9Z.03", "paragraph": "1"}]
check(provision_problems(s, KQ) == [], "an evidence_hint naming its section and paragraph counts")
s.provisions[2] = {"id": "Z4", "not_related": ""}
check(any("not_related" in x for x in provision_problems(s, KQ)), "not_related needs a reason")
s.provisions[2] = {"id": "Z4", "not_related": "no park in this question"}
s.provisions.append({"id": "Z3", "not_related": "Support"})
check(any("is not a Standard, Guidance or Option" in x for x in provision_problems(s, KQ)),
      "a Support item is not listed")
s.provisions.pop()
check(provision_problems(s, KQ) == [] and unaccounted_provisions(s, KQ) == [], "all accounted for")
check(any(x.startswith('"provisions"') for x in coverage_problems(spec(TWO_PARTS), KQ)),
      "rule E is part of the coverage check (sent back for repair)")

s2 = spec(TWO_PARTS)
s2.provisions = [{"id": "Z1", "checked_by": ["o_req"]}]      # Z2 is not listed, but o_col rests on it
added = add_checks_for_unaccounted(s2, KQ)
new = [o for o in s2.obligations if o.id in added]
check(added == ["prov1", "prov2"] and [o.source_chunk for o in new] == ["Z4", "Z5"],
      "after the last attempt, each provision that no obligation rests on, and that is not "
      "called unrelated, gets a check (one an obligation rests on gets none twice)")
check(new[0].authority == "OPTION" and new[0].type == "classification"
      and "Near a park: the panel may face west." in new[0].claim
      and "either this provision does not cover the case, or the case meets" in new[0].claim
      and new[1].authority == "STANDARD",
      "in the provision's own words, at its own heading, for the language-model checker")
check(not instantiate(s2)[1] and unaccounted_provisions(s2, KQ) == []
      and any(p.get("added_by_code") for p in s2.provisions), "the plan still builds; the account is complete and says so")

GOOD_PLAN = {"terminal": "m_all",
             "obligations": [{"id": "o_req", "claim": "A panel is required here.", "type": "classification",
                              "authority": "STANDARD", "source_chunk": "Z1"},
                             {"id": "o_col", "claim": "The recommended panel is blue.",
                              "type": "classification", "authority": "GUIDANCE", "source_chunk": "Z2"}],
             "merges": [{"id": "m_all", "claim": "both hold", "kind": "conjunction",
                         "inputs": ["o_req", "o_col"]}],
             "asked": TWO_PARTS}
calls = []


def parser_model(prompt, images):
    calls.append(prompt)
    return json.dumps(GOOD_PLAN)          # never gives "provisions"


sp, rep = make_semantic_parser(parser_model, fall_back_to_baseline=False)("Q?", KQ)
check(sp is not None and rep.attempts == 3 and "YOUR PREVIOUS PLAN WAS REJECTED" in calls[1]
      and '"provisions" leaves out' in calls[1], "a plan without the account is sent back")
check(sorted(o.source_chunk for o in sp.obligations if o.id.startswith("prov")) == ["Z4", "Z5"]
      and any("added 2 check(s)" in n for n in rep.notes),
      "never given: the plan is used, and the code adds a check for each provision left out")
check("Step 6. Account for every provision" in PARSER_CONTRACT and '"provisions": [' in PARSER_CONTRACT
      and any("provisions" in g for g in GROUNDING_RULES), "the instructions and the repair rules say so")
check("One case per claim" in PARSER_CONTRACT and "Not prohibited does not mean allowed" in PARSER_CONTRACT
      and 'Do not join a reason to it ("because ...")' in PARSER_CONTRACT
      and "reads like the rule itself" in PARSER_CONTRACT,
      "the instructions on how to write a claim")

s3 = NetworkSpec.from_dict({
    "query": "Do Designs A and B meet the rule?", "terminal": "m1",
    "facts": [{"id": "f1", "fact": "Design A is 7 feet high."}, {"id": "f2", "fact": "Design B is 5 feet high."}],
    "obligations": [{"id": "o1", "claim": "In Design A and Design B, the top is 6 feet up or more.",
                     "type": "numerical", "authority": "STANDARD", "source_chunk": "Z1"},
                    {"id": "o2", "claim": "For Design A, the height is at least 6 feet.",
                     "type": "numerical", "authority": "STANDARD", "source_chunk": "Z1"}],
    "merges": [{"id": "m1", "claim": "Designs A and B meet the rule.", "kind": "conjunction",
                "inputs": ["o1", "o2"]}],
    "asked": [{"id": "a1", "ask": "Do Designs A and B meet the rule", "answered_by": ["m1"]}]})
pa = coverage_problems(s3)
check(len(pa) == 1 and pa[0].startswith("o1:") and "one claim per design" in pa[0],
      "a claim about two labelled cases at once is sent back; a merge may join them")

# --------------------------------------------------------------------------- #
print("5. The plan record keeps the account")
d = s2.as_dict()
check("provisions" in d and NetworkSpec.from_dict(d).provisions == s2.provisions,
      "\"provisions\" is written and read back with the plan")
check("provisions" not in spec(TWO_PARTS).as_dict(), "a plan without it reads, and hashes, as before")

print(f"\nALL CHANGES_104 TESTS PASSED ({n_checks} checks)")
