"""vine2/vidorag_ocr.py -- ViDoRAG's page pictures and its OCR text of every MUTCD page (CPU).

    $VINE_HOME/envs/vidorag_ocr/bin/python -I vine2/vidorag_ocr.py --pdf PDF --work DIR \
        --code $VINE_HOME/ext/vidorag --ocr-models $VINE_HOME/ext/vidorag_ocr_models

ViDoRAG (Wang et al., EMNLP 2025; github.com/Alibaba-NLP/ViDoRAG) searches page pictures and
the OCR text of the pages. This script makes both, with ViDoRAG's own code at the pinned
commit (PINNED) and nothing of VINE's, in ViDoRAG's own folder layout (WORK/data/MUTCD/):
  img/MUTCD_N.jpg    scripts/pdf2images.py: pdf2image.convert_from_path(pdf, thread_count=4)
                     (its default 200 dpi), saved as JPEG, N the page number from 1. That
                     script loops over its own dataset names, so its few lines are done here
                     the same way, 50 pages at a time (first_page/last_page: the same pictures,
                     less memory);
  ppocr/MUTCD_N.txt  scripts/ocr_triditional.py, imported as it is: its PP-OCRv3 models
                     (English detection and recognition, angle classifier, CPU, its settings),
                     and its main(image) -> layout-preserving text, one file a page. Its own
                     loop is in its __main__ block (made for its dataset), so it is done here.
A page already done is not done again; a file is written whole or not at all.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vis_common as vc  # noqa: E402

PINNED = "2c1ec39c5e3a04daa01f91545feaaa79512134bf"      # github.com/Alibaba-NLP/ViDoRAG, 11 Jan 2026
DATASET = "MUTCD"
OCR_MODELS = ("en_PP-OCRv3_det_infer", "en_PP-OCRv3_rec_infer", "ch_ppocr_mobile_v2.0_cls_infer")
BLOCK = 50


def page_name(n: int) -> str:
    return f"{DATASET}_{n}"


def render(pdf: Path, img_dir: Path, n_pages: int, convert) -> int:
    """ViDoRAG's pdf2images.py for one PDF: every page as img/MUTCD_N.jpg."""
    img_dir.mkdir(parents=True, exist_ok=True)
    for f in img_dir.glob(".*.part"):                    # left by a stopped job: ViDoRAG would read it
        f.unlink()
    made = 0
    for start in range(1, n_pages + 1, BLOCK):
        stop = min(start + BLOCK - 1, n_pages)
        if all((img_dir / f"{page_name(n)}.jpg").exists() for n in range(start, stop + 1)):
            continue
        images = convert(str(pdf), thread_count=4, first_page=start, last_page=stop)
        assert len(images) == stop - start + 1, (start, stop, len(images))
        for n, image in zip(range(start, stop + 1), images):
            out = img_dir / f"{page_name(n)}.jpg"
            if not out.exists():
                tmp = img_dir / f".{page_name(n)}.jpg.part"
                image.save(tmp, "JPEG")
                os.replace(tmp, out)
                made += 1
        vc.log(f"  pictures: pages {start}-{stop} of {n_pages}")
    return made


def ocr_all(img_dir: Path, txt_dir: Path, n_pages: int, ocr_main) -> int:
    """scripts/ocr_triditional.py's loop: each picture's text into ppocr/MUTCD_N.txt."""
    txt_dir.mkdir(parents=True, exist_ok=True)
    for f in txt_dir.glob(".*.part"):
        f.unlink()
    made = 0
    for n in range(1, n_pages + 1):
        out = txt_dir / f"{page_name(n)}.txt"
        if out.exists():
            continue
        text = ocr_main(str(img_dir / f"{page_name(n)}.jpg"))
        tmp = txt_dir / f".{page_name(n)}.txt.part"
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, out)
        made += 1
        if made % 50 == 0:
            vc.log(f"  OCR: {made} pages done this run (page {n} of {n_pages})")
    return made


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path, help="ViDoRAG's working folder (it holds data/MUTCD)")
    ap.add_argument("--code", required=True, type=Path)
    ap.add_argument("--ocr-models", required=True, type=Path)
    args = ap.parse_args()
    commit = vc.check_commit(args.code, PINNED)
    for m in OCR_MODELS:
        for f in ("inference.pdmodel", "inference.pdiparams"):
            if not (args.ocr_models / m / f).is_file():
                sys.exit(f"STOPPED: {args.ocr_models / m / f} is missing: run  bash vine2/vis_setup.sh vidorag")
    if not (args.ocr_models / "en_dict.txt").is_file():
        sys.exit(f"STOPPED: {args.ocr_models / 'en_dict.txt'} is missing: run  bash vine2/vis_setup.sh vidorag")
    from pdf2image import convert_from_path, pdfinfo_from_path
    poppler = vc.tool_version(["pdftoppm", "-v"])
    if poppler == "missing":
        sys.exit("STOPPED: pdftoppm (poppler) is missing on this node: ViDoRAG's pdf2image needs it")
    data = args.work / "data" / DATASET
    pdf_sha = vc.sha256_file(args.pdf)
    # the pictures and OCR text are never made again: the folder is tied to this PDF and OCR
    vc.stamp(data, {"pdf_sha256": pdf_sha, "code_commit": commit, "ocr": "PP-OCRv3 (FastDeploy, CPU)"})
    (data / "pdf").mkdir(parents=True, exist_ok=True)
    link = data / "pdf" / f"{DATASET}.pdf"
    if not link.exists():
        link.symlink_to(args.pdf.resolve())
    if link.resolve() != args.pdf.resolve():
        sys.exit(f"STOPPED: {link} points to {link.resolve()}, not {args.pdf}")
    n_pages = int(pdfinfo_from_path(str(link))["Pages"])
    vc.log(f"ViDoRAG {commit[:12]} | {n_pages} pages | work folder {args.work} | {poppler}")

    made = render(link, data / "img", n_pages, convert_from_path)
    vc.log(f"pictures: {made} made now, {n_pages} in all (pdf2image default 200 dpi, JPEG)")

    # ViDoRAG's OCR script, imported as it is; its model paths are relative to the folder it runs in
    here = Path.cwd()
    os.chdir(args.ocr_models)
    spec = importlib.util.spec_from_file_location("vidorag_ocr_traditional", args.code / "scripts/ocr_triditional.py")
    ocr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ocr)
    os.chdir(here)
    assert ocr.BACKEND.lower() == "cpu" and ocr.MIN_SCORE == 0.6, (ocr.BACKEND, ocr.MIN_SCORE)
    made = ocr_all(data / "img", data / "ppocr", n_pages, ocr.main)
    empty = sum(1 for n in range(1, n_pages + 1)
                if not (data / "ppocr" / f"{page_name(n)}.txt").read_text(encoding="utf-8").strip())
    man = {"system": "vidorag", "step": "pictures and OCR", "code_commit": commit, "n_pages": n_pages,
           "pictures": "pdf2image.convert_from_path(thread_count=4), default dpi 200, JPEG",
           "ocr": "scripts/ocr_triditional.py (FastDeploy PP-OCRv3, CPU, its settings)",
           "ocr_models_sha256": {m: {f: vc.sha256_file(args.ocr_models / m / f)
                                     for f in ("inference.pdmodel", "inference.pdiparams")} for m in OCR_MODELS},
           "en_dict_sha256": vc.sha256_file(args.ocr_models / "en_dict.txt"),
           "pages_with_no_text": empty, "pdf": str(args.pdf), "pdf_sha256": pdf_sha, "poppler": poppler,
           "versions": vc.versions("fastdeploy-python", "opencv-python", "numpy", "pillow", "pdf2image"),
           "finished_utc": vc.now()}
    (data / "ocr_manifest.json").write_text(json.dumps(man, indent=2))
    vc.log(f"OCR: {made} pages done now; {n_pages} in all; {empty} with no text -> {data / 'ppocr'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
