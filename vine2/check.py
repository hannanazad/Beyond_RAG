"""vine2/check.py -- stage B of VINE answer-then-check: the checker judges every statement.

    $RETR_ENV/bin/python -u vine2/check.py --kq KQ_FILE --questions QUESTIONS_FILE \
        --drafts DRAFTS_JSONL --tag TAG [--only VQ001,VQ002] [--workers 4]

Stage A (vine2/answer_job.slurm) has the writer model, Qwen3.8-27B on our own GPUs, answer
every question from ALL of VINE's evidence, with the plain-RAG runner
(compare40/run_qwen_rag.py, unchanged). Its answers are the drafts read here.

For each question this stage:
  1. splits the draft into numbered statements (core.split_statements);
  2. asks the checker model (Claude Sonnet 5.5, effort high) to judge every statement
     against the whole question, all the evidence and the same images the writer saw,
     and to list what the draft is missing (core.checker_prompt);
  3. verifies the checker's work in code: every quote must be found word for word in the
     evidence piece it names; arithmetic written as "a x b = c" is recomputed; every
     provision in the draft's citation list must be in the evidence (core.read_reply,
     core.arithmetic_checks, core.citation_checks);
  4. writes the final answer: corrections and additions only where a quote was verified,
     everything else kept and marked (core.assemble).
The writer and the checker are different models, and the checker is the stronger one.

There is always an answer:
  - no draft for a question (the writer failed): the checker model writes one from the
    same evidence, marked as not independently checked;
  - the check fails (the API, a refusal, a reply that cannot be read even when asked
    again): the draft is given as it is, marked unchecked.

Every checker reply is saved in a reply cache (mrag/vine/anthropic_client.py), so a run
can be repeated exactly, and a stopped run goes on where it stopped at no extra cost.
Output, in $SCRATCH/Beyond_RAG/vine2_runs/TAG/ (or --out):
  final.jsonl          one record per question: the draft, the final answer, every
                       statement's verdict with its verified quotes, the additions, the
                       code checks, the checker's calls and cost;
  answers_final.md     the final answers with every mark;
  answers_final_clean.md                the same, without marks, for grading;
  answers_final_corrections_only.md     the clean answers without the additions;
  answers_draft.md     the writer's drafts as they were, for grading the same way;
  manifest.json        settings, file fingerprints, totals.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from vine2 import core  # noqa: E402

WRITER = "Qwen/Qwen3.8-27B-FP8"     # stage A's model (compare40/run_qwen_rag.py); read from the drafts
CHECKER = "claude-sonnet-5-5"
EFFORT = "high"
MAX_TOKENS = 32000
MAX_IMAGES = 4
REASK_NOTE = ("\n\nYour previous reply could not be read as one JSON object. Reply now with the "
              "JSON object only, exactly in the form given above.")
FALLBACK_WRITER_RULES = """Answer the question about the MUTCD (11th Edition) from the evidence below only.
Start with a direct answer. Then give the provisions that decide it, grouped as Standards
(shall), Guidance (should), Options (may) and Support, each with its section and paragraph
and how it applies to the facts of the question. Give any value from a table or figure with
its source. Say plainly what the evidence leaves open. Do not use outside knowledge."""


def say(*a: Any) -> None:
    print(*a, flush=True)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass                              # a line cut off by a stopped job
    return out


def latest_drafts(path: Path, writer: str, kq_name: str, checker: str,
                  questions: Dict[str, str]) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """The writer's answer for each question: its last good record for this evidence file.

    `writer` empty: the file must hold good answers from exactly one model, and that model
    must not be the checker (the writer and the checker are different models).
    Every good answer must be to the same question text as in `questions`: an answer to
    another question with the same id (an old file) stops the run."""
    good = [r for r in read_jsonl(path)
            if isinstance(r, dict) and r.get("status") == "ok" and r.get("kq_file") == kq_name
            and str(r.get("answer") or "").strip()]
    other = sorted({str(r.get("question_id")) for r in good
                    if r.get("question_id") in questions and r.get("question") != questions[r["question_id"]]})
    if other:
        raise SystemExit(f"STOPPED: {len(other)} drafts in {path.name} answer another question text with the same "
                         f"id (an old file?), e.g. {other[:5]}. Move every {path.stem}*.jsonl file into another "
                         f"folder and run the launcher again.")
    models = sorted({str(r.get("model_id")) for r in good})
    if writer:
        good = [r for r in good if r.get("model_id") == writer]
    elif len(models) > 1:
        raise SystemExit(f"STOPPED: the drafts file holds answers from several models {models}: give --writer")
    name = writer or (models[0] if models else "")
    if name and name == checker:
        raise SystemExit(f"STOPPED: the drafts were written by the checker model itself ({name})")
    out: Dict[str, Dict[str, Any]] = {}
    for r in good:
        out[r["question_id"]] = r
    return out, name


def image_list(entry: Dict[str, Any], draft: Optional[Dict[str, Any]]) -> List[str]:
    """The images the writer was shown (from its record); without a record, VINE's own
    order, at most 4 files (as compare40/run_vine_rag.py picks them)."""
    if draft and isinstance(draft.get("images"), list):
        return [str(p) for p in draft["images"]][:MAX_IMAGES]
    out: List[str] = []
    for f in entry.get("figures") or []:
        for p in [p for p in (f.get("image_paths") or [f.get("image_path")]) if p]:
            if len(out) < MAX_IMAGES:
                out.append(str(p))
    for c in entry.get("chunks") or []:                 # whole pages that carry their picture
        if core.is_page(c) and c.get("image_path") and len(out) < MAX_IMAGES:
            out.append(str(c["image_path"]))
    return out


def image_ids(entry: Dict[str, Any], paths: List[str]) -> List[str]:
    """The evidence id of each attached image: its figure, or its page."""
    names = {}
    for f in entry.get("figures") or []:
        for p in [p for p in (f.get("image_paths") or [f.get("image_path")]) if p]:
            names[Path(str(p)).name] = str(f.get("figure_id") or Path(str(p)).stem)
    for c in entry.get("chunks") or []:
        if core.is_page(c) and c.get("image_path"):
            names[Path(str(c["image_path"])).name] = str(c.get("chunk_id"))
    return [names.get(Path(p).name, Path(p).stem) for p in paths]


class Checker:
    """One checker conversation per thread (the HTTP session is not shared)."""

    def __init__(self, cache_dir: Path, checker: str, effort: str, max_tokens: int, cache_only: bool):
        from mrag.vine.anthropic_client import cost_usd, make_ask_anthropic
        self.cost_usd = cost_usd
        self.local = threading.local()
        self.args = dict(model=checker, effort=effort, max_tokens=max_tokens, cache_dir=str(cache_dir),
                         cache_only=cache_only, say=say, timeout=1800, max_retries=2)
        self.make = make_ask_anthropic
        self.model = checker

    def ask(self):
        if not hasattr(self.local, "ask"):
            self.local.ask = self.make(**self.args)
        return self.local.ask


NORMAL_STOPS = ("end_turn", "stop_sequence")
MAX_SPLIT_DEPTH = 2            # a reply cut off at the token limit: check the statements in halves, then quarters


def _ask_checker(ask, question: str, entry: Dict[str, Any], statements: List[Dict[str, Any]],
                 ids: List[str], paths: List[str], nums: List[int], depth: int, additions: bool,
                 log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Judge statements `nums` and merge the replies: {"statements": [...], "additions": [...],
    "failed": [numbers left unjudged], "why": the last failure}.

    - the reply ended normally but its JSON cannot be read: asked once more, the same way;
    - cut off at the token limit: asked again for each half of `nums` (two levels at most;
      the additions are asked for with the second half only);
    - a refusal, a context-window stop or an API failure: not asked again; the statements
      stay unjudged."""
    whole = len(nums) == sum(1 for s in statements if s["kind"] == "claim")
    prompt = core.checker_prompt(question, entry, statements, ids, None if whole else nums, additions)
    for attempt, p in enumerate((prompt, prompt + REASK_NOTE), 1):
        try:
            raw = ask(p, paths)
        except Exception as e:                                         # noqa: BLE001
            log.append({"nums": [nums[0], nums[-1]], "attempt": attempt, "error": repr(e)[:400]})
            return {"statements": [], "additions": [], "failed": list(nums),
                    "why": f"the checker could not be reached: {e!r}"[:500]}
        stop = (ask.last or {}).get("finish_reason")
        reply = core.extract_json(raw) if stop in NORMAL_STOPS else None
        log.append({"nums": [nums[0], nums[-1]], "attempt": attempt, "stop": stop, "depth": depth,
                    "readable": reply is not None, "prompt_sha256": sha(p)})
        if reply is not None and isinstance(reply.get("statements"), (list, dict)):
            got = core._as_list(reply.get("statements"))
            if not whole:                      # a verdict on a statement it was not asked about is not used
                wanted = set(nums)
                got = [r for r in got if isinstance(r, dict) and re.search(r"\d+", str(r.get("n")))
                       and int(re.search(r"\d+", str(r.get("n"))).group(0)) in wanted]
            return {"statements": got,
                    "additions": core._as_list(reply.get("additions")) if additions else [],
                    "failed": [], "why": ""}
        if stop == "max_tokens" and len(nums) > 1 and depth < MAX_SPLIT_DEPTH:
            half = len(nums) // 2
            a = _ask_checker(ask, question, entry, statements, ids, paths, nums[:half], depth + 1, False, log)
            b = _ask_checker(ask, question, entry, statements, ids, paths, nums[half:], depth + 1, additions, log)
            return {"statements": a["statements"] + b["statements"], "additions": b["additions"],
                    "failed": a["failed"] + b["failed"], "why": b["why"] or a["why"]}
        if stop not in NORMAL_STOPS:
            return {"statements": [], "additions": [], "failed": list(nums),
                    "why": f"the checker's reply stopped with {stop}"}
    return {"statements": [], "additions": [], "failed": list(nums),
            "why": "the checker's reply could not be read, twice"}


def check_one(qid: str, question: str, entry: Dict[str, Any], draft: Optional[Dict[str, Any]],
              checker: Checker, fallback_writer: bool) -> Dict[str, Any]:
    """Stage B for one question. Never raises: every failure gives an answer and a reason."""
    paths = image_list(entry, draft)
    missing = [p for p in paths if not Path(p).exists()]
    paths = [p for p in paths if Path(p).exists()]
    ids = image_ids(entry, paths)
    idx = core.evidence_index(entry, ids)
    rec: Dict[str, Any] = {"question_id": qid, "question": question, "started_at": now(),
                           "images": paths, "images_missing": missing, "calls": []}
    ask = checker.ask()
    mark = len(ask.calls)

    def finish(**kw: Any) -> Dict[str, Any]:
        calls = ask.calls[mark:]
        rec.update(kw)
        rec["calls"] = json.loads(json.dumps(calls, default=str))
        rec["cost_usd"] = checker.cost_usd(calls, checker.model)
        rec["completed_at"] = now()
        return rec

    # 1. the draft, or the fallback writer
    if draft is None:
        if not fallback_writer:
            return finish(status="no_answer", final_answer="", final_answer_clean="",
                          reason="the writer gave no answer")
        prompt = (f"{FALLBACK_WRITER_RULES}\n\n##### QUESTION\n{question.strip()}\n\n##### EVIDENCE\n"
                  f"{core.evidence_block(entry)}\n\nAnswer now.")
        try:
            text = ask(prompt, paths)
        except Exception as e:                                         # noqa: BLE001
            return finish(status="no_answer", final_answer="", final_answer_clean="",
                          reason=f"the writer gave no answer, and the fallback failed: {e!r}"[:800])
        if not text.strip() or (ask.last or {}).get("finish_reason") not in NORMAL_STOPS:
            return finish(status="no_answer", final_answer="", final_answer_clean="",
                          reason=f"fallback answer unusable (stop reason {(ask.last or {}).get('finish_reason')})")
        return finish(status="fallback", draft_model=checker.model, fallback_answer=text, draft_sha256=sha(text),
                      reason="the writer gave no answer; the checker model wrote this one (unchecked)",
                      final_answer=core.unchecked(text, "the writer model gave no answer, so the checker "
                                                        "model wrote this one; it is not independently checked"),
                      final_answer_clean=text, final_answer_corrections_only=text)

    text = str(draft["answer"])
    rec.update({"draft_model": draft.get("model_id"), "draft": text, "draft_sha256": sha(text),
                "draft_prompt_sha256": draft.get("prompt_sha256")})
    statements = core.split_statements(text)
    rec["statements_split"] = [{k: s[k] for k in ("n", "kind", "row", "section", "text", "start", "end")}
                               for s in statements]
    nums = [s["n"] for s in statements if s["kind"] == "claim"]
    if not nums:
        return finish(status="unchecked", final_answer=core.unchecked(text, "no statements found to check"),
                      final_answer_clean=text, final_answer_corrections_only=text)

    # 2. the checker
    log: List[Dict[str, Any]] = []
    got = _ask_checker(ask, question, entry, statements, ids, paths, nums, 0, True, log)
    rec["checker_requests"] = log
    if not got["statements"]:
        why = got["why"] or "the checker judged no statement"
        return finish(status="unchecked", final_answer=core.unchecked(text, why), final_answer_clean=text,
                      final_answer_corrections_only=text, reason=why)

    # 3. code checks the checker, and 4. the final answers
    checked = core.read_reply({"statements": got["statements"], "additions": got["additions"]},
                              statements, idx, question)
    citations = core.citation_checks(statements, idx)
    marked, clean, counts, corr_only = core.assemble(text, statements, checked, citations, idx, checker.model,
                                                     got["failed"], got["why"])
    by_n = {s["n"]: s for s in statements if s["kind"] == "claim"}
    for r in checked["statements"]:
        r["text"], r["section"] = by_n[r["n"]]["text"], by_n[r["n"]]["section"]
    return finish(status="checked", final_answer=marked, final_answer_clean=clean,
                  final_answer_corrections_only=corr_only, counts=counts,
                  statements=checked["statements"], unjudged=got["failed"],
                  unjudged_why=got["why"] if got["failed"] else "", additions=checked["additions"],
                  additions_rejected=checked["additions_rejected"], citations=citations)


def write_md(path: Path, records: Dict[str, Dict[str, Any]], ids: List[str], field: str,
             drafts: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """One section per question. For the drafts file, a question the writer did not answer
    says so (the checker model's fallback answer is not a writer draft); a question not
    checked yet shows its draft from the drafts file."""
    parts = []
    for q in ids:
        r = records.get(q) or {}
        empty = "(no writer draft)" if field == "draft" else "(no answer)"
        text = r.get(field) or (str((drafts or {}).get(q, {}).get("answer") or "") if field == "draft" else "")
        parts.append(f"### {q}\n\n{(text or empty).strip()}\n")
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(parts), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kq", required=True, help="VINE's evidence file")
    ap.add_argument("--questions", required=True, help="{id: question text}")
    ap.add_argument("--drafts", required=True, help="the writer's answers (stage A's answers_<tag>.jsonl)")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="", help="default $SCRATCH/Beyond_RAG/vine2_runs/TAG")
    ap.add_argument("--only", default="", help="comma-separated question ids")
    ap.add_argument("--writer", default="", help="the drafts' model id (default: the one model in the file)")
    ap.add_argument("--min-drafts", type=float, default=0.95,
                    help="stop if fewer questions than this share have a draft (default 0.95)")
    ap.add_argument("--checker", default=CHECKER)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-fallback-writer", action="store_true")
    ap.add_argument("--cache-only", action="store_true", help="replay saved replies only; never call the API")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else Path(os.environ["SCRATCH"]) / "Beyond_RAG" / "vine2_runs" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    kq_path = Path(args.kq)
    kq = json.loads(kq_path.read_text())
    questions = json.loads(Path(args.questions).read_text())
    ids = [q.strip() for q in args.only.split(",") if q.strip()] or list(questions)
    bad = [q for q in ids if q not in questions or q not in kq or kq[q].get("question") != questions[q]]
    if bad:
        say(f"STOPPED: no VINE evidence with this exact question text for {len(bad)} ids, e.g. {bad[:5]}")
        return 1
    drafts, writer = latest_drafts(Path(args.drafts), args.writer, kq_path.name, args.checker, questions)
    have = sum(1 for q in ids if q in drafts)
    say(f"questions {len(ids)} | drafts by {writer or '(none)'}: {have} | "
        f"checker {args.checker} (effort {args.effort}, max tokens {args.max_tokens:,}) | workers {args.workers}")
    if have < args.min_drafts * len(ids):
        say(f"STOPPED: only {have} of {len(ids)} questions have a draft (at least {args.min_drafts:.0%} needed). "
            f"The writer stage did not work: look at its log, then run the same command again. "
            f"(The checker model answers a missing draft only for single failures.)")
        return 1

    final_path = out_dir / "final.jsonl"
    rules_sha = sha(core.CHECKER_RULES)[:12]
    code_sha = sha((HERE / "core.py").read_text() + (HERE / "check.py").read_text()
                   + f"|{args.checker}|{args.effort}|{args.max_tokens}")[:12]   # the code and the checker's settings
    latest: Dict[str, Dict[str, Any]] = {}        # each question's last record with this code and draft
    for r in read_jsonl(final_path):
        d = drafts.get(r.get("question_id"))
        same_draft = (d is not None and r.get("draft_sha256") == sha(str(d["answer"]))) or \
                     (d is None and r.get("status") == "fallback")
        if same_draft and r.get("code_sha") == code_sha:
            old = latest.get(r["question_id"])
            if old and old.get("status") in ("checked", "fallback") and r.get("status") not in ("checked", "fallback"):
                old["unjudged"] = old.get("unjudged") or ["(asked again, and that call failed)"]
                continue                        # keep the checked answer; ask again next time
            latest[r["question_id"]] = r
    done = {q: r for q, r in latest.items()        # statements left unjudged: asked again
            if r.get("status") in ("checked", "fallback") and not r.get("unjudged")}
    todo = [q for q in ids if q not in done]
    say(f"already done with this code and these drafts: {len(done)} | to do: {len(todo)}")

    checker = Checker(out_dir / "checker_cache", args.checker, args.effort, args.max_tokens, args.cache_only)
    lock = threading.Lock()
    records = dict(latest)
    t0 = time.time()

    def work(i: int, qid: str) -> None:
        try:
            r = check_one(qid, questions[qid], kq[qid], drafts.get(qid), checker, not args.no_fallback_writer)
        except Exception as e:                                         # noqa: BLE001  (never lose a question)
            d = drafts.get(qid)
            r = {"question_id": qid, "status": "unchecked" if d else "no_answer",
                 "final_answer": core.unchecked(str(d["answer"]), f"internal error: {e!r}"[:300]) if d else "",
                 "final_answer_clean": str(d["answer"]) if d else "",
                 "final_answer_corrections_only": str(d["answer"]) if d else "",
                 "draft": str(d["answer"]) if d else "", "error": traceback.format_exc()[-3000:],
                 "reason": f"internal error: {e!r}"[:300], "completed_at": now(), "cost_usd": 0.0}
        r.update({"tag": args.tag, "code_sha": code_sha, "rules_sha": rules_sha, "kq_file": kq_path.name})
        with lock:
            old = records.get(qid)
            if not (old and old.get("status") in ("checked", "fallback")
                    and r.get("status") not in ("checked", "fallback") and old.get("draft_sha256") == r.get("draft_sha256")):
                records[qid] = r                # a failed try does not replace a checked answer in the files
            with final_path.open("a", encoding="utf-8") as w:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
            c = r.get("counts") or {}
            detail = (f"{c.get('statements', 0)} statements: {c.get('checked', 0)} checked, "
                      f"{c.get('corrected', 0)} corrected, {c.get('disputed', 0)} disputed, "
                      f"{c.get('unconfirmed', 0)} not confirmed"
                      + (f", {c['unjudged']} NOT JUDGED" if c.get("unjudged") else "")
                      + f"; additions {c.get('additions', 0)}" if c else r.get("reason", ""))
            say(f"[{i}/{len(todo)}] {r['status'].upper():9s} {qid} | {detail} | ${r.get('cost_usd', 0):.3f}")

    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(lambda a: work(*a), enumerate(todo, 1)))

    # the files cover every question in the question file, also when --only checked a few
    every = list(questions)
    write_md(out_dir / "answers_final.md", records, every, "final_answer")
    write_md(out_dir / "answers_final_clean.md", records, every, "final_answer_clean")
    write_md(out_dir / "answers_final_corrections_only.md", records, every, "final_answer_corrections_only")
    write_md(out_dir / "answers_draft.md", records, every, "draft", drafts)
    statuses: Dict[str, int] = {}
    by_status: Dict[str, List[str]] = {}
    totals = {"statements": 0, "checked": 0, "checked_image": 0, "corrected": 0, "row_corrections": 0,
              "disputed": 0, "unconfirmed": 0, "unjudged": 0, "no_claim": 0, "additions": 0,
              "arithmetic_flags": 0, "citations_not_in_evidence": 0}
    for q in every:
        r = records.get(q) or {"status": "missing"}
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        by_status.setdefault(r["status"], []).append(q)
        for k in totals:
            totals[k] += int((r.get("counts") or {}).get(k, 0))
    with_unjudged = [q for q in every if (records.get(q) or {}).get("unjudged")]
    # every record ever written, including attempts that were later done again: what was paid
    cost = round(sum(float(r.get("cost_usd") or 0) for r in read_jsonl(final_path)), 2)
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    manifest = {"tag": args.tag, "written": now(), "repo_commit": commit, "code_sha": code_sha,
                "rules_sha": rules_sha, "kq_file": kq_path.name,
                "questions_sha256": sha(Path(args.questions).read_text()),
                "drafts_file": str(args.drafts), "writer": writer, "checker": args.checker,
                "effort": args.effort, "max_tokens": args.max_tokens, "fallback_writer": not args.no_fallback_writer,
                "questions": len(every), "checked_this_run": ids if args.only else "all",
                "statuses": statuses, "totals": totals,
                "not_checked": {k: v for k, v in by_status.items() if k != "checked"},
                "with_statements_not_judged": with_unjudged,
                "checker_cost_usd_all_runs": cost,
                "minutes_this_run": round((time.time() - t0) / 60, 1)}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    say(f"\nstatuses {statuses} | totals {totals} | checker cost ${cost:.2f} | "
        f"{manifest['minutes_this_run']} min")
    say(f"final answers -> {out_dir / 'answers_final.md'} (marked) and {out_dir / 'answers_final_clean.md'}")
    if with_unjudged:
        say(f"{len(with_unjudged)} questions have statements the checker did not judge: run the same command "
            f"again to ask for them, e.g. {with_unjudged[:5]}")
    ok = all((records.get(q) or {}).get("status") in ("checked", "fallback") and not records[q].get("unjudged")
             for q in ids)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
