"""vine2/visrag_pages.py -- VisRAG's pages as the evidence of VINE answer-then-check.

    $VISRAG_ENV/bin/python -I vine2/visrag_pages.py --retrieval DIR --questions FILE \
        --pdf PDF --pages-dir DIR --out FILE [--pages 20] [--images 4]

VisRAG-Ret (compare40/visrag_retrieve.py, unchanged) ranks the manual's pages for each
question. This file turns that ranking into evidence, using nothing of VINE's:
  - the top PAGES pages, in VisRAG's order;
  - each page is one piece: its id is "Page X" (X the number printed on the page), and
    its text is the words printed on it, read straight from the manual PDF with PyMuPDF
    (its default settings), nothing cut, nothing added: no VINE piece, label, type or
    section number. A page with no words that can be read (a full-page drawing) stays,
    with no words; its picture, if it is one of the first pages, still goes;
  - the first IMAGES pages also carry their page picture (VisRAG's own 180 dpi
    rendering). A picture over 3.7 MB, or a set of pictures over 24 MB, is sent as
    JPEG, the rule of the VisRAG baseline (compare40/run_visrag.py, page_files), so
    the writer and the checker send the same files and stay under the API's limits.
The words are there so that the checker's quotes can be checked word for word: they are
the same words as on the page pictures.

Output: one JSON file in the layout vine2 reads, {id: {"question", "chunks", "figures"}},
and next to it FILE.manifest.json with the settings and fingerprints (the retrieval's model
and commit, the question file, the PDF). It stops if a question's retrieval was made for
another text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pdf_page_text(pdf: Path) -> Callable[[int], str]:
    """page number in the PDF (1, 2, ...) -> the words printed on that page."""
    import fitz  # PyMuPDF, in the VisRAG environment

    doc = fitz.open(str(pdf))

    def text(page_pdf: int) -> str:
        return doc.load_page(page_pdf - 1).get_text("text")      # PyMuPDF's own default settings
    return text


def clean(text: str) -> str:
    """The page's words as PyMuPDF gives them, with trailing spaces and runs of blank lines
    taken out (nothing else changed)."""
    lines = [ln.rstrip() for ln in str(text).replace("\r", "").split("\n")]
    out: List[str] = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return "\n".join(out).strip()


def build(questions: Dict[str, str], ranked: Dict[str, Dict[str, Any]], text_of: Callable[[int], str],
          pages_dir: Path, n_pages: int, n_images: int, page_files: Callable) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for qid, question in questions.items():
        r = ranked.get(qid)
        if r is None:
            raise SystemExit(f"STOPPED: {qid} has no VisRAG retrieval")
        if r.get("question_sha256") != hashlib.sha256(question.encode()).hexdigest():
            raise SystemExit(f"STOPPED: {qid}: the retrieval was made for a different question text")
        top = list(r.get("top_pages") or [])[:n_pages]
        if len(top) < n_pages:
            raise SystemExit(f"STOPPED: {qid}: the retrieval kept {len(top)} pages, {n_pages} asked for")
        pics = {int(p["page_pdf"]): p for p in page_files(top[:n_images], pages_dir)} if n_images else {}
        chunks, seen = [], {}
        for t in top:
            pdf_no = int(t["page_pdf"])
            printed = str(t.get("page_printed") or pdf_no)
            cid = f"Page {printed}"
            if cid in seen:                                   # two pages with the same printed number
                cid = f"Page {printed} (PDF page {pdf_no})"
            seen[cid] = True
            words = clean(text_of(pdf_no))
            c = {"chunk_id": cid, "source": "visrag_page", "content_type": "Page", "page_pdf": pdf_no,
                 "page_printed": printed, "text": words, "visrag_rank": t.get("rank"), "visrag_score": t.get("score")}
            if pdf_no in pics:
                c["image_path"] = pics[pdf_no]["image_path"]
                c["image_form"] = pics[pdf_no]["form"]
            chunks.append(c)
        out[qid] = {"question": question, "chunks": chunks, "figures": []}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval", required=True, type=Path, help="the folder visrag_retrieve.py wrote")
    ap.add_argument("--questions", required=True, type=Path, help="{id: question text}")
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--pages-dir", required=True, type=Path, help="VisRAG's page pictures")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pages", type=int, default=20, help="pages a question (1 to 20; default 20)")
    ap.add_argument("--images", type=int, default=4, help="of those, the first N go as pictures (0 to 4)")
    args = ap.parse_args()
    assert 1 <= args.pages <= 20 and 0 <= args.images <= min(4, args.pages), "--pages 1-20, --images 0-4"

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if not isinstance(questions, dict) or not all(isinstance(v, str) and v.strip() for v in questions.values()):
        raise SystemExit("STOPPED: the question file must be {id: question text}")
    man = json.loads((args.retrieval / "retrieval_manifest.json").read_text())
    if man.get("dry_run") or int(man.get("save_top", 0)) < args.pages:
        raise SystemExit(f"STOPPED: the retrieval is a dry run or kept fewer than {args.pages} pages")
    ranked = {}
    for line in (args.retrieval / "retrieval.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            ranked[r["question_id"]] = r
    sys.path.insert(0, str(REPO / "compare40"))
    from run_visrag import page_files  # noqa: E402  (the VisRAG baseline's own picture rule)

    ev = build(questions, ranked, pdf_page_text(args.pdf), args.pages_dir, args.pages, args.images, page_files)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(ev, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, args.out)
    meta = {"what": "VisRAG's top pages as evidence: the words printed on each page (PyMuPDF) and the first "
                    "pages' pictures; nothing of VINE's", "pages": args.pages, "images": args.images,
            "retrieval_dir": str(args.retrieval), "retrieval_model": man.get("model_id"),
            "retrieval_commit": man.get("model_commit_loaded"), "questions_file": str(args.questions),
            "questions_sha256": sha256_file(args.questions), "pdf": str(args.pdf), "pdf_sha256": sha256_file(args.pdf),
            "evidence_sha256": sha256_file(args.out), "n_questions": len(ev),
            "pages_with_no_words": sorted({c["chunk_id"] for e in ev.values() for c in e["chunks"] if not c["text"]}),
            "chars_per_question": sorted(sum(len(c["text"]) for c in e["chunks"]) for e in ev.values())}
    args.out.with_name(args.out.name + ".manifest.json").write_text(json.dumps(meta, indent=1))
    chars = meta["chars_per_question"]
    print(f"evidence -> {args.out} | {len(ev)} questions | {args.pages} pages each, {args.images} as pictures | "
          f"words a question: median {chars[len(chars) // 2]:,} characters, at most {chars[-1]:,} | "
          f"pages with no words: {len(meta['pages_with_no_words'])} {meta['pages_with_no_words'][:5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
