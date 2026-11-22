"""vine2/vis_evidence.py -- what M3DocRAG, ViDoRAG or RegionRAG found, as the evidence of VINE
answer-then-check (the same layout as vine2/visrag_pages.py makes for VisRAG).

    $VISRAG_ENV/bin/python -I vine2/vis_evidence.py --system SYSTEM --retrieval DIR \
        --questions FILE --pdf PDF --out FILE [--pieces 20] [--images 4]

It reads the system's retrieval (vine2/vis_common.py layout) and the manual PDF, and nothing
of VINE's: no VINE piece, label, type or section number. For each question, in the system's
own order, at most PIECES pieces:
  m3docrag   its top pages. A piece is a page, "Page X" (X the number printed on the page),
             with the words printed on it read straight from the PDF (PyMuPDF defaults, as for
             VisRAG); the first IMAGES pages also go as their picture (M3DocRAG's own, 144 dpi).
  vidorag    the pages ViDoRAG returned (5 to 20), in its order (page order). A piece is a
             page with the text ViDoRAG gave for it (its OCR of the page), as it is; the
             IMAGES pages ViDoRAG's picture side ranked highest also go as their picture
             (ViDoRAG's own JPEG).
  regionrag  its best regions. A piece is a region, "Page X (region k)" (k counts the regions
             of that page, in RegionRAG's order), with the words printed inside its box, read
             from the PDF (PyMuPDF defaults, clipped to the box); the first IMAGES regions also
             go as their picture, the region cut from the page picture RegionRAG scored.
Two pages printed with the same number get "Page X (PDF page N)". A page or region with no
words stays, with no words. The picture-size rule is the VisRAG baseline's
(compare40/run_visrag.py): a PNG over 3.7 MB, or a set over 24 MB, is sent as JPEG.

Output: {id: {"question", "chunks", "figures": []}} and FILE.manifest.json.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import vis_common as vc  # noqa: E402
from visrag_pages import clean  # noqa: E402  (the same clean-up of the page words as VisRAG's run)

SOURCE = {"m3docrag": "m3docrag_page", "vidorag": "vidorag_page", "regionrag": "regionrag_region"}


def picture_rule(paths: List[Path], max_one: int, max_all: int, jpeg_of: Callable,
                 smaller_jpeg: Callable = None) -> List[Tuple[str, str]]:
    """(file to send, its form) for each picture: the VisRAG baseline's rule. A JPEG is sent as
    it is, unless it is over the one-picture limit: then a copy saved at a lower JPEG quality."""
    total = sum(p.stat().st_size for p in paths)
    out = []
    for p in paths:
        if p.suffix.lower() in (".jpg", ".jpeg"):
            if p.stat().st_size > max_one and smaller_jpeg is not None:
                out.append((str(smaller_jpeg(p)), "jpeg"))
            else:
                out.append((str(p), "jpeg"))
        elif total > max_all or p.stat().st_size > max_one:
            out.append((str(jpeg_of(p)), "jpeg"))
        else:
            out.append((str(p), "png"))
    return out


class Pdf:
    """The manual: each page's printed number, its words, the words inside a box."""

    def __init__(self, path: Path):
        import fitz
        self.fitz = fitz
        self.doc = fitz.open(str(path))
        self.n = self.doc.page_count

    def label(self, page_pdf: int) -> str:
        return str(self.doc.load_page(page_pdf - 1).get_label() or page_pdf)

    def words(self, page_pdf: int) -> str:
        return self.doc.load_page(page_pdf - 1).get_text("text")

    def words_in(self, page_pdf: int, box: List[float], image_size: List[int]) -> str:
        """The words inside a box given in pixels of the page's picture (height, width)."""
        page = self.doc.load_page(page_pdf - 1)
        if page.rotation:
            raise SystemExit(f"STOPPED: PDF page {page_pdf} is rotated ({page.rotation}); a region box "
                             f"cannot be mapped to its words safely")
        r = page.rect
        h, w = image_size
        sx, sy = r.width / w, r.height / h
        x1, y1, x2, y2 = box
        clip = self.fitz.Rect(r.x0 + x1 * sx, r.y0 + y1 * sy, r.x0 + x2 * sx, r.y0 + y2 * sy)
        return page.get_text("text", clip=clip)


def build(system: str, questions: Dict[str, str], ranked: Dict[str, Dict[str, Any]], pdf, n_pieces: int,
          n_images: int, pictures: Callable, crop: Callable) -> Dict[str, Any]:
    """`pdf`: label(n), words(n), words_in(n, box, size); `pictures(paths)` -> [(file, form)];
    `crop(page_picture, box, out_name)` -> the region's picture file."""
    source = SOURCE[system]
    out: Dict[str, Any] = {}
    for qid, question in questions.items():
        r = ranked.get(qid)
        if r is None:
            raise SystemExit(f"STOPPED: {qid} has no {system} retrieval")
        if r.get("system") != system:
            raise SystemExit(f"STOPPED: {qid}: the retrieval is {r.get('system')}'s, not {system}'s")
        if r.get("question_sha256") != vc.text_sha(question):
            raise SystemExit(f"STOPPED: {qid}: the retrieval was made for a different question text")
        items = list(r.get("items") or [])[:n_pieces]
        if not items:
            raise SystemExit(f"STOPPED: {qid}: the retrieval found nothing")
        if system != "vidorag" and len(items) < n_pieces:
            raise SystemExit(f"STOPPED: {qid}: the retrieval kept {len(items)} items, {n_pieces} asked for")
        chunks, seen, per_page, page_ids = [], set(), {}, {}
        for it in items:
            n = int(it["page_pdf"])
            if n not in page_ids:
                printed = pdf.label(n)
                pid = f"Page {printed}"
                if pid in seen:                                    # two pages with the same printed number
                    pid = f"Page {printed} (PDF page {n})"
                page_ids[n] = pid
                seen.add(pid)
            c = {"source": source, "content_type": "Page", "page_pdf": n, "page_printed": page_ids[n][len("Page "):],
                 "rank": it.get("rank"), "score": it.get("score")}
            if system == "regionrag":
                per_page[n] = per_page.get(n, 0) + 1
                c["chunk_id"] = f"{page_ids[n]} (region {per_page[n]})"
                c["page_printed"] = c["chunk_id"][len("Page "):]
                c["box"], c["image_size"] = it["box"], it["image_size"]
                c["text"] = clean(pdf.words_in(n, it["box"], it["image_size"]))
            else:
                c["chunk_id"] = page_ids[n]
                c["text"] = clean(it["text"]) if system == "vidorag" else clean(pdf.words(n))
                if system == "vidorag":
                    c["visual_rank"] = it.get("visual_rank")
            c["_picture"] = it.get("image_path")
            chunks.append(c)
        if len({c["chunk_id"] for c in chunks}) != len(chunks):
            raise SystemExit(f"STOPPED: {qid}: two pieces have the same id")
        # which pieces carry a picture
        if system == "vidorag":
            order = sorted(range(len(chunks)), key=lambda i: (chunks[i].get("visual_rank") or 10 ** 6, i))
        else:
            order = list(range(len(chunks)))
        with_pic = sorted(order[:n_images])
        files = []
        for i in with_pic:
            c = chunks[i]
            if system == "regionrag":
                files.append(Path(crop(c["_picture"], c["box"], f"{qid}_region{int(c['rank']):02d}.png")))
            else:
                files.append(Path(c["_picture"]))
        missing = [str(f) for f in files if not f.is_file()]
        if missing:
            raise SystemExit(f"STOPPED: {qid}: picture(s) not found, e.g. {missing[:3]}")
        for i, (f, form) in zip(with_pic, pictures(files)):
            chunks[i]["image_path"], chunks[i]["image_form"] = f, form
        for c in chunks:
            c.pop("_picture", None)
        out[qid] = {"question": question, "chunks": chunks, "figures": []}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=sorted(SOURCE))
    ap.add_argument("--retrieval", required=True, type=Path)
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pieces", type=int, default=20)
    ap.add_argument("--images", type=int, default=4)
    args = ap.parse_args()
    assert 1 <= args.pieces <= vc.SAVE_TOP and 0 <= args.images <= min(4, args.pieces), "--pieces 1-20, --images 0-4"
    questions = vc.load_questions(args.questions)
    man = json.loads((args.retrieval / "retrieval_manifest.json").read_text())
    if man.get("system") != args.system or man.get("dry_run") or int(man.get("save_top", 0)) < args.pieces:
        raise SystemExit(f"STOPPED: {args.retrieval} is not a finished {args.system} retrieval of {args.pieces} items")
    ranked = vc.read_retrieval(args.retrieval)
    sys.path.insert(0, str(REPO / "compare40"))
    from run_visrag import MAX_IMAGE_BYTES, MAX_REQUEST_IMAGE_BYTES, jpeg_of  # noqa: E402

    crops_dir = args.out.parent / f"{args.out.stem}_regions"
    if crops_dir.exists():                              # made again with the evidence: never an old cut
        shutil.rmtree(crops_dir)

    def crop(page_picture: str, box: List[float], name: str) -> str:
        from PIL import Image
        crops_dir.mkdir(parents=True, exist_ok=True)
        out = crops_dir / name
        with Image.open(page_picture) as im:
            part = im.crop(tuple(box))                  # as RegionRAG cuts a region (image.crop(box))
            tmp = out.with_suffix(".part.png")
            part.save(tmp)
        os.replace(tmp, out)
        return str(out)

    small_dir = args.out.parent / f"{args.out.stem}_smaller"

    def smaller_jpeg(p: Path) -> Path:
        """A copy under the one-picture limit: quality 60, then 0.85 times smaller each try."""
        from PIL import Image
        small_dir.mkdir(parents=True, exist_ok=True)
        out = small_dir / p.name
        with Image.open(p) as im:
            im = im.convert("RGB")
            scale = 1.0
            while True:
                sized = im if scale == 1.0 else im.resize((int(im.width * scale), int(im.height * scale)))
                sized.save(out, quality=60)
                if out.stat().st_size <= MAX_IMAGE_BYTES or scale < 0.3:
                    break
                scale *= 0.85
        if out.stat().st_size > MAX_IMAGE_BYTES:
            raise SystemExit(f"STOPPED: {p} cannot be made small enough to send")
        return out

    def pictures(paths: List[Path]):
        return picture_rule(paths, MAX_IMAGE_BYTES, MAX_REQUEST_IMAGE_BYTES, jpeg_of, smaller_jpeg)

    ev = build(args.system, questions, ranked, Pdf(args.pdf), args.pieces, args.images, pictures, crop)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, args.out)
    chars = sorted(sum(len(c["text"]) for c in e["chunks"]) for e in ev.values())
    counts = sorted(len(e["chunks"]) for e in ev.values())
    meta = {"what": f"{args.system}'s retrieval as evidence; nothing of VINE's", "system": args.system,
            "source": SOURCE[args.system], "pieces": args.pieces, "images": args.images,
            "retrieval_dir": str(args.retrieval), "retrieval_code_commit": man.get("code_commit"),
            "retrieval_models": man.get("models"), "questions_file": str(args.questions),
            "questions_sha256": vc.sha256_file(args.questions), "pdf": str(args.pdf),
            "pdf_sha256": vc.sha256_file(args.pdf), "evidence_sha256": vc.sha256_file(args.out),
            "n_questions": len(ev), "pieces_per_question": {"min": counts[0], "max": counts[-1]},
            "pieces_with_no_words": sorted({f"{q}:{c['chunk_id']}" for q, e in ev.items() for c in e["chunks"]
                                            if not c["text"]}),
            "chars_per_question": chars, "versions": vc.versions("pymupdf", "pillow")}
    args.out.with_name(args.out.name + ".manifest.json").write_text(json.dumps(meta, indent=1))
    print(f"evidence -> {args.out} | {len(ev)} questions | {counts[0]}-{counts[-1]} pieces each, up to "
          f"{args.images} as pictures | words a question: median {chars[len(chars) // 2]:,} characters, at most "
          f"{chars[-1]:,} | pieces with no words: {len(meta['pieces_with_no_words'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
