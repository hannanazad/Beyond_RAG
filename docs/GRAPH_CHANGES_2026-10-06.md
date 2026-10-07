# VINE graph — audit and changes, 6 October 2026

The VINE graph is now **the pipeline's graph**: retrieval, the question router, per-check
retrieval (Eq 5) and the cross-reference verifier all read it, for the RAG baseline and for
VINE alike. The old `graph.gpickle` is not read by anything (`CFG.graph_backend = "vine"`).

The VINE graph went from 19,650 nodes / 49,092 edges to **19,671 / 45,488**:
- 21 table rows were restored.
- 1,451 links were added: 1,359 references and 92 row-to-chart links.
- 137 reading links on the wrong figure or table were removed.
- 4,918 note links were removed. Each pointed at a row its note does not apply to (see §4).

All counts come from rebuilding the graph with the repo code from `chunks.jsonl`,
`mutcd_tables.jsonl` and the MUTCD PDF.

## 1. What came from the test questions, and what happened to it

**Removed:** the block in `graph_links.py` titled "VOCABULARY WIDENED FOR QUESTION
WORDING". It added "posted at", "is posted", "posted", "signed at", "prevailing" and two
spellings of 85th percentile. A test question's wording is why it was written, and the
block's own comment told people to add more words whenever a question used different
wording.

**Kept from that block:** "posted speed limit" and "statutory speed limit". Both are 1C.02
headwords. Without them, the manual's own phrase "the posted speed limit is 35 mph" is filed
as a plain speed limit.

**Effect on the graph:** 1 node and 2 edges. The 2B.21 ¶10 lead-in had been filed as POSTED
only because of the words "is posted".

**Checked and clean:**
- the figure reading log;
- the manual reading log;
- the engineer rulings;
- the exception rulings;
- the computable rules;
- every node and edge;
- every file written today;
- every vector-store item.

They were scanned for 5- and 6-word phrases from the 11 sample questions and all 150
MUTCD-150 records that do not appear in the manual's text. The remaining matches are the
manual's own content written the same short way: figure labels, printed values, table
cells. They were checked against the pages. The readings and rulings are dated 22
September, and the ten sample questions were prepared on 4 October. FHWA Interpretation
2(09)-2 is kept as its own authority; no test question touches 2C.06.

## 2. The VINE graph is the pipeline's graph (`mrag/kg_vine.py`)

`VineKG` answers, method for method, everything the code asks of a graph:
- `sections_cited_by`, `chunks_for_section`, `chunks_for_paragraph`, `paragraph_items`;
- `note_chunks_for`, `notes_for_section`, `figures_for_chunk`, `figures_for_section`;
- `terms_defined_in`, `definition_chunk`, `query_entities`, `proximity_score`;
- `resolves`, `section_cites_figures`, `is_known_citation`.

It also keeps the node attributes callers read directly: chunk type and ordinal, figure
image paths and sheets, and sign names.

Compared with the old graph on every chunk, section and paragraph:
- **Sections:** the same chunks for all 953.
- **Cross-references:** 1,927 against 1,337. The only old links not kept point at the four
  sections the manual cites but does not contain (8B.05, 8C.05, 8E.10, 9D.10).
- **Figures named by a chunk:** everything the old graph had, plus 153 more chunks.
- **Notes:** the same on all 553 figures and tables.
- **Paragraphs:** the same on 6,199 of 6,547. The 348 differences are an old-graph error:
  it counted a figure or table note numbered 1 as "Paragraph 1" of the section printing it.

Two new things the graph adds to retrieval:
- When a provision names a figure, the closure brings the figure's reading. When it names
  a small table (15 rows or fewer, e.g. Table 2C-4), it brings the whole table.
- Each chunk's payload gains the references the graph found: 429 figure, 75 table and 867
  section references. Nothing is removed.

The closure now looks up a named figure or table by its kind. "2B-1" under `table_refs` is
Table 2B-1, not Figure 2B-1. The old code tried both and could take the wrong one.

## 3. Build bugs fixed (objective, against the manual)

| Bug | Before | After |
|---|---|---|
| Tables 2C-4, 4C-1 and 7B-1 print two charts on one sheet; chart B rows overwrote chart A rows | 21 rows lost; "5 mph" carried the Freeways row's "Required" values | each chart's rows kept separately |
| A figure reading was also attached to the table with the same number | 64 readings, 73 findings misplaced | 0 |
| Plural and range references ("Sections 2A.15 and 2A.16", "Sections 2C.70 through 2C.73") | 556 of 2,095 written section ids had no link | 6 (bare ids with no "Section" word) |
| Lead-in sentences of lists got no references ("Notes for Figure 6P-10 ...") | 523 of 2,241 figure/table ids had no link | 0 |
| 60 figure-log headings wrapped onto a second line | the tail of the title opened the reading | heading joined |
| M1-7 "data correction" blamed extraction | — | records that the manual itself prints M1-1 in Table 2A-1 and M1-7 in 2D.11 ¶18 / Figure 2D-4 |

## 4. Table note marks: nothing dropped, each note where the manual puts it

The transcription records every note mark on its cell. In 275 cells the mark was only in a
side field, so the cell text read as if the note did not exist ("Octagon" for "Octagon*").

All 497 marks are now visible:
- 222 were already in the cell text;
- 131 are printed back on the cell;
- 112 are shown on their column heading;
- 32 are general-note keys, kept for the whole table.

Each note now applies by where its mark is printed, as a reader of the printed table reads
it:

| Mark printed on | The note applies to | Notes |
|---|---|---|
| the title, or no mark ("Note 1") | the whole table | 117 |
| a column heading (Table 4C-1's a–d, Table 2C-3's ²–⁴) | every row, through that column | 34 |
| a row heading (Table 2M-1's * on the symbol name, Table 2A-1's * on the shape), or one cell (Table 2A-5's * on a sheeting value) | that row only; the link names the cell | 60 |
| nowhere the transcription recorded | the whole table, so nothing is lost | 19 |

Each table-row item in the vector store now carries the full text of the notes that apply
to that row.

## 5. Figure readings corrected against the page

Seven readings were compared with the page images. Three were wrong:
- **3B-28:** it said the lines get shorter and further apart toward the hump. It is the
  reverse (3B.30 ¶3). The `ADVANCE_SPEED_HUMP_MARKINGS` rule note had the same error.
- **2E-21:** it put the W9-7 sign 600 ft ahead of the gore. The 600 ft is measured from the
  ¼-mile guide sign.
- **2E-31:** it listed a ½-mile advance sign. The figure shows 2-mile and 1-mile signs only.

The readings help retrieval find the right figure. They are marked "not normative", and the
VLM checks anything a figure is cited for.

## 6. In the vector store (`mrag/vine/vector_items.py`)

| Type | Items | What it is | Authority in the payload |
|---|---|---|---|
| FigureReading | 451 | what a figure shows; one per figure where the log separates them | NOT NORMATIVE: a reading of the figure, not the manual's words |
| TableRow | 1,914 | one printed row: column labels, values with their marks, and the notes that apply | TABLE: printed in the manual |

The store's text side is rebuilt fresh (`notebooks/Fresh_Build.ipynb`): 9,191 manual chunks
plus these items, all embedded again with BGE-M3. Retrieval weight: TableRow 1.0,
FigureReading 0.7 (the same as Support).

## 7. Read as an engineer: what is still imperfect, and whether it causes harm

None of these is changed. In the current plan the LLM parser reads the paragraph text
itself, so the graph labels below do not reach it.

1. **Lists inside lists** (30). The sub-items are tied to the top list. In 4C.04 (Warrant
   3), the graph's labels would allow any one of conditions 1–3, but the manual needs all
   three in the same hour. Harmful only to something that builds checks from the graph's
   any/all labels (the idle graph parser).
2. **Example lists marked "all"** (12). Ten are Support text, and 2B.34 is correct as it is.
   Harmless.
3. **Road classes and "Chapter X" references with no links.** These are missing links, not
   wrong ones. Harmless.
4. **Numbers.** In a random 30: 18 right, 10 with a missing type or comparison, 2 wrong (for
   example, 8A.08 "more than 100 feet" stored without "more than"). Harmless on the LLM
   path.
5. **Lookup columns turned into classes** (e.g. Table 1D-1's "Word Message"). Harmless.
   Retrieval does not follow class links.

## 8. The calculator

It sits at execution only: `run.py` → `build_verifiers` → `execute`, after retrieval,
parsing and compiling. When it runs, it looks values up in `mutcd_tables.jsonl` directly.

## 9. How to run

1. Push these files. Delete `notebooks/Graph_and_Vector_Store.ipynb` from the repo; this
   notebook replaces it.
2. Run `notebooks/Fresh_Build.ipynb`, CELL 1 to CELL 8:
   - CELL 2 lists and labels your Drive.
   - CELL 3 rebuilds the graph and stops if a fix did not take.
   - CELL 5 rebuilds the text store from scratch.
   - CELL 7 shows the pipeline running on the VINE graph.
   - CELL 8 moves the old files into `Beyond_RAG/_to_delete/`.
3. Run `notebooks/Retrieval_Test.ipynb`, CELL 1 to CELL 8. CELL 8 compares the result with
   the run on the old graph.
