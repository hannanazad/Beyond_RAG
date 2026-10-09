# Retrieval: finding the governing provisions, and one notebook from start to end (9 October 2026)

## 1. Why retrieval changed

On the 154 DEV cases (written from the MUTCD, never from a test question), the retrieval test of 7 October 2026 found that **17 cases lost a needed section or paragraph before the parser saw it**. If a provision never reaches Kq, it can never become a check (paper §3.1: obligations come from Kq). The paper calls a missing check an "obligation omission" (Appendix C). Two of the 11 DEV cases run end to end showed it: P33 (5B.01 ¶2 never seen) and P35 (6C.01 ¶1 never seen).

Reading the 17 misses against the manual showed four causes:

| Cause | Example (DEV) |
|---|---|
| A side fact in the question pulls the one search away | "the ramp's advisory speed is 25 mph" pulled the search to 2C.12 instead of 2C.46 Added Lane signs |
| Everyday words instead of the manual's words | "QR-style pattern" for a *scanning graphic* (1C.02 item 209); "automated vehicles" for a *driving automation system* (1C.02 item 15, 5A.03) |
| The right section is named by its heading only | "EXIT CLOSED Panel" (6I.03), "Pavement Markings for Two-Way Left-Turn Lanes" (3B.05) |
| A paragraph ranked without its heading | 6C.01 ¶1 ("shall be applied by knowledgeable … persons") says nothing about work zones until you see it sits in Section 6C.01 |

## 2. What changed (`mrag/find_provisions.py`, used by `retrieve_for_compile`)

No language model is added before retrieval. The encoder and the reranker are the same ones as before.

**More places to look:**
1. the whole question (as before);
2. each *informative* sentence of the question on its own (one with at least 3 content words; "Does the manual allow this?" is not informative);
3. the manual's own terms whose definitions match the question (1C.02 and 5A.03), including "see" links ("Automated Vehicle-see Driving Automation System");
4. the sections whose headings (Part, Chapter, Section title) match the question, with their Standard, Guidance and Option paragraphs.

**One judge, reading like an engineer:** the cross-encoder now reads each paragraph *with* its Part, Section and heading (and a list item with its lead-in).

**Taking turns for the slots:** the searched slots are filled in turn: one from the whole question's ranking, then one from a sentence's ranking (the sentences take turns), and so on.
- Why not a vote? The whole question contains the side fact, so its ranking is pulled the same way as the side fact's own sentence. A vote would give the side fact most of the say. A made-up case in `tests/test_find_provisions.py` shows this.
- Taking turns gives every fact in the question its own best provisions in Kq. The whole question still fills half the slots, in its own order.
- A question with only one informative sentence is ranked by the whole question alone, as before.

**Kq does not grow.** It has the same 20 searched and expanded slots and the same closure budget of 60. Cross-reference expansion and the closure work as before.

**The old path is unchanged.** With `CFG.compile_find_provisions = False`, `retrieve_for_compile` gives exactly what the previous commit gives: the same chunks, scores, figures and debug record. This was checked on all 154 DEV cases with stand-in models.

**Every provision records how it was found** (`found_by`: question, sentence n, term: X, heading: 2C.46), and every view's ranking is kept in `debug["find"]`. So a run can be read afterwards without running it again.

## 3. How it is measured

`notebooks/VINE_Run.ipynb`, CELL 5, uses the 154 DEV cases:
- **Before:** the 7 October run (the retrieval code did not change between then and this change). The exception is the 12 cases corrected on 9 October, which are run again in the same session with the new part switched off.
- **After:** the new retrieval.
- **A case passes** when every target section, and the paragraph the case was written from, reach what the parser reads.
- **The gate:** if fewer cases pass than before, the notebook stops there, before the parser or the API is used.
- For every case that misses now or missed before, it prints where each target came from and how each view ranked it.

**What could not be done here:** the real encoder and reranker cannot be downloaded in this workspace. Here they were replaced by simple word-matching stand-ins, which only show that the code works end to end. With the stand-ins, 99 → 104 cases pass, but word matching is not the real model. **The real number comes from CELL 5 on Colab.**

## 4. One notebook, start to end: `notebooks/VINE_Run.ipynb`

Press **Run all**. On an A100:

| Cell | What | Time |
|---|---|---|
| 1–4 | Drive, repo, packages, vector store, retrieval models, the questions | 5–10 min |
| 5 | retrieval check on 154 DEV cases, before and after, **the gate** | 30–60 min |
| 6 | Kq for every question (11 DEV + 20 sample) | a few min |
| 7–9 | free the GPU, install and start the parser (Qwen3.8-27B, xhigh) | 15–25 min |
| 10 | the parser writes every plan | about 7 min a question |
| 11–12 | retrieval back on the GPU, the checker model (Sonnet 5.5) and its probes | a few min |
| 13 | the checkers execute every plan; DEV printed in full | 15–30 min, about $3 |
| 14 | the sample answers (for scoring outside the pipeline), and one file with the whole run | — |

- **Resumable:** every stage is saved on Drive as it goes, in a run folder named after the retrieval code, the store and the parser instructions. If Colab disconnects, Run all again and it carries on where it stopped.
  - A plan that broke because the model call or the run broke is tried again.
  - A plan that failed its own checks is kept as a result.
- **The parser's window:** each prompt is counted by the server's own tokenizer. It gets 49,152 tokens to think and write, or what fits if the prompt is very long. Without this, a long prompt would be refused by the server.
- **Sealed questions, later:** set `SEALED_FILE` in CELL 4 to a JSON file of `{id: text}` on Drive, then Run all. Those questions are answered instead of the samples.
- **No gold answer is anywhere in the notebook.** The sample answers are saved and downloaded for scoring outside the pipeline.

## 5. Files

| Path | What |
|---|---|
| `mrag/find_provisions.py` | NEW: the four ways of looking, the definitions and headings, ranking by every view, taking turns |
| `mrag/retrieval.py` | `retrieve_for_compile` uses the finder when `compile_find_provisions` is on |
| `mrag/config.py` | `compile_find_provisions` (on) and its settings |
| `evaluation/retrieval_check.py` | per target: in the pool, found by, rank in each view, searched rank; `passes`, `gate`; the older `retrieve()` top 6 is off by default |
| `evaluation/vine_run.py` | NEW: the notebook's helper code (resumable check, "before", the parser's token budget, files, answers) |
| `notebooks/VINE_Run.ipynb` | NEW: the whole pipeline in one run |
| `notebooks/Parser_Test.ipynb`, `notebooks/Execution_Test.ipynb` | only the list of retrieval files gained `mrag/find_provisions.py` |
| `tests/test_find_provisions.py`, `tests/test_vine_run.py` | NEW: made-up data only |

## 6. A standing rule from Hannan (9 October 2026)

The paper is used **for its method only**. The GEMS-RAG / RAG baseline and the "backbone kept fixed" parts are no longer this project and will be removed from the paper.
- They are never a reason to freeze, limit or compare anything.
- No RAG comparison is planned.
- A retrieval failure is ours to fix.
