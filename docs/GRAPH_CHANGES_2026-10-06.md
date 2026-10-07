# VINE graph — audit and changes, 6 October 2026

The VINE graph went from 19,650 nodes / 49,092 edges to **19,671 / 50,406**. All counts
below come from rebuilding it with the repo code from `chunks.jsonl`, `mutcd_tables.jsonl`
and the MUTCD PDF.

## 1. What came from the test questions, and what happened to it

**Removed:** the block in `graph_links.py` titled "VOCABULARY WIDENED FOR QUESTION
WORDING". It added "posted at", "is posted", "posted", "signed at", "prevailing" and two
spellings of 85th percentile. A test question's wording is why it was written, and the
block's own comment told people to add more words whenever a question used different
wording.

**Kept from that block:** "posted speed limit" and "statutory speed limit". Both are 1C.02
headwords. Without them, the manual's own phrase "the posted speed limit is 35 mph" is
filed as a plain speed limit.

**Effect on the graph:** 1 node and 2 edges. The 2B.21 ¶10 lead-in ("the speed limit that
is posted") had been filed as POSTED only because of the word "is posted".

**Effect on the graph parser:** it uses the same speed reader on questions, so it no longer
reads those everyday paraphrases as a posted limit. That is intended: it should not be tuned
to a test question.

## 2. Checked, and not from the test questions

These were scanned for phrases of 6 words (and 5 words) from the 11 sample questions and
all 150 MUTCD-150 records that do not appear in the manual's text:
- the figure reading log;
- the manual reading log;
- the engineer rulings;
- the exception rulings;
- the computable rules;
- every node and edge.

Every remaining match is the manual's own content written the same short way: a label
drawn in a figure, or a printed value stated briefly. The matches were checked against the
pages. (The match list is not kept in the repo, because it holds test wording.)

The dates agree. The readings and rulings are dated 22 September. The ten sample questions
were prepared on 4 October.

FHWA Official Interpretation 2(09)-2 is kept. It is outside the MUTCD (stored as its own
authority), and no test question touches 2C.06.

## 3. Build bugs fixed (objective, against the manual)

| Bug | Before | After |
|---|---|---|
| Tables 2C-4, 4C-1 and 7B-1 print two charts on one sheet; chart B rows overwrote chart A rows | 21 rows lost; "5 mph" carried the Freeways row's "Required" values | each chart's rows kept separately, each with only its own notes |
| A figure reading was also attached to the table with the same number (e.g., Table 2C-4 got Figure 2C-4's speed-feedback sign reading) | 64 readings, 73 findings misplaced | 0 |
| Plural and range references ("Sections 2A.15 and 2A.16", "Sections 2C.70 through 2C.73") were never linked | 556 of 2,095 written section ids had no edge | 6 (bare ids with no "Section" word) |
| Lead-in sentences of lists got no references ("Notes for Figure 6P-10 ...", "(see Figures 2D-17 through 2D-19):") | 523 of 2,241 figure/table ids had no edge | 0 |
| 60 figure-log headings wrapped onto a second line | the tail of the title opened the reading | heading joined |
| M1-7 "data correction" said the text layer was wrong | it blamed extraction | it now records that the manual itself prints M1-1 in Table 2A-1 and M1-7 in 2D.11 ¶18 / Figure 2D-4 |

## 4. Figure readings corrected against the page

Seven readings were compared with the page images. Three were wrong:
- **3B-28:** it said the lines get shorter and further apart toward the hump. It is the
  reverse (3B.30 ¶3). The `ADVANCE_SPEED_HUMP_MARKINGS` rule note had the same error.
- **2E-21:** it put the W9-7 sign 600 ft ahead of the gore. The 600 ft is measured from the
  ¼-mile guide sign.
- **2E-31:** it listed a ½-mile advance sign. The figure shows 2-mile and 1-mile signs only.

Three wrong out of seven is too many to trust the other 351 readings for numbers. They are
fine for finding the right figure. The VLM must settle anything a figure is cited for.

## 5. Added to the vector store (`mrag/vine/vector_items.py`)

| Type | Items | What it is | Authority in the payload |
|---|---|---|---|
| FigureReading | 451 | one per figure where the log splits a multi-figure entry, otherwise one shared item | NOT NORMATIVE: a reading of the figure, not the manual's words |
| TableRow | 1,914 | one per printed row, with column labels and the chart name | TABLE: printed in the manual |

- The text is embedded the same way ingest embeds chunks.
- `section_id` is the row's own Section column; otherwise it is the section that names
  the figure or table most often.
- Retrieval weight: TableRow 1.0 (what any unlisted type already had). FigureReading 0.7,
  the same as Support (`config.py`).

## 6. Shortcomings found, not fixed (a decision for the author)

1. **Lists inside lists are flattened.** Example: in 2J.01 ¶11, the GAS/FOOD/... criteria
   each have items 1–3 joined by "and". 30 lists like this are filed as one level under the
   top lead-in.
2. **Example lists are read as conditions.** "such as, but not limited to: A, B, and C" is
   marked ALL in 12 lists.
3. **The CLASS nodes (Freeway, Expressway, Conventional Road — Multi-Lane, ...) only
   connect to table rows.** 540 sentences name these classes, and none links to them.
4. **"Chapter 2C" references (245) link to nothing.** The VINE graph has no chapter nodes.
5. **Quantities:** 381 of 1,718 have no kind. 394 have no comparison (">=", "<=").
   Example: 2I.14 records 18 in and 30 in both as SIZE, losing vertical vs horizontal.
6. **Table footnote markers were stripped from the cells.** Every row is linked to every
   note of its table, so Table 2A-1's "Diamond" row gets "This shape shall be limited
   exclusively ...", which applies only to the starred shapes.
7. **Table row labels:** some are the group column (66 rows of Table 1D-1 are all labelled
   "General Abbreviations"). The item text uses all cells, so retrieval is not affected.
8. **Lookup columns are turned into classes:** "Word Message" and "Standard Abbreviation"
   become CLASS nodes that rows "apply under".

## 7. The calculator

It sits at execution only: `run.py` → `build_verifiers` → `execute`, after retrieval,
parsing and compiling. Nothing in retrieval or the parser reads the table file. When it
runs, it looks values up in `mutcd_tables.jsonl` directly, not in what retrieval returned.

## 8. How to run

1. Push these files.
2. Run `notebooks/Graph_and_Vector_Store.ipynb` (CELL 1–6). It:
   - rebuilds the graph and saves it to `vine_data/graph_cache.pkl` (the old one is kept);
   - writes `vine_data/vine_items.jsonl`;
   - embeds and adds the items;
   - snapshots the store (the old one is kept as `qdrant_db.before_vine_items.tar`).
3. Run `notebooks/Retrieval_Test.ipynb` (CELL 1–8). CELL 8 compares the results with the
   run from before the items were added.
