"""The only file with paths in it. Set these four, once.

Every other script in this folder imports from here, so there is nothing else
to edit and no line numbers to hunt for.
"""
from pathlib import Path

# The MUTCD PDF.
PDF = Path("/content/drive/MyDrive/Beyond_RAG/mutcd11theditionr1hl.pdf")

# figures.jsonl produced by the ingest.
FIGURES = Path("/content/drive/MyDrive/Beyond_RAG/mmrag_cache_v3/figures.jsonl")

# Where the finished table file is written.
TABLES_OUT = Path("/content/drive/MyDrive/Beyond_RAG/mmrag_cache_v3/mutcd_tables.jsonl")

# The repo root — the folder holding mrag/, scripts/, tests/.
# Worked out from this file's own location, so it needs no editing as long as
# this folder sits at <repo>/scripts/table_transcription/.
REPO = Path(__file__).resolve().parents[2]

# Scratch folder for rendered page images. Anywhere you like.
RENDER_OUT = Path(__file__).resolve().parent / "_renders"
