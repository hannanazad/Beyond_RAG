"""Where the table-transcription scripts read and write.

Nothing here is hardcoded to one machine. Every path is derived from
`mrag.config.CFG`, which resolves its base directory in this order:

    MRAG_BASE_DIR (env var)  ->  the per-environment default in config.py

So a reviewer sets one environment variable, or nothing at all on a machine
where the default is already right, and every script in this folder follows.
Each path can still be overridden individually by its own env var, listed
beside it below, which is what the tests use.

    MUTCD_PDF          the MUTCD PDF
    MUTCD_FIGURES      figures.jsonl      (written by scripts/ingest_v4.py)
    MUTCD_CHUNKS       chunks.jsonl       (written by scripts/ingest_v4.py)
    MUTCD_GPICKLE      graph.gpickle      (written by scripts/ingest_v4.py)
    MUTCD_TABLES_OUT   mutcd_tables.jsonl (written by build.py)
"""
import os
import sys
from pathlib import Path

# The repo root — the folder holding mrag/, scripts/, tests/. Worked out from
# this file's own location, so it needs no editing as long as this folder sits
# at <repo>/scripts/table_transcription/.
REPO = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO))
from mrag.config import CFG  # noqa: E402


def _p(env_var: str, default: Path) -> Path:
    """The env var if it is set, otherwise the value derived from CFG."""
    value = os.environ.get(env_var)
    return Path(value) if value else default


# The MUTCD PDF.
PDF = _p("MUTCD_PDF", CFG.pdf_path)

# figures.jsonl produced by the ingest.
FIGURES = _p("MUTCD_FIGURES", CFG.figures_jsonl)

# chunks.jsonl produced by the ingest.
CHUNKS = _p("MUTCD_CHUNKS", CFG.chunks_jsonl)

# graph.gpickle produced by the ingest.
GRAPH = _p("MUTCD_GPICKLE", CFG.graph_pickle)

# Where the finished table file is written.
TABLES_OUT = _p("MUTCD_TABLES_OUT", CFG.cache_dir / "mutcd_tables.jsonl")

# Scratch folder for rendered page images.
RENDER_OUT = Path(__file__).resolve().parent / "_renders"
