"""compare40/run_gems_rag.py -- system 1: GEMS-RAG, as it is, on the 40 questions.

    $RETR_ENV/bin/python -u compare40/run_gems_rag.py [--only SAMPLE002,SAMPLE022] [--run-id NAME]

The code is the untouched copy in gems_rag/ (github.com/hannanazad/gemsrag, commit
6b61de1). Its data is the copy of My Drive/MRAG in $SCRATCH/Beyond_RAG/gems_rag. This
script changes NO file of GEMS-RAG. It:

  1. checks that the copy is untouched: a fingerprint of every file in gems_rag/mrag and
     gems_rag/benchmark/runner must equal the one taken from commit 6b61de1;
  2. points GEMS-RAG at its data copy, through the setting GEMS-RAG itself reads
     (MRAG_BASE_DIR);
  3. maps the image paths in GEMS-RAG's data, recorded on Colab
     (/content/drive/MyDrive/MRAG/...), to the same files in that copy. On Colab those
     paths existed. On FASTER they do not, and GEMS-RAG quietly leaves out an image it
     cannot find, so without this it would answer with no images. The mapping is done on
     the retrieval output, before the figure filter and the answer read the images
     (retrieval never opens an image file). A missing image stops the run;
  4. stops if any part of GEMS-RAG is not working as it did for the paper. GEMS-RAG itself
     would only log a warning and carry on. Before the run: the text model must be in the
     mode the paper's runs used, "st-fallback" (with GEMS-RAG's pinned packages BGE-M3's
     own loader fails and GEMS-RAG falls back to dense-only search: requirements.txt and
     docs/01_SYSTEM_ARCHITECTURE.md say so, and the rebuttal found sparse retrieval never
     ran); the reranker must be mxbai-rerank-large-v2 (not the BGE stand-in); ColQwen2 must
     load AND find pages and figure crops for a check question. The only warning allowed
     before the run is that BGE-M3 fallback. During the run, every warning GEMS-RAG logs is
     kept (added to compare40_warnings.json, which a rerun never empties), and the run
     ends with exit code 1 if any says something failed or fell back;
  5. runs GEMS-RAG's own benchmark runner with the settings of the paper's full
     MUTCD-150 run (notebooks/02_benchmark_multi_model.ipynb): logging at INFO, the
     few-shot answer prompt, the figure filter done by the answer model, 3 tries a
     question, 8 s back-off, 2 s between calls, seed 20260710. The only runner options
     changed are strict_benchmark_hash and strict_question_count, which accept only the
     MUTCD-150 file. (The runner's own records still say "MUTCD-150-v1.0" and name this
     repo's commit; compare40_note.json in the run folder says what was really run.)

The question file holds question text only (the runner itself refuses gold fields).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True          # write nothing into gems_rag/
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
GEMS = REPO / "gems_rag"
GEMS_COMMIT = "6b61de19ea1f5ad1debc20d2b78108d90ecaa80b"
# sha256 over (path, sha256 of the file) of every file in gems_rag/mrag and
# gems_rag/benchmark/runner (19 files, __pycache__ left out), taken from commit 6b61de1
GEMS_FINGERPRINT = "168ddc52dce368faf0ef7ba6a7505da3f14d18cc52ba9ed8e379b59584299884"
COLAB_BASE = "/content/drive/MyDrive/MRAG/"
MODELS = "claude-sonnet-5-5,claude-fable-5"
# a question that is not a test question, used only for the checks before the run
# (the benchmark notebook's own interactive test question)
CHECK_QUERY = "Explain Figure 2B-1 and the plaques it shows."
DEGRADED = ("fail", "falling back", "fallback", "unavailable", "disabled")
TEXT_MODE_OF_THE_PAPER = "st-fallback"
PAPER_FALLBACK_WARNING = "BGE-M3 unavailable"     # embeddings.py, the warning of that fallback


def fingerprint(root: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    files = sorted(p for d in ("mrag", "benchmark/runner") for p in (root / d).rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)
    for p in files:
        h.update(str(p.relative_to(root)).encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return len(files), h.hexdigest()


class Watch(logging.Handler):
    """Keeps every warning GEMS-RAG logs, with the question and model being answered."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.qid, self.model = "(before the run)", ""
        self.hits: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("mrag"):
            self.hits.append({"job": os.environ.get("SLURM_JOB_ID", "nojob"), "question_id": self.qid,
                              "model_id": self.model,
                              "time": dt.datetime.now(dt.timezone.utc).isoformat(),
                              "logger": record.name, "message": record.getMessage()[:400]})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=MODELS, help=f"comma-separated model ids (default {MODELS})")
    ap.add_argument("--questions", default=str(HERE / "questions_40.jsonl"))
    ap.add_argument("--out", default="", help="default $SCRATCH/Beyond_RAG/compare40_runs/gems_rag")
    ap.add_argument("--run-id", default="compare40_gemsrag_v1")
    ap.add_argument("--only", default="", help="comma-separated question ids (a smoke test)")
    args = ap.parse_args()

    # 1. the copy is untouched
    n_files, fp = fingerprint(GEMS)
    assert fp == GEMS_FINGERPRINT, (f"gems_rag/ differs from gemsrag commit {GEMS_COMMIT[:7]} "
                                    f"({n_files} files, fingerprint {fp}): stopping")
    print(f"GEMS-RAG code : {GEMS} | {n_files} files identical to gemsrag commit {GEMS_COMMIT[:7]}")

    scratch = Path(os.environ["SCRATCH"])
    data = scratch / "Beyond_RAG" / "gems_rag"
    out = Path(args.out) if args.out else scratch / "Beyond_RAG" / "compare40_runs" / "gems_rag"
    assert data.is_dir(), f"GEMS-RAG's data copy is missing: {data}"

    # 2. GEMS-RAG's code from the copy, pointed at its own data copy
    os.environ["MRAG_ENV"] = "hprc"
    os.environ["MRAG_BASE_DIR"] = str(data)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")   # as in the notebook
    watch = Watch()
    logging.getLogger().addHandler(watch)
    sys.path.insert(0, str(GEMS / "benchmark" / "runner"))
    sys.path.insert(0, str(GEMS))
    import mrag  # noqa: E402
    assert Path(mrag.__file__).resolve().is_relative_to(GEMS.resolve()), \
        f"imported the wrong mrag: {mrag.__file__} (must be the GEMS-RAG copy in {GEMS})"
    from mrag.config import CFG  # noqa: E402
    assert Path(CFG.base_dir) == data, f"data: {CFG.base_dir}, wanted {data}"
    assert Path(CFG.qdrant_dir) == data / "qdrant_db", f"vector store: {CFG.qdrant_dir}"
    print(f"GEMS-RAG data : {CFG.base_dir} | vector store {CFG.qdrant_dir} | models {CFG.hf_home}")

    from mrag.ask import ask, init_pipeline  # noqa: E402
    from mutcd_benchmark_runner import run_benchmark, validate_run_outputs  # noqa: E402

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    CFG.set_vlm_model(models[0])
    CFG.use_vlm_figure_filter = True
    CFG.set_filter_model(None)            # the answer model also filters the figures

    # 4. every part loaded as on Colab
    pipeline = init_pipeline()
    text_mode = getattr(pipeline.text, "_mode", None)
    reranker = type(getattr(pipeline.rerank, "_model", None)).__name__
    assert text_mode == TEXT_MODE_OF_THE_PAPER, \
        f"the text model is in mode {text_mode!r}, not {TEXT_MODE_OF_THE_PAPER!r} as in the paper's runs: stopping"
    assert reranker == "MxbaiRerankV2", f"the reranker is {reranker}, not mxbai-rerank-large-v2: stopping"
    assert pipeline.image is not None, "ColQwen2 did not load (see the warning above): stopping"
    counts = {c: pipeline.store.client.count(c, exact=True).count
              for c in (CFG.coll_chunks, CFG.coll_figures, CFG.coll_figures_visual, CFG.coll_pages)}
    q_mv = pipeline.image.encode_queries([CHECK_QUERY])[0]
    n_vis = len(pipeline.store.search_figures_visual(CFG.coll_figures_visual, q_mv, top_k=CFG.top_k_figures_visual))
    n_pages = len(pipeline.store.search_pages(CFG.coll_pages, q_mv, top_k=CFG.top_k_pages))
    print(f"models        : text {text_mode} | reranker {reranker} | ColQwen2 loaded")
    print(f"vector store  : {counts}")
    print(f"graph         : {pipeline.kg.g.number_of_nodes():,} nodes, {pipeline.kg.g.number_of_edges():,} edges")
    print(f"ColQwen2 check: {n_pages} pages (of {CFG.top_k_pages}), {n_vis} figure crops")
    assert n_pages == CFG.top_k_pages and n_vis > 0, "ColQwen2 search finds nothing: stopping"

    # 3. the Colab image paths -> the same files in the data copy
    def local(p):
        s = str(p or "")
        return str(data / s[len(COLAB_BASE):]) if s.startswith(COLAB_BASE) else s

    def image_paths(res):
        for v in list(res.figures) + list(res.pages):
            for p in [v.get("image_path")] + list(v.get("image_paths") or []):
                if p:
                    yield p

    original_retrieve = pipeline.retriever.retrieve

    def retrieve(query):
        res = original_retrieve(query)
        for v in list(res.figures) + list(res.pages):
            if v.get("image_path"):
                v["image_path"] = local(v["image_path"])
            if v.get("image_paths"):
                v["image_paths"] = [local(p) for p in v["image_paths"]]
        missing = sorted({p for p in image_paths(res) if not Path(p).exists()})
        if missing:
            raise RuntimeError(f"{len(missing)} image file(s) not found on FASTER, e.g. {missing[:3]}")
        return res

    pipeline.retriever.retrieve = retrieve
    res = pipeline.retriever.retrieve(CHECK_QUERY)
    n_img = len(set(image_paths(res)))
    print(f"image check   : {len(res.figures)} figures, {len(res.pages)} pages, {n_img} image files, all found")
    assert n_img > 0, "the check question found no images: the image paths are not working"
    before = [h for h in watch.hits if not h["message"].startswith(PAPER_FALLBACK_WARNING)]
    for h in watch.hits:
        print(f"WARNING before the run: {h['logger']} | {h['message']}",
              "(as in the paper's runs)" if h not in before else "")
    if before:
        return 1
    watch.hits = []

    # the record of what was really run
    run_dir = out / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    qfile = Path(args.questions)
    (run_dir / "compare40_note.json").write_text(json.dumps({
        "system": "GEMS-RAG as it is", "gems_commit": GEMS_COMMIT, "gems_fingerprint": fp,
        "data_dir": str(data), "questions_file": str(qfile),
        "questions_sha256": hashlib.sha256(qfile.read_bytes()).hexdigest(), "models": models,
        "text_model_mode": text_mode, "reranker": reranker, "vector_store_counts": counts,
        "image_path_mapping": {COLAB_BASE: str(data) + "/"},
        "changed_runner_options": {"strict_benchmark_hash": False, "strict_question_count": False},
    }, indent=1) + "\n")

    qid_of = {}
    for line in qfile.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            qid_of[str(r["question"]).strip()] = r["question_id"]

    def ask_watched(question, **kw):
        watch.qid, watch.model = qid_of.get(question.strip(), question[:60]), str(CFG.vlm_model_api)
        return ask(question, **kw)

    # 5. GEMS-RAG's own runner, the paper's settings
    only = [q.strip() for q in args.only.split(",") if q.strip()]
    paths = run_benchmark(
        CFG=CFG, ask_fn=ask_watched, questions_path=qfile, output_root=out, run_id=args.run_id,
        models=[{"alias": m, "selector": m, "provider": "anthropic"} for m in models],
        prompt_style="fewshot", replicates=1, question_ids=only or None,
        show_scores=False, show_text=False, max_attempts=3, retry_base_seconds=8.0,
        inter_request_seconds=2.0, seed=20260710, resume=True, rerun_errors=True,
        strict_benchmark_hash=False, strict_question_count=False,
        store_serialized_return=True, store_raw_debug=True, echo_answer_preview=True,
    )
    summary = validate_run_outputs(paths["run_dir"], args.run_id)
    print(json.dumps(summary, indent=2, default=str))

    n_q = len(only) if only else sum(1 for line in qfile.read_text().splitlines() if line.strip())
    rc = 0
    if summary.get("ok_records") != n_q * len(models) or summary.get("unresolved_error_records"):
        print(f"\nNOT COMPLETE: {summary.get('ok_records')} answers of {n_q * len(models)} expected")
        rc = 1
    # the warnings of every run into this folder: a rerun that skips answered questions
    # must not hide a fallback that happened while one of them was answered
    wfile = run_dir / "compare40_warnings.json"
    earlier = json.loads(wfile.read_text()) if wfile.exists() else []
    hits = earlier + watch.hits
    wfile.write_text(json.dumps(hits, indent=1) + "\n")
    # the answer that is kept for each (model, question): the last successful record
    kept = {}
    afile = Path(paths["answers"])
    for line in (afile.read_text().splitlines() if afile.exists() else []):
        if line.strip():
            r = json.loads(line)
            if r.get("status") == "ok":
                kept[(r["model_id"], r["question_id"])] = (dt.datetime.fromisoformat(r["started_at"]),
                                                          dt.datetime.fromisoformat(r["completed_at"]))

    def while_kept_answer_was_made(h):
        span = kept.get((h["model_id"], h["question_id"]))
        return bool(span) and span[0] <= dt.datetime.fromisoformat(h["time"]) <= span[1]

    # a failure or fallback counts if it happened while a kept answer was being made (a failed
    # answer call is tried again by the runner itself; a question still without an answer
    # is caught by the count above)
    bad = [h for h in hits if any(w in h["message"].lower() for w in DEGRADED)
           and not h["message"].startswith("VLM generation failed") and while_kept_answer_was_made(h)]
    for h in hits:
        print(f"WARNING | job {h['job']} | {h['model_id']} {h['question_id']} | {h['logger']} | {h['message']}"
              + ("   <-- in a kept answer" if h in bad else ""))
    if bad:
        print(f"\nGEMS-RAG REPORTED {len(bad)} FAILURE(S) OR FALLBACK(S) IN KEPT ANSWERS (marked above, all "
              f"in {wfile.name}): those answers were not made as for the paper")
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
