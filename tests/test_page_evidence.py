"""The pages run (changes_106): VINE reads everything its store holds on the
pages another retriever chose. Made-up questions, pages and pieces only."""
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from mrag.vine import page_evidence as pe  # noqa: E402

QUESTIONS = {"Q1": "Made-up question one about a sign on a pole?",
             "Q2": "Made-up question two about a marking on a road?"}


def _sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _pages_line(qid, pages, text=None, **extra):
    row = {"question_id": qid, "question_sha256": _sha(text if text is not None else QUESTIONS[qid]),
           "top_pages": [{"rank": i + 1, "page_pdf": p, "page_printed": str(p - 41) if isinstance(p, int) else "", "score": round(0.9 - i / 100, 3)}
                         for i, p in enumerate(pages)]}
    row.update(extra)
    return json.dumps(row)


def _write(d, lines, name="retrieval.jsonl"):
    p = Path(d) / name
    p.write_text("\n".join(lines) + "\n")
    return p


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except pe.PagesFileError as e:
        return str(e)
    raise AssertionError("no PagesFileError")


# --------------------------------------------------------------------------- #
# the pages file
# --------------------------------------------------------------------------- #
def test_pages_file_gives_the_top_k_pages_best_first():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, [_pages_line("Q1", [213, 100, 242]), _pages_line("Q2", [50, 51, 52]),
                       _pages_line("Q9", [1, 2, 3], text="a question not in this run")])
        got = pe.read_pages_file(p, QUESTIONS, 2)
        assert sorted(got) == ["Q1", "Q2"]                      # only this run's questions
        assert [x["page_pdf"] for x in got["Q1"]] == [213, 100] and [x["rank"] for x in got["Q1"]] == [1, 2]
        assert got["Q1"][0]["page_printed"] == "172" and got["Q1"][0]["score"] == 0.9


def test_pages_file_ranks_are_read_not_the_line_order():
    with tempfile.TemporaryDirectory() as d:
        row = json.loads(_pages_line("Q1", [213, 100, 242]))
        row["top_pages"] = list(reversed(row["top_pages"]))
        p = _write(d, [json.dumps(row), _pages_line("Q2", [50, 51, 52])])
        assert [x["page_pdf"] for x in pe.read_pages_file(p, QUESTIONS, 3)["Q1"]] == [213, 100, 242]


def test_pages_file_refuses_what_does_not_fit_the_run():
    with tempfile.TemporaryDirectory() as d:
        ok = _pages_line("Q2", [50, 51, 52])
        assert "have no pages" in _raises(pe.read_pages_file, _write(d, [ok]), QUESTIONS, 2)
        changed = _pages_line("Q1", [1, 2, 3], text="another wording of question one")
        assert "different question text" in _raises(pe.read_pages_file, _write(d, [changed, ok]), QUESTIONS, 2)
        short = _pages_line("Q1", [1, 2])
        assert "2 pages saved, 3 asked for" in _raises(pe.read_pages_file, _write(d, [short, ok]), QUESTIONS, 3)
        twice = _pages_line("Q1", [7, 7, 8])
        assert "appears twice" in _raises(pe.read_pages_file, _write(d, [twice, ok]), QUESTIONS, 3)
        dup = _pages_line("Q1", [1, 2, 3])
        assert "appears twice" in _raises(pe.read_pages_file, _write(d, [dup, dup, ok]), QUESTIONS, 2)
        bad = _pages_line("Q1", ["x", 2, 3])
        assert "not a page number" in _raises(pe.read_pages_file, _write(d, [bad, ok]), QUESTIONS, 2)
        assert "at least 1" in _raises(pe.read_pages_file, _write(d, [ok]), QUESTIONS, 0)


def test_pages_file_with_any_field_beyond_the_question_and_pages_is_refused():
    with tempfile.TemporaryDirectory() as d:
        ok = _pages_line("Q2", [50, 51, 52])
        extra = _pages_line("Q1", [1, 2, 3], answer="anything")
        assert "fields other than" in _raises(pe.read_pages_file, _write(d, [extra, ok]), QUESTIONS, 2)
        row = json.loads(_pages_line("Q1", [1, 2, 3]))
        row["top_pages"][0]["note"] = "anything"
        assert "page fields other than" in _raises(pe.read_pages_file, _write(d, [json.dumps(row), ok]), QUESTIONS, 2)


# --------------------------------------------------------------------------- #
# the pieces and figures of the pages
# --------------------------------------------------------------------------- #
def _piece(cid, sec, kind, page, ordinal=None, **kw):
    return {"chunk_id": cid, "section_id": sec, "section_title": f"Title {sec}", "content_type": kind,
            "ordinal": ordinal, "page_pdf": page, "text": f"text of {cid}", "source": "paragraph", **kw}


STORE = [
    _piece("A_S_02", "2A.01", "Standard", 10, 2),
    _piece("A_G_01", "2A.01", "Guidance", 10, 1),
    _piece("B_O_01", "2A.02", "Option", "10", 1),                          # a page held as text
    _piece("C_S_01", "3B.01", "Standard", 20, 1),
    _piece("C_N_01", "3B.01", "Support", 20, None, parent_id="Figure 3B-1", item="1", source="figure_note"),
    _piece("vine:trow:Table 3B-2#s1r0", "3B.01", "TableRow", 20, None, parent_id="figure:Table 3B-2",
           source="vine_graph", graph_node="trow:Table 3B-2#s1r0", table_refs=["Table 3B-2"]),
    _piece("vine:trow:Table 3B-2#s2r0", "3B.01", "TableRow", 20, None, parent_id="figure:Table 3B-2",
           source="vine_graph", graph_node="trow:Table 3B-2#s2r0", table_refs=["Table 3B-2"]),   # its page: 21
    _piece("vine:trow:Table 6Z-1#s1r0", "6Z.01", "TableRow", None, None, parent_id="figure:Table 6Z-1",
           source="vine_graph", graph_node="trow:Table 6Z-1#s1r0"),                             # no page of its own
    _piece("vine:reading:2A-5#0:Figure 2A-5", "2A.01", "FigureReading", 10, None, parent_id="figure:Figure 2A-5",
           source="vine_graph", figure_refs="['Figure 2A-5']", table_refs="[]"),
    _piece("D_S_01", "4A.01", "Standard", 30, 1),
    _piece("E_S_01", "4A.02", "Standard", None, 1),                        # no page: never shown
    _piece("A_S_02", "2A.01", "Standard", 10, 2),                          # the same piece twice
]


# figures.jsonl: one record per sheet
FIGURE_RECORDS = [
    {"figure_id": "Figure 3B-1", "sheet": "None", "page_pdf": "20"},
    {"figure_id": "Table 3B-2", "sheet": 1, "page_pdf": 20}, {"figure_id": "Table 3B-2", "sheet": 2, "page_pdf": 21},
    {"figure_id": "Table 3B-2", "sheet": 3, "page_pdf": 22},
    {"figure_id": "Figure 2A-5", "sheet": 1, "page_pdf": 10}, {"figure_id": "Figure 2A-5", "sheet": 2, "page_pdf": 11},
    {"figure_id": "Table 6Z-1", "sheet": "None", "page_pdf": 40},
    {"figure_id": "Figure 9Z-9", "sheet": "None", "page_pdf": 99},
]
SHEETS = pe.sheet_pages(FIGURE_RECORDS)


class FakeKG:
    def __init__(self):
        self.g = SimpleNamespace(nodes={
            "figure:Figure 3B-1": {"id": "Figure 3B-1", "page_pdf": 20, "caption": "Fig one", "n_sheets": 1},
            "figure:Table 3B-2": {"id": "Table 3B-2", "page_pdf": 20, "caption": "Table two", "n_sheets": 3},
            "figure:Figure 2A-5": {"id": "Figure 2A-5", "page_pdf": 10, "caption": "Fig five", "n_sheets": 2},
            "figure:Table 6Z-1": {"id": "Table 6Z-1", "page_pdf": 40, "caption": "Table far", "n_sheets": 1},
            "figure:Figure 9Z-9": {"id": "Figure 9Z-9", "page_pdf": 99, "caption": "Far away", "n_sheets": 1},
        })
        self._figures = {k.split(":", 1)[1].upper(): k for k in self.g.nodes}

    def figure(self, fid):
        f = str(fid)
        if f.lower().startswith("figure:"):
            f = f.split(":", 1)[1]
        return self._figures.get(f.upper())


def _payload(kg, fid):
    from mrag.retrieval import _figure_payload_from_graph
    return _figure_payload_from_graph(kg, fid)


def test_pages_of_a_row_a_reading_and_a_paragraph():
    rows = {c["chunk_id"]: c for c in STORE}
    assert pe.pages_of(rows["C_S_01"], SHEETS) == [20]
    assert pe.pages_of(rows["vine:trow:Table 3B-2#s2r0"], SHEETS) == [21]          # its own sheet's page
    assert pe.pages_of(rows["vine:trow:Table 6Z-1#s1r0"], SHEETS) == [40]          # no page of its own
    assert pe.pages_of(rows["vine:reading:2A-5#0:Figure 2A-5"], SHEETS) == [10, 11]  # every sheet of its figure
    assert pe.pages_of(rows["E_S_01"], SHEETS) == []
    # a row whose sheet is unknown is on every page of its table
    assert pe.pages_of({"content_type": "TableRow", "parent_id": "figure:Table 3B-2", "graph_node": "x"},
                       SHEETS) == [20, 21, 22]
    assert pe.page_number("213.0") == 213 and pe.page_number("213.5") is None and pe.page_number(0) is None
    assert SHEETS["Figure 3B-1"] == {1: 20} and SHEETS["Table 3B-2"] == {1: 20, 2: 21, 3: 22}
    # a figure over several pages with no sheet numbers: sheets in page order
    s = pe.sheet_pages([{"figure_id": "Table 1Z-2", "sheet": "None", "page_pdf": 78},
                        {"figure_id": "Table 1Z-2", "sheet": None, "page_pdf": "77"}])
    assert s == {"Table 1Z-2": {1: 77, 2: 78}}
    assert pe.pages_of({"content_type": "TableRow", "parent_id": "figure:Table 1Z-2",
                        "graph_node": "trow:Table 1Z-2#s2r5", "page_pdf": 77}, s) == [78]
    assert pe.figures_by_page(s) == {77: ["Table 1Z-2"], 78: ["Table 1Z-2"]}


def test_every_piece_on_the_pages_best_page_first_in_the_manuals_order():
    from mrag.vine.parser import _sort_key
    pieces, no_page = pe.by_page(STORE, SHEETS)
    assert no_page == 1 and sorted(pieces) == [10, 11, 20, 21, 30, 40]
    kg = FakeKG()
    pages = [{"rank": 1, "page_pdf": 20, "score": 0.8}, {"rank": 2, "page_pdf": 10, "score": 0.7},
             {"rank": 3, "page_pdf": 55, "score": 0.6}]                    # a page with nothing on it
    chunks, figures = pe.evidence_for_pages(pages, pieces, pe.figures_by_page(SHEETS), lambda f: _payload(kg, f),
                                            _sort_key)
    assert [c["chunk_id"] for c in chunks] == ["C_S_01", "C_N_01", "vine:trow:Table 3B-2#s1r0",
                                               "A_G_01", "A_S_02", "vine:reading:2A-5#0:Figure 2A-5", "B_O_01"]
    # (within a page: section by section, each in the parser's own order; a description after its section's text)
    assert all(c["source"] == pe.SOURCE for c in chunks)
    assert [c["page_rank"] for c in chunks] == [1, 1, 1, 2, 2, 2, 2] and chunks[0]["score"] == 0.8
    assert chunks[1]["text"] == "text of C_N_01" and chunks[1]["parent_id"] == "Figure 3B-1"   # the store's own piece
    # the figures of the notes and rows on the pages, then the figures with a sheet on them
    assert [f["figure_id"] for f in figures] == ["Figure 3B-1", "Table 3B-2", "Figure 2A-5"]
    assert all(f["source"] == pe.SOURCE for f in figures)
    assert pe.counts(chunks)["normative"] == 4 and pe.counts(chunks)["TableRow"] == 1


def test_a_later_sheet_brings_its_rows_and_its_table():
    from mrag.vine.parser import _sort_key
    pieces, _ = pe.by_page(STORE, SHEETS)
    kg = FakeKG()
    for pg, rows, figs in ((21, ["vine:trow:Table 3B-2#s2r0"], ["Table 3B-2"]),
                           (40, ["vine:trow:Table 6Z-1#s1r0"], ["Table 6Z-1"]),
                           (11, ["vine:reading:2A-5#0:Figure 2A-5"], ["Figure 2A-5"]),
                           (22, [], ["Table 3B-2"])):
        chunks, figures = pe.evidence_for_pages([{"rank": 1, "page_pdf": pg, "score": 1}], pieces,
                                                pe.figures_by_page(SHEETS), lambda f: _payload(kg, f), _sort_key)
        assert [c["chunk_id"] for c in chunks] == rows, pg
        assert [f["figure_id"] for f in figures] == figs, pg


def test_a_page_given_twice_or_a_piece_on_two_pages_is_shown_once():
    from mrag.vine.parser import _sort_key
    pieces, _ = pe.by_page(STORE, SHEETS)
    kg = FakeKG()
    pages = [{"rank": 1, "page_pdf": 10, "score": 1}, {"rank": 2, "page_pdf": 10, "score": 1},
             {"rank": 3, "page_pdf": 11, "score": 1}]
    chunks, figures = pe.evidence_for_pages(pages, pieces, pe.figures_by_page(SHEETS), lambda f: _payload(kg, f),
                                            _sort_key)
    assert [c["chunk_id"] for c in chunks] == ["A_G_01", "A_S_02", "vine:reading:2A-5#0:Figure 2A-5", "B_O_01"]
    assert [f["figure_id"] for f in figures] == ["Figure 2A-5"]


def test_scroll_reads_every_batch():
    class Client:
        def __init__(self):
            self.calls = []

        def scroll(self, collection_name, limit, offset, with_payload, with_vectors):
            assert with_payload and not with_vectors
            self.calls.append((collection_name, offset))
            start = offset or 0
            batch = [SimpleNamespace(payload={"chunk_id": f"c{i}"}) for i in range(start, min(start + limit, 5))]
            return batch, (start + limit if start + limit < 5 else None)
    c = Client()
    got = pe.scroll_payloads(c, "mutcd_chunks", batch=2)
    assert [p["chunk_id"] for p in got] == [f"c{i}" for i in range(5)]
    assert c.calls == [("mutcd_chunks", None), ("mutcd_chunks", 2), ("mutcd_chunks", 4)]


# --------------------------------------------------------------------------- #
# the run: its own folder and evidence file, the run's questions only
# --------------------------------------------------------------------------- #
class _Patched:
    def __init__(self, attrs=(), env=None):
        self.attrs, self.env, self.saved, self.saved_env = list(attrs), dict(env or {}), [], {}

    def __enter__(self):
        for obj, name, value in self.attrs:
            self.saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        for k, v in self.env.items():
            self.saved_env[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _vine_hprc():
    sys.path.insert(0, str(REPO / "hprc"))
    sys.path.insert(0, str(REPO / "evaluation"))
    return importlib.import_module("vine_hprc")


def _files(d, pages=(20, 10, 30)):
    q = Path(d) / "questions.json"
    q.write_text(json.dumps(QUESTIONS))
    p = Path(d) / "visrag" / "retrieval.jsonl"
    p.parent.mkdir()
    p.write_text(_pages_line("Q1", list(pages)) + "\n" + _pages_line("Q2", [30, 20, 10]) + "\n")
    return q, p


def _env(q=None, p=None, k="2", **more):
    env = {"VINE_QUESTIONS": str(q) if q else None, "VINE_PAGES_FILE": str(p) if p else None,
           "VINE_PAGES": k, "VINE_REPEAT": None, "VINE_PROBE": None, "VINE_MAX_CHECKS": None}
    env.update(more)
    return env


def test_pages_run_has_its_own_evidence_file_and_folder_and_no_dev_cases():
    from mrag.config import CFG
    V = _vine_hprc()
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        with _Patched([(CFG, "base_dir", Path(d))], _env()):
            normal = V.Run()
        with _Patched([(CFG, "base_dir", Path(d))], _env(q, p)):
            R = V.Run()
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        assert R.pages == 2 and R.dev_ids == [] and R.case == {}
        assert sorted(R.questions) == ["Q1", "Q2"] and R.set_name == "sealed"
        code = V.page_evidence_code()[:8]
        assert R.kq_file.name == f"kq_pages2_{sha[:12]}_c{code}_s{R.store_tag}.json" != normal.kq_file.name
        assert R.run_dir.name.startswith(f"e2e_pages2_{sha[:12]}_c{code}_s{R.store_tag}_p{R.instructions_sha[:8]}_k")
        assert R.run_dir != normal.run_dir and R.run_dir.is_dir()
        assert R.model_cache == normal.model_cache            # one model cache; its keys hold the prompt
        assert R.settings["pages_file_sha256"] == sha and R.settings["page_retriever_model"] is None
        # the retriever's own manifest, when it is there, names the retriever in the run's records
        (p.parent / "retrieval_manifest.json").write_text(json.dumps(
            {"method": "VisRAG (VisRAG-Ret page retrieval)", "model_id": "openbmb/VisRAG-Ret",
             "model_commit_loaded": "95ef596df871b606167cb7e4b7215caf1bfdf761"}))
        with _Patched([(CFG, "base_dir", Path(d))], _env(q, p, k="20")):
            R20 = V.Run()
        assert R20.settings["page_retriever_model"] == "openbmb/VisRAG-Ret" and R20.kq_file != R.kq_file
        assert R20.run_dir != R.run_dir
        # other evidence code: other evidence file and run folder, so no old plan is reused
        with _Patched([(CFG, "base_dir", Path(d)), (V, "page_evidence_code", lambda: "f" * 64)], _env(q, p, k="20")):
            Rc = V.Run()
        assert Rc.kq_file != R20.kq_file and Rc.run_dir != R20.run_dir and "_cffffffff_" in Rc.kq_file.name
        # another figures file (each sheet's page): another fingerprint
        with _Patched([(CFG, "base_dir", Path(d)), (CFG, "figures_jsonl", _figures_file(d))], _env(q, p, k="20")):
            Rf = V.Run()
        assert Rf.kq_file != R20.kq_file and Rf.run_dir != R20.run_dir
        # a dry run's pages are refused
        (p.parent / "retrieval_manifest.json").write_text(json.dumps({"dry_run": True}))
        with _Patched([(CFG, "base_dir", Path(d))], _env(q, p)):
            try:
                V.Run()
            except AssertionError as e:
                assert "dry run" in str(e)
            else:
                raise AssertionError("a dry run's pages were accepted")


def test_pages_run_refuses_a_bad_setting():
    from mrag.config import CFG
    V = _vine_hprc()
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        bad = [_env(q, p, k=""), _env(q, p, k="0"), _env(q, p, k="x"), _env(None, p),
               _env(q, Path(d) / "none.jsonl"), _env(q, p, VINE_REPEAT="r1"), _env(q, p, VINE_PROBE="p1")]
        for env in bad:
            with _Patched([(CFG, "base_dir", Path(d))], env):
                try:
                    V.Run()
                except AssertionError:
                    continue
            raise AssertionError(f"accepted: {env}")


class FakeStore:
    def __init__(self, payloads):
        self.client = SimpleNamespace(scroll=self.scroll)
        self.payloads = payloads

    def scroll(self, collection_name, limit, offset, with_payload, with_vectors):
        from mrag.config import CFG
        assert collection_name == CFG.coll_chunks
        start = offset or 0
        batch = [SimpleNamespace(payload=dict(x)) for x in self.payloads[start:start + limit]]
        return batch, (start + limit if start + limit < len(self.payloads) else None)


def _figures_file(d):
    f = Path(d) / "figures.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in FIGURE_RECORDS) + "\n")
    return f


def test_retrieval_stage_of_a_pages_run_writes_the_evidence_the_parser_reads():
    from mrag.config import CFG
    from mrag.vine.parser import build_parser_prompt
    V = _vine_hprc()
    pipeline = SimpleNamespace(kg=FakeKG(), retriever=SimpleNamespace(store=FakeStore(STORE)))
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        with _Patched([(CFG, "base_dir", Path(d)), (CFG, "figures_jsonl", _figures_file(d)),
                       (V, "load_retrieval", lambda: pipeline), (V, "gpu_names", lambda: ["fake"])], _env(q, p)):
            R = V.Run()
            assert V.stage_retrieval(R) == 0
        kq = json.loads(R.kq_file.read_text())
        assert sorted(kq) == ["Q1", "Q2"] and kq["Q1"]["question"] == QUESTIONS["Q1"]
        assert [c["chunk_id"] for c in kq["Q1"]["chunks"]] == ["C_S_01", "C_N_01", "vine:trow:Table 3B-2#s1r0",
                                                               "A_G_01", "A_S_02",
                                                               "vine:reading:2A-5#0:Figure 2A-5", "B_O_01"]
        assert [c["chunk_id"] for c in kq["Q2"]["chunks"]] == ["D_S_01", "C_S_01", "C_N_01", "vine:trow:Table 3B-2#s1r0"]
        assert {v["evidence_code"] for v in kq.values()} == {R.settings["page_evidence_code_sha256"]}
        assert [x["page_pdf"] for x in kq["Q1"]["pages"]] == [20, 10]
        assert [f["figure_id"] for f in kq["Q1"]["figures"]] == ["Figure 3B-1", "Table 3B-2", "Figure 2A-5"]
        assert set(kq["Q1"]["figures"][0]) <= set(V.FIG_KEYS)
        prompt = build_parser_prompt(kq["Q1"]["question"], kq["Q1"]["chunks"], "", None, kq["Q1"]["figures"])
        assert "[C_S_01] Standard, paragraph 1" in prompt and "[Figure 2A-5] Fig five (2 sheets)" in prompt
        assert prompt.index("=== Section 3B.01") < prompt.index("=== Section 2A.01")   # best page first
        assert "E_S_01" not in prompt and "D_S_01" not in prompt


def test_retrieval_stage_stops_when_a_question_has_nothing_on_its_pages():
    from mrag.config import CFG
    V = _vine_hprc()
    pipeline = SimpleNamespace(kg=FakeKG(), retriever=SimpleNamespace(store=FakeStore(STORE)))
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d, pages=(55, 56, 57))
        with _Patched([(CFG, "base_dir", Path(d)), (CFG, "figures_jsonl", _figures_file(d)),
                       (V, "load_retrieval", lambda: pipeline), (V, "gpu_names", lambda: ["fake"])], _env(q, p)):
            R = V.Run()
            assert V.stage_retrieval(R) == 1
        assert not R.kq_file.exists()


def _plans(R, n_obligations):
    R.plans_file.write_text(json.dumps({q: {"case_id": q, "question": R.questions[q],
                                            "spec": {"obligations": [{"id": f"o{i}"} for i in range(n_obligations)]}}
                                        for q in R.questions}))


def test_execute_of_a_pages_run_stops_before_the_api_when_the_plans_grew_past_the_limit():
    from mrag.config import CFG
    V = _vine_hprc()

    def no(*a, **k):
        raise AssertionError("the retrieval stack was loaded")
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        with _Patched([(CFG, "base_dir", Path(d)), (V, "load_retrieval", no)],
                      _env(q, p, ANTHROPIC_API_KEY="sim-key")):
            R = V.Run()
            _plans(R, 1001)                                    # 2002 checks: over the default 2000
            assert V.stage_execute(R) == 1
        with _Patched([(CFG, "base_dir", Path(d)), (V, "load_retrieval", no)],
                      _env(q, p, ANTHROPIC_API_KEY="sim-key", VINE_MAX_CHECKS="100")):
            R = V.Run()
            _plans(R, 51)
            assert V.stage_execute(R) == 1
        # under the limit it goes on (here to the key check, with no key set)
        with _Patched([(CFG, "base_dir", Path(d)), (V, "load_retrieval", no)],
                      _env(q, p, ANTHROPIC_API_KEY=None, VINE_MAX_CHECKS="102")):
            R = V.Run()
            _plans(R, 51)
            try:
                V.stage_execute(R)
            except AssertionError as e:
                assert "no Anthropic key" in str(e)
            else:
                raise AssertionError("went past the key check")


def test_a_normal_run_has_no_check_limit():
    from mrag.config import CFG
    V = _vine_hprc()
    with tempfile.TemporaryDirectory() as d:
        with _Patched([(CFG, "base_dir", Path(d))], _env(ANTHROPIC_API_KEY=None, VINE_MAX_CHECKS="1")):
            R = V.Run()
            assert R.pages is None
            R.plans_file.write_text(json.dumps({q: {"spec": {"obligations": [{"id": "o1"}, {"id": "o2"}]}}
                                                for q in R.questions}))
            try:
                V.stage_execute(R)
            except AssertionError as e:
                assert "no Anthropic key" in str(e)
            else:
                raise AssertionError("went past the key check")


# --------------------------------------------------------------------------- #
# hprc/run.sh: the pages option, with a fake sbatch
# --------------------------------------------------------------------------- #
def _run_sh(d, args, env_extra=None):
    root = Path(d) / "repo"
    (root / "hprc").mkdir(parents=True, exist_ok=True)
    (root / "hprc" / "run.sh").write_text((REPO / "hprc" / "run.sh").read_text())
    (root / "hprc" / "vine_job.slurm").write_text("#!/bin/bash\n")
    home = Path(d) / "vine"
    home.mkdir(exist_ok=True)
    (home / ".done_models").write_text("")
    (home / "anthropic_key").write_text("k")
    (root / "hprc" / "env.sh").write_text(f'export VINE_HOME="{home}"\nexport MRAG_BASE_DIR="{d}/base"\n')
    stub = Path(d) / "bin"
    stub.mkdir(exist_ok=True)
    log = Path(d) / "sbatch.log"
    (stub / "sbatch").write_text(f'#!/bin/bash\necho "$@" >> "{log}"\necho $((RANDOM + 1000))\n')
    (stub / "sbatch").chmod(0o755)
    env = {"PATH": f"{stub}:/usr/bin:/bin", "HOME": str(d), "USER": "u"}
    env.update(env_extra or {})
    if log.exists():
        log.unlink()
    r = subprocess.run(["bash", str(root / "hprc" / "run.sh"), *args], env=env, capture_output=True, text=True,
                       cwd=d)
    calls = log.read_text().splitlines() if log.exists() else []
    return r, calls


def test_run_sh_pages_option_submits_the_three_stages_with_the_pages_settings():
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        r, calls = _run_sh(d, ["ACCT", "2", "pages", str(p), "20"], {"VINE_QUESTIONS": str(q)})
        assert r.returncode == 0, r.stdout + r.stderr
        assert [c.split("--job-name=")[1].split()[0] for c in calls] == ["vine_retrieval", "vine_parse", "vine_execute"]
        for c in calls:
            assert f"VINE_PAGES_FILE={p}," in c and "VINE_PAGES=20," in c and f"VINE_QUESTIONS={q}," in c
        assert "--gres=gpu:a100:2" in calls[1] and "--time=24:00:00" in calls[1]
        assert "pages run: the top 20 pages" in r.stdout
        # from the parse stage on
        r, calls = _run_sh(d, ["ACCT", "2", "pages", str(p), "20", "parse"],
                           {"VINE_QUESTIONS": str(q), "VINE_MAX_CHECKS": "3000"})
        assert r.returncode == 0 and [c.split("--job-name=")[1].split()[0] for c in calls] == ["vine_parse", "vine_execute"]
        assert all("VINE_MAX_CHECKS=3000" in c for c in calls)
        # a relative pages file and questions file are passed on as full paths
        r, calls = _run_sh(d, ["ACCT", "2", "pages", "visrag/retrieval.jsonl", "20"], {"VINE_QUESTIONS": q.name})
        assert r.returncode == 0 and all(f"VINE_PAGES_FILE={p}," in c and f"VINE_QUESTIONS={q}," in c for c in calls)
        r, calls = _run_sh(d, ["ACCT", "2", "pages", str(p), "20"], {"VINE_QUESTIONS": str(q), "VINE_MAX_CHECKS": "2k"})
        assert r.returncode != 0 and calls == []


def test_run_sh_pages_option_refuses_bad_arguments_and_normal_runs_carry_no_pages():
    with tempfile.TemporaryDirectory() as d:
        q, p = _files(d)
        for args, env in ((["ACCT", "2", "pages", str(Path(d) / "none.jsonl"), "20"], {"VINE_QUESTIONS": str(q)}),
                          (["ACCT", "2", "pages", str(p), "0"], {"VINE_QUESTIONS": str(q)}),
                          (["ACCT", "2", "pages", str(p), "x"], {"VINE_QUESTIONS": str(q)}),
                          (["ACCT", "2", "pages", str(p), "20"], {}),
                          (["ACCT", "2", "pages", str(p), "20", "repeat"], {"VINE_QUESTIONS": str(q)})):
            r, calls = _run_sh(d, args, env)
            assert r.returncode != 0 and calls == [], (args, r.stdout)
        # a value left in the shell never turns a normal run into a pages run
        r, calls = _run_sh(d, ["ACCT", "2", "parse"], {"VINE_QUESTIONS": str(q), "VINE_PAGES_FILE": str(p),
                                                        "VINE_PAGES": "20"})
        assert r.returncode == 0 and len(calls) == 2
        assert all("VINE_PAGES_FILE=,VINE_PAGES=," in c for c in calls)


if __name__ == "__main__":
    for _name, _f in sorted(globals().items()):
        if _name.startswith("test_") and callable(_f):
            _f()
            print("ok", _name)
    print("ALL PAGE EVIDENCE TESTS PASSED")
