"""Emit one skeleton record per table crop, ready to be filled in.

Everything the repo already knows is filled from code — table id, sheet, page,
crop file, title, and the note chunks already in the knowledge graph — so a
transcription only has to supply the grid and the footnote text. That keeps
provenance automatic and out of the transcriber's hands, and it means a
certificate citing a table value points at the same objects retrieval returns.

usage: python scripts/make_table_skeletons.py <figures.jsonl> <graph.gpickle> <out.jsonl>
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.kg import KG, read as kg_read            # noqa: E402
from mrag.vine.table_data import SCHEMA_VERSION    # noqa: E402


def main(figures_path: str, graph_path: str, out_path: str) -> None:
    crops = [json.loads(l) for l in Path(figures_path).read_text().splitlines()
             if l.strip()]
    tables = [c for c in crops if c.get("kind") == "Table"]
    kg = KG(kg_read(Path(graph_path)))

    out = []
    for c in sorted(tables, key=lambda c: (c["figure_id"], c.get("sheet") or 0)):
        out.append({
            "table_id": c["figure_id"],
            "sheet": c.get("sheet"),
            "sheet_of": c.get("sheet_of"),
            "page_pdf": c["page_pdf"],
            "page_printed": str(c.get("page_printed") or ""),
            "title": c.get("title") or "",
            "crop_file": os.path.basename(c.get("image_path") or ""),
            "note_chunk_ids": kg.note_chunks_for(c["figure_id"]),
            "schema_version": SCHEMA_VERSION,
            # ---- to be filled in ----
            "kind": "",                 # numeric | text | mixed | formula
            "column_labels": [],
            "row_key_columns": [0],
            "rows": [],
            "footnotes": [],
            "variables": {},
            "verified": False,
            "source": "",
        })
    Path(out_path).write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in out) + "\n")
    print(f"{len(out)} skeletons -> {out_path}")
    print(f"  tables: {len({t['table_id'] for t in out})} ids, "
          f"{sum(1 for t in out if t['sheet'])} sheet records")
    print(f"  with note chunks already linked: "
          f"{sum(1 for t in out if t['note_chunk_ids'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
