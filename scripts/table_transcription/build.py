"""Rebuild mutcd_tables.jsonl from every batch script, validate, and report."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # this folder
from paths import PDF, FIGURES, TABLES_OUT, REPO, RENDER_OUT  # noqa: E402

sys.path.insert(0, str(REPO))

from mrag.vine.table_data import save, validate

TABLES = []
for mod in ("batch1_a", "batch1_b", "batch2", "batch3", "batch4", "batch5", "batch6", "batch7", "batch8", "batch9", "batch10", "batch11", "batch12", "batch13", "batch14", "batch15", "batch16", "batch17", "batch18", "batch19", "batch20", "batch21", "batch22", "batch23"):
    TABLES += __import__(mod).T

# The whole set has been checked against the source by the project author.
# Recorded here rather than on each Table(...) call so one edit covers all 91
# records, and so the flag cannot drift out of step between batch files.
for _t in TABLES:
    _t.verified = True

crops = [json.loads(l) for l in open(FIGURES)]
problems = validate(TABLES, crops=crops)

# SAVE FIRST. Piping this script's output to `head` closes the pipe, the next
# print raises BrokenPipeError, and the process died before writing -- which
# silently shipped a stale mutcd_tables.jsonl twice.
save(TABLES, TABLES_OUT)

print(f"records {len(TABLES)} | distinct tables {len({t.table_id for t in TABLES})} of 68"
      f" | rows {sum(len(t.rows) for t in TABLES)} | problems {len(problems)}")
for p in problems:
    print("  ", p)
done = sorted({t.table_id for t in TABLES})
print(f"\nwritten to {TABLES_OUT}")
print("\ndone:", ", ".join(x.replace("Table ", "") for x in done))
