"""vine2/pages_writer.py -- the writer of VINE answer-then-check, on VisRAG's pages.

Started by vine2/run_qwen_pages.py (compare40/run_qwen_rag.py, unchanged, with this file in
place of compare40/run_vine_rag.py), once a question, with the same options:

    $RETR_ENV/bin/python -u vine2/pages_writer.py --kq PAGES_EVIDENCE --questions FILE \
        --models Qwen/Qwen3.8-27B-FP8 --only VQ001 --tag TAG --out DIR \
        --local-server URL --local-max-len N

The evidence is vine2/visrag_pages.py's file (VisRAG's top pages) or vine2/vis_evidence.py's
(M3DocRAG's or ViDoRAG's pages, RegionRAG's regions): each piece the words printed on it, the
first ones also as pictures. Nothing of VINE's.

The answer is ONE call to the answer model with GEMS-RAG's answer prompt (the few-shot style
of the untouched copy in gems_rag/), as in compare40/run_vine_rag.py and run_visrag.py. The
prompt is GEMS-RAG's own, with two differences that live in this file only:
  - the text evidence is each page whole, as "[Page X]" and its words (GEMS-RAG would group
    pieces by type and cut each to 1,400 characters; a page has no type);
  - the allowed citations are the pages, "Page X" (GEMS-RAG's own form for a page).
The page pictures are passed as GEMS-RAG passes pages ("[Image N] Page X (full page view)").
A region's picture (RegionRAG) is a part of a page, so it is named so: "[Image N] Page X
(region k) (part of the page)"; for pages the prompt is unchanged.

Output: answers_<tag>.jsonl in --out, one line per answer, in the format of
run_vine_rag.py's records (so run_qwen_rag.py merges them and vine2/check.py reads them).
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
C40 = REPO / "compare40"
MODELS = "Qwen/Qwen3.8-27B-FP8"
# the evidence sources this writer takes (the same as vine2/core.py PAGE_SOURCES), and the
# name each run's records carry
SYSTEMS = {"visrag_page": "vine2_visrag_pages", "m3docrag_page": "vine2_m3docrag_pages",
           "vidorag_page": "vine2_vidorag_pages", "regionrag_region": "vine2_regionrag_regions"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def page_text_block(chunks) -> str:
    """The text evidence: every page whole, in VisRAG's order."""
    return "\n\n".join(f"[{c['chunk_id']}]\n{str(c.get('text') or '').strip()}" for c in chunks)


def page_cites(chunks, used_visuals) -> list:
    cites = [str(c["chunk_id"]) for c in chunks]
    for kind, v in used_visuals:
        cite = f"Page {v.get('page_printed', '?')}"
        if kind == "Page" and cite not in cites:
            cites.append(cite)
    return cites


def region_visual_lines(used_visuals) -> list:
    """The picture lines for regions: GEMS-RAG's page line, named as a part of the page."""
    return [f"[Image {i}] Page {v.get('page_printed', '?')} (part of the page)"
            for i, (_kind, v) in enumerate(used_visuals, 1)]


def pages_vlm(VLM, regions: bool = False):
    """GEMS-RAG's VLM class, with only the evidence text and the allowed citations printed for
    pages (see the top); for regions, also the picture lines."""
    class PagesVLM(VLM):
        def _format_evidence_text(self, chunks):
            return page_text_block(chunks)

        def _format_allowed_cites(self, chunks, used_visuals):
            return page_cites(chunks, used_visuals)

    class RegionsVLM(PagesVLM):
        def _format_visual_lines(self, used_visuals):
            return region_visual_lines(used_visuals)
    return RegionsVLM if regions else PagesVLM


def pictures(entry):
    """The page pictures of one question's evidence, in VisRAG's order, and any file missing."""
    shown, missing = [], []
    for c in entry["chunks"]:
        p = c.get("image_path")
        if not p:
            continue
        if not Path(p).exists():
            missing.append(str(p))
            continue
        # GEMS-RAG labels a picture "Page " + this: the same name as the page's text ("Page 7 (PDF page 11)")
        shown.append({"image_path": str(p), "page_printed": str(c["chunk_id"])[len("Page "):]})
    return shown, missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kq", required=True, help="the page evidence file (vine2/visrag_pages.py)")
    ap.add_argument("--models", default=MODELS)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--local-server", default="")
    ap.add_argument("--local-max-len", type=int, default=0)
    args = ap.parse_args()
    assert bool(args.local_server) == bool(args.local_max_len), "--local-server needs --local-max-len"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"answers_{args.tag}.jsonl"
    kq_path = Path(args.kq)
    kq = json.loads(kq_path.read_text())
    questions = json.loads(Path(args.questions).read_text())
    ids = [q.strip() for q in args.only.split(",") if q.strip()] or list(questions)
    sources = set()
    for qid in ids:
        assert qid in kq, f"{qid} has no page evidence in {kq_path.name}"
        assert kq[qid]["question"] == questions[qid], f"{qid}: the page evidence was made for a different text"
        assert kq[qid]["chunks"] and all(c.get("source") in SYSTEMS for c in kq[qid]["chunks"]), \
            f"{qid}: {kq_path.name} is not a page evidence file"
        sources |= {c["source"] for c in kq[qid]["chunks"]}
    assert len(sources) == 1, f"{kq_path.name} mixes pieces of different systems: {sorted(sources)}"
    source = sources.pop()
    print(f"page evidence : {kq_path} ({len(ids)} questions, {source})")

    os.environ["MRAG_ENV"] = "hprc"
    os.environ["MRAG_BASE_DIR"] = str(Path(os.environ["SCRATCH"]) / "Beyond_RAG" / "gems_rag")
    sys.path.insert(0, str(GEMS))
    import mrag  # noqa: E402
    assert Path(mrag.__file__).resolve().is_relative_to(GEMS.resolve()), \
        f"imported the wrong mrag: {mrag.__file__} (must be the GEMS-RAG copy in {GEMS})"
    from mrag.config import CFG  # noqa: E402
    from mrag.vlm import VLM  # noqa: E402
    local = None
    if args.local_server:
        sys.path.insert(0, str(C40))
        import qwen_local  # noqa: E402
        from mrag.config import VLM_PROVIDERS, provider_of_model  # noqa: E402
        for m in args.models.split(","):
            if m.strip():
                qwen_local.use_local_server(CFG, VLM_PROVIDERS, provider_of_model, m.strip(), args.local_server)
        reasoning_file = out_dir / f"reasoning_{args.tag}.jsonl"
        print(f"answer model on our own server: {args.local_server} (window {args.local_max_len:,} tokens)")

    PagesVLM = pages_vlm(VLM, regions=source == "regionrag_region")

    done = {}
    if out_file.exists():
        for line in out_file.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "ok":
                    done[(r["model_id"], r["question_id"])] = r.get("prompt_sha256")

    CFG.set_answer_style("fewshot")
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    n_err = 0
    with out_file.open("a", encoding="utf-8") as w:
        for model in models:
            resolved = str(CFG.set_vlm_model(model))
            vlm = PagesVLM(CFG.vlm_model, CFG.vlm_model_fallback).load()
            if args.local_server:
                local = qwen_local.LocalServer(args.local_server, args.local_max_len)
                vlm._api_clients["dashscope"] = local      # GEMS-RAG's client for this provider
            print(f"\n=== {model} -> {resolved} ===")
            for i, qid in enumerate(ids, 1):
                question = questions[qid]
                chunks = kq[qid]["chunks"]
                pages, missing = pictures(kq[qid])
                if missing:
                    raise RuntimeError(f"{qid}: {len(missing)} page picture(s) not found, e.g. {missing[:3]}")
                prompt, sent = vlm._build_prompt_and_images(question, chunks, [], pages)
                sha = hashlib.sha256(prompt.encode()).hexdigest()
                if done.get((resolved, qid)) == sha:
                    print(f"[{i}/{len(ids)}] SKIP {qid} (already answered from this prompt)")
                    continue
                rec = {"system": SYSTEMS[source], "model_id": resolved, "question_id": qid,
                       "question": question, "kq_file": kq_path.name,
                       "n_pieces": len(chunks), "piece_ids": [c.get("chunk_id") for c in chunks],
                       "images": sent, "prompt_sha256": sha, "prompt_chars": len(prompt),
                       "prompt_style": CFG.prompt_style_answer, "max_new_tokens": CFG.max_new_tokens,
                       "started_at": now()}
                answer, err, t0 = "", None, time.time()
                mark, rmark = (len(local.calls), len(local.reasoning)) if local else (0, 0)
                for attempt in range(1, 4):                 # GEMS-RAG's runner: 3 tries, 8 s back-off
                    try:
                        vlm.last_api_debug = {}
                        answer = vlm.answer(question, chunks, [], pages, max_new_tokens=CFG.max_new_tokens)
                        if not answer or not answer.strip() or answer.strip().startswith("(VLM error"):
                            raise RuntimeError(f"no usable answer: {answer[:200]!r}")
                        err = None
                        break
                    except Exception as e:                  # noqa: BLE001
                        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                        if local and not local.transient(e):
                            break                           # our server, same seed: the same reply again
                        if attempt < 3:
                            time.sleep(8.0 * 2 ** (attempt - 1))
                rec.update({"status": "ok" if err is None else "error", "attempts": attempt,
                            "answer": answer if err is None else "", "error": err,
                            "api_debug": json.loads(json.dumps(vlm.last_api_debug or {}, default=str)),
                            "latency_s": round(time.time() - t0, 1), "completed_at": now()})
                if local:
                    rec["local_server"] = {"url": args.local_server, "window": args.local_max_len,
                                           "settings": qwen_local.settings(),
                                           "calls": json.loads(json.dumps(local.calls[mark:], default=str))}
                    with reasoning_file.open("a", encoding="utf-8") as rw:
                        rw.write(json.dumps({"model_id": resolved, "question_id": qid, "prompt_sha256": sha,
                                             "status": rec["status"], "completed_at": rec["completed_at"],
                                             "reasoning": local.reasoning[rmark:]}, ensure_ascii=False) + "\n")
                w.write(json.dumps(rec, ensure_ascii=False) + "\n")
                w.flush()
                n_err += err is not None
                print(f"[{i}/{len(ids)}] {'OK ' if err is None else 'ERR'} {qid} | {len(chunks)} pages, "
                      f"{len(sent)} pictures | {rec['latency_s']}s | {len(answer)} chars")
                time.sleep(2.0)                             # GEMS-RAG's runner: 2 s between calls
    print(f"\nanswers -> {out_file} | errors {n_err}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
