#!/usr/bin/env python3
"""
Recover the 107 chunks lost to chunk_id collisions -- WITHOUT re-embedding.

Why this works
--------------
chunks_dense.npy already holds 5,812 rows, one per line of chunks.jsonl, in
order. The embeddings were computed BEFORE the collision mattered: the loss
happens at upsert time, when chunk_id_to_int() maps two different chunks to the
same Qdrant point id and the second overwrites the first.

So the fix is just: make the ids unique, keep row order, re-upsert. No model
loads, no GPU, no API calls.

Usage
-----
    python scripts/repair_chunk_ids.py --cache /path/to/mmrag_cache_v3
    python scripts/repair_chunk_ids.py --cache ... --apply

Without --apply it only reports. With --apply it rewrites chunks.jsonl
(after taking a .prerepair.bak) and prints the next steps.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path


def unique_ids(rows: list[dict]) -> tuple[list[str], int]:
    """Suffix only 2nd+ occurrences so existing ids stay byte-identical."""
    seen: dict[str, int] = {}
    out: list[str] = []
    changed = 0
    for r in rows:
        cid = r["chunk_id"]
        if cid in seen:
            seen[cid] += 1
            cid = f"{cid}_{seen[cid]}"
            changed += 1
        else:
            seen[cid] = 0
        out.append(cid)
    return out, changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    src = args.cache / "chunks.jsonl"
    rows = [json.loads(l) for l in src.open() if l.strip()]

    before = len({r["chunk_id"] for r in rows})
    new_ids, changed = unique_ids(rows)
    after = len(set(new_ids))

    print(f"rows in chunks.jsonl : {len(rows)}")
    print(f"unique ids before    : {before}")
    print(f"unique ids after     : {after}")
    print(f"chunks recovered     : {after - before}")
    print(f"ids rewritten        : {changed}  (all others untouched)")

    dense = args.cache / "chunks_dense.npy"
    if dense.exists():
        import numpy as np

        n = np.load(dense, mmap_mode="r").shape[0]
        print(f"chunks_dense.npy rows: {n}  ->  aligned: {n == len(rows)}")
        if n != len(rows):
            raise SystemExit(
                "ABORT: embedding rows != chunk rows. Do not re-upsert; re-ingest instead."
            )

    worst = Counter(r["chunk_id"] for r in rows)
    print("\nmost-collided ids:")
    for cid, k in worst.most_common(5):
        if k > 1:
            print(f"  {cid}  x{k}")

    if not args.apply:
        print("\nreport only -- pass --apply to rewrite chunks.jsonl")
        return

    bak = src.with_suffix(".prerepair.bak.jsonl")
    if not bak.exists():
        shutil.copy2(src, bak)
        print(f"\nbackup written: {bak}")

    with src.open("w") as fh:
        for r, cid in zip(rows, new_ids):
            r["chunk_id"] = cid
            fh.write(json.dumps(r) + "\n")
    print(f"rewrote {src} with {after} unique ids")

    print(
        "\nNEXT (no embedding needed):\n"
        "  1. rebuild the graph from the repaired chunks.jsonl -- cheap, no models\n"
        "  2. re-upsert chunks to Qdrant reusing chunks_dense.npy row-for-row\n"
        "  3. sanity check: Qdrant point count should now be 5812, not 5705\n"
        "\nNote: chunks_sparse.json is empty for every row. Re-upserting does NOT\n"
        "fix that -- sparse needs a fresh encode with FlagEmbedding actually loading.\n"
    )


if __name__ == "__main__":
    main()
