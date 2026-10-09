"""The end-to-end notebook's glue (evaluation/vine_run.py) and the retrieval
check's new records (evaluation/retrieval_check.py), 9 October 2026.

  1. The parser's model call with room for every prompt: the prompt is counted
     by the server's tokenizer; an ordinary prompt gets the full budget (and
     the same client, so the same cached replies); a long one gets what fits;
     one with no room is refused before the server sees it; without the
     tokenizer, a safe estimate is used; `.last` carries the budget.
  2. The retrieval check: resumable (saved every few cases, finished cases are
     not run again), "before" taken from the earlier run except for cases
     corrected since, the gate (no fewer cases pass than before), and where
     each target came from.
  3. Files and answers: atomic writes, JSON comparison, the answer lines.

Everything here is made up. No sample question, gold answer or MUTCD text is used.
"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

import retrieval_check as rc
import vine_run as vr

TMP = Path(tempfile.mkdtemp())


# ---- 1. BudgetedAsk -----------------------------------------------------------------
class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


class Session:
    def __init__(self, ok=True):
        self.ok, self.bodies = ok, []

    def post(self, url, json=None, timeout=None):
        assert url == "http://srv/tokenize", url
        self.bodies.append(json)
        if not self.ok:
            raise ConnectionError("no tokenizer here")
        return Resp(200, {"count": len(json["messages"][0]["content"].split()), "max_model_len": 1000})


made = []


def make_ask(max_tokens):
    def ask(prompt, images):
        ask.last = {"cached": False, "finish_reason": "stop", "max_tokens_seen": max_tokens}
        return f"reply with {max_tokens}"
    ask.last = None
    made.append(max_tokens)
    return ask


s = Session()
a = vr.BudgetedAsk(make_ask, "http://srv/", "parser", max_len=1000, max_tokens=500, margin=50, min_tokens=100,
                   template_kwargs={"reasoning_effort": "xhigh"}, session=s)
assert a("w " * 100, []) == "reply with 500" and a("w " * 200, []) == "reply with 500"
assert made == [500], "ordinary prompts share one client (and its cached replies)"
assert s.bodies[0]["chat_template_kwargs"] == {"reasoning_effort": "xhigh"}
assert s.bodies[0]["add_generation_prompt"] is True and s.bodies[0]["model"] == "parser"
assert a.last["max_tokens"] == 500 and a.last["prompt_tokens"] == 200 and a.last["prompt_tokens_how"] == "server"
assert a.last["finish_reason"] == "stop" and len(a.calls) == 2
assert a("w " * 700, []) == "reply with 250", "a long prompt gets what fits: 1000 - 700 - 50"
assert made == [500, 250] and a.budgets[-1]["room"] == 250
try:
    a("w " * 900, [])
    raise AssertionError("a prompt with no room must be refused")
except vr.PromptTooLong as e:
    assert "900 tokens" in str(e) and "at least 100" in str(e), e
    too_long = f"the model call failed: {e!r}"
assert a.last is None and len(a.calls) == 3, "a refused call leaves no stale record"
b = vr.BudgetedAsk(make_ask, "http://srv", "parser", max_len=1000, max_tokens=500, margin=50,
                   min_tokens=100, session=Session(ok=False))
assert b.count("x" * 300) == {"tokens": 101, "how": "estimate"}, "no tokenizer: about 3 characters a token"
assert b.session.bodies and "chat_template_kwargs" not in b.session.bodies[0], \
    "the server was asked first; no template keywords when none are given"
print("1. the parser's call: counted by the server, full budget or what fits, refused with no room")

# ---- 2. the retrieval check ---------------------------------------------------------------
cases = [{"case_id": f"C{i}", "style": "scenario", "part": "9", "target_sections": ["9Z.01"],
          "target_chunk_ids": [f"Z01_{i}"], "text": f"made-up case {i}"} for i in range(1, 8)]
cases[2]["revised"] = "made-up correction"
ran = []


def run_case(c):
    ran.append(c["case_id"])
    ok = c["case_id"] not in ("C4",)
    return {"case_id": c["case_id"], "style": c["style"], "target_sections": c["target_sections"],
            "in_kq": {"9Z.01": ok}, "chunk_in_kq": ok, "seconds": 0.1}


out = TMP / "check.json"
res = vr.run_check_resumable(run_case, cases[:4], out, every=3, say=lambda s: None)
assert [r["case_id"] for r in res] == ["C1", "C2", "C3", "C4"] and ran == ["C1", "C2", "C3", "C4"]
assert len(json.loads(out.read_text())["results"]) == 4
ran.clear()
data = json.loads(out.read_text())
data["results"][1]["error_compile"] = "RuntimeError('made up')"
out.write_text(json.dumps(data))
res = vr.run_check_resumable(run_case, cases, out, every=2, say=lambda s: None)
assert ran == ["C2", "C5", "C6", "C7"], f"finished cases are not run again; a crashed one is: {ran}"
assert [r["case_id"] for r in res] == [c["case_id"] for c in cases]
assert all(r["text_sha"] == vr.text_sha(c["text"]) for r, c in zip(res, cases))
ran.clear()
changed = [dict(c) for c in cases]
changed[0]["text"] = "made-up case 1, worded again"
vr.run_check_resumable(run_case, changed, out, say=lambda s: None)
assert ran == ["C1"], f"a case whose text changed is run again: {ran}"
ran.clear()
res = vr.run_check_resumable(run_case, cases, out, say=lambda s: None)
assert ran == ["C1"]

earlier = [{"case_id": f"C{i}", "style": "scenario", "in_kq": {"9Z.01": i not in (5, 6)},
            "chunk_in_kq": i not in (5, 6)} for i in range(1, 8)]
earlier[3]["error_compile"] = "x"
old_ran = []


def run_old(c):
    old_ran.append(c["case_id"])
    return {"case_id": c["case_id"], "style": "scenario", "in_kq": {"9Z.01": True}, "chunk_in_kq": True}


bf = TMP / "before.json"
before = vr.results_before(cases, earlier, run_old, out_path=bf, say=lambda s: None)
assert old_ran == ["C3", "C4"], f"corrected or crashed cases are run again with the old setting: {old_ran}"
assert [r["case_id"] for r in before] == [c["case_id"] for c in cases]
assert [r["case_id"] for r in json.loads(bf.read_text())["results"]] == ["C3", "C4"], "saved as it goes"
old_ran.clear()
again = vr.results_before(cases, earlier, run_old, out_path=bf, say=lambda s: None)
assert old_ran == [] and [r["case_id"] for r in again] == [c["case_id"] for c in cases], "resumed from the file"
assert vr.results_before(cases[:2], None, run_old, say=lambda s: None)[0]["chunk_in_kq"] is True
assert old_ran == ["C1", "C2"], "no earlier run: every case is run with the old setting"

assert rc.passes({"in_kq": {"a": True}, "chunk_in_kq": None}) is True, "a two-section case has no paragraph"
assert rc.passes({"in_kq": {"a": True, "b": False}, "chunk_in_kq": None}) is False
assert rc.passes({"in_kq": {"a": True}, "chunk_in_kq": False}) is False
assert rc.passes({"error_compile": "x"}) is None
g = rc.gate(res, before)
assert g["pass_before"] == 5 and g["pass_now"] == 6, g      # before: C5, C6 fail; now: C4 fails
assert g["gained"] == ["C5", "C6"] and g["lost"] == ["C4"] and g["ok"], g
g2 = rc.gate(before, res)
assert not g2["ok"] and g2["lost"] == ["C5", "C6"]
g3 = rc.gate([{"case_id": "C1", "error_compile": "x"}], before)
assert not g3["ok"] and g3["errors"] == ["C1"], "a crash never passes the gate"
buf = io.StringIO()
with redirect_stdout(buf):
    rc.print_gate(g)
assert "5 before -> 6 now" in buf.getvalue()

find = {"pool_ids": ["Z01_1", "Z02_1", "Y01_1"], "pool_sections": ["9Z.01", "9Z.02", "9Y.01"],
        "sources": {"Z01_1": ["sentence 2", "heading: 9Z.01"], "Z02_1": ["question"]},
        "rankings": {"question": ["Z02_1", "Z01_1", "Y01_1"], "sentence 1": ["Y01_1", "Z02_1", "Z01_1"]},
        "sentences": ["a b c", "d e f"], "terms": [{"term": "Blue Panel", "see": "Panel"}],
        "headings": [{"section": "9Z.01"}], "pool": 3}
case = {"case_id": "C1", "target_sections": ["9Z.01", "9Y.01"], "target_chunk_ids": ["Z01_1"]}
rec = rc._find_record(find, case, [{"chunk_id": "Z01_1"}, {"chunk_id": "Q1"}],
                      [{"chunk_id": "Q1"}, {"chunk_id": "Z01_1"}])
t = rec["targets"]["Z01_1"]
assert t == {"in_pool": True, "found_by": ["sentence 2", "heading: 9Z.01"],
             "view_ranks": {"question": 2, "sentence 1": 3}, "searched_rank": 2, "in_kq": True}, t
assert rec["section_found_by"] == {"9Z.01": ["sentence 2", "heading: 9Z.01"], "9Y.01": []}
assert rec["find"] == {"sentences": 2, "terms": ["Blue Panel -> Panel"], "headings": ["9Z.01"], "pool": 3}
json.dumps(rec)


class FakeRetriever:
    def retrieve_for_compile(self, text):
        from types import SimpleNamespace
        return SimpleNamespace(chunks=[{"chunk_id": "Z01_1", "section_id": "9Z.01", "source": "searched",
                                        "content_type": "Standard"}],
                               figures=[], debug={"find": find})


r = rc.run_case(FakeRetriever(), {**case, "style": "scenario", "part": "9", "text": "x"})
assert "rag_rank" not in r, "the older retrieve() is not run by default"
assert r["targets"]["Z01_1"]["searched_rank"] == 1 and r["in_kq"] == {"9Z.01": True, "9Y.01": False}
assert rc.passes(r) is False
buf = io.StringIO()
with redirect_stdout(buf):
    rc.print_targets([r], ["C1"])
assert "found by ['sentence 2', 'heading: 9Z.01']" in buf.getvalue() and "section 9Y.01" in buf.getvalue()
print("2. retrieval check: resumable, 'before' from the earlier run, the gate, where targets came from")

# ---- 3. files and answers -------------------------------------------------------------
p = TMP / "sub" / "x.json"
vr.save_json(p, {"a": (1, 2), "n": 3.0})
assert vr.load_json(p, None) == {"a": [1, 2], "n": 3.0} and not (TMP / "sub" / "x.json.tmp").exists()
assert vr.load_json(TMP / "missing.json", {"d": 1}) == {"d": 1}
(TMP / "bad.json").write_text("{half")
assert vr.load_json(TMP / "bad.json", []) == []
assert vr.same_json({"a": (1, 2)}, {"a": [1, 2]}) and not vr.same_json({"a": 1}, {"a": 2})
recs = [{"case_id": "Q1", "terminal": "TRUE", "answer": {"text": "It holds.", "citations": [{"id": "Z01_1"}]}},
        {"case_id": "Q2", "terminal": None, "answer": None},
        {"case_id": "Q3", "terminal": "FALSE", "unsupported_certification": True,
         "answer": {"text": "It does not hold.", "unresolved": ["o2"]}},
        {"case_id": "Q4", "terminal": None, "answer": None, "error": "RuntimeError('x')"}]
buf = io.StringIO()
with redirect_stdout(buf):
    vr.print_answers(recs)
outp = buf.getvalue()
assert "Q1  decision TRUE  certified True" in outp and "cites: Z01_1" in outp
assert "Q2  decision None  certified False" in outp and "(no answer)" in outp
assert "Q3  decision FALSE  certified False" in outp and "left open: 1" in outp
assert "Q4  decision None  certified False  ERROR RuntimeError('x')" in outp
assert vr.answer_line(recs[0]).split() == ["Q1", "TRUE", "It", "holds."]
f = vr.failed_plan_record("Q9", "made-up", "the parse stopped: x",
                          kq={"chunks": [{"content_type": "Standard"}, {"content_type": "Option"}]})
assert f["outcome"] == "failed" and f["spec"] is None and f["problems"] == [["the parse stopped: x"]]
assert f["kq_size"] == 2 and f["kq_types"] == {"Standard": 1, "Option": 1}
import parser_check as pc
with redirect_stdout(io.StringIO()):
    pc.print_plan(f)                  # a failed record prints, it does not stop the notebook
assert vr.plan_needs_retry(None, "q") and vr.plan_needs_retry({"question": "old", "outcome": "valid first time"}, "q")
assert not vr.plan_needs_retry({"question": "q", "outcome": "valid first time"}, "q")
assert vr.plan_needs_retry(f | {"question": "q"}, "q"), "the run broke: try again"
broke = {"question": "q", "outcome": "failed", "problems": [["the model call failed: RuntimeError('503')"]]}
assert vr.plan_needs_retry(broke, "q")
wrong = {"question": "q", "outcome": "failed", "problems": [["o2: unknown source chunk"], ["o2: unknown source chunk"]]}
assert not vr.plan_needs_retry(wrong, "q"), "a plan that failed its checks is a result, not retried"
assert not vr.plan_needs_retry({"question": "q", "outcome": "failed", "problems": [[too_long]]}, "q"), \
    "a prompt too long for the window fails the same way every time"
bad_req = "the model call failed: RuntimeError('the model server answered 400: bad request')"
assert not vr.plan_needs_retry({"question": "q", "outcome": "failed", "problems": [[bad_req]]}, "q")
import numpy as np
assert vr.plain({"ok": np.bool_(False), "n": np.float32(0.5), "k": np.int64(3)}) == {"ok": False, "n": 0.5, "k": 3}
assert vr.plain(np.array([True, False])) == [True, False]
assert "mrag/find_provisions.py" in vr.RETRIEVAL_FILES, "new retrieval code gives a new Kq file"
print("3. files written whole, JSON compared as JSON, answers and failures printed plainly")

print("\nALL VINE RUN TESTS PASSED")
