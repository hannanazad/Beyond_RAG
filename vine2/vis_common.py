"""vine2/vis_common.py -- what the three visual-RAG retrieval scripts share (standard library
only: each script runs in its own system's Python environment).

The three scripts (vine2/m3docrag_retrieve.py, vine2/vidorag_retrieve.py,
vine2/regionrag_retrieve.py) run each system's OWN retrieval code, from a copy of its
repository at a fixed commit, on the MUTCD PDF and the question texts. They read the question
text only: never a gold answer or a gold page, never anything of VINE's. Each writes, in its
output folder:
  retrieval.jsonl           one line a question: {"question_id", "question_sha256", "system",
                            "items": [...]}; an item is a page or a region, in the system's
                            own order, with the page's number in the PDF ("page_pdf", from 1)
                            and what the system gave for it
  retrieval_manifest.json   the system, its code commit, its models and their commits, the
                            settings, the PDF and question file fingerprints
vine2/vis_evidence.py turns that into the evidence vine2 reads.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SYSTEMS = ("m3docrag", "vidorag", "regionrag")
SAVE_TOP = 20                      # items kept a question (vine2 uses at most 20 pieces)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_questions(path: Path) -> Dict[str, str]:
    """{id: question text} and nothing else: retrieval must see the question only."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or not d or not all(isinstance(v, str) and v.strip() for v in d.values()):
        sys.exit(f"STOPPED: {path} must map each question id to its text, and nothing else")
    return d


def git_commit(repo: Path) -> str:
    """The commit of a system's code copy; it must be exactly the pinned one, unchanged."""
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"STOPPED: {repo} is not a git copy of the system's code (vine2/vis_setup.sh makes it)")
    if dirty.stdout.strip():
        sys.exit(f"STOPPED: the system's code in {repo} is changed locally:\n{dirty.stdout}")
    return out.stdout.strip()


def check_commit(repo: Path, pinned: str) -> str:
    got = git_commit(repo)
    if got != pinned:
        sys.exit(f"STOPPED: {repo} is at {got}, not the pinned commit {pinned}")
    return got


def item(rank: int, page_pdf: int, **extra: Any) -> Dict[str, Any]:
    return {"rank": int(rank), "page_pdf": int(page_pdf), **extra}


def write_retrieval(out_dir: Path, system: str, questions: Dict[str, str],
                    items: Dict[str, List[Dict[str, Any]]], manifest: Dict[str, Any]) -> None:
    """retrieval.jsonl and retrieval_manifest.json (written last: a folder without it is not a
    finished retrieval)."""
    assert system in SYSTEMS, system
    out_dir.mkdir(parents=True, exist_ok=True)
    man_path = out_dir / "retrieval_manifest.json"
    if man_path.exists():
        man_path.unlink()                                   # an old manifest never vouches for new lines
    missing = [q for q in questions if not items.get(q)]
    if missing:
        sys.exit(f"STOPPED: the retrieval gave nothing for {len(missing)} questions, e.g. {missing[:5]}")
    tmp = out_dir / "retrieval.jsonl.part"
    with open(tmp, "w", encoding="utf-8") as f:
        for qid, text in questions.items():
            f.write(json.dumps({"question_id": qid, "question_sha256": text_sha(text), "system": system,
                                "items": items[qid]}, ensure_ascii=False) + "\n")
    os.replace(tmp, out_dir / "retrieval.jsonl")
    man = {"system": system, "n_questions": len(questions), "save_top": SAVE_TOP, "dry_run": False,
           **manifest, "finished_utc": now()}
    man_path.write_text(json.dumps(man, indent=2, default=str), encoding="utf-8")


def read_retrieval(out_dir: Path) -> Dict[str, Dict[str, Any]]:
    out = {}
    for line in (out_dir / "retrieval.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["question_id"]] = r
    return out


def retrieval_done(out_dir: Path, system: str, questions: Dict[str, str], pinned: Dict[str, Any]) -> bool:
    """A finished retrieval of this system, for exactly these question texts and these pinned
    settings (code commit, models)."""
    try:
        man = json.loads((out_dir / "retrieval_manifest.json").read_text())
        have = read_retrieval(out_dir)
    except (FileNotFoundError, ValueError, KeyError):
        return False
    if man.get("system") != system or man.get("dry_run") or any(man.get(k) != v for k, v in pinned.items()):
        return False
    return all(q in have and have[q].get("question_sha256") == text_sha(t) and have[q].get("items")
               for q, t in questions.items())


def snapshot(revisions: Dict[str, Any], repo_id: str) -> Path:
    """The local folder of a downloaded model, at the commit vine2/vis_setup.sh recorded."""
    rev = revisions["models"][repo_id]
    path = Path(os.environ["HF_HUB_CACHE"]) / f"models--{repo_id.replace('/', '--')}" / "snapshots" / rev
    if not path.is_dir():
        sys.exit(f"STOPPED: {repo_id} at {rev} is not downloaded: run  bash vine2/vis_setup.sh")
    return path


def load_revisions(path: Path, needed: Iterable[str] = ()) -> Dict[str, Any]:
    """The model commits vine2/vis_setup.sh recorded; each of `needed` must be there."""
    try:
        revs = json.loads(Path(path).read_text())
    except (FileNotFoundError, ValueError):
        sys.exit(f"STOPPED: {path} is missing: run  bash vine2/vis_setup.sh SYSTEM  on a login node")
    missing = [m for m in needed if m not in (revs.get("models") or {})]
    if missing:
        sys.exit(f"STOPPED: {path} records no commit for {missing}: run  bash vine2/vis_setup.sh SYSTEM  again")
    return revs


def versions(*packages: str) -> Dict[str, str]:
    """The installed version of each package (and Python), for the manifest."""
    import platform
    from importlib import metadata
    out = {"python": platform.python_version()}
    for name in packages:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "not installed"
    return out


# a model that loads with weights made up on the spot, or an adapter with keys missing, gives
# wrong rankings and no error: such a load stops the job
_BAD_LOAD = ("newly initialized", "were not initialized", "missing adapter keys", "missing key(s)",
             "led to unexpected keys", "led to missing keys")    # PEFT's and transformers' own wording


class LoadGuard:
    """with LoadGuard("ColPali"): ...  -- every warning transformers or PEFT gives while the
    model loads is printed; one of _BAD_LOAD stops the job."""

    def __init__(self, what: str):
        self.what, self.msgs = what, []

    def __enter__(self):
        import logging
        import warnings
        guard = self

        class _H(logging.Handler):
            def emit(self, record):
                guard.msgs.append(record.getMessage())
        self._h = _H(level=logging.WARNING)
        self._loggers = [logging.getLogger(n) for n in ("transformers", "peft", "sentence_transformers")]
        for lg in self._loggers:
            lg.addHandler(self._h)
        self._w = warnings.catch_warnings(record=True)
        self._caught = self._w.__enter__()
        warnings.simplefilter("always")
        return self

    def __exit__(self, *exc):
        self._w.__exit__(*exc)
        for lg in self._loggers:
            lg.removeHandler(self._h)
        self.msgs += [str(w.message) for w in self._caught]
        for m in self.msgs:
            log(f"  load warning ({self.what}): {m[:300]}")
        bad = [m for m in self.msgs if any(b in m.lower() for b in _BAD_LOAD)]
        if bad and exc[0] is None:
            sys.exit(f"STOPPED: {self.what} did not load cleanly (its weights would not be the released ones): "
                     f"{bad[0][:400]}")
        return False


def check_refs(revs: Dict[str, Any], repos: Iterable[str]) -> Dict[str, str]:
    """Models a system loads BY NAME must resolve, offline, to the recorded commit (refs/main)."""
    out = {}
    for repo in repos:
        ref = Path(os.environ["HF_HUB_CACHE"]) / f"models--{repo.replace('/', '--')}" / "refs" / "main"
        got = ref.read_text().strip() if ref.exists() else ""
        if got != revs["models"].get(repo):
            sys.exit(f"STOPPED: {repo} would load commit {got or '(none)'}, not the recorded "
                     f"{revs['models'].get(repo)}: run  bash vine2/vis_setup.sh  again")
        snapshot(revs, repo)
        out[repo] = got
    return out


def stamp(folder: Path, what: Dict[str, Any]) -> None:
    """Files a system reuses (it never makes them again) belong to these inputs: the first run
    writes them down; a later run with other inputs stops instead of mixing old and new."""
    f = folder / "vine2_inputs.json"
    if f.exists():
        old = json.loads(f.read_text())
        if old != what:
            sys.exit(f"STOPPED: {folder} was made from other inputs ({old} here, {what} now): move the folder "
                     f"away and run again")
        return
    folder.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(what, indent=1, sort_keys=True))


def tool_version(cmd: List[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "?"
    except (OSError, subprocess.SubprocessError):
        return "missing"


def unique(seq: Iterable[Any]) -> List[Any]:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
