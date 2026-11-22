"""vine2/vidorag_retrieve.py -- ViDoRAG's hybrid page retrieval on the MUTCD, for vine2 (GPU).

    $VINE_HOME/envs/vidorag/bin/python -I vine2/vidorag_retrieve.py --questions FILE --work DIR \
        --code $VINE_HOME/ext/vidorag --revisions FILE --out-dir DIR

Runs after vine2/vidorag_ocr.py (the page pictures and their OCR text). ViDoRAG's own code at
the pinned commit, nothing changed in it, nothing of VINE's; it runs in WORK, since ViDoRAG
reads ./data/<dataset>/:
  1. ingestion.py, as in its __main__: the pictures with vidore/colqwen2-v1.0
     (colqwen_ingestion/) and the OCR text with BAAI/bge-m3 (bge_ingestion/; its sentence
     splitter, 1,024-token chunks). The models are loaded by name, as ViDoRAG does, from the
     local copies vine2/vis_setup.sh downloaded (checked to be the recorded commits).
  2. search_engine.HybridSearchEngine(dataset, embed_model_name_vl="vidore/colqwen2-v1.0",
     embed_model_name_text="BAAI/bge-m3", gmm=True), its defaults otherwise (top-k 10): for
     each question (its text as it is) ViDoRAG's Gaussian-mixture cut on each side (5 to 10
     pages), the two sides joined, topped up to its next list size (at most 20), in page order.
What ViDoRAG returns for each page (its picture and the OCR text of the page) is written as
it is, in its order. The rank ViDoRAG's picture side gave each returned page is also written
(engine_vl.search, the same scores): vine2 sends at most 4 pictures, and takes the 4 that
ViDoRAG's picture side ranked highest.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vis_common as vc  # noqa: E402
from vidorag_ocr import DATASET, PINNED  # noqa: E402

SYSTEM = "vidorag"
VL_MODEL = "vidore/colqwen2-v1.0"          # ViDoRAG's code default (search_engine.py, ingestion.py)
TEXT_MODEL = "BAAI/bge-m3"
_PAGE = re.compile(re.escape(DATASET) + r"_(\d+)\.(?:jpg|png|txt)")


def page_of(path: str) -> int:
    m = _PAGE.fullmatch(os.path.basename(str(path)))
    if not m:
        raise ValueError(f"not a ViDoRAG page file name: {path}")
    return int(m.group(1))


def items_of(result: Dict[str, Any], vl_rank: Dict[int, int]) -> List[Dict[str, Any]]:
    """ViDoRAG's answer for one question (nodes2dict of its ImageNodes) -> vine2 items, in its order."""
    out = []
    for r, node in enumerate(result["source_nodes"], 1):
        n = node["node"]
        page = page_of(n["image_path"])
        out.append(vc.item(r, page, text=str(n.get("text") or ""), image_path=os.path.abspath(n["image_path"]),
                           visual_rank=vl_rank.get(page)))
    pages = [i["page_pdf"] for i in out]
    if len(set(pages)) != len(pages):
        raise ValueError(f"ViDoRAG returned a page twice: {pages}")
    return out


def check_nodes(folder: Path) -> int:
    """Remove node files left half written by a stopped run (ViDoRAG writes them in place), so
    its ingestion makes them again; returns how many were removed."""
    bad = 0
    for f in folder.glob("*.node") if folder.is_dir() else []:
        try:
            json.loads(f.read_text())
        except ValueError:
            f.unlink()
            bad += 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--code", required=True, type=Path)
    ap.add_argument("--revisions", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    commit = vc.check_commit(args.code, PINNED)
    revs = vc.load_revisions(args.revisions, (VL_MODEL, TEXT_MODEL))
    questions = vc.load_questions(args.questions)
    models = vc.check_refs(revs, sorted(revs["models"]))     # ViDoRAG loads its models by name
    pdf_sha = vc.sha256_file(args.pdf)
    if vc.retrieval_done(args.out_dir, SYSTEM, questions, {"code_commit": commit, "models": models,
                                                           "pdf_sha256": pdf_sha}):
        vc.log(f"a retrieval for exactly these question texts, code and models is there already: {args.out_dir}")
        return 0
    data = args.work / "data" / DATASET
    ocr_man = json.loads((data / "ocr_manifest.json").read_text())
    if ocr_man.get("pdf_sha256") != pdf_sha or ocr_man.get("code_commit") != commit:
        sys.exit(f"STOPPED: the OCR in {data} was made from another PDF or ViDoRAG commit")
    n_pages = int(ocr_man["n_pages"])
    for sub, ext in (("img", "jpg"), ("ppocr", "txt")):
        have = sorted(f.name for f in (data / sub).iterdir()) if (data / sub).is_dir() else []
        want = sorted(f"{DATASET}_{n}.{ext}" for n in range(1, n_pages + 1))
        if have != want:                                 # ViDoRAG reads every file in these folders
            sys.exit(f"STOPPED: {data / sub} does not hold exactly the {n_pages} page files "
                     f"({len(have)} files there): run the OCR job again")
    vc.log(f"ViDoRAG {commit[:12]} | {len(questions)} questions | {n_pages} pages")

    import torch
    if not torch.cuda.is_available():
        sys.exit("STOPPED: no CUDA GPU here; run this in a GPU job")
    os.chdir(args.work)                          # ViDoRAG reads ./data/<dataset>
    sys.path.insert(0, str(args.code))
    from ingestion import Ingestion
    from search_engine import HybridSearchEngine

    dataset_dir = os.path.join("./data", DATASET)
    for inp, outp, model in (("img", "colqwen_ingestion", VL_MODEL), ("ppocr", "bge_ingestion", TEXT_MODEL)):
        # ViDoRAG never makes a node file again: the folder is tied to this PDF, model and commit
        vc.stamp(data / outp, {"pdf_sha256": pdf_sha, "model": model, "models": models,
                               "bases": revs.get("bases", {}), "code_commit": commit})
        for attempt in (1, 2):
            removed = check_nodes(data / outp)
            if removed:
                vc.log(f"  {removed} half-written node files removed from {outp}/ (made again)")
            with vc.LoadGuard(model):
                ing = Ingestion(dataset_dir, input_prefix=inp, output_prefix=outp, embed_model_name=model)
            ing.ingestion_multi_session()
            del ing
            if not check_nodes(data / outp):
                break
        have = len(list((data / outp).glob("*.node")))
        if have != n_pages:
            sys.exit(f"STOPPED: {outp}/ has {have} node files, not {n_pages}")
        vc.log(f"ingestion {outp}: {have} pages ({model})")

    with vc.LoadGuard("ViDoRAG's search engine"):
        engine = HybridSearchEngine(DATASET, embed_model_name_vl=VL_MODEL, embed_model_name_text=TEXT_MODEL, gmm=True)
    items, sizes = {}, []
    for i, (qid, q) in enumerate(questions.items(), 1):
        result = engine.search(q)
        engine.engine_vl.return_raw = True
        raw_vl = engine.engine_vl.search(q)                  # ViDoRAG's picture side, its top 100
        vl_rank = {}
        for r, node in enumerate(raw_vl, 1):
            vl_rank.setdefault(page_of(node.node.image_path), r)
        items[qid] = items_of(result, vl_rank)
        sizes.append(len(items[qid]))
        if i % 25 == 0:
            vc.log(f"  searched {i}/{len(questions)}")
    sizes.sort()
    vc.log(f"pages a question: {sizes[0]} to {sizes[-1]} (median {sizes[len(sizes) // 2]})")

    vc.write_retrieval(args.out_dir, SYSTEM, questions, items, {
        "method": "ViDoRAG hybrid retrieval: ColQwen2 v1.0 on page pictures + BGE-M3 on OCR text, "
                  "Gaussian-mixture cut (gmm=True, top-k 10), joined, in page order",
        "code_repo": "https://github.com/Alibaba-NLP/ViDoRAG", "code_commit": commit, "models": models,
        "ocr_manifest": ocr_man, "query": "the question text as it is", "n_pages": n_pages,
        "pdf": str(args.pdf), "pdf_sha256": pdf_sha,
        "env": {k: os.environ.get(k) for k in ("LLAMA_INDEX_CACHE_DIR", "TIKTOKEN_CACHE_DIR", "HF_HUB_CACHE")},
        "pages_a_question": {"min": sizes[0], "median": sizes[len(sizes) // 2], "max": sizes[-1]},
        "questions_file": str(args.questions), "questions_sha256": vc.sha256_file(args.questions),
        "gpu": torch.cuda.get_device_name(0),
        "versions": vc.versions("torch", "transformers", "colpali-engine", "llama-index-core",
                                "llama-index-embeddings-huggingface", "sentence-transformers", "scikit-learn")})
    vc.log(f"wrote ViDoRAG's pages for {len(items)} questions -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
