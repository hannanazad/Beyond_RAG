# GEMS-RAG: What Was Trained vs. What Is Rules — Component-by-Component

**Short answer: nothing was trained.** Not `figure_core.py`, not the parser, not the KG builder, not the router. There is not a single training loop, labeled training set, or fine-tuned weight anywhere in this project. Every component is one of two kinds: **hand-written deterministic code**, or a **pre-trained model someone else built, used frozen, off the shelf**.

---

## 1. How `figure_core.py` Cropped Without Any Learning

The trick is that a born-digital PDF is not a picture. The MUTCD PDF contains a **text layer** where every single word is stored with its exact coordinates on the page. PyMuPDF's `page.get_text("words")` returns a list of tuples like `(x0, y0, x1, y1, "Figure", ...)`. So "where is the text" was never a question to be learned — **the PDF literally tells you where each word sits.** What remained was two purely mechanical problems: which lines are captions, and given a caption, what rectangle is the figure.

### 1.1 Which lines are captions: a regular expression, not vision

1. Words get reassembled into lines by their y-coordinates.
2. Unicode hyphens U+2010 through U+2014 get normalized to a plain "-" (the Rev-1 pages use invisible non-breaking hyphens, e.g. "Table 6B‑2" with U+2011, that break ASCII matching).
3. Each line is tested against `CAPTION_RE` — a regex whose key discriminator is the **id-terminating period**:

| line | verdict | why |
|---|---|---|
| `Figure 4C-2. Title` | **caption** | period immediately after the id |
| `Table 2C-1 may be used.` | reference only | no period after the id — a body sentence that happens to start a line |
| `Figure 9D-2 shows...` | reference only | same |

That single punctuation rule separates captions from references throughout the entire 1,162 pages.

### 1.2 Who identified that rule: a human debugging session, not a dataset

The layout invariants were discovered by **looking at the actual document** during the v4 rebuild:

1. The v1 extractor had shipped with the wrong assumption — captions below figures, so crop *above* the caption.
2. The symptoms (eleven missing figures, crops showing the wrong content) forced a diagnosis.
3. The PDF was inspected directly — pages 151 and 115 were visually verified — and the invariant was established: **the MUTCD puts every caption above its content.**
4. That fact, the id-terminating-period rule, the dot-leader signature of table-of-contents pages, the "(Sheet n of m)" title suffix, and the fact that "Table 3-1 / 3-3" are external AASHTO citations were **all human-discovered observations about this one document, then hard-coded as rules.**

### 1.3 Given a caption, the rectangle is arithmetic

- **Top edge:** just below the caption line.
- **Bottom edge:** whichever comes first of the next caption on the page, the column boundary, or the page margin.
- **X-bounds:** from the column layout, narrowed to the caption's own column for inset figures, and partitioned by width when two captions share a row.
- **The crop itself:** PyMuPDF rasterizes exactly that rectangle to a PNG.

Every step is a coordinate comparison.

### 1.4 How it could be trusted without a model's benchmark: the census

1. A second regex sweep scans the **whole document** for every "Figure X-Y" and "Table X-Y" mention, producing the complete list of ids that *must* exist.
2. Extraction coverage is checked against that list.
3. The same extraction is cross-validated through a **second independent PDF backend (poppler)**.
4. `validate_coverage()` **hard-fails the ingest below 99 percent.**

This gate is why the approach worked — it caught a live bug in production: fitz's span-joined text carried encoding artifacts like `Figure4F-1.` (missing space glyph) and `4F- 1` (id split across glyph runs) that hid five 4F figures. That is why the extractor was rebuilt on **geometric word segmentation** (`page.get_text("words")`, never span joins), plus `canonicalize_ids()` to repair fused/split ids.

**Final state — verified, not estimated:** 485/485 figures, 68/68 tables, 727 crop images, 553 canonical ids, 0 duplicates.

---

## 2. The Same Question Asked of Every Other Component

| component | trained by us? | how it actually works |
|---|---|---|
| `figure_core.py` / `figures.py` | No — pure code | regex + coordinate geometry over the PDF text layer, as above |
| `parsing.py` (chunking) | No — pure code | the MUTCD prints "Standard", "Guidance", "Option", "Support" as literal headings; the parser splits on those headings, string-matches shall/should/may for `modal_verbs`, and regex-extracts figure/table/section refs and sign codes |
| `kg.py` (knowledge graph) | No — pure bookkeeping | nodes come from ids the parser already found; edges come from the refs it already extracted plus hierarchy read off the id format; the 3-tier anchoring is an if/elif preference; networkx just stores it |
| `question_router.py` | No — hand-set rules | hard-yes/hard-no patterns plus additive scores (+0.45 sign codes, +0.30 visual nouns, +0.15 placement, −0.35 textual, +0.35 × KG fraction) against a 0.5 threshold; **the weights were set by human judgment and iteration, not fit by any optimizer** |
| fusion priors (`w_graph`, `w_ruletype`, `w_hierarchy`) | No | hand-set config constants added to similarity scores |
| BGE-M3 embedder | No — **pre-trained, frozen** | BAAI's off-the-shelf model; we only ran inference to turn chunks, captions, and queries into vectors |
| ColQwen2 page/figure retriever | No — pre-trained, frozen | off-the-shelf ColPali-style model; relevance is max-sim math between its query vectors and image-patch vectors |
| mxbai-rerank-large-v2 | No — pre-trained, frozen | off-the-shelf cross-encoder scoring (query, chunk) pairs; we call it, keep top 6; fallback BGE-reranker-v2-m3 likewise |
| VLM figure filter (P2) | No — **prompted**, not trained | an off-the-shelf flash-tier VLM given a zero-shot instruction ("which crops must the reader see") returning JSON indices |
| answer VLM (P1) | No — prompted, not trained | frontier VLMs via API; **"few-shot" means example Q&As placed inside the prompt at inference time — in-context prompting, which involves no weight updates whatsoever** |
| GPT-5.6 judge | No — prompted | rubric supplied in the prompt |

---

## 3. The Clean Division of Intelligence

- **Document understanding at ingest time** is entirely deterministic rules derived from manually verified invariants of this one document.
- **All learned behavior** comes from frozen pre-trained models we selected and prompted but never touched the weights of.
- The closest thing to "learning from data" anywhere in the project is **configuration selection** — choosing the fewshot prompt style and the flagship answer model *after* running the benchmark sweeps — which is hyperparameter selection by evaluation, not model training.

---

## 4. Why Rules Instead of a Trained Layout Detector (Reviewer-Ready Justification)

The MUTCD is a single, extremely regular document with absolute invariants, and the mention census gives you **free, exhaustive ground truth** for what must exist. A rules-plus-census pipeline is:

1. **deterministic** — same input, same output, every run,
2. **fully auditable** — every crop traces to a caption line and a rectangle computation,
3. **provably complete** — 485/485 is a verified count, not a benchmark estimate.

A trained detector would add labeling cost and non-determinism while making that 100 percent guarantee impossible to state.

---

## 5. One-Sentence Version (Paper / Defense)

> The system trains nothing — document understanding at ingest is deterministic rule-based parsing of the PDF's native text layer, with rules derived from manually verified layout invariants and enforced by a 99-percent coverage gate, while all learned behavior comes from frozen pre-trained models (BGE-M3, ColQwen2, mxbai-rerank, and API-served VLMs) that are prompted, never fine-tuned.
