"""Tests for hprc/drop_report.py on a small made-up run (no model, no GPU, no gold).
run: python3 tests/test_drop_report.py"""
import csv
import io
import json
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hprc"))
sys.path.insert(0, str(HERE))
import drop_report as dr  # noqa: E402


def piece(cid, kind, sec, para, text="text"):
    return {"chunk_id": cid, "content_type": kind, "section_id": sec, "ordinal": para, "text": text}


def obl(oid, src="", hint=None):
    return {"id": oid, "claim": "c", "source_chunk": src, "evidence_hint": hint or [], "requires": [], "guard": None}


def make(tmp):
    q1 = [
        piece("MUTCD11e_9Z01_Standard_01", "Standard", "9Z.01", 1),            # checked, in decision, cited (with a full stop)
        piece("MUTCD11e_9Z01_Standard_02_itemA", "Standard", "9Z.01", 2),      # set aside
        piece("MUTCD11e_9Z01_Standard_02_itemB", "Standard", "9Z.01", 2),      # checked by o2, outside decision
        piece("MUTCD11e_9Z01_Standard_02_itemC", "Standard", "9Z.01", 2),      # LEFT OUT: no entry, other item checked
        piece("MUTCD11e_9Z01_Guidance_03", "Guidance", "9Z.01", 3, "=formula"),  # set aside; text starts with '='
        piece("MUTCD11e_9Z01_Option_04", "Option", "9Z.01", 4),                # added by code (prov1, flagged)
        piece("MUTCD11e_9Z01_Standard_05", "Standard", "9Z.01", 5),            # not accounted
        piece("MUTCD11e_9Z01_Support_06", "Support", "9Z.01", 6),              # not a provision
        piece("MUTCD11e_9Z02_Standard_01", "Standard", "9Z.02", 1, "≥ 3°"),     # checked by hint, UNKNOWN, not cited
        piece("MUTCD11e_9Z02_Standard_02", "Standard", "9Z.02", 2),            # checked_by names o1, which does not rest on it
        piece("MUTCD11e_9Z03_Option_01", "Option", "9Z.03", 1),                # checked by a parser check named prov9 (not code)
        piece("MUTCD11e_9Z04_Standard_01_itemA", "Standard", "9Z.04", 1),      # cited through its paragraph id
    ]
    spec = {"terminal": "m1", "obligations": [
        obl("o1", "MUTCD11e_9Z01_Standard_01"), obl("o2", "MUTCD11e_9Z01_Standard_02_itemB"),
        obl("o3", "", [{"type": "section", "id": "9Z.02", "paragraph": "1"}]),
        obl("prov1", "MUTCD11e_9Z01_Option_04"), obl("prov9", "MUTCD11e_9Z03_Option_01"),
        obl("o4", "MUTCD11e_9Z04_Standard_01_itemA"),
    ], "merges": [{"id": "m1", "kind": "conjunction", "inputs": ["o1", "o3", "o4"],
                   "guard": {"all": [{"state": "prov9", "status": "TRUE"}]}}],
        "provisions": [
            {"id": "MUTCD11e_9Z01_Standard_01", "checked_by": ["o1"]},
            {"id": "MUTCD11e_9Z01_Standard_02_itemA", "not_related": "reason A"},
            {"id": "MUTCD11e_9Z01_Standard_02_itemB", "checked_by": ["o2"]},
            {"id": "MUTCD11e_9Z01_Guidance_03", "not_related": "reason G"},
            {"id": "MUTCD11e_9Z01_Option_04", "checked_by": ["prov1"], "added_by_code": True},
            {"id": "MUTCD11e_9Z02_Standard_01", "checked_by": ["o3"]},
            {"id": "MUTCD11e_9Z02_Standard_02", "checked_by": ["o1"]},
            {"id": "MUTCD11e_9Z03_Option_01", "checked_by": ["prov9"]},
            {"id": "MUTCD11e_9Z04_Standard_01_itemA", "checked_by": ["o4"]},
        ]}
    certs = [{"id": "o1", "kind": "check", "status": "TRUE"}, {"id": "o2", "kind": "check", "status": "FALSE"},
             {"id": "o3", "kind": "check", "status": "UNKNOWN", "reason": "the figure was not readable"},
             {"id": "prov1", "kind": "check", "status": "TRUE"}, {"id": "prov9", "kind": "check", "status": "TRUE"},
             {"id": "o4", "kind": "check", "status": "TRUE"}, {"id": "m1", "kind": "merge", "status": "UNKNOWN"}]
    kq = {"Q1": {"question": "q one", "chunks": q1},
          "Q2": {"question": "q two", "chunks": [piece("MUTCD11e_9Z05_Standard_01", "Standard", "9Z.05", 1)]},
          "Q3": {"question": "q three", "chunks": [piece("MUTCD11e_9Z06_Standard_01", "Standard", "9Z.06", 1)]}}
    run = {"commit": "abc", "parse_manifest": {"kq_file": "kq.json"},
           "plans": {"Q1": {"question": "q one", "kq_size": len(q1), "outcome": "valid first time", "spec": spec},
                     "Q2": {"question": "q two", "kq_size": 1, "outcome": "no plan", "spec": None},
                     "Q3": {"question": "q three", "kq_size": 1, "outcome": "valid first time",
                            "spec": {"terminal": "x", "obligations": [obl("x", "MUTCD11e_9Z06_Standard_01")],
                                     "merges": [], "provisions": [{"id": "MUTCD11e_9Z06_Standard_01", "checked_by": ["x"]}]}}},
           "executions": {"Q1": {"terminal": "UNKNOWN", "certificates": certs,
                                 "answer": {"text": "Yes, see MUTCD11e_9Z01_Standard_01. Also MUTCD11e_9Z04_Standard_01.",
                                            "citations": [{"type": "chunk", "id": "MUTCD11e_9Z01_Option_04"}]}},
                          "Q2": {"terminal": None, "certificates": [], "answer": None},
                          "Q3": {"terminal": None, "certificates": [], "answer": None, "error": "boom"}}}
    (tmp / "run.json").write_text(json.dumps(run))
    (tmp / "kq.json").write_text(json.dumps(kq))
    return run, kq


def stops(argv):
    try:
        with redirect_stderr(io.StringIO()):
            dr.main(argv)
    except SystemExit as e:
        return "STOPPED" in str(e)
    return False


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        run, kq = make(tmp)
        dr.main([str(tmp / "run.json"), str(tmp / "out"), "--kq", str(tmp / "kq.json")])
        raw = (tmp / "out" / "provisions.csv").read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf"), "UTF-8 with a BOM, for Excel"
        rows = {r["provision"].replace("MUTCD11e_", ""): r
                for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))}
        assert "9Z01_Support_06" not in rows, "Support is not a provision"
        r = rows["9Z01_Standard_01"]
        assert (r["parser"], r["in_final_decision"], r["cited_in_answer"]) == ("CHECKED", "yes", "yes"), r
        r = rows["9Z01_Standard_02_itemA"]
        assert (r["parser"], r["parser_reason_if_set_aside"]) == ("SET ASIDE", "reason A")
        assert r["in_final_decision"] == "" and r["cited_in_answer"] == ""
        r = rows["9Z01_Standard_02_itemB"]
        assert (r["parser"], r["checks"], r["in_final_decision"], r["cited_in_answer"]) == ("CHECKED", "o2=FALSE", "no", "no")
        r = rows["9Z01_Standard_02_itemC"]
        assert r["parser"] == "LEFT OUT" and "o2" in r["note"], r
        assert r["in_final_decision"] == "" and r["cited_in_answer"] == "", "a left-out item is not said to be used"
        r = rows["9Z01_Guidance_03"]
        assert r["parser"] == "SET ASIDE" and r["text"] == "'=formula", "a formula sign is escaped"
        r = rows["9Z01_Option_04"]
        assert (r["parser"], r["cited_in_answer"]) == ("ADDED BY CODE", "yes"), "flag, and answer.citations"
        assert rows["9Z03_Option_01"]["parser"] == "CHECKED", "a parser check named prov9 is not a code-added check"
        assert rows["9Z03_Option_01"]["in_final_decision"] == "yes", "reached through a guard"
        assert rows["9Z01_Standard_05"]["parser"] == "NOT ACCOUNTED"
        r = rows["9Z02_Standard_01"]
        assert (r["parser"], r["checks"], r["cited_in_answer"]) == ("CHECKED", "o3=UNKNOWN", "no")
        assert "figure was not readable" in r["why_open"] and r["text"] == "≥ 3°"
        r = rows["9Z02_Standard_02"]
        assert r["parser"] == "NOT ACCOUNTED" and "do not rest on it" in r["note"], r
        assert rows["9Z04_Standard_01_itemA"]["cited_in_answer"] == "yes", "an item cited through its paragraph id"
        assert rows["9Z05_Standard_01"]["parser"] == "NOT ACCOUNTED"
        qs = {r["question"]: r for r in csv.DictReader(io.StringIO((tmp / "out" / "questions.csv").read_text(encoding="utf-8-sig")))}
        assert qs["Q1"]["question_status"] == "ok"
        assert qs["Q2"]["question_status"] == "PLAN FAILED"
        assert qs["Q3"]["question_status"].startswith("EXECUTION ERROR")
        assert (qs["Q1"]["set_aside_standard"], qs["Q1"]["set_aside_guidance"], qs["Q1"]["left_out"],
                qs["Q1"]["not_accounted"], qs["Q1"]["added_by_code"], qs["Q1"]["checked_left_open"]) == ("1", "1", "1", "2", "1", "1"), qs["Q1"]
        md = (tmp / "out" / "report.md").read_text(encoding="utf-8")
        for s in ("reason A", "reason G", "NOT ACCOUNTED", "Left out by the parser (another item",
                  "the code added a check", "MUTCD11e_9Z01_Standard_02_itemC", "Q2 (PLAN FAILED)"):
            assert s in md, s

        # wrong inputs stop with a message instead of an empty report
        (tmp / "plans_only.json").write_text(json.dumps({"Q1": {}}))
        assert stops([str(tmp / "plans_only.json"), str(tmp / "o2"), "--kq", str(tmp / "kq.json")])
        other = dict(kq)
        other.pop("Q3")
        (tmp / "kq.json").write_text(json.dumps(other))
        assert stops([str(tmp / "run.json"), str(tmp / "o3"), "--kq", str(tmp / "kq.json")]), "a question missing from Kq"
        other = json.loads(json.dumps(kq))
        other["Q1"]["question"] = "another text"
        (tmp / "kq.json").write_text(json.dumps(other))
        assert stops([str(tmp / "run.json"), str(tmp / "o4"), "--kq", str(tmp / "kq.json")]), "another question text"
        other = json.loads(json.dumps(kq))
        other["Q1"]["chunks"] = other["Q1"]["chunks"][:-1]
        (tmp / "kq.json").write_text(json.dumps(other))
        assert stops([str(tmp / "run.json"), str(tmp / "o5"), "--kq", str(tmp / "kq.json")]), "another Kq size"
        (tmp / "kq_other_name.json").write_text(json.dumps(kq))
        assert stops([str(tmp / "run.json"), str(tmp / "o6"), "--kq", str(tmp / "kq_other_name.json")]), "another Kq file"
    print("ALL drop_report TESTS PASSED")


if __name__ == "__main__":
    main()
