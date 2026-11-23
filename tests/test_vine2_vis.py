"""VINE answer-then-check on M3DocRAG's, ViDoRAG's and RegionRAG's retrieval (vine2/vis_*.py,
the three *_retrieve.py scripts, vidorag_ocr.py, and the page and region parts of core.py and
pages_writer.py): offline tests.

Every page, rule and answer here is invented ("zorb markers on blip lanes"). Nothing comes
from a benchmark question or its answer. No GPU, no API, no model, no PDF: each system's
model and the PDF are replaced by small stand-ins; the systems' own small functions are used
where they are plain Python (M3DocRAG's get_top_k_pages, if its code copy is found).
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vine2"))
sys.dont_write_bytecode = True
from vine2 import check, core, pages_writer, vis_common as vc, vis_evidence  # noqa: E402
import m3docrag_retrieve as m3  # noqa: E402
import regionrag_retrieve as rr  # noqa: E402
import vidorag_ocr as vo  # noqa: E402
import vidorag_retrieve as vr  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="vine2_vis_"))
QUESTION = "A zorb marker 24 inches wide is proposed on a blip lane. Is that acceptable?"
QS = {"Z1": QUESTION}
SHA = hashlib.sha256(QUESTION.encode()).hexdigest()
WORDS = {
    130: "9Z.01 Zorb Markers\nStandard:\n01 Zorb markers shall be at least 30 inches wide on blip lanes.\n",
    131: "Option:\n03 On blip lanes signed for under 20 mph, zorb markers may be white.\n",
    140: "Table 9Z-1. Minimum Zorb Sizes\nWide blip lane   36 inches\n",
}
LABEL = {130: "120", 131: "121", 140: "130"}


def stops(fn, why):
    try:
        fn()
    except SystemExit as e:
        assert why in str(e), (why, str(e))
        return
    raise AssertionError(f"must stop: {why}")


class FakePdf:
    def __init__(self, labels=LABEL):
        self.labels, self.clips = labels, []

    def label(self, n):
        return self.labels[n]

    def words(self, n):
        return "  " + WORDS[n] + "\n\n\n  \n"

    def words_in(self, n, box, size):
        self.clips.append((n, tuple(box), tuple(size)))
        return WORDS[n].split("\n")[int(box[1]) // 100]          # one line, by the box's top


def pic(name):
    p = TMP / name
    p.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return str(p)


def same_files(paths):
    return [(str(p), "png") for p in paths]


def no_crop(*a):
    raise AssertionError("only regions are cut")


# ---- 1. core: the new sources, the region rules, one page = one piece --------------------
assert set(core.PAGE_SOURCES) == {"visrag_page", "m3docrag_page", "vidorag_page", "regionrag_region"}
assert set(pages_writer.SYSTEMS) == set(core.PAGE_SOURCES)
assert set(vis_evidence.SOURCE.values()) | {"visrag_page"} == set(core.PAGE_SOURCES)
assert core.is_region({"source": "regionrag_region"}) and not core.is_region({"source": "m3docrag_page"})
assert not core.is_page({"source": "vine"}) and core.is_page({"source": "vidorag_page"})
st = core.split_statements("Direct Answer: No. It is too narrow.\n")
p_page = core.checker_prompt(QUESTION, {"chunks": [{"chunk_id": "Page 1", "source": "m3docrag_page", "text": "x"}]}, st, [])
p_reg = core.checker_prompt(QUESTION, {"chunks": [{"chunk_id": "Page 1 (region 1)", "source": "regionrag_region",
                                                   "text": "x"}]}, st, [])
assert "whole manual pages" in p_page and "parts of manual pages" not in p_page
assert "parts of manual pages (regions)" in p_reg and "whole manual pages" not in p_reg
assert core._piece("Page 7 (region 2)") == "Page 7" and core._piece("Page 7 (PDF page 11) (region 3)") == "Page 7 (PDF page 11)"
assert core._piece("Page 7 (PDF page 11)") == "Page 7 (PDF page 11)" and core._piece("Page 7") == "Page 7"
# the main answer turned round with two regions of ONE page: one piece, refused; of two pages: allowed
R = {"question": QUESTION, "figures": [], "chunks": [
    {"chunk_id": "Page 120 (region 1)", "source": "regionrag_region", "text": "Zorb markers shall be at least 30 inches wide on blip lanes."},
    {"chunk_id": "Page 120 (region 2)", "source": "regionrag_region", "text": "Zorb markers under 30 inches wide are not allowed on blip lanes."},
    {"chunk_id": "Page 121 (region 1)", "source": "regionrag_region", "text": "Zorb markers under 30 inches wide are not allowed on blip lanes."}]}
IDX = core.evidence_index(R, [])
assert all(IDX[i]["page"] for i in IDX)
st = core.split_statements("Direct Answer: Yes. A 24 inch zorb marker is fine.\n")
src = lambda i, q: {"id": i, "quote": q}  # noqa: E731
flip = lambda a, b: {"statements": [{"n": 1, "verdict": "CONTRADICTED", "sources": [  # noqa: E731
    src(a, "Zorb markers shall be at least 30 inches wide"), src(b, "Zorb markers under 30 inches wide are not allowed")],
    "correction": "No. A zorb marker must be at least 30 inches wide."}]}
assert core.read_reply(flip("Page 120 (region 1)", "Page 120 (region 2)"), st, IDX, QUESTION)["statements"][0]["outcome"] == "disputed"
assert core.read_reply(flip("Page 120 (region 1)", "Page 121 (region 1)"), st, IDX, QUESTION)["statements"][0]["outcome"] == "corrected"
print("1. core: three new sources; regions get their own rules; two regions of one page are one piece")

# ---- 2. the writer: the same for pages, region pictures named as parts of pages ----------
lines = pages_writer.region_visual_lines([("Page", {"page_printed": "120 (region 2)"})])
assert lines == ["[Image 1] Page 120 (region 2) (part of the page)"]


class _VLM:
    def _format_visual_lines(self, used):
        return ["gems"]


assert pages_writer.pages_vlm(_VLM)()._format_visual_lines([]) == ["gems"]               # pages: GEMS-RAG's lines
assert pages_writer.pages_vlm(_VLM, regions=True)()._format_visual_lines([("Page", {"page_printed": "1"})]) == \
    ["[Image 1] Page 1 (part of the page)"]
print("2. the writer: GEMS-RAG's prompt; region pictures are named as parts of a page")

# ---- 3. M3DocRAG's pages: its order, the PDF's words, its first pictures --------------------
P = {n: pic(f"mutcd.pdf_{n}.png") for n in WORDS}
ranked = {"Z1": {"question_id": "Z1", "question_sha256": SHA, "system": "m3docrag", "items": [
    vc.item(1, 130, score=9.1, image_path=P[130]), vc.item(2, 140, score=8.0, image_path=P[140]),
    vc.item(3, 131, score=7.0, image_path=P[131])]}}
ev = vis_evidence.build("m3docrag", QS, ranked, FakePdf(), 3, 2, same_files, no_crop)["Z1"]
assert [c["chunk_id"] for c in ev["chunks"]] == ["Page 120", "Page 130", "Page 121"]
assert all(c["source"] == "m3docrag_page" and c["content_type"] == "Page" for c in ev["chunks"])
assert not any(k in c for c in ev["chunks"] for k in ("section_id", "ordinal", "section_title", "authority", "_picture"))
assert ev["chunks"][0]["text"] == WORDS[130].strip() and ev["figures"] == []
assert [c.get("image_path") for c in ev["chunks"]] == [P[130], P[140], None]
assert check.image_list(ev, None) == [P[130], P[140]] and check.image_ids(ev, [P[130]]) == ["Page 120"]
dup = vis_evidence.build("m3docrag", QS, ranked, FakePdf({130: "7", 131: "7", 140: "7"}), 3, 0, same_files, no_crop)
assert [c["chunk_id"] for c in dup["Z1"]["chunks"]] == ["Page 7", "Page 7 (PDF page 140)", "Page 7 (PDF page 131)"]
stops(lambda: vis_evidence.build("m3docrag", QS, {"Z1": dict(ranked["Z1"], question_sha256="0" * 64)}, FakePdf(), 3, 2,
                                 same_files, no_crop), "different question text")
stops(lambda: vis_evidence.build("m3docrag", QS, {"Z1": dict(ranked["Z1"], system="vidorag")}, FakePdf(), 3, 2,
                                 same_files, no_crop), "not m3docrag")
stops(lambda: vis_evidence.build("m3docrag", QS, ranked, FakePdf(), 5, 2, same_files, no_crop), "kept 3 items")
stops(lambda: vis_evidence.build("m3docrag", QS, {}, FakePdf(), 3, 2, same_files, no_crop), "no m3docrag retrieval")
stops(lambda: vis_evidence.build("m3docrag", QS, {"Z1": dict(ranked["Z1"], items=[dict(ranked["Z1"]["items"][0],
      image_path=str(TMP / "gone.png"))] + ranked["Z1"]["items"][1:])}, FakePdf(), 3, 2, same_files, no_crop), "not found")
print("3. M3DocRAG: its pages in its order, the PDF's words only, its first pictures")

# ---- 4. ViDoRAG's pages: its text as it gave it, its order, pictures by its picture side ---
J = {n: pic(f"MUTCD_{n}.jpg") for n in WORDS}
vid = {"Z1": {"question_id": "Z1", "question_sha256": SHA, "system": "vidorag", "items": [
    vc.item(1, 130, text="Standard: zorbs shall be wide  \n\n\n", image_path=J[130], visual_rank=7),
    vc.item(2, 131, text="Option: zorbs may be white", image_path=J[131], visual_rank=None),
    vc.item(3, 140, text="Table 9Z-1 36 inches", image_path=J[140], visual_rank=2)]}}
ev = vis_evidence.build("vidorag", QS, vid, FakePdf(), 20, 2, same_files, no_crop)["Z1"]
assert [c["chunk_id"] for c in ev["chunks"]] == ["Page 120", "Page 121", "Page 130"]       # ViDoRAG's order
assert ev["chunks"][0]["text"] == "Standard: zorbs shall be wide"                            # its text, cleaned only
assert [bool(c.get("image_path")) for c in ev["chunks"]] == [True, False, True]             # ranks 2 and 7, not None
assert all(c["source"] == "vidorag_page" for c in ev["chunks"])
one = vis_evidence.build("vidorag", QS, vid, FakePdf(), 2, 1, same_files, no_crop)["Z1"]     # PIECES is the most
assert len(one["chunks"]) == 2 and [bool(c.get("image_path")) for c in one["chunks"]] == [True, False]
print("4. ViDoRAG: the pages and OCR text it returned, in its order; pictures by its picture ranks")

# ---- 5. RegionRAG's regions: ids by page, words inside the box, the first ones cut out -----
reg = {"Z1": {"question_id": "Z1", "question_sha256": SHA, "system": "regionrag", "items": [
    vc.item(1, 130, score=0.9, box=[0, 100, 50, 150], image_size=[2000, 1500], image_path=P[130]),
    vc.item(2, 140, score=0.8, box=[0, 0, 50, 50], image_size=[2000, 1500], image_path=P[140]),
    vc.item(3, 130, score=0.7, box=[0, 200, 50, 250], image_size=[2000, 1500], image_path=P[130])]}}
cuts = []


def fake_crop(page_picture, box, name):
    cuts.append((page_picture, tuple(box), name))
    return pic(name)


pdf = FakePdf()
ev = vis_evidence.build("regionrag", QS, reg, pdf, 3, 2, same_files, fake_crop)["Z1"]
assert [c["chunk_id"] for c in ev["chunks"]] == ["Page 120 (region 1)", "Page 130 (region 1)", "Page 120 (region 2)"]
assert [c["text"] for c in ev["chunks"]] == ["Standard:", "Table 9Z-1. Minimum Zorb Sizes", "01 Zorb markers shall be at least 30 inches wide on blip lanes."]
assert pdf.clips[0] == (130, (0, 100, 50, 150), (2000, 1500))
assert [c[2] for c in cuts] == ["Z1_region01.png", "Z1_region02.png"] and cuts[0][0] == P[130]
assert [bool(c.get("image_path")) for c in ev["chunks"]] == [True, True, False]
assert ev["chunks"][0]["page_printed"] == "120 (region 1)" and ev["chunks"][0]["box"] == [0, 100, 50, 150]
assert [p["page_printed"] for p in pages_writer.pictures(ev)[0]] == ["120 (region 1)", "130 (region 1)"]
assert check.image_ids(ev, [ev["chunks"][1]["image_path"]]) == ["Page 130 (region 1)"]


class _Rect:
    x0, y0, width, height = 0.0, 0.0, 600.0, 800.0


class _Page:
    rotation, rect = 0, _Rect()

    def get_text(self, kind, clip=None):
        return f"{kind}:{clip}"


class _Doc:
    page_count = 3

    def load_page(self, i):
        return _Page()


class _Fitz:
    @staticmethod
    def Rect(*a):
        return tuple(round(x, 3) for x in a)


real = vis_evidence.Pdf.__new__(vis_evidence.Pdf)
real.fitz, real.doc, real.n = _Fitz, _Doc(), 3
assert real.words_in(1, [150, 200, 300, 400], [1600, 1200]) == "text:(75.0, 100.0, 150.0, 200.0)"   # pixels -> points
_Page.rotation = 90
stops(lambda: real.words_in(1, [0, 0, 1, 1], [10, 10]), "rotated")
_Page.rotation = 0
print("5. RegionRAG: its regions in its order, named by page, the words inside each box, the first ones cut out")

# ---- 6. the picture-size rule of the VisRAG baseline ---------------------------------------
small, big, jpg = TMP / "s.png", TMP / "b.png", TMP / "j.jpg"
small.write_bytes(b"x" * 10)
big.write_bytes(b"x" * 100)
jpg.write_bytes(b"x" * 500)
to_j = lambda p: Path(str(p) + ".jpg")  # noqa: E731
assert vis_evidence.picture_rule([small, jpg], 50, 10_000, to_j) == [(str(small), "png"), (str(jpg), "jpeg")]
assert vis_evidence.picture_rule([small, big], 50, 10_000, to_j) == [(str(small), "png"), (str(big) + ".jpg", "jpeg")]
assert vis_evidence.picture_rule([small, big], 500, 100, to_j)[0] == (str(small) + ".jpg", "jpeg")   # the set too big
print("6. pictures: a PNG over the size limits goes as JPEG; a JPEG goes as it is")

# ---- 7. the retrieval files: written whole, found again only for the same texts and models -
out = TMP / "retr"
items = {"Z1": ranked["Z1"]["items"]}
vc.write_retrieval(out, "m3docrag", QS, items, {"code_commit": "c1", "models": {"a/b": "r1"}})
assert vc.read_retrieval(out)["Z1"]["items"] == items["Z1"] and vc.read_retrieval(out)["Z1"]["question_sha256"] == SHA
assert vc.retrieval_done(out, "m3docrag", QS, {"code_commit": "c1", "models": {"a/b": "r1"}})
assert not vc.retrieval_done(out, "m3docrag", QS, {"code_commit": "c1", "models": {"a/b": "r2"}})   # other model
assert not vc.retrieval_done(out, "m3docrag", {"Z1": QUESTION + " "}, {"code_commit": "c1"})        # other text
assert not vc.retrieval_done(out, "vidorag", QS, {})                                               # other system
assert not vc.retrieval_done(TMP / "none", "m3docrag", QS, {})
stops(lambda: vc.write_retrieval(out, "m3docrag", {"Z1": QUESTION, "Z2": "Other?"}, items, {}), "nothing for 1")
assert not (out / "retrieval_manifest.json").exists()                  # a stopped write leaves no manifest
qf = TMP / "qs.json"
qf.write_text(json.dumps({"Z1": QUESTION, "gold": {"answer": "x"}}))
stops(lambda: vc.load_questions(qf), "nothing else")
print("7. retrieval files: whole or not at all; reused only for the same system, texts, code and models")

# ---- 8. M3DocRAG's ranking: its own get_top_k_pages over one document ----------------------
ext = Path(os.environ.get("VIS_EXT", os.path.join(os.environ.get("SCRATCH", "/nonexistent"), "vine", "ext")))
if (ext / "m3docrag/src/m3docrag/rag/utils.py").is_file():
    try:
        import tqdm.auto  # noqa: F401  (rag/utils.py imports it; a stand-in where it is not installed)
    except ImportError:
        import types
        sys.modules["tqdm"] = types.ModuleType("tqdm")
        sys.modules["tqdm.auto"] = types.SimpleNamespace(tqdm=lambda x, **k: x)
    top_k = m3.load_top_k(ext / "m3docrag")
    which = "M3DocRAG's own"
else:                                                     # the same function, for a machine without the copy
    def top_k(docid2scores, k):
        flat = [(d, i, s) for d, ss in docid2scores.items() for i, s in enumerate(ss)]
        flat.sort(key=lambda x: x[2], reverse=True)
        return flat[:k]
    which = "a stand-in for M3DocRAG's"
got = m3.rank({"Z1": [0.1, 0.9, 0.5, 0.7]}, top_k, Path("/d/mutcd.pdf"), Path("/pages"), k=3)["Z1"]
assert [(i["rank"], i["page_pdf"]) for i in got] == [(1, 2), (2, 4), (3, 3)]
assert got[0]["image_path"] == "/pages/mutcd.pdf_2.png" and got[0]["score"] == 0.9
print(f"8. M3DocRAG: pages ranked by {which} get_top_k_pages; pictures named as its get_images_from_pdf saves them")

# ---- 9. ViDoRAG: its page names, its nodes, the OCR step --------------------------------------
assert vr.page_of("./data/MUTCD/img/MUTCD_12.jpg") == 12 and vr.page_of("MUTCD_7.txt") == 7
for bad in ("MUTCD_x.jpg", "OTHER_3.jpg", "MUTCD_3.pdf"):
    try:
        vr.page_of(bad)
        raise AssertionError(bad)
    except ValueError:
        pass
res = {"source_nodes": [{"node": {"image_path": "./data/MUTCD/img/MUTCD_4.jpg", "text": "four"}},
                        {"node": {"image_path": "./data/MUTCD/img/MUTCD_9.jpg", "text": "nine"}}]}
it = vr.items_of(res, {9: 1})
assert [(i["rank"], i["page_pdf"], i["text"], i["visual_rank"]) for i in it] == [(1, 4, "four", None), (2, 9, "nine", 1)]
assert os.path.isabs(it[0]["image_path"])
try:
    vr.items_of({"source_nodes": res["source_nodes"] * 2}, {})
    raise AssertionError("a page twice must stop")
except ValueError:
    pass
nodes = TMP / "nodes"
nodes.mkdir()
(nodes / "MUTCD_1.node").write_text("[]")
(nodes / "MUTCD_2.node").write_text('[{"text": "cut of')
assert vr.check_nodes(nodes) == 1 and [f.name for f in nodes.iterdir()] == ["MUTCD_1.node"]
calls = []


class _Img:
    def save(self, path, fmt):
        assert fmt == "JPEG"
        Path(path).write_bytes(b"jpg")


def fake_convert(pdf, thread_count, first_page, last_page):
    calls.append((thread_count, first_page, last_page))
    return [_Img() for _ in range(first_page, last_page + 1)]


img = TMP / "w" / "img"
assert vo.render(Path("x.pdf"), img, 120, fake_convert) == 120 and calls == [(4, 1, 50), (4, 51, 100), (4, 101, 120)]
(img / "MUTCD_77.jpg").unlink()
calls.clear()
assert vo.render(Path("x.pdf"), img, 120, fake_convert) == 1 and calls == [(4, 51, 100)]        # only what is missing
assert not list(img.glob(".*part"))
txt = TMP / "w" / "ppocr"
seen = []
assert vo.ocr_all(img, txt, 3, lambda p: seen.append(p) or f"text of {Path(p).name}") == 3
assert (txt / "MUTCD_2.txt").read_text() == "text of MUTCD_2.jpg" and seen[0].endswith("MUTCD_1.jpg")
assert vo.ocr_all(img, txt, 3, lambda p: 1 / 0) == 0                                       # done pages kept
# its models by name, as folders: links to the recorded downloads (PEFT 0.11.1 offline)
hfc = TMP / "hfc"
for repo, rev in (("vidore/colzorb-v1.0", "c" * 40), ("vidore/colzorb-base", "d" * 40)):
    (hfc / f"models--{repo.replace('/', '--')}" / "snapshots" / rev).mkdir(parents=True)
os.environ["HF_HUB_CACHE"] = str(hfc)
revs_l = {"models": {"vidore/colzorb-v1.0": "c" * 40, "vidore/colzorb-base": "d" * 40}}
work = TMP / "vwork"
assert vr.link_models(work, revs_l, ["vidore/colzorb-v1.0", "vidore/colzorb-base"]) == \
    ["vidore/colzorb-v1.0", "vidore/colzorb-base"]
assert (work / "vidore/colzorb-v1.0").resolve() == (hfc / "models--vidore--colzorb-v1.0/snapshots" / ("c" * 40)).resolve()
(work / "vidore/colzorb-base").unlink()
(work / "vidore/colzorb-base").symlink_to(TMP)                         # a stale link is made again
vr.link_models(work, revs_l, ["vidore/colzorb-base"])
assert (work / "vidore/colzorb-base").resolve().name == "d" * 40
(work / "vidore/real").mkdir()
(hfc / "models--vidore--real" / "snapshots" / ("c" * 40)).mkdir(parents=True)
stops(lambda: vr.link_models(work, {"models": {"vidore/real": "c" * 40}}, ["vidore/real"]), "is not a link")
stops(lambda: vr.link_models(work, revs_l, ["../x/y"]), "not a plain")
print("9. ViDoRAG: its file names, its returned pages in order (no repeats), half-written nodes made again, "
      "its pictures and OCR page by page; its models linked by name for offline loading")

# ---- 10. RegionRAG: its regions, page names, collators ----------------------------------------
assert rr.page_of("page_0130.png") == 130
regions = [{"image_id": "page_0130.png", "bounding_box": (0, 100, 50.5, 150), "score": 0.91},
           {"image_id": "page_0140.png", "bounding_box": [1, 2, 3, 4], "score": 0.5}]
it = rr.items_of(regions, {"page_0130.png": (2000, 1500), "page_0140.png": (2000, 1500)}, Path("/p"), k=1)
assert it == [{"rank": 1, "page_pdf": 130, "score": 0.91, "box": [0.0, 100.0, 50.5, 150.0], "image_size": [2000, 1500],
               "image_path": "/p/page_0130.png"}]


class _Proc:
    def process_images(self, images):
        return ("imgs", len(images))

    def process_queries(self, queries):
        return ("qs", list(queries))


class _Im:
    height, width = 20, 10


ids, imgs, sizes = rr.CorpusDataCollator(_Proc())([{"corpus-id": "page_0001.png", "image": _Im()}])
assert ids == ["page_0001.png"] and imgs == ("imgs", 1) and sizes == [(20, 10)]
assert rr.QueryDataCollator(_Proc())([rr.Queries(QS)[0]]) == (["Z1"], ("qs", [QUESTION]))
assert rr.BBOX["bbox_threshold"] == 0.0 and rr.BBOX["bbox_neighbor_range"] == [-1, 0, 1] and rr.TOPKS[-1] == 100
print("10. RegionRAG: its regions in its order with box and picture size; its collators; its default settings")

# ---- 11. the pinned commits are the same everywhere ---------------------------------------
setup = (ROOT / "vine2/vis_setup.sh").read_text()
assert "pinned m3docrag_retrieve.py" in setup and "pinned vidorag_ocr.py" in setup and "pinned regionrag_retrieve.py" in setup
for mod in (m3, vo, rr):
    assert len(mod.PINNED) == 40 and all(ch in "0123456789abcdef" for ch in mod.PINNED)
assert vr.PINNED == vo.PINNED
vsrc = (ROOT / "vine2/vidorag_retrieve.py").read_text()
assert vsrc.index("globals_helper.punkt_tokenizer, globals_helper.stopwords") < vsrc.index("Ingestion(dataset_dir")
assert vsrc.index("Ingestion(dataset_dir") < vsrc.index("emb.get_text_embedding('warm-up')") < vsrc.index("ing.ingestion_multi_session()")
assert "need_files" in setup and 'make_poppler' in setup and '"torch==2.6.0" "torchvision==0.21.0"' in setup
for job in ("vine2/vis_retrieve_job.slurm", "vine2/vidorag_ocr_job.slurm"):
    assert 'export PATH="$VINE_HOME/vis/poppler_bin:$PATH"' in (ROOT / job).read_text(), job
print("11. the pinned code commits: one place each, read by the setup; file-limit check; poppler wrappers")
# ---- 12. the review's safeguards: clean model loads, reused files tied to their inputs -------
import logging  # noqa: E402
import warnings  # noqa: E402
with vc.LoadGuard("fine"):
    logging.getLogger("transformers.modeling_utils").warning("a harmless note")
def _made_up_weights():
    with vc.LoadGuard("ColZorb"):
        logging.getLogger("transformers.modeling_utils").warning(
            "Some weights of ColZorb were not initialized from the model checkpoint and are newly initialized: "
            "['custom_text_proj.weight']")


stops(_made_up_weights, "did not load cleanly")


def _peft_missing():
    with vc.LoadGuard("adapter"):
        warnings.warn("Found missing adapter keys while loading the checkpoint: ['base_model.x.lora_A']")


stops(_peft_missing, "did not load cleanly")


def _transformers_adapter_mismatch():
    with vc.LoadGuard("adapter"):
        logging.getLogger("transformers.integrations.peft").warning(
            "Loading adapter weights from /m led to unexpected keys not found in the model: ['x.lora_B']")


stops(_transformers_adapter_mismatch, "did not load cleanly")
st_dir = TMP / "stamped"
vc.stamp(st_dir, {"pdf_sha256": "aa", "model": "m"})
vc.stamp(st_dir, {"pdf_sha256": "aa", "model": "m"})                  # the same inputs: fine
stops(lambda: vc.stamp(st_dir, {"pdf_sha256": "bb", "model": "m"}), "made from other inputs")
hf = TMP / "hf"
(hf / "models--vidore--colzorb" / "refs").mkdir(parents=True)
(hf / "models--vidore--colzorb" / "snapshots" / ("a" * 40)).mkdir(parents=True)
(hf / "models--vidore--colzorb" / "refs" / "main").write_text("a" * 40)
os.environ["HF_HUB_CACHE"] = str(hf)
assert vc.check_refs({"models": {"vidore/colzorb": "a" * 40}}, ["vidore/colzorb"]) == {"vidore/colzorb": "a" * 40}
stops(lambda: vc.check_refs({"models": {"vidore/colzorb": "b" * 40}}, ["vidore/colzorb"]), "would load commit")
stops(lambda: vc.load_revisions(TMP / "nope.json"), "is missing")
(TMP / "revs.json").write_text(json.dumps({"models": {"x/y": "1"}}))
stops(lambda: vc.load_revisions(TMP / "revs.json", ("x/y", "vidore/colpali-v1.2")), "records no commit")
assert vc.tool_version(["no-such-tool-zorb"]) == "missing"
bigj = TMP / "big.jpg"
bigj.write_bytes(b"x" * 100)
assert vis_evidence.picture_rule([bigj], 50, 10_000, to_j, lambda p: Path(str(p) + ".small.jpg")) == \
    [(str(bigj) + ".small.jpg", "jpeg")]                                # an over-size JPEG goes smaller
print("12. model loads that make up weights stop the job; reused files are tied to their inputs; "
      "models loaded by name must be the recorded commit")
print("\nall vine2 visual-RAG checks passed")
