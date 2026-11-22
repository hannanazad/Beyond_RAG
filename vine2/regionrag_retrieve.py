"""vine2/regionrag_retrieve.py -- RegionRAG's region retrieval on the MUTCD, for vine2 (GPU).

    $VINE_HOME/envs/regionrag/bin/python -I vine2/regionrag_retrieve.py --questions FILE \
        --pages-dir DIR --code $VINE_HOME/ext/regionrag --revisions FILE --out-dir DIR

RegionRAG (Li et al., AAAI 2026; github.com/Aeryn666/RegionRAG) finds the parts of pages
(regions) that match a question. This script runs RegionRAG's own code at the pinned commit
(PINNED), nothing changed in it, nothing of VINE's:
  - the model: its RetrievalEvaluator.build_model_and_processor on its released checkpoint
    (Aeryn666/RegionRet, a LoRA on ColQwen2.5), bfloat16, as in scripts/eval/eval.sh;
  - the pages and the questions: its collators for VisRAG-style data (page picture and its
    size (height, width); the question text as it is), on the MUTCD pages. RegionRAG has no
    PDF step of its own, so the pages are the same pictures VisRAG's run used (PyMuPDF, 180
    dpi, compare40/visrag_retrieve.py);
  - the regions: its get_bbox_retrieval_results (per-patch similarity, patches above the
    threshold, joined with their neighbours, one box a group, scored by its best patch), with
    the defaults of its scripts/eval/retrieval.py and eval.sh: threshold 0.0, neighbour range
    1, score "max", the best 100 regions a question. The paper gives no threshold (it says the
    best one depends on the data); nothing is tuned on our questions.
The best SAVE_TOP (20) regions of each question are written, in RegionRAG's order, each with
its page, its box (pixels of the page picture) and the picture's size.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vis_common as vc  # noqa: E402

SYSTEM = "regionrag"
PINNED = "1ff0f29220e05d288ebe48f7c9070f396a358552"      # github.com/Aeryn666/RegionRAG, 20 Apr 2026
MODEL = "Aeryn666/RegionRet"
TOPKS = [1, 2, 5, 10, 100]                               # scripts/eval/eval.sh
BBOX = {"bbox_score_method": "max", "bbox_threshold": 0.0, "bbox_neighbor_range": [-1, 0, 1],
        "bbox_num_process": 30, "eval_iou_threshold": 0.5}   # scripts/eval/retrieval.py defaults, eval.sh
_PAGE = re.compile(r"page_(\d{4})\.png")


def page_of(image_id: str) -> int:
    m = _PAGE.fullmatch(str(image_id))
    if not m:
        raise ValueError(f"not a page picture name: {image_id}")
    return int(m.group(1))


def items_of(regions: List[Dict[str, Any]], sizes: Dict[str, Any], pages_dir: Path,
             k: int = vc.SAVE_TOP) -> List[Dict[str, Any]]:
    """RegionRAG's ranked regions for one question -> vine2 items (the first k, its order)."""
    out = []
    for r, reg in enumerate(regions[:k], 1):
        x1, y1, x2, y2 = (float(v) for v in reg["bounding_box"])
        out.append(vc.item(r, page_of(reg["image_id"]), score=round(float(reg["score"]), 6),
                           box=[x1, y1, x2, y2], image_size=list(sizes[reg["image_id"]]),
                           image_path=str(pages_dir / reg["image_id"])))
    return out


@dataclass
class CorpusDataCollator:
    """RegionRAG's collator for VisRAG-style pages (build_visrag_dataloader), for files."""
    processor: Optional[Callable]

    def __call__(self, instances):
        corpus_ids, images = tuple([instance[key] for instance in instances] for key in ("corpus-id", "image"))
        image_sizes = [(img.height, img.width) for img in images]
        images = self.processor.process_images(images=images)
        return corpus_ids, images, image_sizes


@dataclass
class QueryDataCollator:
    """RegionRAG's collator for VisRAG-style queries (build_visrag_dataloader)."""
    processor: Optional[Callable]

    def __call__(self, instances):
        query_ids, queries = tuple([instance[key] for instance in instances] for key in ("query-id", "query"))
        queries = self.processor.process_queries(queries=queries)
        return query_ids, queries


class Pages:
    """The page pictures as {"corpus-id", "image"} rows (RegionRAG reads them so)."""

    def __init__(self, files: List[Path]):
        self.files = files

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        from PIL import Image
        return {"corpus-id": self.files[i].name, "image": Image.open(self.files[i]).convert("RGB")}


class Queries:
    def __init__(self, questions: Dict[str, str]):
        self.rows = list(questions.items())

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        return {"query-id": self.rows[i][0], "query": self.rows[i][1]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--pages-dir", required=True, type=Path, help="the page pictures (page_0001.png ...)")
    ap.add_argument("--n-pages", required=True, type=int, help="pages in the PDF (every one must be there)")
    ap.add_argument("--code", required=True, type=Path)
    ap.add_argument("--revisions", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--batch", type=int, default=16, help="pages a forward pass (scripts/eval/eval.sh: 16)")
    args = ap.parse_args()
    commit = vc.check_commit(args.code, PINNED)
    revs = vc.load_revisions(args.revisions, (MODEL,))
    questions = vc.load_questions(args.questions)
    models = dict(revs["models"])
    base = (revs.get("bases") or {}).get(MODEL)
    if not base:
        sys.exit(f"STOPPED: {args.revisions} does not say which base {MODEL} is loaded on: run  bash vine2/vis_setup.sh regionrag")
    if vc.retrieval_done(args.out_dir, SYSTEM, questions, {"code_commit": commit, "models": models}):
        vc.log(f"a retrieval for exactly these question texts, code and models is there already: {args.out_dir}")
        return 0
    files = [args.pages_dir / f"page_{n:04d}.png" for n in range(1, args.n_pages + 1)]
    missing = [f.name for f in files if not f.is_file()]
    if missing:
        sys.exit(f"STOPPED: {len(missing)} page pictures are missing in {args.pages_dir}, e.g. {missing[:3]}")
    vc.log(f"RegionRAG {commit[:12]} | {len(questions)} questions | {len(files)} pages")

    import torch
    from torch.utils.data import DataLoader
    if not torch.cuda.is_available():
        sys.exit("STOPPED: no CUDA GPU here; run this in a GPU job")
    sys.path.insert(0, str(args.code))
    from colpali_engine.evaluation.retrieval_evaluator import RetrievalEvaluator

    model_dir = vc.snapshot(revs, MODEL)                 # its name holds "regionret": RegionRAG's ColQwen2.5 path
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # the base the adapter names: RegionRAG's own local path ("./models/colqwen2.5-base") is made
    # to point at the recorded download, and the job runs from that folder; a Hugging Face id
    # must resolve offline to the recorded commit
    if base["local"]:
        declared = Path(base["declared"])
        if declared.is_absolute() or ".." in declared.parts:
            sys.exit(f"STOPPED: the adapter's base path {base['declared']} is not a plain relative path")
        work = args.out_dir / "work"                     # one per question file: no two runs share it
        link = work / declared
        link.parent.mkdir(parents=True, exist_ok=True)
        target = vc.snapshot(revs, base["repo"])
        if link.is_symlink() and link.resolve() != target.resolve():
            link.unlink()
        if not link.exists():
            link.symlink_to(target)
        os.chdir(work)
        vc.log(f"base: {base['declared']} -> {base['repo']}@{revs['models'][base['repo']][:12]} (from {work})")
    else:
        vc.check_refs(revs, [base["repo"]])
    tag = f"{revs['models'][MODEL][:12]}"
    for cache in (args.out_dir / f"image_{tag}.pth", ):    # RegionRAG writes its caches in place
        if cache.exists():
            try:
                torch.load(cache)
            except Exception:                            # noqa: BLE001
                vc.log(f"  {cache.name} was left half written: made again")
                cache.unlink()
    for cache in args.out_dir.glob(f"text_{tag}_*.pth"):
        cache.unlink()                                   # 150 questions: quick to make again, never stale
    with vc.LoadGuard("RegionRet"):
        ev = RetrievalEvaluator(
        str(model_dir), "mutcd", "", TOPKS, args.batch,
        str(args.out_dir / f"image_{tag}.pth"),                                   # page vectors, reused
        str(args.out_dir / f"text_{tag}_{vc.sha256_file(args.questions)[:12]}.pth"),  # question vectors
        str(args.out_dir / "regions_raw.json"), False,
        True, None, BBOX["bbox_score_method"], BBOX["bbox_threshold"], BBOX["bbox_neighbor_range"],
        BBOX["bbox_num_process"], BBOX["eval_iou_threshold"])
    from transformers.utils.import_utils import is_flash_attn_2_available
    flash = bool(is_flash_attn_2_available())
    ev.image_dataloader = DataLoader(Pages(files), batch_size=args.batch, shuffle=False, num_workers=4,
                                     collate_fn=CorpusDataCollator(ev.processor))
    ev.text_dataloader = DataLoader(Queries(questions), batch_size=args.batch, shuffle=False, num_workers=0,
                                    collate_fn=QueryDataCollator(ev.processor))
    vc.log(f"RegionRet ready on {torch.cuda.get_device_name(0)}: {MODEL}@{revs['models'][MODEL][:12]}")
    results = ev.get_bbox_retrieval_results()            # {question id: its best 100 regions}

    from PIL import Image
    sizes = {}
    for f in files:
        with Image.open(f) as im:
            sizes[f.name] = (im.height, im.width)
    items = {qid: items_of(results.get(qid) or [], sizes, args.pages_dir) for qid in questions}
    n_pages_hit = sorted(len({i["page_pdf"] for i in v}) for v in items.values())
    area = sorted(((i["box"][2] - i["box"][0]) * (i["box"][3] - i["box"][1])) / (i["image_size"][0] * i["image_size"][1])
                  for v in items.values() for i in v)
    vc.log(f"regions a question: {vc.SAVE_TOP}; pages they are on: {n_pages_hit[0]} to {n_pages_hit[-1]}; "
           f"region size: smallest {area[0]:.2%}, median {area[len(area) // 2]:.1%}, largest {area[-1]:.1%} of a page")
    vc.write_retrieval(args.out_dir, SYSTEM, questions, items, {
        "method": "RegionRAG region retrieval (RegionRet, per-patch similarity, connected regions)",
        "code_repo": "https://github.com/Aeryn666/RegionRAG", "code_commit": commit, "models": models,
        "bbox_settings": BBOX, "topks": TOPKS, "pages": "compare40/visrag_retrieve.py's pictures (PyMuPDF, 180 dpi)",
        "pages_dir": str(args.pages_dir), "n_pages": len(files), "query": "the question text as it is",
        "regions_on_pages": {"min": n_pages_hit[0], "median": n_pages_hit[len(n_pages_hit) // 2], "max": n_pages_hit[-1]},
        "region_area_of_page": {"min": area[0], "median": area[len(area) // 2], "max": area[-1]},
        "base": base, "batch": args.batch, "flash_attention_2": flash,
        "note": "RegionRAG's requirements.txt has no flash-attn, so its code uses the default attention",
        "questions_file": str(args.questions), "questions_sha256": vc.sha256_file(args.questions),
        "gpu": torch.cuda.get_device_name(0),
        "versions": vc.versions("torch", "transformers", "peft", "vllm", "qwen-vl-utils", "pillow")})
    vc.log(f"wrote RegionRAG's best {vc.SAVE_TOP} regions of {len(items)} questions -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
