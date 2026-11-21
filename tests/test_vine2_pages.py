"""VINE answer-then-check on VisRAG's pages (vine2/visrag_pages.py, pages_writer.py,
run_qwen_pages.py and the page parts of core.py and check.py): offline tests.

Every page, rule and answer here is invented ("zorb markers on blip lanes"). Nothing comes
from a benchmark question or its answer. No GPU, no API, no data files, no PDF.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from vine2 import check, core, visrag_pages  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="vine2_pages_"))
PAGE_TEXT = {
    130: "9Z.01 Zorb Markers\nStandard:\n01 Zorb markers shall be at least 30 inches wide on blip lanes.\n"
         "Guidance:\n02 Zorb markers should stand at least 6 feet back from the blip lane rim.\n",
    131: "Option:\n03 On blip lanes signed for under 20 mph, zorb markers may be white.\n"
         "Support:\n04 Zorb markers help riders see the blip lane rim at night.\n",
    140: "Table 9Z-1. Minimum Zorb Sizes\nLane type   Minimum zorb width\nWide blip lane   36 inches\n",
}
PNG = {}
for n in PAGE_TEXT:
    PNG[n] = TMP / f"page_{n:04d}.png"
    PNG[n].write_bytes(b"\x89PNG\r\n\x1a\nfake")
QUESTION = "A zorb marker 24 inches wide is proposed on a blip lane. Is that acceptable?"
QS = {"Z1": QUESTION}


def fake_page_files(top, pages_dir):
    return [{**t, "image_path": str(PNG[int(t["page_pdf"])]), "form": "png"} for t in top]


# ---- 1. the page evidence: VisRAG's pages, their words, nothing else ------------------
import hashlib  # noqa: E402
ranked = {"Z1": {"question_id": "Z1", "question_sha256": hashlib.sha256(QUESTION.encode()).hexdigest(),
                 "top_pages": [{"rank": 1, "page_pdf": 130, "page_printed": "120", "score": 0.9},
                               {"rank": 2, "page_pdf": 140, "page_printed": "130", "score": 0.8},
                               {"rank": 3, "page_pdf": 131, "page_printed": "121", "score": 0.7}]}}
ev = visrag_pages.build(QS, ranked, lambda n: "  " + PAGE_TEXT[n] + "\n\n\n  \n", TMP, 3, 2, fake_page_files)
E = ev["Z1"]
assert [c["chunk_id"] for c in E["chunks"]] == ["Page 120", "Page 130", "Page 121"]        # VisRAG's order
assert all(set(c) <= {"chunk_id", "source", "content_type", "page_pdf", "page_printed", "text", "visrag_rank",
                      "visrag_score", "image_path", "image_form"} for c in E["chunks"])
assert all(c["source"] == "visrag_page" and c["content_type"] == "Page" for c in E["chunks"])     # no type, no section
assert not any(k in c for c in E["chunks"] for k in ("section_id", "ordinal", "section_title", "authority"))
assert E["chunks"][0]["text"] == PAGE_TEXT[130].strip() and E["figures"] == []
assert [bool(c.get("image_path")) for c in E["chunks"]] == [True, True, False]          # the first 2 as pictures
for bad, why in [({"Z1": dict(ranked["Z1"], question_sha256="0" * 64)}, "different question text"),
                 ({}, "no VisRAG retrieval")]:
    try:
        visrag_pages.build(QS, bad, lambda n: PAGE_TEXT[n], TMP, 3, 2, fake_page_files)
        raise AssertionError("must stop")
    except SystemExit as e:
        assert why in str(e), e
blank = visrag_pages.build(QS, ranked, lambda n: "   \n " if n == 140 else PAGE_TEXT[n], TMP, 3, 2, fake_page_files)
assert blank["Z1"]["chunks"][1]["text"] == "" and blank["Z1"]["chunks"][1]["image_path"]   # a drawing page stays
try:
    visrag_pages.build(QS, ranked, lambda n: PAGE_TEXT[n], TMP, 5, 2, fake_page_files)
    raise AssertionError("fewer pages than asked must stop")
except SystemExit as e:
    assert "kept 3 pages" in str(e)
dup = {"Z1": dict(ranked["Z1"], top_pages=[dict(p, page_printed="7") for p in ranked["Z1"]["top_pages"]])}
assert [c["chunk_id"] for c in visrag_pages.build(QS, dup, lambda n: PAGE_TEXT[n], TMP, 3, 0, fake_page_files)
        ["Z1"]["chunks"]] == ["Page 7", "Page 7 (PDF page 140)", "Page 7 (PDF page 131)"]
from vine2 import pages_writer  # noqa: E402
assert [p["page_printed"] for p in pages_writer.pictures(visrag_pages.build(QS, dup, lambda n: PAGE_TEXT[n], TMP, 3, 2,
        fake_page_files)["Z1"])[0]] == ["7", "7 (PDF page 140)"]            # each picture named as its page's text
print("1. page evidence: VisRAG's pages in its order, their words only, the first ones as pictures")

# ---- 2. the checker's view of pages ------------------------------------------------------
ids = check.image_ids(E, [str(PNG[130]), str(PNG[140])])
assert ids == ["Page 120", "Page 130"]
assert check.image_list(E, None) == [str(PNG[130]), str(PNG[140])]
IDX = core.evidence_index(E, ids)
assert IDX["Page 120"]["page"] and IDX["Page 120"]["image"] and not IDX["Page 121"]["image"]
assert IDX["Page 121"]["kind"] == "Page"
block = core.evidence_block(E)
assert block.startswith("=== Pages ===\n[Page 120]\n9Z.01 Zorb Markers") and "Section" not in block.split("[Page 121]")[0][:20]
prompt = core.checker_prompt(QUESTION, E, core.split_statements("Direct Answer: No. It is too narrow.\n"), ids)
assert "The evidence here is whole manual pages" in prompt
assert "whole manual pages" not in core.checker_prompt(QUESTION, {"chunks": [], "figures": []},
                                                       core.split_statements("No. It is.\n"), [])
V = core.verify_quote
assert V("Zorb markers shall be at least 30 inches wide", "Page 120", IDX)["verified"] == "text"
assert V("zorb markers may be white", "Page 120", IDX)["id"] == "Page 121"               # found on the other page
assert V("the drawing shows a zorb in red", "Page 120", IDX)["verified"] == "image"     # its picture was attached
assert V("the drawing shows a zorb in red", "Page 121", IDX)["verified"] is False       # no picture of it
print("2. the checker: page ids, pictures attached by page, quotes found in a page's words")

# ---- 3. the code's checks on pages: force and type from the quote's own words ----------
DRAFT = ("Direct Answer: No. The zorb marker must be at least 30 inches wide.\n\nRules:\n"
         "- Zorb markers may stand 6 feet back from the rim.\n- The width rule is Guidance.\n"
         "- White zorb markers are never allowed.\n")
st = core.split_statements(DRAFT)
src = lambda i, q: {"id": i, "quote": q}  # noqa: E731
P_SHALL = src("Page 120", "Zorb markers shall be at least 30 inches wide on blip lanes")
P_SHOULD = src("Page 120", "Zorb markers should stand at least 6 feet back from the blip lane rim")
P_MAY = src("Page 121", "zorb markers may be white")
reply = {"statements": [
    {"n": 1, "verdict": "SUPPORTED", "sources": [P_SHALL]},
    {"n": 2, "verdict": "CONTRADICTED", "sources": [P_SHOULD],
     "correction": "Zorb markers should stand at least 6 feet back from the blip lane rim."},
    {"n": 3, "verdict": "CONTRADICTED", "sources": [P_SHALL], "correction": "The width rule is a Standard."},
    {"n": 4, "verdict": "CONTRADICTED", "sources": [src("Page 121", "On blip lanes signed for under 20 mph, zorb markers may be white")],
     "correction": "White zorb markers are permitted on lanes signed for under 20 mph."}],
    "additions": [
        {"text": "A Guidance in Section 9Z.01 says zorb markers should stand 6 feet back from the rim.",
         "sources": [P_SHOULD]},
        {"text": "A Standard says zorb markers may be white on lanes signed for under 20 mph.",
         "sources": [src("Page 121", "On blip lanes signed for under 20 mph, zorb markers may be white")]},
        {"text": "Zorb markers help riders see the blip lane rim at night, as Support.",
         "sources": [src("Page 121", "Zorb markers help riders see the blip lane rim at night")]}]}
chk = core.read_reply(reply, st, IDX, QUESTION)
out = {r["n"]: r["outcome"] for r in chk["statements"]}
assert out == {1: "checked", 2: "corrected", 3: "corrected", 4: "disputed"}, chk["statements"]
assert "negation" in chk["statements"][3]["not_applied_because"]       # "never allowed" turned round, one page
assert [a["text"][:12] for a in chk["additions"]] == ["Zorb markers"]                 # Support: a quote with no force word
assert [x["rejected_because"][:14] for x in chk["additions_rejected"]] == ["it repeats a s", "it names a pro"]
assert "standard" in chk["additions_rejected"][1]["rejected_because"]                   # "Standard" under "Option:"
bad = {"statements": [{"n": 2, "verdict": "CONTRADICTED", "sources": [P_SHOULD],
                       "correction": "Zorb markers shall stand at least 6 feet back from the blip lane rim."}]}
r2 = core.read_reply(bad, st, IDX, QUESTION)["statements"][1]
assert r2["outcome"] == "disputed" and "shall" in r2["not_applied_because"]             # "shall" from a "should"
m, c, k, co = core.assemble(DRAFT, st, chk, core.citation_checks(st, IDX), IDX, "checker-x")
assert "at night, as Support. (Page 121)" in c                                      # cited by its page
# the review's cases: numbers from the quote only; a page's type from its own printed heading; broken words
PT = {"chunk_id": "Page 50", "source": "visrag_page", "text":
      "Standard:\n01 Zorb markers are placed 30 inches from the rim on narrow lanes.\n"
      "Table 9Z-2. Wide blip lane 36 inches\nGuidance:\n02 The right-of-\nway near zorbs should be kept clear of "
      "require-\nments for paint.\n"}
E2 = {"question": QUESTION, "chunks": [PT], "figures": []}
I2 = core.evidence_index(E2, [])
st2 = core.split_statements("Rules:\n- Zorb markers are placed 24 inches from the rim on narrow lanes.\n")
Q30 = src("Page 50", "Zorb markers are placed 30 inches from the rim")
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [Q30],
                     "correction": "Zorb markers are placed 36 inches from the rim on narrow lanes."}]}, st2, I2, QUESTION)
assert r["statements"][0]["outcome"] == "disputed" and "36" in r["statements"][0]["not_applied_because"]
r = core.read_reply({"statements": [], "additions": [
    {"text": "A Standard places zorb markers 30 inches from the rim on narrow lanes.", "sources": [Q30]},
    {"text": "Support text places zorb markers 30 inches from the rim on narrow lanes.", "sources": [Q30]}]},
    st2, I2, QUESTION)
assert [a["text"][:10] for a in r["additions"]] == ["A Standard"], r                 # its heading on the page
assert "support" in r["additions_rejected"][0]["rejected_because"]
st5 = core.split_statements("Rules:\n- Zorb markers can be placed 24 inches from the rim on narrow lanes.\n")
r = core.read_reply({"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [Q30],
                     "correction": "Zorb markers shall be placed 30 inches from the rim on narrow lanes."}]}, st5, I2, QUESTION)
assert r["statements"][0]["outcome"] == "corrected"            # "shall" backed by the page's "Standard:" heading
assert core._page_types("should be kept clear of requirements for paint", I2["Page 50"]) == {"guidance"}
assert core.verify_quote("The right-of-way near zorbs should be kept clear", "Page 50", I2)["verified"] == "text"
assert core.verify_quote("should be kept clear of requirements for paint", "Page 50", I2)["verified"] == "text"
I3 = core.evidence_index(E2, ["Page 50"])                                   # its picture attached
assert core.verify_quote("Zorb markers are placed 31 inches from the rim", "Page 50", I3)["verified"] is False
assert core.verify_quote("the drawing shows a red zorb beside the curb", "Page 50", I3)["verified"] == "image"
print("3. code checks on pages: requirement words and types from the quote's own words")

# ---- 4. one question from start to finish, with a stand-in checker ---------------------------------
class FakeAsk:
    def __init__(self, replies):
        self.replies, self.calls, self.last, self.prompts = list(replies), [], None, []

    def __call__(self, prompt, images=None):
        self.prompts.append((prompt, list(images or [])))
        text = self.replies.pop(0)
        self.last = {"cached": False, "finish_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 1}}
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
        return 0.0


draft = {"answer": DRAFT, "model_id": "writer-y", "images": [str(PNG[130]), str(PNG[140])]}
fc = FakeChecker([json.dumps(reply)])
rec = check.check_one("Z1", QUESTION, E, draft, fc, True)
assert rec["status"] == "checked" and rec["counts"]["corrected"] == 2
assert fc.a.prompts[0][1] == [str(PNG[130]), str(PNG[140])]
assert "Attached images, in order: Page 120, Page 130." in fc.a.prompts[0][0]
fc = FakeChecker(["A fallback answer from the pages."])
rec = check.check_one("Z1", QUESTION, E, None, fc, True)
assert rec["status"] == "fallback" and fc.a.prompts[0][1] == [str(PNG[130]), str(PNG[140])]
assert "[Page 121]" in fc.a.prompts[0][0]
print("4. one question: checked from pages, the same pictures as the writer; the fallback sees the pages")

# ---- 5. the writer's prompt: GEMS-RAG's, the pages whole, cited as pages ------------------
os.environ.setdefault("SCRATCH", str(TMP))
(TMP / "Beyond_RAG" / "gems_rag").mkdir(parents=True, exist_ok=True)
os.environ["MRAG_ENV"] = "hprc"
os.environ["MRAG_BASE_DIR"] = str(Path(os.environ["SCRATCH"]) / "Beyond_RAG" / "gems_rag")
sys.path.insert(0, str(ROOT / "gems_rag"))
from mrag.config import CFG  # noqa: E402
from mrag.vlm import VLM  # noqa: E402
from vine2 import pages_writer  # noqa: E402
CFG.set_answer_style("fewshot")
CFG.set_vlm_model("Qwen/Qwen3.8-27B-FP8")
PV = pages_writer.pages_vlm(VLM)
vlm = PV(CFG.vlm_model, CFG.vlm_model_fallback)
pics, missing = pages_writer.pictures(E)
assert missing == [] and [p["page_printed"] for p in pics] == ["120", "130"]
prompt, images = vlm._build_prompt_and_images(QUESTION, E["chunks"], [], pics)
assert images == [str(PNG[130]), str(PNG[140])]
assert "[Page 120]\n9Z.01 Zorb Markers\nStandard:" in prompt and "[Page 121]\nOption:" in prompt
assert "[Image 1] Page 120 (full page view)" in prompt and "[Image 2] Page 130 (full page view)" in prompt
assert prompt.count("Zorb markers should stand at least 6 feet back") == 1                # each page whole, once
assert "Section None" not in prompt and "§" not in prompt.split("Text evidence")[-1][:3000]
base, _ = VLM(CFG.vlm_model, CFG.vlm_model_fallback)._build_prompt_and_images(QUESTION, [], [], pics)
head = prompt[:prompt.index("Text evidence")] if "Text evidence" in prompt else prompt[:500]
assert head[:400] == base[:400]                                                             # GEMS-RAG's own instructions
long_page = {"chunk_id": "Page 9", "text": "zorb " * 1500 + "LAST WORDS"}
assert pages_writer.page_text_block([long_page]).endswith("LAST WORDS")                  # a page is never cut
print("5. the writer: GEMS-RAG's prompt, each page whole, the first pages as GEMS-RAG's page pictures")

# ---- 6. stage A: run_qwen_rag.py unchanged, its writer swapped for the page writer --------
from vine2 import run_qwen_pages  # noqa: E402
stub = TMP / "stub_writer.py"
stub.write_text("import sys; print('PAGE WRITER', ' '.join(sys.argv[1:]))\n")
run_qwen_pages.WRITER = stub
sp = run_qwen_pages._Subprocess()
r = sp.run([sys.executable, "-u", str(run_qwen_pages.OLD_WRITER), "--kq", "K", "--only", "Z1"],
           capture_output=True, text=True)
assert r.stdout.strip() == "PAGE WRITER --kq K --only Z1" and run_qwen_pages._Subprocess.swapped == 1
r = sp.run([sys.executable, "-c", "print('other')"], capture_output=True, text=True)
assert r.stdout.strip() == "other" and sp.STDOUT == subprocess.STDOUT and sp.SubprocessError is subprocess.SubprocessError
src_rq = (ROOT / "compare40" / "run_qwen_rag.py").read_text()
assert src_rq.count('str(HERE / "run_vine_rag.py")') == 1 and "subprocess.run(cmd" in src_rq   # the one call swapped
print("6. stage A: the Qwen runner unchanged; only its writer command points at the page writer")
print("\nall vine2 page checks passed")
