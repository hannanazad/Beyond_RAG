"""compare40/run_vine_rag.py -- system 2: VINE as plain RAG, on the 40 questions.

    $RETR_ENV/bin/python -u compare40/run_vine_rag.py --kq KQ_FILE [--only SAMPLE002,SAMPLE022] [--tag NAME]

The evidence is exactly what VINE's retrieval gives VINE's plan-maker and checkers (Kq),
read from VINE's own evidence file (parser_runs_faster/kq_r..._s....json; the job script
passes its name, worked out by VINE's own code). Each question gets:
  - all of its manual pieces (80 a question), each one whole;
  - every figure and table in the evidence, listed by id and caption, as VINE's
    checkers list them (model_verifiers._evidence_block);
  - their images, at most 4 image files, in VINE's order, every sheet of a figure
    counted (the checkers' own rule and limit, model_verifiers.verify).
Nothing is cut down.

The answer is ONE call to the answer model, with GEMS-RAG's answer prompt (the few-shot
style of the untouched copy in gems_rag/), so systems 1 and 2 differ only in the evidence.
There is no plan-maker, no checker and no figure filter (VINE has none).

So that VINE's evidence reaches the model whole, the question's own evidence is printed
in GEMS-RAG's format with these differences. They live in this file only; no file of
GEMS-RAG is changed:
  - no 1,400-character cut of a piece's text (GEMS-RAG cuts each piece);
  - table rows and figure readings are printed too, each with VINE's own label
    ("TABLE: printed in the manual"; "NOT NORMATIVE: a reading of the figure, not the
    manual's words"). GEMS-RAG prints only Standard, Guidance, Option and Support and
    would silently drop the rest (200 of the 1,600 pieces of the first 20 samples);
  - a list item carries its lead-in sentence, as VINE's checkers see it;
  - a "Figures and tables in the evidence" list, and those ids among the allowed
    citations (GEMS-RAG names only the figures whose images are attached).
GEMS-RAG's instructions and few-shot examples are left exactly as GEMS-RAG prints them.

Output: $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_<tag>.jsonl, one line per
answer: the evidence ids, the images, the prompt's SHA-256, the usage and the timing.
Run again, it skips an answer already made from the same prompt and makes it again if
the prompt changed (a new line; the last line of a (model, question) is the one to use).
A missing image file stops the run (as in run_gems_rag.py).
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
MODELS = "claude-sonnet-5-5,claude-fable-5"
MAX_IMAGES = 4                   # VINE's checkers' own image limit (model_verifiers.verify)
GROUP_ORDER = ("Standard", "Guidance", "Option", "Support")   # GEMS-RAG's order; others after


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def blank(v) -> bool:
    return v is None or str(v).strip() in ("", "None")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kq", required=True, help="VINE's evidence file (the job script passes it)")
    ap.add_argument("--models", default=MODELS, help=f"comma-separated model ids (default {MODELS})")
    ap.add_argument("--questions", default=str(HERE / "questions_40.json"))
    ap.add_argument("--out", default="", help="default $SCRATCH/Beyond_RAG/compare40_runs/vine_rag")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--only", default="", help="comma-separated question ids (a smoke test)")
    args = ap.parse_args()

    scratch = Path(os.environ["SCRATCH"])
    vine_data = scratch / "Beyond_RAG"
    out_dir = Path(args.out) if args.out else vine_data / "compare40_runs" / "vine_rag"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"answers_{args.tag}.jsonl"

    # VINE's evidence for each question
    kq_path = Path(args.kq)
    kq = json.loads(kq_path.read_text())
    questions = json.loads(Path(args.questions).read_text())
    ids = [q.strip() for q in args.only.split(",") if q.strip()] or list(questions)
    for qid in ids:
        assert qid in kq, f"{qid} has no VINE evidence in {kq_path.name}: run VINE's retrieval stage first"
        assert kq[qid]["question"] == questions[qid], f"{qid}: VINE's evidence was found for a different text"
    print(f"VINE evidence : {kq_path} ({len(ids)} questions)")

    # VINE's figure records: each image's printed page and its sheet caption
    fig_meta = {}
    for line in (vine_data / "mmrag_cache_v3" / "figures.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            fig_meta[Path(str(r.get("image_path") or "")).name] = r

    # GEMS-RAG's answer step, from the untouched copy
    os.environ["MRAG_ENV"] = "hprc"
    os.environ["MRAG_BASE_DIR"] = str(vine_data / "gems_rag")
    sys.path.insert(0, str(GEMS))
    import mrag  # noqa: E402
    assert Path(mrag.__file__).resolve().is_relative_to(GEMS.resolve()), \
        f"imported the wrong mrag: {mrag.__file__} (must be the GEMS-RAG copy in {GEMS})"
    from mrag.config import CFG  # noqa: E402
    from mrag.vlm import VLM  # noqa: E402

    class VineEvidenceVLM(VLM):
        """GEMS-RAG's VLM. Only the question's own evidence is printed differently (see the top)."""
        figure_lines: list = []        # set for each question
        figure_cites: list = []

        def _format_evidence_text(self, chunks):
            groups = {}
            for c in chunks:
                groups.setdefault(c.get("content_type", "Support"), []).append(c)
            order = list(GROUP_ORDER) + [g for g in groups if g not in GROUP_ORDER]
            blocks = []
            for ct in order:
                cs = groups.get(ct, [])
                if not cs:
                    continue
                blocks.append(f"=== {ct} provisions ===")
                for c in cs:
                    label = f" ({c['authority']})" if c.get("authority") else ""
                    blocks.append(
                        f"[Section {c.get('section_id')} §{c.get('ordinal')} — "
                        f"{c.get('section_title', '')} (p.{c.get('page_printed', '?')})]{label}\n"
                        f"{c.get('text', '') or ''}"
                    )
                blocks.append("")
            return "\n".join(blocks)

        def _format_allowed_cites(self, chunks, used_visuals):
            cites = super()._format_allowed_cites(chunks, used_visuals)
            return cites + [c for c in self.figure_cites if c not in cites]

        def _question_and_evidence_block(self, question, evidence_text, visual_lines, allowed_cites):
            block = VLM._question_and_evidence_block(question, evidence_text, visual_lines, allowed_cites)
            if not self.figure_lines:
                return block
            listing = "Figures and tables in the evidence:\n" + "\n".join(self.figure_lines) + "\n\n"
            return block.replace("Text evidence:\n", listing + "Text evidence:\n", 1)

    def pieces(qid):
        out = []
        for c in kq[qid]["chunks"]:
            c = dict(c)
            if not blank(c.get("lead_in")):
                c["text"] = f"{str(c['lead_in']).strip()} {c.get('text') or ''}".strip()
            for k in ("ordinal", "page_printed"):
                if blank(c.get(k)):
                    c[k] = "?"
            out.append(c)
        return out

    def figures(qid):
        """VINE's figures: every one listed (id and caption) and cited; images in VINE's order, at most 4."""
        shown, missing, lines, cites = [], [], [], []
        for f in kq[qid].get("figures") or []:
            fid = str(f.get("figure_id") or "")
            paths = [p for p in (f.get("image_paths") or [f.get("image_path")]) if p]
            if fid:
                lines.append(f"[{fid}] {f.get('caption', '')}")
                first = fig_meta.get(Path(paths[0]).name, {}) if paths else {}
                cites.append(f"{fid} (p.{first.get('page_printed') or '?'})")
            for p in paths:
                if not Path(p).exists():
                    missing.append(str(p))
                    continue
                if len(shown) < MAX_IMAGES:
                    m = fig_meta.get(Path(p).name, {})
                    shown.append({"figure_id": fid or m.get("figure_id", "?"),
                                  "caption": m.get("caption") or f.get("caption", ""),
                                  "page_printed": m.get("page_printed") or "?",
                                  "image_path": str(p)})
        return shown, missing, lines, cites

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
            vlm = VineEvidenceVLM(CFG.vlm_model, CFG.vlm_model_fallback).load()
            print(f"\n=== {model} -> {resolved} ===")
            for i, qid in enumerate(ids, 1):
                question = questions[qid]
                chunks = pieces(qid)
                figs, missing, vlm.figure_lines, vlm.figure_cites = figures(qid)
                if missing:
                    raise RuntimeError(f"{qid}: {len(missing)} image file(s) of VINE's evidence not found, "
                                       f"e.g. {missing[:3]}")
                prompt, sent = vlm._build_prompt_and_images(question, chunks, figs, [])
                sha = hashlib.sha256(prompt.encode()).hexdigest()
                if done.get((resolved, qid)) == sha:
                    print(f"[{i}/{len(ids)}] SKIP {qid} (already answered from this prompt)")
                    continue
                rec = {"system": "vine_as_rag", "model_id": resolved, "question_id": qid,
                       "question": question, "kq_file": kq_path.name,
                       "n_pieces": len(chunks), "piece_ids": [c.get("chunk_id") for c in chunks],
                       "figures_listed": [ln.split("]")[0].lstrip("[") for ln in vlm.figure_lines],
                       "images": sent, "prompt_sha256": sha, "prompt_chars": len(prompt),
                       "prompt_style": CFG.prompt_style_answer, "max_new_tokens": CFG.max_new_tokens,
                       "started_at": now()}
                answer, err, t0 = "", None, time.time()
                for attempt in range(1, 4):                 # GEMS-RAG's runner: 3 tries, 8 s back-off
                    try:
                        vlm.last_api_debug = {}
                        answer = vlm.answer(question, chunks, figs, [], max_new_tokens=CFG.max_new_tokens)
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
                print(f"[{i}/{len(ids)}] {'OK ' if err is None else 'ERR'} {qid} | {len(chunks)} pieces, "
                      f"{len(vlm.figure_lines)} figures listed, {len(sent)} images | {rec['latency_s']}s | "
                      f"{len(answer)} chars")
                time.sleep(2.0)                             # GEMS-RAG's runner: 2 s between calls
    print(f"\nanswers -> {out_file} | errors {n_err}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
