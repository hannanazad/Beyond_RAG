"""VINE answer-then-check (vine2/): offline tests with made-up evidence and stand-in models.

Every rule, value and answer here is invented ("zorb markers on blip lanes"). Nothing
comes from a benchmark question or its answer. No GPU, no API, no data files.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vine2 import check, core  # noqa: E402

# ---- made-up evidence --------------------------------------------------------
ENTRY = {
    "question": "Q",
    "chunks": [
        {"chunk_id": "MUTCD11e_9Z01_Standard_02", "content_type": "Standard", "section_id": "9Z.01",
         "ordinal": 2, "section_title": "Zorb Markers", "page_printed": 12,
         "text": "Zorb markers shall be at least 30 inches wide on blip lanes."},
        {"chunk_id": "MUTCD11e_9Z01_Standard_03", "content_type": "Standard", "section_id": "9Z.01",
         "ordinal": 3, "section_title": "Zorb Markers", "page_printed": 12,
         "text": "Unless Paragraph 5 says otherwise, zorb markers shall be yellow — never blue."},
        {"chunk_id": "MUTCD11e_9Z01_Option_05", "content_type": "Option", "section_id": "9Z.01",
         "ordinal": 5, "section_title": "Zorb Markers", "page_printed": 12,
         "lead_in": "On blip lanes signed for under 20 mph:", "text": "zorb markers may be white."},
        {"chunk_id": "MUTCD11e_9Z02_Guidance_07", "content_type": "Guidance", "section_id": "9Z.02",
         "ordinal": 7, "section_title": "Zorb Placement", "page_printed": 13,
         "text": "Zorb markers should stand at least 6 feet back from the blip lane rim."},
        {"chunk_id": "MUTCD11e_9Z02_Guidance_08", "content_type": "Guidance", "section_id": "9Z.02",
         "ordinal": 8, "section_title": "Zorb Placement", "page_printed": 13,
         "text": "Zorb markers should stand at least 6 feet back from the blip lane rim in farm zones."},
        {"chunk_id": "MUTCD11e_TBLNOTE_9Z-1_02", "content_type": "TableNote", "section_id": "9Z.03",
         "ordinal": 2, "section_title": "Zorb Sizes", "page_printed": 14,
         "text": "Bigger zorbs are allowed on crowded lanes."},
        {"chunk_id": "vine:trow:Table 9Z-1#s1r2", "content_type": "TableRow", "section_id": "9Z.03",
         "ordinal": None, "section_title": "Zorb Sizes", "page_printed": 14,
         "authority": "TABLE: printed in the manual",
         "text": "Table 9Z-1 | Lane type: Wide blip lane | Minimum zorb width: 36 inches"},
    ],
    "figures": [{"figure_id": "Table 9Z-1", "caption": "Table 9Z-1. Minimum Zorb Sizes",
                 "image_paths": ["/nonexistent/table_9Z-1.png"]},
                {"figure_id": "Figure 9Z-2", "caption": "Figure 9Z-2. Example of Zorb Placement",
                 "image_paths": ["/nonexistent/figure_9Z-2.png"]}],
}
IDX = core.evidence_index(ENTRY, ["Table 9Z-1"])          # only Table 9Z-1's image was attached
QUESTION = "A zorb marker 24 inches wide is proposed on a blip lane. Is that acceptable?"
DRAFT = """Direct Answer: No. The zorb marker must be at least 30 inches wide, and the proposed one is 24 inches.

Standards (mandatory):
- Zorb markers shall be blue. The width rule is a Standard in Section 9Z.01.
- The shortfall is 30 − 24 = 7 inches.

Guidance (recommended):
- Zorb markers should stand at least 6 feet back from the blip lane rim.
- The evidence gives no zorb width for a wide blip lane.

Pictures:
- [Picture 2] Figure 9Z-2 shows the marker 6 feet back from the rim.

| Lane | Width |
|---|---|
| wide blip lane | 30 inches |

Citations:
- Section 9Z.01 Standard §2 (p.12)
- Section 9Z.09 Standard §1 (p.99)
- Section 9Z.03 TableNote § 2 (p.14)
- Section 9Z.03 TableRow §? (p.?)
- Table 9Z-1 (p.14)
"""

# ---- 1. statements --------------------------------------------------------------
st = core.split_statements(DRAFT)
claims = [s for s in st if s["kind"] == "claim"]
assert all(DRAFT[s["start"]:s["end"]] == s["text"] for s in st), "every span is the exact text"
assert [s["n"] for s in claims] == list(range(1, len(claims) + 1))
assert claims[0]["section"] == "Direct Answer" and claims[0]["text"].startswith("No.")
assert [s["text"] for s in st if s["kind"] == "heading"] == \
    ["Standards (mandatory):", "Guidance (recommended):", "Pictures:", "Citations:"]
assert len([s for s in st if s["kind"] == "citation"]) == 5
rows = [s for s in claims if s["row"]]
assert [r["text"] for r in rows] == ["| Lane | Width", "| wide blip lane | 30 inches"]
assert [s["kind"] for s in st if s["row"] and s["kind"] != "claim"] == ["other"]     # the |---| row
assert len(claims) == 9, [s["text"] for s in claims]
num = core.numbered_answer(st)
assert "[S1] (Direct Answer) No." in num and "Citations:" in num and "Section 9Z.09" not in num
s2 = core.split_statements(
    "## Direct Answer\nYes. The marker passes here.\nA. First lettered item here.\nB) Second lettered item here.\n"
    "Sources used:\n- This line is a claim, not a citation.\n**Citations**\n- Section 9Z.01 Standard § 2 (p.12)\n"
    "\r\nPlain line one. The 4 ft. wide lane is narrow. e.g. text here.\n")
assert [(s["kind"], s["text"]) for s in s2] == [
    ("heading", "## Direct Answer"), ("claim", "Yes. The marker passes here."),
    ("claim", "First lettered item here."), ("claim", "Second lettered item here."),
    ("heading", "Sources used:"), ("claim", "This line is a claim, not a citation."),
    ("heading", "**Citations**"), ("citation", "Section 9Z.01 Standard § 2 (p.12)"),
    ("citation", "Plain line one."), ("citation", "The 4 ft. wide lane is narrow. e.g. text here.")]
print(f"1. statements: {len(claims)} claims, exact spans; markdown, bold and lettered lines; table rows kept whole")

# ---- 2. quotes are checked against the evidence --------------------------------
V = core.verify_quote
assert V("shall be at least 30 inches wide", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] == "text"
assert V("zorb markers shall be yellow - never blue", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] == "text"
assert V("“Zorb  markers shall be at least 30”", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] == "text"
assert V("Unless Paragraph 5 says ... yellow — never blue", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] == "text"
assert V("never blue at all ... Unless Paragraph 5 says", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] is False  # order
assert V("Unless ... never blue", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] is False            # 1-word part
assert V("Unless ... yellow \u2014 never blue", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] is False  # 5 words, a 1-word part
assert V("markers shall be at least 3", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] is False      # 3 is not 30
assert V("signed for under 20 mph: zorb markers may be white", "MUTCD11e_9Z01_Option_05", IDX)["verified"] == "text"
r = V("shall be at least 30 inches wide", "MUTCD11e_9Z02_Guidance_07", IDX)          # wrong id, found once elsewhere
assert r["verified"] == "text" and r["id"] == "MUTCD11e_9Z01_Standard_02"
assert V("stand at least 6 feet back from", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] is False  # in two pieces
assert V("shall be wide here", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] is False   # under 5 words
assert V("zorb markers shall be purple always", "MUTCD11e_9Z01_Standard_02", IDX)["verified"] is False
assert V("this text appears nowhere at all", "MUTCD11e_9Z77_Standard_01", IDX)["verified"] is False
assert V("Lane type: Wide blip lane | Minimum zorb width: 36 inches", "Table 9Z-1", IDX)["verified"] == "text"
assert V("the row for narrow lanes reads 28", "Table 9Z-1", IDX)["verified"] == "image"     # attached image
assert V("the marker is drawn at six feet", "Figure 9Z-2", IDX)["verified"] is False       # image not attached
assert V("Unless Paragraph 5 says [...] yellow — never blue.", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] == "text"
assert V("zorb markers shall be yellow,", "MUTCD11e_9Z01_Standard_03", IDX)["verified"] == "text"
IDX45 = {"x": {"text": "The zorb rim gap is 4.5 feet on wide lanes.", "figure": False, "image": False}}
assert V("the zorb rim gap is 4", "x", IDX45)["verified"] is False                          # 4 is not 4.5
assert V("the zorb rim gap is 4.5", "x", IDX45)["verified"] == "text"
print("2. quotes: whole words and numbers, in order, parts of 3+ words, [...] cuts; an image counts only if attached")

# ---- 3. arithmetic and citations --------------------------------------------------
A = core.arithmetic_checks
assert [a["holds"] for a in A("The shortfall is 30 − 24 = 7 inches.")] == [False]
assert [a["holds"] for a in A("8 x 25² / 50 = 100 ft and 0.5 × 100 = 50")] == [True, True]
assert A("Q = AB²/7 = 63") == []                                 # a formula, not arithmetic
assert [a["holds"] for a in A("1,000 × 3 = 3,000; 2/3 = 0.67; 2/3 = 0.6")] == [True, True, False]
assert A("Section 2 = 5 feet") == [] and A("(p.12) = 3") == []
assert [a["holds"] for a in A("8/10 = 80% and 1/3 = 33 percent")] == [True, True]
assert [a["holds"] for a in A("-5 + 3 = -2")] == [True]
assert A("a range of 20-50 = 30 feet") == []
assert [a["holds"] for a in A("2 + 3 = 5 + 1 = 6")] == [True]
assert [a["holds"] for a in A("100 ft x 0.5 = 50 ft, and 12 in x 3 = 36 inches")] == [True, True]   # units ignored
assert A("Station 10+50 = 1050") == []                          # a station number, not a sum
assert [a["stated_written"] for a in A("8/10 = 80%")] == ["80"]
assert core._numbers("a 12-inch zorb at 45-mph, sign R3-2, Figure 9Z-2") == {"12", "45"}
cites = core.citation_checks(st, IDX)
assert [(c["cited"], c["in_evidence"]) for c in cites] == [
    ("9Z.01 standard 2", True), ("9Z.09 standard 1", False), ("9Z.03 tablenote 2", True), ("Table 9Z-1", True)]
print("3. arithmetic recomputed (shares, signs, ranges, chains); citations looked up by section, type, paragraph")


# ---- 4. the checker's reply, verified ---------------------------------------------
def src(i, q):
    return {"id": i, "quote": q}


S1 = src("MUTCD11e_9Z01_Standard_02", "shall be at least 30 inches wide on blip lanes")
REPLY = {"statements": [
    {"n": 1, "verdict": "SUPPORTED", "sources": [S1]},
    {"n": 2, "verdict": "CONTRADICTED", "sources": [src("MUTCD11e_9Z01_Standard_03", "zorb markers shall be yellow")],
     "correction": "Zorb markers shall be yellow\n unless Paragraph 5 says otherwise (Standard, Section 9Z.01)."},
    {"n": 3, "verdict": "SUPPORTED", "sources": [src("MUTCD11e_9Z01_Standard_02", "a quote that is not there at all")]},
    {"n": 4, "verdict": "CONTRADICTED", "sources": [S1], "correction": "The shortfall is 30 − 24 = 6 inches."},
    {"n": "[S5]", "verdict": "CONTRADICTED", "sources": src("MUTCD11e_9Z02_Guidance_07", "should stand at least 6 feet back"),
     "correction": "Zorb markers shall stand at least 6 feet back from the blip lane rim."},
    {"n": 6.0, "verdict": "CONTRADICTED", "sources": [src("Table 9Z-1", "Minimum zorb width: 36 inches")],
     "correction": "Table 9Z-1 gives a minimum zorb width of 36 inches for a wide blip lane."},
    {"n": 7, "verdict": "SUPPORTED", "sources": [src("Figure 9Z-2", "the marker stands six feet back")]},
    {"n": 9, "verdict": "CONTRADICTED", "sources": [src("Table 9Z-1", "Minimum zorb width: 36 inches")],
     "correction": "| wide blip lane | 36 inches"},
    {"n": 9, "verdict": "SUPPORTED", "sources": [src("MUTCD11e_9Z01_Standard_02", "words that are not there")]},
    {"n": 99, "verdict": "SUPPORTED"}],
    "additions": [
        {"text": "An Option (Section 9Z.01, paragraph 5) lets zorb markers be white under 20 mph.",
         "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]},
        {"text": "An invented rule with no real quote.", "sources": [src("MUTCD11e_9Z01_Option_05", "markers may be green on Sundays")]},
        {"text": "Zorb markers should stand at least 6 feet back from the blip lane rim (Guidance).",
         "sources": [src("MUTCD11e_9Z02_Guidance_07", "should stand at least 6 feet back from the blip lane rim")]},
        {"text": "Bigger zorbs, up to 99 inches, are allowed on crowded lanes.",
         "sources": [src("MUTCD11e_TBLNOTE_9Z-1_02", "Bigger zorbs are allowed on crowded lanes")]},
        {"text": "Two widths make 30 + 36 = 67 inches.", "sources": [S1]}]
    + [{"text": f"extra point number {i}", "sources": [S1]} for i in range(9)]}
chk = core.read_reply(REPLY, st, IDX, QUESTION)
out = {r["n"]: r["outcome"] for r in chk["statements"]}
assert out == {1: "checked", 2: "corrected", 3: "unconfirmed", 4: "corrected", 5: "disputed", 6: "corrected",
               7: "unconfirmed", 8: "unconfirmed", 9: "corrected"}, out
why = {r["n"]: r["not_applied_because"] for r in chk["statements"]}
assert "requirement words" in why[5] and "shall" in why[5]
assert [a["text"][:12] for a in chk["additions"]] == ["An Option (S"]
assert [a["rejected_because"].split()[0] for a in chk["additions_rejected"]] == ["no", "it", "it", "its", "it"]
# the main answer turned round needs two verified sources from different pieces
flip = {"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [S1],
                        "correction": "Yes. The zorb marker must be at least 30 inches wide."}]}
assert core.read_reply(flip, st, IDX, QUESTION)["statements"][0]["outcome"] == "disputed"
flip["statements"][0]["sources"].append(src("vine:trow:Table 9Z-1#s1r2", "Lane type: Wide blip lane | Minimum zorb"))
assert core.read_reply(flip, st, IDX, QUESTION)["statements"][0]["outcome"] == "corrected"
# a correction may not bring in a number that no verified quote or the question gives
newnum = {"statements": [{"n": 8, "verdict": "CONTRADICTED", "sources": [src("Table 9Z-1", "Minimum zorb width: 36 inches")],
                          "correction": "Table 9Z-1 gives 40 inches for a wide blip lane."}]}
r8 = core.read_reply(newnum, st, IDX, QUESTION)["statements"][7]
assert r8["outcome"] == "disputed" and "numbers" in r8["not_applied_because"], r8
# two verdicts for one statement: the one with more verified sources is used, wherever it comes
dup = {"statements": [{"n": 3, "verdict": "SUPPORTED", "sources": [src("MUTCD11e_9Z01_Standard_02", "not in the piece at all")]},
                      {"n": 3, "verdict": "SUPPORTED", "sources": [S1]}]}
assert core.read_reply(dup, st, IDX, QUESTION)["statements"][2]["outcome"] == "checked"
# a reply with "additions" as an object, and a reply with text and braces after the JSON
assert core.read_reply({"statements": [], "additions": {"text": "x"}}, st, IDX)["additions"] == []
assert core.extract_json('```json\n{"statements": [], "additions": []}\n```\nnote: {not json}') == \
    {"statements": [], "additions": []}
# a requirement word is allowed when a verified source has that force (here "should": Guidance)
g = {"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [src("MUTCD11e_9Z02_Guidance_07",
                     "Zorb markers should stand at least 6 feet back")],
                     "correction": "Zorb markers should stand at least 6 feet back from the blip lane rim."}]}
assert core.read_reply(g, st, IDX, QUESTION)["statements"][1]["outcome"] == "corrected"
g["statements"][0]["correction"] = "Zorb markers may stand at least 6 feet back from the blip lane rim."
r2 = core.read_reply(g, st, IDX, QUESTION)["statements"][1]
assert r2["outcome"] == "disputed" and "may" in r2["not_applied_because"]          # "may" is an Option, not Guidance
# the question never backs a requirement word
gq = {"statements": [{"n": 3, "verdict": "CONTRADICTED", "sources": [S1],
                      "correction": "The width rule is optional in Section 9Z.01."}]}
assert core.read_reply(gq, st, IDX, "Is the width rule optional?")["statements"][2]["outcome"] == "disputed"
# a requirement turned round ("shall" -> "shall not") with one source and no limiting word: not applied
neg = {"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [S1],
                       "correction": "Zorb markers shall not be blue."}]}
r2 = core.read_reply(neg, st, IDX, QUESTION)["statements"][1]
assert r2["outcome"] == "disputed" and "negation" in r2["not_applied_because"]
neg["statements"][0]["sources"] = [src("MUTCD11e_9Z01_Standard_03", "zorb markers shall be yellow — never blue")]
assert core.read_reply(neg, st, IDX, QUESTION)["statements"][1]["outcome"] == "corrected"   # its quote says "never"
# "the evidence gives no ..." corrected with the value: allowed (that is not a requirement turned round)
assert out[6] == "corrected"
# the main answer kept (disputed): a yes/no turned round elsewhere is held back too
S3 = src("MUTCD11e_9Z01_Standard_03", "zorb markers shall be yellow")
both = {"statements": [
    {"n": 1, "verdict": "CONTRADICTED", "sources": [S1], "correction": "Yes. The zorb marker needs only 20 inches."},
    {"n": 3, "verdict": "CONTRADICTED", "sources": [S1, S3],
     "correction": "Yes, the width rule is a Standard in Section 9Z.01."}]}
rb = core.read_reply(both, st, IDX, QUESTION)["statements"]
assert rb[0]["outcome"] == "disputed" and "numbers" in rb[0]["not_applied_because"]
assert rb[2]["outcome"] == "disputed" and "main answer was not applied" in rb[2]["not_applied_because"]
# the main answer turned with one piece, and another turning correction with a second piece: together, two
both = {"statements": [
    {"n": 1, "verdict": "CONTRADICTED", "sources": [S1], "correction": "Yes. The zorb marker is wide enough."},
    {"n": 3, "verdict": "CONTRADICTED", "sources": [S3], "correction": "Yes. The width rule is a Standard in Section 9Z.01."}]}
rb = core.read_reply(both, st, IDX, QUESTION)["statements"]
assert rb[0]["outcome"] == "corrected" and rb[2]["outcome"] == "corrected"
# a correction elsewhere that does not turn anything round does not count as a second piece
both["statements"][1] = {"n": 2, "verdict": "CONTRADICTED", "sources": [S3],
                         "correction": "Zorb markers shall be yellow unless Paragraph 5 says otherwise."}
rb = core.read_reply(both, st, IDX, QUESTION)["statements"]
assert rb[0]["outcome"] == "disputed" and rb[1]["outcome"] == "corrected"
# additions: a named type its source is not, a yes/no against the main answer, an unbacked force word
adds = {"statements": [], "additions": [
    {"text": "A Standard in Section 9Z.01 lets zorb markers be white on slow lanes.",
     "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]},
    {"text": "Yes, the zorb markers may be white on slow lanes.",
     "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]},
    {"text": "Zorb markers shall be white on lanes signed for under 20 mph.",
     "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]},
    {"text": "Bigger zorbs are allowed on crowded lanes, as a table note says.",
     "sources": [src("MUTCD11e_TBLNOTE_9Z-1_02", "Bigger zorbs are allowed on crowded lanes")]}]}
ra = core.read_reply(adds, st, IDX, QUESTION)
assert [x["rejected_because"][:22] for x in ra["additions_rejected"]] == [
    "it names a provision t", "it contradicts the mai", "brings in requirement "], ra["additions_rejected"]
assert [x["text"][:12] for x in ra["additions"]] == ["Bigger zorbs"]    # "allowed" backed by its own quote

# ---- 4b. the third review's cases -------------------------------------------------
ROW = src("vine:trow:Table 9Z-1#s1r2", "Lane type: Wide blip lane | Minimum zorb width: 36 inches")
TAB = src("Table 9Z-1", "Lane type: Wide blip lane | Minimum zorb width: 36 inches")
D2 = "Direct Answer: No. The marker is too narrow for this lane. It must also be blue in color.\n\nBody:\n" \
     "- No, a zorb marker of this size fails here.\n- The zorb marker must span 30 inches or more.\n"
st2 = core.split_statements(D2)
assert [(s["n"], s["section"]) for s in st2 if s["kind"] == "claim"] == \
    [(1, "Direct Answer"), (2, "Direct Answer"), (3, "Body"), (4, "Body")]
# an inline lead covers its own paragraph only
assert [s["section"] for s in core.split_statements("Direct Answer: No. It fails here.\n\nZorb markers should be blue.")
        if s["kind"] == "claim"] == ["Direct Answer", ""]
yes2 = {"n": 1, "verdict": "CONTRADICTED", "sources": [S1, ROW], "correction": "Yes. The marker is wide enough for this lane."}
# 1. a failed non-turning change in the answer section does not hold back the main answer's own correction
r = core.read_reply({"statements": [yes2, {"n": 2, "verdict": "CONTRADICTED", "sources": [S3],
                     "correction": "It must also be yellow at 25 mph."}]}, st2, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "corrected" and r[1]["outcome"] == "disputed", r
# 3. a change in the answer section that turns nothing round needs one piece
r = core.read_reply({"statements": [{"n": 4, "verdict": "CONTRADICTED", "sources": [TAB],
                     "correction": "The zorb marker must span 36 inches or more."}]}, st2, IDX, QUESTION)["statements"]
assert r[3]["outcome"] == "corrected"
st3 = core.split_statements("Direct Answer: No. The zorb marker must span 30 inches or more.\n")
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [TAB],
                     "correction": "No. The zorb marker must span 36 inches or more."}]}, st3, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "corrected", r
# 4. the pool counts only corrections that pass their own checks
r = core.read_reply({"statements": [dict(yes2, sources=[S1]), {"n": 3, "verdict": "CONTRADICTED", "sources": [S3],
                     "correction": "Yes, a zorb marker of 99 inches passes here."}]}, st2, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed" and r[2]["outcome"] == "disputed"
# 5. a table and its own row are one piece
r = core.read_reply({"statements": [dict(yes2, sources=[TAB, ROW])]}, st2, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed"
# 6. a yes/no in the body may not be turned against the main answer as it stands
r = core.read_reply({"statements": [{"n": 1, "verdict": "SUPPORTED", "sources": [S1]},
                                    {"n": 3, "verdict": "CONTRADICTED", "sources": [S1, ROW],
                                     "correction": "Yes, a zorb marker of this size passes here."}]}, st2, IDX, QUESTION)
assert r["statements"][2]["outcome"] == "disputed" and "disagree" in r["statements"][2]["not_applied_because"]
# 7. additions are compared with the main answer as corrected
r = core.read_reply({"statements": [yes2], "additions": [
    {"text": "Yes, and zorb markers may be white on lanes signed for under 20 mph.", "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]},
    {"text": "No, and zorb markers may be white on lanes signed for under 20 mph too.", "sources": [src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")]}]},
    st2, IDX, QUESTION)
assert r["statements"][0]["outcome"] == "corrected" and [a["text"][:3] for a in r["additions"]] == ["Yes"]
# 8. "not required" states no requirement; 9. a word used only under a negation is new
OPT = src("MUTCD11e_9Z01_Option_05", "zorb markers may be white")
r = core.read_reply({"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [OPT],
                     "correction": "White zorb markers are permitted but not required."}]}, st, IDX, QUESTION)
assert r["statements"][1]["outcome"] == "corrected", r["statements"][1]
r = core.read_reply({"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [S1],
                     "correction": "Blue paint is not required for zorb markers."}]}, st, IDX, QUESTION)
assert r["statements"][1]["outcome"] == "disputed"            # "not required" from a Standard alone: no
# a turn of the main answer refused in one of its statements: the others in it are held back too
r = core.read_reply({"statements": [yes2, {"n": 2, "verdict": "CONTRADICTED", "sources": [S3],
                     "correction": "It need not be blue at 25 mph."}]}, st2, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed" and r[1]["outcome"] == "disputed"
st4 = core.split_statements("Body:\n- There is no rule text saying zorb markers are required on lanes.\n")
G7 = src("MUTCD11e_9Z02_Guidance_07", "Zorb markers should stand at least 6 feet back")
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "Zorb markers are required on lanes."}]}, st4, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed" and "required" in r[0]["not_applied_because"]
# 10. a Guidance piece backs "should" only, even if it uses "shall" in passing
IDXG = dict(IDX, g9={"text": "Where zorb markers shall go on blip lanes, they should sit by the rim.",
                     "kind": "Guidance", "section": "9Z.02", "ordinal": 9, "figure": False, "image": False})
r = core.read_reply({"statements": [{"n": 5, "verdict": "CONTRADICTED", "sources": [src("g9", "zorb markers shall go on blip lanes")],
                     "correction": "Zorb markers shall sit by the rim of the blip lane."}]}, st, IDXG, QUESTION)["statements"]
assert r[4]["outcome"] == "disputed" and "shall" in r[4]["not_applied_because"]
# 11. a provision type a correction newly names must be its source's type
r = core.read_reply({"statements": [{"n": 3, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "The width rule is Guidance in Section 9Z.02."}]}, st, IDX, QUESTION)["statements"]
assert r[2]["outcome"] == "corrected"           # "Standard" was there; Guidance is its source's type
r = core.read_reply({"statements": [{"n": 5, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "That rule is a Standard."}]}, st, IDX, QUESTION)["statements"]
assert r[4]["outcome"] == "disputed" and "provision type" in r[4]["not_applied_because"]
# 12. an exception is not a repeat; 13. ordinary words are not provision types
assert not core._repeats("Zorb markers shall not sit on blip lanes in farms.", ["Zorb markers shall sit on blip lanes."])
assert core._repeats("Zorb markers shall sit on all blip lanes.", ["Zorb markers shall sit on blip lanes."])
assert core._types_named("the standard zorb size on a breakaway support") == set()
assert core._types_named("Zorb spacing counts as Guidance, never a Standard.") == {"guidance"}
# 14, 15. numbers
assert core._numbers("36x36 and 12-inch-wide and 48-by-60-inch, two lanes") == {"36", "12", "48", "60", "2"}
assert core._numbers("paragraphs 3 and 5, Part 6, 4.50 and .5, sign R3-2") == {"4.5", "0.5"}
assert core._numbers("Paragraph 3 and 30 inches") == {"30"}
# 16. conversions and percents are not wrong arithmetic
for ok in ("36 x 36 inches = 9 square feet", "48 x 36 inches = 12 sq ft", "1/2 mile = 2,640 feet"):
    assert all(a["holds"] for a in A(ok)), ok
assert [a["holds"] for a in A("(36 - 30) / 30 x 100 = 20% and 0.06 x 100 = 6%")] == [True, True]
assert [a["holds"] for a in A("36 x 36 inches = 1,200 inches")] == [False]
# 20. "No sign is needed" is not a "No" answer; "should not" to "shall not" turns nothing round
assert core._lead("No sign is needed here.") == "" and core._lead("No, it fails.") == "no" and core._lead("Yes.") == "yes"
assert not core._turns("X should not be Y.", "X shall not be Y.", False) and core._turns("X shall be Y.", "X shall not be Y.", False)
# ---- 4c. the fourth review's cases -----------------------------------------------
assert core._lead("**No**. The marker fails.") == "no" and core._lead("**Yes**, it passes.") == "yes"
st5 = core.split_statements("Direct Answer: The zorb marker meets the width rule.\n\nBody:\n"
                            "- No zorb marker shall sit inside the rim zone.\n- Zorb markers shall be blue.\n")
r = core.read_reply({"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "A zorb marker shall sit inside the rim zone."}]}, st5, IDX, QUESTION)["statements"]
assert r[1]["outcome"] == "disputed"                         # a ban turned into a requirement on one Guidance quote
r = core.read_reply({"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "No zorb marker shall sit inside the rim zone except on farm lanes."}]}, st5, IDX, QUESTION)
assert r["statements"][1]["outcome"] == "disputed" and "shall" in r["statements"][1]["not_applied_because"]
r = core.read_reply({"statements": [{"n": 3, "verdict": "CONTRADICTED", "sources": [G7],
                     "correction": "Blue paint on zorb markers is not required."}]}, st5, IDX, QUESTION)["statements"]
assert r[2]["outcome"] == "disputed"                         # "not required" from a Guidance about something else
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [S1],
                     "correction": "The zorb marker doesn't meet the width rule."}]}, st5, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed"                         # "doesn't" turns the main answer round
# a turn in the body unrelated to the main answer does not back its turn
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [S1],
                                     "correction": "Yes. The zorb marker is wide enough."},
                                    {"n": 2, "verdict": "CONTRADICTED", "sources": [S3N := src(
                                        "MUTCD11e_9Z01_Standard_03", "zorb markers shall be yellow \u2014 never blue")],
                                     "correction": "Zorb markers shall never be blue."}]}, st, IDX, QUESTION)["statements"]
assert r[0]["outcome"] == "disputed" and r[1]["outcome"] == "disputed"
# a main answer kept as written: a value it states is not changed elsewhere
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [S1],
                                     "correction": "Yes. The zorb marker is wide enough."},
                                    {"n": 4, "verdict": "CONTRADICTED", "sources": [TAB],
                                     "correction": "The shortfall is 36 \u2212 24 = 12 inches."}]}, st, IDX, QUESTION)["statements"]
assert r[3]["outcome"] == "disputed" and "value" in r[3]["not_applied_because"]
assert core._numbers('40in and 9ft and 45mph and 48"x48" and two-lane') == {"40", "9", "45", "48", "2"}
assert core._repeats("Zorb markers should stand at least 6 feet back from the blip lane rim (Guidance, Section 9Z.02).",
                     ["Zorb markers should stand at least 6 feet back from the blip lane rim."])
assert not core._turns("It must also be blue.", "It must also be yellow, not blue.", True)
assert core._negs("The evidence never gives a zorb width.") == 0 and core._negs("Zorb markers shall never be blue.") == 1
assert core._negs("No zorb marker shall sit there.") == 1 and core._negs("No. The marker shall be blue.") == 0
assert [a["holds"] for a in A("36 x 36 inches = 1,400 square inches; 36 x 36 inches = 1,296 square inches")] == [False, True]
print("4c. fourth review: bold yes/no, bans, short forms, unrelated turns, kept values, stuck units, repeats")
print("4b. third review: the main answer is never held back by a non-turning failure; a table is one piece; body and"
      " additions follow the corrected main answer; not-required, force by type, new type names; exceptions;"
      " numbers in sizes and words; conversions and percents")
print("4. verdicts need verified quotes; a correction may not bring in unquoted numbers, nor a requirement word"
      " or negation its sources do not back; the main answer needs two sources and stays consistent;"
      " additions may not repeat, misname a type or contradict the main answer")

# ---- 5. the final answers ----------------------------------------------------------
marked, clean, counts, corr_only = core.assemble(DRAFT, st, chk, cites, IDX, "checker-x")
assert "Zorb markers shall be blue." not in marked and "Zorb markers shall be blue." not in clean
assert ("Zorb markers shall be yellow unless Paragraph 5 says otherwise (Standard, Section 9Z.01). [corrected]"
        in marked)
assert "Zorb markers shall be yellow unless Paragraph 5 says otherwise (Standard, Section 9Z.01)." in clean
assert "The width rule is a Standard in Section 9Z.01. [not confirmed]" in marked
assert "The shortfall is 30 − 24 = 6 inches. [corrected]" in marked
assert "Zorb markers should stand at least 6 feet back from the blip lane rim. [disputed by the checker]" in marked
assert "not applied: brings in requirement words" in marked
assert "| wide blip lane | 36 inches [corrected] |" in marked and "| wide blip lane | 36 inches |" in clean
assert "Section 9Z.09 Standard §1 (p.99) [citation not found in evidence]" in marked
assert "[" not in clean.split("Additional points")[0].replace("[Picture 2]", "")        # no marks in the clean one
assert clean.index("Additional points from the evidence:") < clean.index("Citations:")
assert "- An Option (Section 9Z.01, paragraph 5) lets zorb markers be white under 20 mph.\n" in clean + "\n"
assert "§5)" not in clean and "green on Sundays" not in marked                   # the section is not named twice
assert "Additional points" not in corr_only and corr_only in clean.replace(
    clean[clean.index("Additional points") - 2:clean.index("Citations:")], "\n\n") + "\n"
for keep in ("Direct Answer: No. The zorb marker must be at least 30 inches wide", "Guidance (recommended):",
             "Table 9Z-1 (p.14)"):
    assert keep in marked and keep in clean, keep
assert counts == {"statements": 9, "checked": 1, "checked_image": 0, "corrected": 4, "row_corrections": 0,
                  "disputed": 1, "unconfirmed": 3, "unjudged": 0, "no_claim": 0, "arithmetic_flags": 0,
                  "citations_not_in_evidence": 1, "additions": 1}, counts
assert marked.rstrip().endswith("1 addition.") and "5 of 9 statements checked" in marked
# a row correction that is not a row: the marked answer keeps the row and lists it; the clean one
# drops the row and gives the correction just after the table
sent = {"statements": [{"n": 9, "verdict": "CONTRADICTED", "sources": [src("Table 9Z-1", "Minimum zorb width: 36 inches")],
                        "correction": "Table 9Z-1 gives 36 inches for a wide blip lane."}], "additions": []}
m2, c2, k2, _ = core.assemble(DRAFT, st, core.read_reply(sent, st, IDX, QUESTION), [], IDX, "checker-x")
assert "| wide blip lane | 30 inches [corrected below] |" in m2 and k2["row_corrections"] == 1
assert "Corrections to table rows (applied in the clean answer):\n- Table 9Z-1 gives 36 inches" in m2
assert "30 inches" not in c2.split("Citations:")[0].split("Direct Answer")[1].replace("at least 30 inches", "")
assert "| Lane | Width |\n|---|---|\n\nTable 9Z-1 gives 36 inches for a wide blip lane.\n\nCitations:" in c2
# statements the checker never judged are marked apart, with the reason
m3, _, k3, _ = core.assemble(DRAFT, st, core.read_reply({"statements": [REPLY["statements"][0]]}, st, IDX), [],
                             IDX, "checker-x", [2, 3], "the checker's reply stopped with refusal")
assert k3["unjudged"] == 2 and k3["unconfirmed"] == 6
assert "Zorb markers shall be blue. [not judged]" in m3 and "2 not judged (the checker's reply stopped with refusal)" in m3
# a table at the very end of the answer, its last row corrected as a sentence: one blank line before it
DE = "Direct Answer: No. It fails here.\n\n| Lane | Width |\n|---|---|\n| wide blip lane | 30 inches |"
ste = core.split_statements(DE)
fixe = {"statements": [{"n": 3, "verdict": "CONTRADICTED", "sources": [src("Table 9Z-1", "Minimum zorb width: 36 inches")],
                        "correction": "Table 9Z-1 gives 36 inches for a wide blip lane."}]}
ce = core.assemble(DE, ste, core.read_reply(fixe, ste, IDX, QUESTION), [], IDX, "x")[1]
assert ce.endswith("|---|---|\n\nTable 9Z-1 gives 36 inches for a wide blip lane."), repr(ce)
DRN = DRAFT.replace("\n", "\r\n")
stn = core.split_statements(DRN)
m4, c4, _, o4 = core.assemble(DRN, stn, core.read_reply(sent, stn, IDX, QUESTION), [], IDX, "checker-x")
for t in (m4, c4, o4):
    assert "\n" not in t.replace("\r\n", ""), "one kind of line ending"
print("5. marked, clean and corrections-only answers: corrections in place (a row when it is a row),"
      " disputes kept and listed, unjudged marked apart")


# ---- 6. one question, start to finish, using a stand-in checker ----------------------
class FakeAsk:
    def __init__(self, replies):
        self.replies, self.calls, self.last, self.prompts = list(replies), [], None, []

    def __call__(self, prompt, images=None):
        self.prompts.append((prompt, list(images or [])))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        text, stop = r if isinstance(r, tuple) else (r, "end_turn")
        self.last = {"cached": False, "finish_reason": stop, "usage": {"input_tokens": 1000, "output_tokens": 100}}
        self.calls.append(self.last)
        return text


class FakeChecker:
    model = "checker-x"

    def __init__(self, replies):
        self.a = FakeAsk(replies)

    def ask(self):
        return self.a

    @staticmethod
    def cost_usd(calls, model):
        return round(sum(c["usage"]["input_tokens"] * 2 + c["usage"]["output_tokens"] * 10 for c in calls) / 1e6, 6)


draft = {"answer": DRAFT, "model_id": "writer-y", "prompt_sha256": "p", "images": ["/nonexistent/table_9Z-1.png"]}
fc = FakeChecker(["```json\n" + json.dumps(REPLY) + "\n```"])
rec = check.check_one("Z1", QUESTION, ENTRY, draft, fc, True)
assert rec["status"] == "checked" and rec["counts"]["corrected"] == 4 and rec["cost_usd"] == 0.003
assert rec["counts"]["checked_image"] == 0          # no image file was found, so nothing counts as read from one
prompt = fc.a.prompts[0][0]
assert "[MUTCD11e_9Z01_Option_05] Section 9Z.01 paragraph 5" in prompt and "On blip lanes signed for under 20 mph" in prompt
assert "[S1] (Direct Answer)" in prompt and "Check all 9 statements" in prompt
assert rec["images_missing"] == ["/nonexistent/table_9Z-1.png"] and fc.a.prompts[0][1] == []
assert "[corrected]" not in rec["final_answer_clean"] and "[corrected]" in rec["final_answer"]
# cut off at the token limit: the statements are asked for in halves, the additions with the second half
half1 = {"statements": [x for x in REPLY["statements"] if x["n"] in (1, 2, 3, 4)]
         + [{"n": 7, "verdict": "SUPPORTED", "sources": [S1]}], "additions": REPLY["additions"]}   # 7 not asked
half2 = {"statements": [x for x in REPLY["statements"] if x["n"] not in (1, 2, 3, 4)], "additions": REPLY["additions"]}
fc = FakeChecker([("{\"statements\": [", "max_tokens"), json.dumps(half1), json.dumps(half2)])
rec = check.check_one("Z1", QUESTION, ENTRY, draft, fc, True)
assert rec["status"] == "checked" and len(fc.a.prompts) == 3 and rec["unjudged"] == []
assert "Judge ONLY statements [S1] to [S4]" in fc.a.prompts[1][0] and '"additions": [] in this reply' in fc.a.prompts[1][0]
assert "Judge ONLY statements [S5] to [S9]" in fc.a.prompts[2][0] and len(rec["additions"]) == 1
assert rec["counts"]["corrected"] == 4
half2s = {"statements": [dict(x, n=f"S0{x['n']}" if x["n"] == 9 else x["n"]) for x in half2["statements"]],
          "additions": []}
fc = FakeChecker([("x", "max_tokens"), json.dumps(half1), json.dumps(half2s)])
rec = check.check_one("Z1", QUESTION, ENTRY, draft, fc, True)
assert {r["n"]: r["outcome"] for r in rec["statements"]}[9] == "corrected" and rec["unjudged"] == []
fc = FakeChecker([("x", "max_tokens"), json.dumps(half1), ("x", "model_context_window_exceeded")])
rec = check.check_one("Z1", QUESTION, ENTRY, draft, fc, True)            # the second half hits the context limit
assert rec["status"] == "checked" and len(fc.a.prompts) == 3 and rec["unjudged"] == [5, 6, 7, 8, 9]
assert rec["counts"]["unconfirmed"] == 1 and rec["counts"]["unjudged"] == 5 and rec["additions"] == []
assert "model_context_window_exceeded" in rec["unjudged_why"] and "5 not judged" in rec["final_answer"]
assert core._numbers("1,000 feet, 4.0 ft, Section 9Z.01 \u00a7 5, Table 2B-1, (p.12), 36 inches") == {"1000", "4", "36"}
fc = FakeChecker(["not json", "still not json"])
rec = check.check_one("Z1", "Q?", ENTRY, draft, fc, True)
assert rec["status"] == "unchecked" and rec["final_answer"].startswith(DRAFT.rstrip()) and len(fc.a.prompts) == 2
assert fc.a.prompts[1][0].endswith(check.REASK_NOTE) and rec["final_answer_clean"] == DRAFT
fc = FakeChecker(["not json", json.dumps(REPLY)])
assert check.check_one("Z1", QUESTION, ENTRY, draft, fc, True)["status"] == "checked"
for stop in ("refusal", "model_context_window_exceeded"):
    fc = FakeChecker([("", stop)])
    rec = check.check_one("Z1", "Q?", ENTRY, draft, fc, True)
    assert rec["status"] == "unchecked" and len(fc.a.prompts) == 1 and stop in rec["reason"]
fc = FakeChecker([RuntimeError("the API could not be reached")])
rec = check.check_one("Z1", "Q?", ENTRY, draft, fc, True)
assert rec["status"] == "unchecked" and "Verification: not run" in rec["final_answer"]
fc = FakeChecker(["A fallback answer from the evidence."])
rec = check.check_one("Z1", "Q?", ENTRY, None, fc, True)
assert rec["status"] == "fallback" and "not independently checked" in rec["final_answer"] and "draft" not in rec
assert rec["final_answer_corrections_only"] == "A fallback answer from the evidence."
assert check.check_one("Z1", "Q?", ENTRY, None, FakeChecker([]), False)["status"] == "no_answer"
assert check.check_one("Z1", "Q?", ENTRY, {"answer": "Plain:\n", "model_id": "w"}, FakeChecker([]), True)["status"] == "unchecked"
print("6. one question: checked; cut-off replies split in halves; unreadable reply asked once more;"
      " refusal, context limit, API failure and no draft all still answer")

# ---- 7. the whole stage, twice, from files -----------------------------------------
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    kq = {"Z1": dict(ENTRY, question="First made-up question?"), "Z2": dict(ENTRY, question="Second one?"),
          "Z3": dict(ENTRY, question="Third one?")}
    (d / "kq.json").write_text(json.dumps(kq))
    qs = {k: v["question"] for k, v in kq.items()}
    (d / "q.json").write_text(json.dumps(qs))
    rows = [dict(draft, question_id=k, question=qs[k], status="ok", kq_file="kq.json") for k in ("Z1", "Z2")]
    rows.append({"question_id": "Z3", "status": "error", "model_id": "writer-y", "kq_file": "kq.json", "answer": ""})
    (d / "drafts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + '{"cut off')
    replies = [json.dumps(REPLY), json.dumps(REPLY), "A fallback answer."]

    def fake_checker(*a, **k):
        return FakeChecker(replies)

    real = check.Checker
    check.Checker = fake_checker
    argv = sys.argv
    try:
        sys.argv = ["check.py", "--kq", str(d / "kq.json"), "--questions", str(d / "q.json"), "--drafts",
                    str(d / "drafts.jsonl"), "--tag", "t", "--out", str(d / "out"), "--workers", "1",
                    "--min-drafts", "0.5"]
        assert check.main() == 0
        recs = [json.loads(x) for x in (d / "out" / "final.jsonl").read_text().splitlines()]
        assert sorted(r["status"] for r in recs) == ["checked", "checked", "fallback"]
        md = (d / "out" / "answers_final.md").read_text()
        assert md.count("### Z") == 3 and "[corrected]" in md
        cl = (d / "out" / "answers_final_clean.md").read_text()
        assert cl.count("### Z") == 3 and "[corrected]" not in cl and "A fallback answer." in cl
        co = (d / "out" / "answers_final_corrections_only.md").read_text()
        assert co.count("### Z") == 3 and "Additional points" not in co
        dr = (d / "out" / "answers_draft.md").read_text()
        assert "### Z3\n\n(no writer draft)" in dr and "A fallback answer." not in dr
        man = json.loads((d / "out" / "manifest.json").read_text())
        assert man["statuses"] == {"checked": 2, "fallback": 1} and man["writer"] == "writer-y"
        assert man["not_checked"] == {"fallback": ["Z3"]} and man["with_statements_not_judged"] == []
        assert man["checker_cost_usd_all_runs"] == 0.01
        replies[:] = []                                  # a second run must ask nothing
        assert check.main() == 0 and len((d / "out" / "final.jsonl").read_text().splitlines()) == 3
        sys.argv += ["--effort", "low"]                  # other checker settings: everything again
        replies[:] = [json.dumps(REPLY), json.dumps(REPLY), "A fallback answer."]
        assert check.main() == 0 and len((d / "out" / "final.jsonl").read_text().splitlines()) == 6
        assert json.loads((d / "out" / "manifest.json").read_text())["checker_cost_usd_all_runs"] == 0.02
        # a question whose last record left statements unjudged is asked again; --only keeps every
        # question in the answer files
        last = [json.loads(x) for x in (d / "out" / "final.jsonl").read_text().splitlines()]
        z1 = next(r for r in reversed(last) if r["question_id"] == "Z1")
        with (d / "out" / "final.jsonl").open("a") as w:
            w.write(json.dumps(dict(z1, unjudged=[3])) + "\n")
        replies[:] = [json.dumps(REPLY)]
        assert check.main() == 0
        last = [json.loads(x) for x in (d / "out" / "final.jsonl").read_text().splitlines()]
        assert len(last) == 8 and last[-1]["question_id"] == "Z1" and last[-1]["unjudged"] == []
        replies[:] = []
        assert check.main() == 0                         # nothing left to ask
        only = sys.argv + ["--only", "Z2"]
        sys.argv, argv_all = only, sys.argv
        assert check.main() == 0 and (d / "out" / "answers_final.md").read_text().count("### Z") == 3
        assert json.loads((d / "out" / "manifest.json").read_text())["checked_this_run"] == ["Z2"]
        sys.argv = only[:only.index("--out") + 1] + [str(d / "out6")] + only[only.index("--out") + 2:]
        replies[:] = [json.dumps(REPLY)]
        assert check.main() == 0
        d6 = (d / "out6" / "answers_draft.md").read_text()
        assert d6.count(DRAFT.strip()) == 2 and "### Z3\n\n(no writer draft)" in d6
        sys.argv = argv_all
        # a failed try after a checked answer: the checked answer stays in the files, and is asked again
        last = [json.loads(x) for x in (d / "out" / "final.jsonl").read_text().splitlines()]
        z1 = next(r for r in reversed(last) if r["question_id"] == "Z1")
        with (d / "out" / "final.jsonl").open("a") as w:
            w.write(json.dumps(dict(z1, status="unchecked", final_answer="X", unjudged=[])) + "\n")
        replies[:] = ["not json", "still not json"]
        assert check.main() == 1
        md = (d / "out" / "answers_final.md").read_text()
        assert "[corrected]" in md.split("### Z1")[1].split("### Z2")[0]
        replies[:] = [json.dumps(REPLY)]
        assert check.main() == 0
        # drafts to another question text with the same id (an old file): stopped
        (d / "drafts5.jsonl").write_text(json.dumps(dict(rows[0], question="Another question?")) + "\n")
        sys.argv = sys.argv[:6] + [str(d / "drafts5.jsonl"), "--tag", "t5", "--out", str(d / "out5")]
        try:
            check.main()
            raise AssertionError("drafts to another question text must stop the run")
        except SystemExit as e:
            assert "another question text" in str(e)
        # the writer stage failed for most questions: stop, do not answer everything with the checker
        (d / "drafts2.jsonl").write_text(json.dumps(rows[0]) + "\n")
        sys.argv = sys.argv[:6] + [str(d / "drafts2.jsonl"), "--tag", "t2", "--out", str(d / "out2")]  # noqa
        assert check.main() == 1 and not (d / "out2" / "final.jsonl").exists()
        # drafts by two models, or by the checker model itself: refused
        (d / "drafts3.jsonl").write_text(json.dumps(dict(rows[0], model_id="checker-x")) + "\n"
                                         + json.dumps(rows[1]) + "\n")
        sys.argv[6] = str(d / "drafts3.jsonl")
        try:
            check.main()
            raise AssertionError("two writer models must stop the run")
        except SystemExit as e:
            assert "several models" in str(e)
        (d / "drafts4.jsonl").write_text(json.dumps(dict(rows[0], model_id="claude-sonnet-5-5")) + "\n")
        sys.argv[6] = str(d / "drafts4.jsonl")
        try:
            check.main()
            raise AssertionError("drafts by the checker model must stop the run")
        except SystemExit as e:
            assert "checker model itself" in str(e)
    finally:
        check.Checker = real
        sys.argv = argv
print("7. the stage from files: resumable, unjudged asked again, --only keeps every answer, settings in the"
      " resume key, cost over all runs, stops if the writer failed or the drafts answer other questions")
print("\nall vine2 checks passed")
