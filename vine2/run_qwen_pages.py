"""vine2/run_qwen_pages.py -- stage A of VINE answer-then-check on another system's pages
(VisRAG, M3DocRAG, ViDoRAG) or regions (RegionRAG).

    $RETR_ENV/bin/python -u vine2/run_qwen_pages.py --kq PAGES_EVIDENCE --questions FILE --tag TAG

This is compare40/run_qwen_rag.py, unchanged and imported as it is: the same Qwen3.8-27B
files, servers, settings, picture check, queue and answer files. The one difference: each
question is answered by vine2/pages_writer.py (the page evidence) where run_qwen_rag.py starts
compare40/run_vine_rag.py (VINE's pieces). Only that one command line is changed, on its
way to subprocess.run; every other call goes through untouched.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WRITER = HERE / "pages_writer.py"
OLD_WRITER = REPO / "compare40" / "run_vine_rag.py"


class _Subprocess:
    """subprocess, as run_qwen_rag.py sees it: the same module, except that a command that
    starts compare40/run_vine_rag.py starts vine2/pages_writer.py with the same options."""
    swapped = 0

    def __getattr__(self, name):
        return getattr(subprocess, name)

    def run(self, cmd, *a, **k):
        if isinstance(cmd, list) and len(cmd) > 2 and Path(str(cmd[2])).resolve() == OLD_WRITER.resolve():
            cmd = cmd[:2] + [str(WRITER)] + cmd[3:]
            _Subprocess.swapped += 1
        return subprocess.run(cmd, *a, **k)


def main() -> int:
    sys.path.insert(0, str(REPO / "compare40"))
    import run_qwen_rag as rq  # noqa: E402
    rq.subprocess = _Subprocess()
    print(f"stage A on page evidence: compare40/run_qwen_rag.py, each question answered by {WRITER}", flush=True)
    return rq.main()


if __name__ == "__main__":
    sys.exit(main())
