"""compare40/run_visrag.py -- baseline: VisRAG, on the 40 questions (answer step).

    $RETR_ENV/bin/python -u compare40/run_visrag.py --retrieval DIR [--pages 5]
        [--models claude-sonnet-5-5] [--only SAMPLE002,SAMPLE022] [--tag v1]

The evidence is VisRAG's: the top N page images of the MUTCD that VisRAG-Ret found for the
question (compare40/visrag_retrieve.py wrote them; N is --pages, 5 by default, as in the
VisRAG run of 27 Oct). There are no text pieces and no figure crops: VisRAG works from
page images only.

The answer is ONE call to the answer model with GEMS-RAG's answer prompt (the few-shot
style of the untouched copy in gems_rag/, the same prompt as systems 1 and 2), so VisRAG
differs from them only in the evidence. In that prompt each page is
"[Image N] Page X (full page view)" and the allowed citations are "Page X", as GEMS-RAG
handles page images. No file of GEMS-RAG is changed: its fingerprint must equal the one
of commit 6b61de1 (run_gems_rag.py).

A page image larger than 3.7 MB is sent as a JPEG (quality 92), as in the 27 Oct run, to
keep each image under the API's 5 MB limit. If the N images together would pass 24 MB,
all of them are sent as JPEG, to keep the request under the API's 32 MB limit. Each
record says which pages were sent and in which form.

Output: $SCRATCH/Beyond_RAG/compare40_runs/visrag/answers_p<N>_<tag>.jsonl, one line per
answer, in the format of the other compare40 answer files. Run again, it skips an answer
already made from the same prompt and the same images (the last line of a (model,
question) is the one to use).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True          # write nothing into gems_rag/
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
GEMS = REPO / "gems_rag"
MODELS = "claude-sonnet-5-5"
MAX_IMAGE_BYTES = 3_700_000             # one image (base64 then stays under 5 MB)
MAX_REQUEST_IMAGE_BYTES = 24_000_000    # all images of one request (base64 then under 32 MB)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def jpeg_of(png: Path) -> Path:
    jpg = png.with_suffix(".jpg")
    if not jpg.exists():
        from PIL import Image
        Image.open(png).convert("RGB").save(jpg, quality=92)
    return jpg


def page_files(top: list[dict], pages_dir: Path) -> list[dict]:
    """The image file to send for each page, and in which form (rules in the docstring)."""
    out = []
    for t in top:
        png = pages_dir / f"page_{int(t['page_pdf']):04d}.png"
        if not png.is_file():
            raise FileNotFoundError(f"{png} is missing: run the retrieval step (visrag_retrieve.py) first")
        out.append({**t, "png": png})
    total = sum(p["png"].stat().st_size for p in out)
    all_jpeg = total > MAX_REQUEST_IMAGE_BYTES
    for p in out:
        big = p["png"].stat().st_size > MAX_IMAGE_BYTES
        p["image_path"] = str(jpeg_of(p["png"]) if (all_jpeg or big) else p["png"])
        p["form"] = "jpeg" if (all_jpeg or big) else "png"
        p["why_jpeg"] = ("over 3.7 MB" if big else "the request would pass 24 MB") if p["form"] == "jpeg" else ""
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval", required=True, help="the folder visrag_retrieve.py wrote")
    ap.add_argument("--pages", type=int, default=5, help="page images per question (default 5)")
    ap.add_argument("--pages-dir", default="", help="the rendered pages (default: RETRIEVAL/../pages)")
    ap.add_argument("--models", default=MODELS, help=f"comma-separated model ids (default {MODELS})")
    ap.add_argument("--questions", default=str(HERE / "questions_40.json"))
    ap.add_argument("--out", default="", help="default $SCRATCH/Beyond_RAG/compare40_runs/visrag")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--only", default="", help="comma-separated question ids (a smoke test)")
    args = ap.parse_args()
    assert 1 <= args.pages <= 20, "--pages must be 1 to 20 (the retrieval keeps the top 20)"

    scratch = Path(os.environ["SCRATCH"])
    vine_data = scratch / "Beyond_RAG"
    retr = Path(args.retrieval)
    pages_dir = Path(args.pages_dir) if args.pages_dir else retr.parent / "pages"
    out_dir = Path(args.out) if args.out else vine_data / "compare40_runs" / "visrag"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"answers_p{args.pages}_{args.tag}.jsonl"

    # VisRAG's retrieval, made from the same question text
    questions = json.loads(Path(args.questions).read_text())
    manifest = json.loads((retr / "retrieval_manifest.json").read_text())
    assert not manifest.get("dry_run"), "this retrieval was a dry run (fake vectors): run it for real first"
    assert manifest.get("save_top", 0) >= args.pages, f"the retrieval kept {manifest.get('save_top')} pages"
    ranked = {}
    for line in (retr / "retrieval.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            ranked[r["question_id"]] = r
    ids = [q.strip() for q in args.only.split(",") if q.strip()] or list(questions)
    for qid in ids:
        assert qid in ranked, f"{qid} has no VisRAG retrieval in {retr}"
        assert ranked[qid]["question_sha256"] == hashlib.sha256(questions[qid].encode()).hexdigest(), \
            f"{qid}: the retrieval was made for a different question text"
    print(f"VisRAG retrieval: {retr} | model {manifest['model_id']} commit {manifest['model_commit_loaded']} "
          f"| {manifest['n_pages']} pages | top {args.pages} sent")

    # GEMS-RAG's answer step, from the untouched copy
    sys.path.insert(0, str(HERE))
    from run_gems_rag import GEMS_COMMIT, GEMS_FINGERPRINT, fingerprint  # noqa: E402
    n_files, fp = fingerprint(GEMS)
    assert fp == GEMS_FINGERPRINT, (f"gems_rag/ differs from gemsrag commit {GEMS_COMMIT[:7]} "
                                    f"({n_files} files): stopping")
    os.environ["MRAG_ENV"] = "hprc"
    os.environ["MRAG_BASE_DIR"] = str(vine_data / "gems_rag")
    sys.path.insert(0, str(GEMS))
    import mrag  # noqa: E402
    assert Path(mrag.__file__).resolve().is_relative_to(GEMS.resolve()), \
        f"imported the wrong mrag: {mrag.__file__} (must be the GEMS-RAG copy in {GEMS})"
    from mrag.config import CFG  # noqa: E402
    from mrag.vlm import VLM  # noqa: E402

    done = {}
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "ok":
                    done[(r["model_id"], r["question_id"])] = r.get("request_sha256")

    CFG.set_answer_style("fewshot")
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    n_err = 0
    with out_file.open("a", encoding="utf-8") as w:
        for model in models:
            resolved = str(CFG.set_vlm_model(model))
            vlm = VLM(CFG.vlm_model, CFG.vlm_model_fallback).load()
            print(f"\n=== {model} -> {resolved} | prompt {CFG.prompt_style_answer} ===")
            for i, qid in enumerate(ids, 1):
                question = questions[qid]
                sent_pages = page_files(ranked[qid]["top_pages"][:args.pages], pages_dir)
                vlm_pages = [{"image_path": p["image_path"], "page_printed": p["page_printed"]}
                             for p in sent_pages]
                prompt, images = vlm._build_prompt_and_images(question, [], [], vlm_pages)
                sha = hashlib.sha256(prompt.encode()).hexdigest()
                req = hashlib.sha256((sha + "".join(sha256_file(Path(p)) for p in images)).encode()).hexdigest()
                if done.get((resolved, qid)) == req:
                    print(f"[{i}/{len(ids)}] SKIP {qid} (already answered from this prompt and these images)")
                    continue
                rec = {"system": "visrag", "model_id": resolved, "question_id": qid, "question": question,
                       "retrieval_model": manifest["model_id"],
                       "retrieval_commit": manifest["model_commit_loaded"],
                       "top_k_pages": args.pages,
                       "pages_sent": [{k: p[k] for k in ("rank", "page_pdf", "page_printed", "score", "form",
                                                         "why_jpeg")} for p in sent_pages],
                       "images": [str(p) for p in images], "prompt_sha256": sha, "request_sha256": req,
                       "prompt_chars": len(prompt), "prompt_style": CFG.prompt_style_answer,
                       "max_new_tokens": CFG.max_new_tokens, "started_at": now()}
                answer, err, t0 = "", None, time.time()
                for attempt in range(1, 4):                 # GEMS-RAG's runner: 3 tries, 8 s back-off
                    try:
                        vlm.last_api_debug = {}
                        answer = vlm.answer(question, [], [], vlm_pages, max_new_tokens=CFG.max_new_tokens)
                        if not answer or not answer.strip() or answer.strip().startswith("(VLM error"):
                            raise RuntimeError(f"no usable answer: {answer[:200]!r}")
                        err = None
                        break
                    except Exception as e:                  # noqa: BLE001
                        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                        if attempt < 3:
                            time.sleep(8.0 * 2 ** (attempt - 1))
                rec.update({"status": "ok" if err is None else "error", "attempts": attempt,
                            "answer": answer if err is None else "", "error": err,
                            "api_debug": json.loads(json.dumps(vlm.last_api_debug or {}, default=str)),
                            "latency_s": round(time.time() - t0, 1), "completed_at": now()})
                w.write(json.dumps(rec, ensure_ascii=False) + "\n")
                w.flush()
                n_err += err is not None
                forms = ",".join(p["form"] for p in sent_pages)
                print(f"[{i}/{len(ids)}] {'OK ' if err is None else 'ERR'} {qid} | pages "
                      f"{[p['page_printed'] for p in sent_pages]} ({forms}) | {rec['latency_s']}s | "
                      f"{len(answer)} chars")
                time.sleep(2.0)                             # GEMS-RAG's runner: 2 s between calls
    print(f"\nanswers -> {out_file} | errors {n_err}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
