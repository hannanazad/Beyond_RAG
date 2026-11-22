"""vine2/m3docrag_retrieve.py -- M3DocRAG's page retrieval on the MUTCD, for vine2.

    $VINE_HOME/envs/m3docrag/bin/python -I vine2/m3docrag_retrieve.py --pdf PDF --questions FILE \
        --out-dir DIR --pages-dir DIR --code $VINE_HOME/ext/m3docrag --revisions FILE

M3DocRAG (Cho et al., 2024; github.com/bloomberg/m3docrag) finds pages with ColPali. This
script runs M3DocRAG's own code, from its repository at the pinned commit (PINNED below), with
nothing changed in it and nothing of VINE's:
  1. the pages: m3docrag.utils.pdfs.get_images_from_pdf (pdf2image, 144 dpi, RGB, every page
     resized to the most common page size when sizes differ), saved as PNG;
  2. the model: m3docrag.retrieval.ColPaliRetrievalModel, ColPali v1.2 (the adapter
     vidore/colpali-v1.2 on vidore/colpaligemma-3b-pt-448-base, bfloat16), the default of
     M3DocRAG's README and code; moved to the GPU as M3DocRAG's scripts do (accelerate);
  3. the page vectors: ColPaliRetrievalModel.encode_images, stacked and kept in bfloat16, as
     examples/run_page_embedding.py does (saved once, reused if the model and pages match);
  4. each question: the question text as it is (examples/run_rag_m3docvqa.py), scored against
     every page with ColPaliRetrievalModel.retrieve (MaxSim, exact: one document, M3DocRAG's
     closed-domain setting), and the top pages taken with M3DocRAG's get_top_k_pages
     (rag/utils.py), as RAGModelBase.retrieve_pages_from_docs does for one document.
The top SAVE_TOP (20) pages of each question are written, with the page picture M3DocRAG made.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vis_common as vc  # noqa: E402

SYSTEM = "m3docrag"
PINNED = "29e6ac2294d6b87075a1d45b8a8df175b214248a"      # github.com/bloomberg/m3docrag, 15 Feb 2025
BACKBONE = "vidore/colpaligemma-3b-pt-448-base"
ADAPTER = "vidore/colpali-v1.2"
DOC_ID = "MUTCD"                                         # one document


def load_top_k(code: Path) -> Callable:
    """M3DocRAG's get_top_k_pages, read from its rag/utils.py (that file imports only tqdm),
    without importing m3docrag.rag, which would load every answer model's code."""
    spec = importlib.util.spec_from_file_location("m3docrag_rag_utils", code / "src/m3docrag/rag/utils.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.get_top_k_pages


def page_file(pages_dir: Path, pdf: Path, page_index: int) -> Path:
    """The name get_images_from_pdf saves a page under ("{pdf name}_{page number}.png")."""
    return pages_dir / f"{pdf.name}_{page_index + 1}.png"


def rank(scores: Dict[str, List[float]], top_k: Callable, pdf: Path, pages_dir: Path,
         k: int = vc.SAVE_TOP) -> Dict[str, List[Dict[str, Any]]]:
    """{question id: its score for every page, in page order} -> the top k pages, by
    M3DocRAG's get_top_k_pages."""
    out = {}
    for qid, s in scores.items():
        top = top_k(docid2scores={DOC_ID: list(s)}, k=k)
        out[qid] = [vc.item(r, idx + 1, score=round(float(score), 6),
                            image_path=str(page_file(pages_dir, pdf, idx)))
                    for r, (doc, idx, score) in enumerate(top, 1) if doc == DOC_ID]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--pages-dir", required=True, type=Path, help="where M3DocRAG's page pictures are saved")
    ap.add_argument("--code", required=True, type=Path, help="M3DocRAG's repository (vine2/vis_setup.sh)")
    ap.add_argument("--revisions", required=True, type=Path, help="the model commits (vine2/vis_setup.sh)")
    ap.add_argument("--batch", type=int, default=4, help="pages a forward pass (encode_images' default)")
    args = ap.parse_args()

    commit = vc.check_commit(args.code, PINNED)
    revs = vc.load_revisions(args.revisions, (BACKBONE, ADAPTER))
    questions = vc.load_questions(args.questions)
    vc.log(f"M3DocRAG {commit[:12]} | {len(questions)} questions")
    models = {BACKBONE: revs["models"][BACKBONE], ADAPTER: revs["models"][ADAPTER]}
    pdf_sha = vc.sha256_file(args.pdf)
    if vc.retrieval_done(args.out_dir, SYSTEM, questions, {"code_commit": commit, "models": models,
                                                           "pdf_sha256": pdf_sha}):
        vc.log(f"a retrieval for exactly these question texts, code and models is there already: {args.out_dir}")
        return 0
    sys.path.insert(0, str(args.code / "src"))
    import torch
    from safetensors.torch import load_file, save_file
    from m3docrag.retrieval import ColPaliRetrievalModel
    from m3docrag.utils.pdfs import get_images_from_pdf
    from PIL import Image
    if not torch.cuda.is_available():
        sys.exit("STOPPED: no CUDA GPU here; run this in a GPU job")
    poppler = vc.tool_version(["pdftoppm", "-v"])
    if poppler == "missing":
        sys.exit("STOPPED: pdftoppm (poppler) is missing on this node: M3DocRAG's pdf2image needs it")

    # 1. the pages, as M3DocRAG makes them (its saved pictures are never made again: the folder
    #    is tied to this PDF, and a picture a stopped job left half written is saved again)
    vc.stamp(args.pages_dir, {"pdf_sha256": pdf_sha, "render": "m3docrag get_images_from_pdf, 144 dpi"})
    images = get_images_from_pdf(args.pdf, save_dir=str(args.pages_dir), save_image=True)
    resaved = 0
    for i, im in enumerate(images):
        f = page_file(args.pages_dir, args.pdf, i)
        try:
            with Image.open(f) as chk:
                chk.verify()
        except Exception:                                   # noqa: BLE001
            tmp = f.with_name(f.name + ".part")
            im.save(tmp, format="PNG")
            tmp.replace(f)
            resaved += 1
    sizes = sorted({im.size for im in images})
    vc.log(f"pages: {len(images)}, size(s) {sizes[:3]} (pdf2image, 144 dpi; {poppler}); {resaved} broken pictures saved again")

    # 2. the model
    back, adap = vc.snapshot(revs, BACKBONE), vc.snapshot(revs, ADAPTER)
    with vc.LoadGuard("ColPali v1.2"):
        model = ColPaliRetrievalModel(backbone_name_or_path=back, adapter_name_or_path=adap)
    model.model.to("cuda")
    vc.log(f"ColPali ready on {torch.cuda.get_device_name(0)}: {BACKBONE}@{revs['models'][BACKBONE][:12]} "
           f"+ {ADAPTER}@{revs['models'][ADAPTER][:12]}")

    # 3. the page vectors (saved once; named by the model commits)
    emb_file = args.out_dir.parent / (f"page_embeddings_{revs['models'][ADAPTER][:12]}_{revs['models'][BACKBONE][:12]}"
                                      f"_{pdf_sha[:12]}.safetensors")
    doc_embs = None
    if emb_file.exists():
        doc_embs = load_file(str(emb_file))["embeddings"]
        if doc_embs.shape[0] != len(images):
            doc_embs = None
        else:
            vc.log(f"page vectors reused: {tuple(doc_embs.shape)} from {emb_file.name}")
    if doc_embs is None:
        vc.log(f"embedding {len(images)} pages ...")
        doc_embs = torch.stack(model.encode_images(images=images, batch_size=args.batch, to_cpu=True,
                                                   use_tqdm=False), dim=0).to(torch.bfloat16)
        tmp = emb_file.with_suffix(".part")
        save_file({"embeddings": doc_embs}, str(tmp))
        tmp.replace(emb_file)
        vc.log(f"page vectors: {tuple(doc_embs.shape)} -> {emb_file.name}")
    del images

    # 4. every question
    scores = {}
    for i, (qid, q) in enumerate(questions.items(), 1):
        s = model.retrieve(query=q, doc_embeds=doc_embs, to_cpu=True, return_top_1=False)
        scores[qid] = s.flatten().tolist()
        if i % 25 == 0:
            vc.log(f"  ranked {i}/{len(questions)}")
    items = rank(scores, load_top_k(args.code), args.pdf, args.pages_dir)

    vc.write_retrieval(args.out_dir, SYSTEM, questions, items, {
        "method": "M3DocRAG page retrieval (ColPali v1.2, MaxSim, exact, one document)",
        "code_repo": "https://github.com/bloomberg/m3docrag", "code_commit": commit,
        "models": models,
        "page_render": {"function": "m3docrag.utils.pdfs.get_images_from_pdf", "dpi": 144,
                        "sizes": [list(s) for s in sizes]},
        "query": "the question text as it is", "n_pages": int(doc_embs.shape[0]),
        "page_vectors": str(emb_file), "pdf": str(args.pdf), "pdf_sha256": pdf_sha, "poppler": poppler,
        "questions_file": str(args.questions), "questions_sha256": vc.sha256_file(args.questions),
        "gpu": torch.cuda.get_device_name(0),
        "versions": vc.versions("torch", "transformers", "colpali-engine", "peft", "pdf2image", "pillow")})
    vc.log(f"wrote the top {vc.SAVE_TOP} pages of {len(items)} questions -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
