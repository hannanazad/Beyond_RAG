"""changes_108 (14 Nov 2026), made-up provisions only:
  #1 retrieval: the best-matching other Standards, Guidance and Options of the
     sections Kq already holds (Retriever._section_mates);
  #2-#4 parser instructions: no reason or conclusion joined to a claim; a part
     answered by the check that answers it as asked; "permitted" and changed
     cases checked against the provisions that require or forbid;
  #5 the checker model's second look at the plan (plan_review), and how the
     execute stage uses it (vine_hprc.reviewed_network);
  #7 the answer writer reports each result in its claim's own words."""
import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from mrag.config import CFG  # noqa: E402,F401  (before hprc/vine_hprc.py, which would pick the HPRC paths)
from mrag.vine import plan_review as pr  # noqa: E402
from mrag.vine.compile import NetworkSpec, instantiate  # noqa: E402

ok = 0


def check(c, what):
    global ok
    assert c, what
    ok += 1
    print("  ok ", what)


# --------------------------------------------------------------------------- #
# #2-#4 the parser's instructions
# --------------------------------------------------------------------------- #
from mrag.vine.parser import PARSER_CONTRACT, build_parser_prompt  # noqa: E402

flat = " ".join(PARSER_CONTRACT.split())
check('or a conclusion drawn from it ("..., so ...", "therefore", "which means")' in flat
      and "a conclusion is what a merge or the next obligation states" in flat,
      "#2: a claim joins neither a reason nor a conclusion")
check('Name in "answered_by" the checks whose results ARE the answer to the part as it is asked' in flat
      and "it is answered by a check that says which heading governs it here" in flat,
      "#3: a part is answered by the check that answers it as asked")
check("a check that a provision does not prohibit something never answers such a part on its own" in flat
      and "check the changed case against that provision itself" in flat
      and "check that what it shows or does fits the facts of the case" in flat,
      "#4: permitted / changed / chosen parts are checked against what requires or forbids")
check("Name in" in build_parser_prompt("A made-up question?", [{"chunk_id": "X_Standard_01", "section_id": "9Z.01",
                                       "content_type": "Standard", "text": "A made-up rule."}]),
      "the new instructions reach the parser's prompt")

# --------------------------------------------------------------------------- #
# #7 the answer writer
# --------------------------------------------------------------------------- #
from mrag.vine.answer import WORDS_RULE, build_answer_prompt  # noqa: E402
from mrag.vine.certificate import Certificate, Status  # noqa: E402
from mrag.vine.execute import execute  # noqa: E402

ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")


def ob(i, claim, auth, src="9Z01_Standard_01"):
    return {"id": i, "claim": claim, "type": "applicability", "authority": auth, "requires": [],
            "evidence_hint": [], "source_chunk": src}


def run(spec, table):
    net, problems = instantiate(NetworkSpec.from_dict(spec))
    assert problems == [], problems

    def verify(op, store):
        return Certificate(claim=op.claim, status=table.get(op.id, Status.TRUE),
                           normative_authority=op.normative_authority, verifier=op.verifier,
                           obligation_id=op.id, confidence=0.9, provenance={"reason": "made-up " + op.id})
    return net, execute(net, {v: verify for v in ALL})


ONE = {"query": "q", "terminal": "m", "obligations": [
    ob("a", "Device Q is the size Section 9Z.01 paragraph 1 requires.", "STANDARD"),
    ob("b", "Device Q is at the height Section 9Z.01 paragraph 2 recommends.", "GUIDANCE")],
    "merges": [{"id": "m", "claim": "Device Q meets Section 9Z.01.", "kind": "conjunction", "inputs": ["a", "b"],
                "authority": "STANDARD"}]}
TWO = {**ONE, "asked": [{"id": "a1", "ask": "Is the size right?", "answered_by": ["a"]},
                        {"id": "a2", "ask": "Is the height right?", "answered_by": ["b"]}]}
net, tr = run(ONE, {})
p1 = build_answer_prompt("q", net, tr)
net, tr = run(TWO, {"b": Status.FALSE})
p2 = build_answer_prompt("q", net, tr)
check(WORDS_RULE in p1 and WORDS_RULE in p2 and "never shorten a claim so that it says something else" in WORDS_RULE,
      "#7: both the one-part and the per-part prompts ask for each result in its claim's own words")

# --------------------------------------------------------------------------- #
# #5 the plan review
# --------------------------------------------------------------------------- #
CHUNKS = [
    {"chunk_id": "9Z01_Standard_01", "section_id": "9Z.01", "ordinal": "1", "content_type": "Standard",
     "text": "Device Q shall be 30 inches wide."},
    {"chunk_id": "9Z01_Guidance_02", "section_id": "9Z.01", "ordinal": "2", "content_type": "Guidance",
     "text": "Device Q should be mounted 7 feet high."},
    {"chunk_id": "9Z01_Option_03", "section_id": "9Z.01", "ordinal": "3", "content_type": "Option",
     "text": "Device Q may carry a plaque."},
    {"chunk_id": "9Z02_Standard_01", "section_id": "9Z.02", "ordinal": "1", "content_type": "Standard",
     "text": "A marking replacing Device Q shall be white."},
    {"chunk_id": "9Z01_Support_04", "section_id": "9Z.01", "ordinal": "4", "content_type": "Support",
     "text": "Device Q is common."},
]
PLAN = {"query": "q", "terminal": "m",
        "facts": [{"id": "f1", "fact": "Device Q is 30 inches wide and mounted 6 feet high."}],
        "asked": [{"id": "a1", "ask": "Does Device Q meet the size rule?", "answered_by": ["a"]},
                  {"id": "a2", "ask": "Is replacing Device Q with a marking permitted?", "answered_by": ["c"]}],
        "obligations": [ob("a", "Device Q is 30 inches wide, as Section 9Z.01 paragraph 1 requires.", "STANDARD"),
                        ob("c", "Section 9Z.01 paragraph 3 does not prohibit replacing Device Q.", "OPTION",
                           "9Z01_Option_03")],
        "merges": [{"id": "m", "claim": "Both parts hold.", "kind": "conjunction", "inputs": ["a", "c"],
                    "authority": "STANDARD"}],
        "provisions": [{"id": "9Z01_Standard_01", "checked_by": ["a"]},
                       {"id": "9Z01_Guidance_02", "not_related": "about height"},
                       {"id": "9Z01_Option_03", "checked_by": ["c"]},
                       {"id": "9Z02_Standard_01", "not_related": "about markings"}]}
spec = NetworkSpec.from_dict(PLAN)
prompt = pr.build_review_prompt("Does Device Q comply, and may it be replaced by a marking?", spec, CHUNKS)
check("QUESTION\nDoes Device Q comply" in prompt and "a2. Is replacing Device Q with a marking permitted?" in prompt
      and "   - c [OPTION] Section 9Z.01 paragraph 3 does not prohibit replacing Device Q." in prompt,
      "the review prompt shows the question, each part and the checks that answer it")
check("[9Z01_Guidance_02] Section 9Z.01 paragraph 2 (Guidance): Device Q should be mounted 7 feet high.\n"
      "   -> NOT RELATED, the plan says: about height" in prompt
      and "[9Z01_Standard_01] Section 9Z.01 paragraph 1 (Standard): Device Q shall be 30 inches wide.\n"
          "   -> checked by a" in prompt
      and "9Z01_Support_04" not in prompt,
      "every Standard, Guidance and Option shown is listed with what the plan did with it; Support is not")
check(pr.REVIEW_TASK in prompt and pr.REVIEW_CONTRACT in prompt and pr.PROMPT_SHA256 == __import__("hashlib")
      .sha256((pr.REVIEW_TASK + pr.REVIEW_CONTRACT).encode()).hexdigest(), "the instructions and their fingerprint")

reply = json.dumps({"add": [
    {"for": "not_related", "provision": "9Z01_Guidance_02",
     "claim": "Device Q is mounted 7 feet high, as Section 9Z.01 paragraph 2 recommends.", "why": "height bears"},
    {"for": "a2", "provision": "9Z02_Standard_01",
     "claim": "The marking replacing Device Q is white, as Section 9Z.02 paragraph 1 requires.", "why": "x"},
    {"for": "not_related", "provision": "9Z01_Standard_01", "claim": "again", "why": "already checked"},
    {"for": "a9", "provision": "9Z01_Option_03", "claim": "x", "why": "no such part"},
    {"for": "a2", "provision": "9Z01_Support_04", "claim": "x", "why": "Support"},
    {"for": "a2", "provision": "9Z02_Standard_01", "claim": "Is it white?", "why": "a question"}]})
new, rec = pr.review_plan("q", spec, CHUNKS, lambda p, i: "Thinking...\n```json\n" + reply + "\n```",
                          build=instantiate)
added = {a["id"]: a for a in rec["added"]}
check(list(added) == ["rev1", "rev2"] and len(rec["refused"]) == 4 and not rec["error"],
      "two valid additions are made; a checked provision, an unknown part, a Support and a question are refused")
o = {x.id: x for x in new.obligations}
check(o["rev1"].type == "classification" and o["rev1"].authority == "GUIDANCE" and o["rev1"].verifier == "llm"
      and o["rev1"].source_chunk == "9Z01_Guidance_02"
      and o["rev2"].authority == "STANDARD" and o["rev2"].evidence_hint == [{"type": "section", "id": "9Z.02",
                                                                              "paragraph": "1"}],
      "an added check rests on its provision, at its heading, for the language-model checker")
prov = {p["id"]: p for p in new.provisions}
check(prov["9Z01_Guidance_02"]["checked_by"] == ["rev1"] and prov["9Z01_Guidance_02"]["added_by_review"]
      and prov["9Z01_Guidance_02"]["parser_said"] == {"not_related": "about height"}
      and prov["9Z02_Standard_01"]["checked_by"] == ["rev2"],
      "the provisions account says what the review changed and what the parser had said")
check(next(a for a in new.asked if a.id == "a2").answered_by == ["c", "rev2"]
      and next(a for a in spec.asked if a.id == "a2").answered_by == ["c"]
      and len(spec.obligations) == 2 and new.merges[0].inputs == ["a", "c"],
      "a part's check joins its answered_by; the parser's own plan and merges are untouched")
net2, problems = instantiate(new)
check(net2 is not None and not problems, "the reviewed plan builds")

# nothing missing, an unreadable reply, a failed call, a plan that would not build
same, r0 = pr.review_plan("q", spec, CHUNKS, lambda p, i: '{"add": []}', build=instantiate)
check(same is spec and r0["added"] == [] and not r0["error"], "nothing missing: the plan is used as it was")
same, r1 = pr.review_plan("q", spec, CHUNKS, lambda p, i: "I think the plan is fine.", build=instantiate)
check(same is spec and r1["refused"] == ["the reply contained no JSON object"], "an unreadable reply changes nothing")


def boom(p, i):
    raise RuntimeError("rate limited")


same, r2 = pr.review_plan("q", spec, CHUNKS, boom, build=instantiate)
check(same is spec and "rate limited" in r2["error"], "a failed review call changes nothing")
same, r3 = pr.review_plan("q", spec, CHUNKS, lambda p, i: reply, build=lambda s: (None, ["made-up problem"]))
check(same is spec and r3["added"] == [] and "would not build" in r3["error"], "a plan that would not build is not used")
same_prov = json.dumps({"add": [
    {"for": "a2", "provision": "9Z02_Standard_01", "claim": "The marking replacing Device Q is white.", "why": "x"},
    {"for": "not_related", "provision": "9Z02_Standard_01", "claim": "The marking is white here.", "why": "x"}]})
_n, r5 = pr.review_plan("q", spec, CHUNKS, lambda p, i: same_prov, build=instantiate)
check(len(r5["added"]) == 1 and any("one check per provision" in x for x in r5["refused"]),
      "one check per provision: a second check on the same provision is refused")
BIG = CHUNKS + [{"chunk_id": f"9Z09_Standard_{k:02d}", "section_id": "9Z.09", "ordinal": str(k),
                 "content_type": "Standard", "text": f"Made-up rule {k}."} for k in range(1, 13)]
BIG_PLAN = {**PLAN, "provisions": PLAN["provisions"] + [{"id": f"9Z09_Standard_{k:02d}", "not_related": "other"}
                                                         for k in range(1, 13)]}
bspec = NetworkSpec.from_dict(BIG_PLAN)
many = json.dumps({"add": [{"for": "a2", "provision": f"9Z09_Standard_{k:02d}",
                            "claim": f"Made-up check number {k} about the marking.", "why": "x"} for k in range(1, 13)]})
_n, r4 = pr.review_plan("q", bspec, BIG, lambda p, i: many, build=instantiate)
check(len(r4["added"]) == pr.MAX_ADD and any("more checks than" in x for x in r4["refused"]),
      f"at most {pr.MAX_ADD} checks are added")
nr = json.dumps({"add": [{"for": "not_related", "provision": f"9Z09_Standard_{k:02d}",
                          "claim": f"Made-up check number {k}.", "why": "x"} for k in range(1, 6)]})
_n, r6 = pr.review_plan("q", bspec, BIG, lambda p, i: nr, build=instantiate)
check(len(r6["added"]) == pr.MAX_NOT_RELATED and sum("marked not related" in x for x in r6["refused"]) == 2,
      f"at most {pr.MAX_NOT_RELATED} checks for provisions marked not related")
pm = pr.build_review_prompt("q", NetworkSpec.from_dict({**PLAN, "asked": [
    {"id": "a1", "ask": "x", "answered_by": ["m"]}]}), CHUNKS)
check("   - m (conjunction of a, c) Both parts hold." in pm, "the review prompt says what kind of merge a merge is")
check("it never\nchanges, relaxes or excuses another check's result" in pr.REVIEW_TASK
      or "never changes, relaxes or excuses another check's result" in " ".join(pr.REVIEW_TASK.split()),
      "the reviewer is told an added check never changes, relaxes or excuses another")

# the execute stage's use of it: the parser's network runs first and alone, then the added checks
from mrag.vine.execute import execute as run_net  # noqa: E402
sys.path.insert(0, str(REPO / "hprc"))
sys.path.insert(0, str(REPO / "evaluation"))
V = importlib.import_module("vine_hprc")
net0, problems0 = instantiate(spec)
plan = {"spec": spec, "net": net0, "problems": problems0}
n, review, reviewed = V.reviewed_network("q", plan, CHUNKS, lambda p, i: reply)
check(n is not net0 and reviewed is not None and {"rev1", "rev2"} <= {op.id for op in n.operations}
      and review["added"], "the execute stage runs the reviewed network when checks were added")
seen_by = {}


def spy(op, store):
    seen_by[op.id] = sorted(store.states())
    st = Status.FALSE if op.id == "rev2" else Status.TRUE
    return Certificate(claim=op.claim, status=st, normative_authority=op.normative_authority,
                       verifier=op.verifier, obligation_id=op.id, confidence=0.9)


n, review, reviewed = V.reviewed_network("q", plan, CHUNKS, lambda p, i: reply)
tr = V.execute_with_review(plan, n, review, reviewed, {v: spy for v in ALL})
check(not any(s.startswith("s_rev") for k in ("a", "c") for s in seen_by[k])
      and tr.store.latest("s_rev2").status is Status.FALSE and review["decided"] == ["s_rev1", "s_rev2"],
      "the plan's own checks run before and without the review's; the review's results join the store after")
plain = run_net(net0, {v: spy for v in ALL})
check(tr.store.latest("s_m").status is plain.store.latest("s_m").status
      and tr.terminal.status is plain.terminal.status,
      "the plan's decision is exactly what it is without the review")
prompt_r = build_answer_prompt("q", n, tr)
check("PARTS OF THE QUESTION" in prompt_r and "[FALSE] The marking replacing Device Q is white, as Section 9Z.02 "
      "paragraph 1 requires.  [STANDARD]" in prompt_r
      and "ALL PARTS TOGETHER (the network's decision, together with the checks the plan review added under the "
          "parts; TRUE only when every part holds; this is not the answer to any one part)\nFALSE" in prompt_r,
      "a part answered by a review check shows it, and its FALSE lowers the joined result")
other_block = prompt_r.split("OTHER CHECKS MADE", 1)[1] if "OTHER CHECKS MADE" in prompt_r else ""
check("The marking replacing Device Q is white" not in other_block,
      "a review check listed under its part is not listed again among the other checks")


def spy_open(op, store):
    st = Status.UNKNOWN if op.id == "a" else Status.TRUE      # the decision is left open; the review check holds
    return Certificate(claim=op.claim, status=st, normative_authority=op.normative_authority,
                       verifier=op.verifier, obligation_id=op.id, confidence=0.9)


tro = V.execute_with_review(plan, n, review, reviewed, {v: spy_open for v in ALL})
po = build_answer_prompt("q", n, tro)
check(tro.terminal.status is Status.UNKNOWN and "added under the parts; TRUE only when every part holds; this is "
      "not the answer to any one part)\nUNKNOWN" in po,
      "an open decision stays open: an added check that holds never turns it into a yes")
one = NetworkSpec.from_dict({**PLAN, "asked": [{"id": "a1", "ask": "Does Device Q comply?", "answered_by": ["m"]}]})
net1, _p = instantiate(one)
r1spec, rv1 = pr.review_plan("q", one, CHUNKS, lambda p, i: json.dumps({"add": [
    {"for": "a1", "provision": "9Z02_Standard_01", "claim": "The marking replacing Device Q is white.", "why": "x"}]}),
    build=instantiate)
n1, _r, rs1 = V.reviewed_network("q", {"spec": one, "net": net1, "problems": []}, CHUNKS, lambda p, i: json.dumps(
    {"add": [{"for": "a1", "provision": "9Z02_Standard_01", "claim": "The marking replacing Device Q is white.",
              "why": "x"}]}))
tr1 = V.execute_with_review({"spec": one, "net": net1}, n1, _r, rs1, {v: spy for v in ALL})
p1r = build_answer_prompt("q", n1, tr1)
check("PARTS OF THE QUESTION" in p1r and "DECISION\n" not in p1r and "ALL PARTS TOGETHER (the network's decision" in p1r,
      "a one-part question whose part has a review check is answered by its part, not by the decision alone")
from mrag.vine.answer import answer as write_answer  # noqa: E402
check(write_answer("q", n1, tr1).provenance.get("parts_together") in ("TRUE", "FALSE"),
      "the joined result of the parts is recorded with the answer")
plain_p = build_answer_prompt("q", net0, run_net(net0, {v: spy for v in ALL}))
check("ALL PARTS TOGETHER (TRUE only when every part holds" in plain_p and "the plan review added" not in plain_p,
      "a plan without review checks keeps the joined line from the decision")
n, review, reviewed = V.reviewed_network("q", plan, CHUNKS, lambda p, i: '{"add": []}')
check(n is net0 and reviewed is None and review is not None, "and the parser's own network when nothing was added")
saved = V.PLAN_REVIEW
V.PLAN_REVIEW = False
try:
    n, review, reviewed = V.reviewed_network("q", plan, CHUNKS, lambda p, i: 1 / 0)
    check(n is net0 and review is None and reviewed is None, "with VINE_PLAN_REVIEW=0 nothing is asked")
finally:
    V.PLAN_REVIEW = saved
import subprocess, tempfile  # noqa: E402,E401


def run_sh(env_extra):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "repo"; (root / "hprc").mkdir(parents=True)
        (root / "hprc" / "run.sh").write_text((REPO / "hprc" / "run.sh").read_text())
        (root / "hprc" / "vine_job.slurm").write_text("#!/bin/bash\n")
        home = Path(d) / "vine"; home.mkdir()
        (home / ".done_models").write_text(""); (home / "anthropic_key").write_text("k")
        (root / "hprc" / "env.sh").write_text(f'export VINE_HOME="{home}"\nexport MRAG_BASE_DIR="{d}/b"\n')
        stub = Path(d) / "bin"; stub.mkdir(); log = Path(d) / "s.log"
        (stub / "sbatch").write_text(f'#!/bin/bash\necho "$@" >> "{log}"\necho 1234\n'); (stub / "sbatch").chmod(0o755)
        env = {"PATH": f"{stub}:/usr/bin:/bin", "HOME": d, "USER": "u", **env_extra}
        r = subprocess.run(["bash", str(root / "hprc" / "run.sh"), "ACCT", "2", "parse"], env=env,
                           capture_output=True, text=True)
        return r.returncode, (log.read_text().splitlines() if log.exists() else [])


code, calls = run_sh({})
check(code == 0 and calls and all("VINE_PLAN_REVIEW=1," in c and "VINE_PROBE=,STAGE" in c for c in calls),
      "run.sh passes VINE_PLAN_REVIEW=1 unless told otherwise")
code, calls = run_sh({"VINE_PLAN_REVIEW": "0"})
check(code == 0 and all("VINE_PLAN_REVIEW=0," in c for c in calls), "VINE_PLAN_REVIEW=0 is passed on")
code, calls = run_sh({"VINE_PLAN_REVIEW": "off"})
check(code != 0 and calls == [], "any other value is refused before anything is submitted")
check("section_mates_per_section" in V.SETTING_NAMES and "section_mates_total" in V.SETTING_NAMES,
      "the new retrieval settings are recorded with every run")

# --------------------------------------------------------------------------- #
# #1 retrieval: the best other paragraphs of the sections Kq already holds
# --------------------------------------------------------------------------- #
from mrag.config import CFG  # noqa: E402
from mrag.retrieval import Retriever  # noqa: E402

RECS = {
    "9Z01_S1": {"section_id": "9Z.01", "content_type": "Standard", "source": "paragraph", "text": "rule one"},
    "9Z01_O7": {"section_id": "9Z.01", "content_type": "Option", "source": "paragraph", "text": "departure side may be omitted"},
    "9Z01_G8": {"section_id": "9Z.01", "content_type": "Guidance", "source": "paragraph", "text": "height should be"},
    "9Z01_P9": {"section_id": "9Z.01", "content_type": "Support", "source": "paragraph", "text": "support text"},
    "9Z01_N1": {"section_id": "9Z.01", "content_type": "Standard", "source": "figure_note", "text": "a note"},
    "9Z05_S2": {"section_id": "9Z.05", "content_type": "Standard", "source": "paragraph", "text": "other rule"},
    "9Z05_O3": {"section_id": "9Z.05", "content_type": "Option", "source": "paragraph", "text": "omitted departure"},
    "9Z05_O4": {"section_id": "9Z.05", "content_type": "Option", "source": "paragraph", "text": "unrelated option"},
    "9Z05_O5": {"section_id": "9Z.05", "content_type": "Option", "source": "paragraph", "text": "departure again"},
    "8Y01_S1": {"section_id": "8Y.01", "content_type": "Standard", "source": "paragraph", "text": "far away"},
    "1C02_D1": {"section_id": "1C.02", "content_type": "Standard", "source": "list_item", "text": "departure side omitted defined"},
    "1C02_D2": {"section_id": "1C.02", "content_type": "Standard", "source": "list_item", "text": "another definition"},
}


class Rerank:
    def rank(self, query, docs, top_k):
        words = set(query.split())
        scored = sorted(range(len(docs)), key=lambda i: -len(words & set(docs[i].split())))
        return [(i, float(len(words & set(docs[i].split())))) for i in scored[:top_k]]


fake = SimpleNamespace(
    kg=SimpleNamespace(_chunk={k: {**v, "chunk_id": k} for k, v in RECS.items()},
                       chunks_for_section=lambda sec: [k for k, v in RECS.items() if v["section_id"] == sec]),
    rerank=Rerank(),
    store=SimpleNamespace(fetch_chunks_by_ids=lambda coll, ids, default_score=0.0:
                          [{"payload": {**RECS[i], "chunk_id": i}, "score": default_score} for i in ids]))
saved = (CFG.section_mates_per_section, CFG.section_mates_total)
try:
    kq = [{"chunk_id": "9Z01_S1", "section_id": "9Z.01"}, {"chunk_id": "9Z05_S2", "section_id": "9Z.05"},
          {"chunk_id": "1C02_D2", "section_id": "1C.02"}]
    out = Retriever._section_mates(fake, "departure side omitted", kq)
    ids = [c["chunk_id"] for c in out]
    check(set(ids) <= {"9Z01_O7", "9Z01_G8", "9Z05_O3", "9Z05_O4", "9Z05_O5"} and "9Z01_O7" in ids
          and "9Z05_O3" in ids and "8Y01_S1" not in ids and "9Z01_P9" not in ids and "9Z01_N1" not in ids
          and "1C02_D1" not in ids,
          "#1: other Standards, Guidance and Options of the sections Kq holds come, best match first; "
          "never Support, notes, other sections or the definition sections")
    check(sum(1 for i in ids if i.startswith("9Z05")) <= CFG.section_mates_per_section
          and len(ids) <= CFG.section_mates_total and all(c["source"] == "section_mate" for c in out),
          "#1: at most the set number per section and in all, each tagged section_mate")
    CFG.section_mates_total = 1
    check(len(Retriever._section_mates(fake, "departure side omitted", kq)) == 1, "#1: the total cap holds")
    CFG.section_mates_per_section = 0
    check(Retriever._section_mates(fake, "departure side omitted", kq) == [], "#1: 0 turns it off")
    CFG.section_mates_per_section, CFG.section_mates_total = saved
    full = [{"chunk_id": k, "section_id": v["section_id"]} for k, v in RECS.items() if v["section_id"] == "9Z.01"]
    check(Retriever._section_mates(fake, "departure", full) == [], "#1: nothing is added twice")
finally:
    CFG.section_mates_per_section, CFG.section_mates_total = saved

print(f"ALL CHANGES_108 TESTS PASSED ({ok} checks)")
