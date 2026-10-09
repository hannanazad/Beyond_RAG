"""VINE from start to end, for one notebook (notebooks/VINE_Run.ipynb).

Each question goes through the whole pipeline:

  1. retrieval  -- `retrieve_for_compile`, what the parser reads (Kq)      no LLM
  2. the parser -- Qwen3.8-27B writes the plan (the IR)                    local model
  3. execution  -- the checkers decide each check (Claude Sonnet 5.5),
                   the executor works out the merges and the decision,
                   the answer is written from the certificates               API

Before that, the notebook measures retrieval on the 154 DEV cases (written
from the MUTCD, never from a test question) and stops if it finds the target
provisions for fewer cases than before.

Every stage saves its results on Drive as it goes, in a run folder named
after the code and data it depends on, so running the notebook again after a
disconnect carries on where it stopped.

This file holds the notebook's glue, so it can be tested without Colab. It
changes nothing in the pipeline.
"""
from __future__ import annotations

import hashlib
import json
import numbers
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

# The files whose change changes what retrieval returns. The Kq file is named
# after the last commit that touched any of them, so new retrieval code means a
# new Kq file, and a change elsewhere (the parser, the checkers) does not.
RETRIEVAL_FILES = ["mrag/retrieval.py", "mrag/find_provisions.py", "mrag/kg_vine.py", "mrag/kg.py",
                   "mrag/config.py", "mrag/embeddings.py", "mrag/vector_store.py",
                   "mrag/question_router.py", "mrag/vine/graph_links.py",
                   "mrag/vine/graph_enrich.py", "mrag/vine/vector_items.py"]

# The 7 October 2026 retrieval test (manual_cases v1; the retrieval code has
# not changed since, until mrag/find_provisions.py).
EARLIER_RETRIEVAL_TEST = "retrieval_dev_results/retrieval_test_20261007_052206.json"


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #
def plain(x: Any) -> Any:
    """numpy numbers and anything else odd -> plain JSON values."""
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if getattr(getattr(x, "dtype", None), "kind", "") == "b":    # numpy's bool is not an int
        return plain(x.tolist()) if getattr(x, "ndim", 0) else bool(x)
    if isinstance(x, numbers.Integral):
        return int(x)
    if isinstance(x, numbers.Real):
        return float(x)
    return str(x)


def load_json(path: Path, default: Any) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def save_json(path: Path, obj: Any, indent: Optional[int] = None) -> None:
    """Write through a temporary file, so a disconnect never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(plain(obj), indent=indent, default=str))
    os.replace(tmp, path)


def retrieval_commit(repo_dir: str) -> str:
    out = subprocess.run(["git", "-C", repo_dir, "log", "-1", "--format=%h", "--"] + RETRIEVAL_FILES,
                         capture_output=True, text=True).stdout.strip()
    return out or "nocommit"


def store_tag(base_dir: str) -> str:
    m = Path(base_dir) / "vine_data" / "text_store_manifest.json"
    return hashlib.sha256(m.read_bytes()).hexdigest()[:6] if m.exists() else "nostore"


# --------------------------------------------------------------------------- #
# Stage 0: the retrieval check on DEV
# --------------------------------------------------------------------------- #
def text_sha(text: str) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


def run_check_resumable(run_case: Callable[[Dict[str, Any]], Dict[str, Any]],
                        cases: Sequence[Dict[str, Any]], out_path: Path,
                        every: int = 10, say: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """`run_case(case) -> result` for every case not already in `out_path`
    (with the same text, and without a crash), saving every `every` cases.
    Results come back in the cases' order."""
    want = {c["case_id"]: text_sha(c.get("text", "")) for c in cases}
    done = {r["case_id"]: r for r in load_json(out_path, {}).get("results", [])
            if "error_compile" not in r and r.get("text_sha") == want.get(r.get("case_id"))}
    todo = [c for c in cases if c["case_id"] not in done]
    if done:
        say(f"  {len(done)} cases already done (from {Path(out_path).name}), {len(todo)} to run")
    t0 = time.time()
    for i, c in enumerate(todo, 1):
        done[c["case_id"]] = {**run_case(c), "text_sha": want[c["case_id"]]}
        if i % every == 0 or i == len(todo):
            save_json(out_path, {"results": [done[x["case_id"]] for x in cases if x["case_id"] in done]})
            say(f"  {i}/{len(todo)} cases, {time.time() - t0:.0f}s")
    return [done[c["case_id"]] for c in cases]


def results_before(cases: Sequence[Dict[str, Any]], earlier: Optional[List[Dict[str, Any]]],
                   run_old: Callable[[Dict[str, Any]], Dict[str, Any]],
                   out_path: Optional[Path] = None,
                   say: Callable[[str], None] = print) -> List[Dict[str, Any]]:
    """What retrieval found before this change, case by case.

    A case whose text is the one the earlier run used comes from the earlier
    run. A case corrected since (it carries "revised"), or one the earlier run
    lacks or crashed on, is run again here with the old setting,
    `run_old(case)` -- saved to `out_path` as it goes, when given. Without an
    earlier run, every case is."""
    by_id = {r["case_id"]: r for r in (earlier or [])}
    keep = {c["case_id"]: by_id[c["case_id"]] for c in cases
            if c["case_id"] in by_id and "revised" not in c and "error_compile" not in by_id[c["case_id"]]}
    rerun = [c for c in cases if c["case_id"] not in keep]
    say(f"  before: {len(keep)} cases from the earlier run, {len(rerun)} run here with the old setting")
    if rerun and out_path is not None:
        fresh = run_check_resumable(run_old, rerun, out_path, say=say)
    else:
        fresh = [run_old(c) for c in rerun]
    got = {**keep, **{r["case_id"]: r for r in fresh}}
    return [got[c["case_id"]] for c in cases]


# --------------------------------------------------------------------------- #
# Stage 2: the parser's model call, with room for every prompt
# --------------------------------------------------------------------------- #
class PromptTooLong(RuntimeError):
    """The prompt leaves too little room in the server's window. Trying again
    gives the same answer, so a plan that failed this way is not retried."""


class BudgetedAsk:
    """The parser's `ask(prompt, images)`, giving the model `max_tokens` to
    think and write -- or less, when a prompt is so long that the prompt plus
    `max_tokens` would not fit in the server's window (`max_len`). Without
    this, such a prompt is refused by the server and the plan fails.

    The prompt is counted by the server's own tokenizer (`/tokenize`), with
    the same chat template. `make_ask(max_tokens)` builds the real client; one
    is kept per budget, so every ordinary prompt uses exactly `max_tokens`
    (and its cached replies). `.last` and `.calls` are the real client's."""

    def __init__(self, make_ask: Callable[[int], Callable], base_url: str, served_name: str,
                 max_len: int, max_tokens: int, margin: int = 1024, min_tokens: int = 8192,
                 template_kwargs: Optional[Dict[str, Any]] = None, session=None) -> None:
        import requests
        self.make_ask = make_ask
        self.base_url, self.served_name = base_url.rstrip("/"), served_name
        self.max_len, self.max_tokens = int(max_len), int(max_tokens)
        self.margin, self.min_tokens = int(margin), int(min_tokens)
        self.template_kwargs = dict(template_kwargs or {})
        self.session = session or requests.Session()
        self._asks: Dict[int, Callable] = {}
        self.last: Optional[Dict[str, Any]] = None
        self.calls: List[Dict[str, Any]] = []
        self.budgets: List[Dict[str, Any]] = []

    def count(self, prompt: str) -> Dict[str, Any]:
        """{"tokens": n, "how": "server" | "estimate"}."""
        body = {"model": self.served_name, "messages": [{"role": "user", "content": prompt}],
                "add_generation_prompt": True}
        if self.template_kwargs:
            body["chat_template_kwargs"] = self.template_kwargs
        try:
            r = self.session.post(f"{self.base_url}/tokenize", json=body, timeout=120)
            if r.status_code == 200:
                n = r.json().get("count")
                if isinstance(n, int) and n > 0:
                    return {"tokens": n, "how": "server"}
        except Exception:                                      # noqa: BLE001
            pass
        # about 4 characters a token in this text; 3 leaves room to spare
        return {"tokens": len(prompt) // 3 + 1, "how": "estimate"}

    def budget(self, prompt: str) -> Dict[str, Any]:
        c = self.count(prompt)
        room = self.max_len - c["tokens"] - self.margin
        return {**c, "max_tokens": min(self.max_tokens, room), "room": room}

    def __call__(self, prompt: str, images: Optional[Sequence[str]] = None) -> str:
        self.last = None
        b = self.budget(prompt)
        self.budgets.append(b)
        if b["max_tokens"] < self.min_tokens:
            raise PromptTooLong(
                f"the prompt has about {b['tokens']:,} tokens; with the server's window of "
                f"{self.max_len:,} that leaves {max(b['room'], 0):,} for thinking and the plan "
                f"(at least {self.min_tokens:,} needed)")
        ask = self._asks.get(b["max_tokens"])
        if ask is None:
            ask = self._asks[b["max_tokens"]] = self.make_ask(b["max_tokens"])
        reply = ask(prompt, list(images or []))
        last = getattr(ask, "last", None)
        self.last = {**(last if isinstance(last, dict) else {}), "max_tokens": b["max_tokens"],
                     "prompt_tokens": b["tokens"], "prompt_tokens_how": b["how"]}
        self.calls.append(self.last)
        return reply


# --------------------------------------------------------------------------- #
# Reading the results
# --------------------------------------------------------------------------- #
def answer_line(rec: Dict[str, Any]) -> str:
    a = rec.get("answer") or {}
    return f"{rec['case_id']:26s} {str(rec.get('terminal')):8s} {a.get('text') or '(no answer)'}"


def print_answers(records: Iterable[Dict[str, Any]], width: int = 110) -> None:
    for r in records:
        a = r.get("answer") or {}
        print("-" * width)
        certified = r.get("terminal") in ("TRUE", "FALSE") and not r.get("unsupported_certification")
        print(f"{r['case_id']}  decision {r.get('terminal')}  certified {certified}"
              + (f"  ERROR {r['error']}" if r.get("error") else ""))
        print(f"  {a.get('text') or '(no answer)'}")
        cites = [c.get("id") for c in a.get("citations") or []]
        if cites:
            print(f"  cites: {', '.join(cites[:12])}{' ...' if len(cites) > 12 else ''}")
        if a.get("unresolved"):
            print(f"  left open: {len(a['unresolved'])}")


def failed_plan_record(qid: str, question: str, error: str,
                       kq: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A plan that could not be made, in the shape of parser_check.make_record."""
    from collections import Counter
    chunks = (kq or {}).get("chunks") or []
    return {"case_id": qid, "question": question, "kq_size": len(chunks),
            "kq_types": dict(Counter(str(c.get("content_type")) for c in chunks)),
            "outcome": "failed", "attempts": 0,
            "problems": [[error]], "notes": [], "spec": None, "stats": {}, "numbers": {},
            "seconds": 0.0, "completion_tokens": 0, "calls": [], "raw_replies": []}


# a failure of the machinery, not of the plan: worth trying again on the next run
_RETRY = ("the model call failed", "the parse stopped")
# ...except these, which come out the same every time
_NO_RETRY = ("PromptTooLong", "answered 400", "answered 422")


def plan_needs_retry(rec: Optional[Dict[str, Any]], question: str) -> bool:
    """True when there is no plan for this question text yet, or the last try
    failed because the model call or the run broke (not because the plan was
    wrong: that is a result, and the same seed gives it again)."""
    if not rec or rec.get("question") != question:
        return True
    if rec.get("outcome") != "failed":
        return False
    text = json.dumps(rec.get("problems") or [])
    return any(m in text for m in _RETRY) and not any(m in text for m in _NO_RETRY)


def same_json(a: Any, b: Any) -> bool:
    """Equal once both are written as JSON (tuples and lists alike)."""
    return json.dumps(plain(a), sort_keys=True) == json.dumps(plain(b), sort_keys=True)
