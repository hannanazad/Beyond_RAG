# Validation: proof that figure extraction was complete

Two files that back a specific claim: **every figure and table in the MUTCD was
successfully extracted — 485 of 485 figures, 68 of 68 tables.**

This matters because a retrieval system that silently misses figures will look
fine in testing and fail on exactly the questions figures were needed for.

---

## How the claim is verified

1. **Census.** Scan the entire 1,162-page manual for every "Figure X-Y" and
   "Table X-Y" reference. That produces the complete list of what *must* exist,
   independently of what the extractor found.
2. **Extract.** Crop figures using caption-anchored geometry.
3. **Cross-check.** Run the same extraction through a second, independent PDF
   backend (poppler) and compare.
4. **Gate.** `validate_coverage()` fails the ingest if coverage drops below
   99 percent. An incomplete index cannot be produced silently.

That gate caught a real bug: text-encoding artifacts were hiding five figures
in chapter 4F. The extractor was rebuilt on geometric word segmentation as a
result. The story is in `../docs/03_FIGURE_EXTRACTION_REBUILD.md`.

---

## The files

- **`census_records.jsonl`** — one record per detected figure and table, with
  its canonical id, page, caption, and bounding box. 727 crop images across
  553 canonical ids.
- **`coverage_report.json`** — the summary: counts, coverage percentages, and
  anything excluded.

Two ids are excluded on purpose: "Table 3-1" and "Table 3-3" are citations to
an external AASHTO publication, not tables in the MUTCD.

---

## Reproducing it

```bash
python scripts/ingest_v4.py
```

The coverage gate runs automatically and writes a fresh report. If your numbers
differ, your PDF differs — check it against
`../benchmark/source/mutcd11theditionr1hl.pdf`.
