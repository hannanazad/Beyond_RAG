# VINE answer-then-check (`vine2/`)

A separate version of VINE. The plan-first pipeline (`mrag/vine`, `hprc/`) is not changed.

## Why

The plan-first VINE lost to plain RAG on the same evidence. These were the design faults:

1. **The plan step filtered the evidence.** It chose which provisions mattered, and the answer writer never saw the rest.
2. **The answer writer could only repeat check results.** So it could not explain a rule, its condition or its exception.
3. **Each check saw one claim and a few pieces of evidence.** The checks lost the links between rules.
4. **A failed plan left a question with no answer.**
5. **Two code checkers gave verdicts without comparing anything.**

This version turns the order round. The answer is written first from all the evidence, and then every statement in it is checked.

## How it works

| Stage | Who | What |
|---|---|---|
| A. write | Qwen3.8-27B on our GPUs | Answers each question from **all** of VINE's evidence (`kq_r4299665_s0c3805.json`), using GEMS-RAG's answer prompt and up to 4 images. This is `compare40/run_qwen_rag.py`, unchanged. |
| B. check | Claude Sonnet 5.5 (effort high) | Splits each answer into numbered statements. Judges every statement against the whole question, all the evidence and the same images, and lists what the answer is missing. |
| B. code | no model | Verifies the checker's work (see below), then writes the final answer. |

**What the code checks before anything the checker says is used:**
- **Quotes:** every quote must appear word for word in the evidence piece it names (whole words and whole numbers, in order). A value read from a picture counts only if that picture was attached.
- **Corrections:**
  - no new number that no verified quote or the question contains (a correct sum written out in the correction is allowed). Sizes ("36x36", "12-inch", "40in") and the words two to twelve count as numbers; section and paragraph numbers do not;
  - no new requirement word unless a verified source has that force: "shall" needs a Standard, "should" a Guidance, "may" an Option (a table or note needs the word in its quote). "Not required" states no requirement. A word the draft used only in a sentence with "not" counts as new. The question never counts for this;
  - no newly named provision type (Standard, Guidance, Option, Support) that its sources are not;
  - turning a requirement round ("shall" to "shall not", "required" to "not required", "no sign shall" to "a sign shall"; "doesn't" counts as "does not") needs a quote with a limiting word (not, except, unless, only, …), or two pieces, or (for "not required") an Option or Guidance source about the same thing and no Standard source;
  - turning the main answer or a leading yes/no round needs two different pieces, counted over the corrections in the reply that turn it the same way and pass their own checks. A table and its rows count as one piece;
  - if a correction that would turn the main answer round is not applied, no correction that turns something round is applied, nor one that changes a value the main answer states: the main answer stays as written, whole;
  - a yes/no elsewhere may not be turned against the main answer as it stands after the corrections.
- **Arithmetic** written as `a x b = c` is recomputed (unit words ignored), in the draft and in every correction and addition. A unit conversion ("36 x 36 inches = 9 square feet") is not checked. "= 20%" may be the share or the share x 100.
- **Additions** need a verified quote; may not repeat what is already there (an exception or a new value is not a repeat), bring in unquoted numbers or unbacked requirement words, name a provision type that their sources are not, or start with a yes/no against the main answer as corrected.
- **Citations:** every provision in the answer's citation list must be in the evidence.

**Each statement ends up as one of these:**

| Outcome | What happens |
|---|---|
| checked | kept as written |
| corrected | replaced by the correction. A table row is rewritten in place when the correction is a row with the same cells; otherwise the clean answer drops the row and gives the correction just after the table |
| disputed | the checker's correction failed the code checks: the statement is kept, and the proposed correction is listed but not applied |
| not confirmed | kept as written and marked |
| not judged | the checker call for it failed: kept as written and marked, and asked again when the same command is run again |

**Three final answers are written:**
- **marked:** every mark is shown, plus a line saying what was checked;
- **clean:** the same corrections and additions with no marks. The additions go just before the citation list;
- **corrections only:** the clean answer without the additions.

Grade the clean one and the drafts, to see what the checks add. The corrections-only file shows how much comes from the corrections alone.

**The writer and the checker are different models,** and the checker is the stronger one.

**There is always an answer:**
- If the writer gives no answer for one question, the checker model writes one, marked as not independently checked.
- If a check fails, the draft is given as it is, marked unchecked.
- A checker reply cut off at its token limit is checked again in halves.
- If the writer stage fails for more than 5% of the questions, stage B stops and says so.

## Run on Grace

```
bash vine2/run_vine2_grace.sh 132692299628 $SCRATCH/questions150/questions_150.json
```

Before submitting, the launcher checks:
- every question is in the evidence file with the same text;
- every image exists;
- the drafts file (if there is one) answers these same question texts, not an old question set with the same ids;
- the code is committed and not changed locally;
- no other vine2 job is queued or running.

It then submits:
- **stage A** (GPU, up to 16 h), only if some question has no draft yet;
- **stage B** (CPU, starts after A, up to 8 h).

Running the same command again does only what is not done yet (and asks again for any statements that were not judged).

To check only some questions in stage B, put `V2_ONLY=VQ001,VQ002` in front of the command. Stage A is then skipped if those questions have drafts; if not, it answers every question that has no draft yet. The answer files still list every question.

**Output** (`STEM` is the question file's name without `.json`):

| File | What it holds |
|---|---|
| `$SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_qwen_STEM.jsonl` | the writer's answers |
| `$SCRATCH/Beyond_RAG/vine2_runs/STEM/final.jsonl` | everything for each question: draft, final answer, each statement's verdict with its verified quotes, additions, code checks, checker calls and cost |
| `.../answers_final.md` | the final answers, with the marks |
| `.../answers_final_clean.md` | the final answers, without marks (grade this one) |
| `.../answers_final_corrections_only.md` | the clean answers without the additions |
| `.../answers_draft.md` | the drafts, graded the same way, to measure what the checks add |
| `.../manifest.json` | settings, fingerprints, totals |
| `.../checker_cache/` | every checker reply, so a run can be repeated exactly |

## On VisRAG's pages instead of VINE's evidence

The same pipeline, with VisRAG's retrieval in place of VINE's, to test VisRAG's retrieval inside VINE. **Nothing of VINE's goes in**: no VINE piece, label, type or section number.

```
bash vine2/run_vine2_visrag_grace.sh 132692299628 $SCRATCH/questions150/questions_150.json
```

| Job | What |
|---|---|
| 1. VisRAG (1 A100) | VisRAG-Ret ranks the manual's pages (`compare40/visrag_retrieve.py`, unchanged; the page vectors of the 40-question run are reused). Then `vine2/visrag_pages.py` takes the top 20 pages of each question: each page is one piece, `Page X`, holding the words printed on it, read straight from the manual PDF. The first 4 pages also go as pictures. |
| 2. writer (2 A100s) | Qwen3.8-27B answers from those pages (`vine2/run_qwen_pages.py`: `compare40/run_qwen_rag.py` unchanged, with `vine2/pages_writer.py` as the writer). GEMS-RAG's prompt, each page whole, cited as "Page X". |
| 3. checker (CPU) | `vine2/check_job.slurm` and `vine2/check.py`, as for VINE's evidence. |

The page words are there so the code can check Sonnet's quotes word for word: they are the same words as on the page pictures.

**How the code checks work on pages** (pages carry no labels):
- a paragraph's type ("shall needs a Standard", and the types a fix may name) is the heading printed above the quote ("Standard:", "Guidance:", "Option:", "Support:") on that page; with no heading above it, the quote's own words (shall / should / may);
- numbers in a fix must be in the quote itself, not just somewhere on the page;
- a word broken at a line end in the PDF is matched both joined and with its hyphen;
- one page is one piece, so two paragraphs on the same page count as one source for the "two pieces" rule (stricter than with VINE's evidence, where each paragraph is a piece).

**Output:** `$SCRATCH/Beyond_RAG/vine2_runs/questions_150_visrag_p20/` (grade `answers_final_clean.md`). The page evidence is `$SCRATCH/Beyond_RAG/compare40_runs/visrag/pages_questions_150_p20.json`, and the drafts are `.../vine_rag/answers_qwen_questions_150_visrag_p20.jsonl`. The run on VINE's evidence is not touched.

Tests: `python3 tests/test_vine2_pages.py`.

## On M3DocRAG's, ViDoRAG's or RegionRAG's retrieval

The same test for three more visual RAG systems (why these three: the project doc `VISUAL_RAG_PICKS_2026-11-21.md`). Only each system's **retrieval** goes in, run with **its own code** at a pinned commit and its released models, and **nothing of VINE's**. Then the same writer, checker and code checks as above.

```
bash vine2/vis_setup.sh m3docrag        # once per system, on a login node (internet)
bash vine2/run_vine2_vis_grace.sh 132692299628 $SCRATCH/questions150/questions_150.json m3docrag
```

| System (code, commit) | What goes in, a question (20 pieces, the first 4 also as pictures) |
|---|---|
| M3DocRAG (bloomberg/m3docrag, 29e6ac2) | Its top 20 pages: ColPali v1.2 on its own page pictures (pdf2image, 144 dpi), the question as it is, MaxSim over every page (`m3docrag_retrieve.py`). Each page is `Page X` with the words printed on it, from the PDF, as for VisRAG. |
| ViDoRAG (Alibaba-NLP/ViDoRAG, 2c1ec39) | The pages ViDoRAG returns (5 to 20; its Gaussian-mixture cut on ColQwen2 v1.0 over page pictures and BGE-M3 over the pages' OCR text, joined, in page order). Each page is `Page X` with the **OCR text ViDoRAG gave**, as it is. Its pictures (200 dpi JPEG) and OCR (FastDeploy PP-OCRv3, CPU) are made first by its own scripts (`vidorag_ocr.py`, job 0). The 4 pictures are the pages its picture side ranked highest. |
| RegionRAG (Aeryn666/RegionRAG, 1ff0f29) | Its best 20 regions (RegionRet: per-patch similarity, connected patches, one box each; its default settings), on the page pictures of the VisRAG run (RegionRAG has no PDF step). Each region is `Page X (region k)` with the words printed inside its box, from the PDF; the first 4 regions also go as the region cut from the page picture. |

- `vis_setup.sh SYSTEM` makes the system's own environment (its authors' library versions), copies its code at the pinned commit, downloads its models and records their commits (`$SCRATCH/vine/vis/SYSTEM_revisions.json`). A model already in the cache is used as it is. RegionRAG's model is gated on Hugging Face: agree to its terms with your account and put a read token in `$SCRATCH/vine/hf_token` first.
- **Files on scratch:** the scratch space has a limit on the number of files (250,000). Before each environment the setup checks there is room, prints the count before and after, and stops otherwise. The estimates come from the environments already on Grace (VINE's torch 2.6.0 one has about 51,000 files): about 42,000 for M3DocRAG, 45,000 for ViDoRAG (20,000 if M3DocRAG's torch is still in uv's store, as the two share it), 15,000 for ViDoRAG's OCR, 62,000 for RegionRAG, each plus 5,000 to spare. So set up M3DocRAG first, then ViDoRAG, without cleaning uv's store between them. M3DocRAG (which pins no torch) and ViDoRAG (whose lock pins torch 2.6.0 and torchvision 0.21.0) get the same torch build and Python 3.12 as VINE's environment. RegionRAG keeps its own torch 2.5.1. The setup writes no .pyc files.
- **poppler:** M3DocRAG and ViDoRAG make page pictures with pdf2image, which runs poppler's `pdftoppm`; Grace has none on the system, so the setup uses Grace's module `poppler/24.04.0` (with `GCC/13.2.0`) through small wrappers in `$SCRATCH/vine/vis/poppler_bin`, which set that module's libraries for the poppler program only (not for Python or torch).
- The code checks on pages are those above. For regions: a region may not show its heading, so then the quote's own words give its type; and **regions of one page are one piece** for the two-pieces rule, as for whole pages.
- The checker gets a short note on regions ("parts of manual pages"); for pages its prompt is the same as in the VisRAG run, word for word.
- A region's box moves in steps of the model's picture patches (about 15 points on the page), so a word at the edge of a box can be cut off or left out.
- Safeguards: a model that loads with weights "newly initialized" or adapter keys missing stops the job (`LoadGuard`); a model a system loads by name must resolve offline to the recorded commit; the files a system never makes again (M3DocRAG's page pictures, ViDoRAG's pictures, OCR and vectors) are tied to the PDF, code and model commits (`vine2_inputs.json`) and a mismatch stops; one retrieval per system at a time (M3DocRAG, ViDoRAG share their folders); a new checker job waits for the checkers already queued.
- **Output:** `$SCRATCH/Beyond_RAG/vine2_runs/questions_150_SYSTEM_p20/` (grade `answers_final_clean.md`); evidence `.../compare40_runs/SYSTEM/pieces_questions_150_p20.json`; drafts `.../vine_rag/answers_qwen_questions_150_SYSTEM_p20.jsonl`. Different systems may run at the same time.

Tests: `python3 tests/test_vine2_vis.py`.

## What it does not promise

"Checked" means a model compared the statement with the quoted manual text, and code confirmed the quote is really there. It is not a proof. A statement can be checked against the wrong paragraph, and the evidence can miss a paragraph that retrieval did not find. The code checks above limit the damage of a wrong check; they cannot rule it out.

## Tests

```
python3 tests/test_vine2.py
python3 tests/test_vine2_pages.py
python3 tests/test_vine2_vis.py
```

The tests use made-up evidence and stand-in models: no GPU, no API, no data.
