# Parser test with Qwen3.8-27B, 7 October 2026

> **Update, 8 October 2026 (evening):** the instructions are now **fix5** (given facts in Γ0q; the exception-base check). Every plan is made again. See `CHECKER_FIXES_2026-10-08.md`.

## What the parser does

The parser gets two things: a question, and everything retrieval returned for it. Retrieval runs on the VINE graph through `retrieve_for_compile`.

The parser writes the plan, which is the IR:
- the obligations;
- what each one depends on;
- the guards;
- the merges;
- where each obligation's evidence is.

The parser does not answer the question. The checkers decide each obligation later, from the manual.

The notebook stops once the plan is written. It does not execute the plan and it writes no answer. **The plan is what is being tested.**

## Files

| File | What changed |
|---|---|
| `notebooks/Parser_Test.ipynb` | new: the parser test (12 cells) |
| `mrag/vine/parser.py` | the instructions were rewritten (see below); new checks on the plan |
| `mrag/vine/vllm_client.py` | new: runs the model with vLLM in its own Python environment |
| `evaluation/parser_check.py` | new: checks on the plans that need no gold answers |
| `mrag/vine/run.py` | small change: `ask_vine` gives the parser the graph and the tables, so it can check references |
| `tests/test_parser.py` | updated for the new checks; 20 checks, all pass |
| `notebooks/Retrieval_Test.ipynb` | two comments now name `Fresh_Build.ipynb` |

**Delete from the repo:**
- `notebooks/LLM_Semantic_Parser_Test.ipynb`. It prints gold counts: "gold for SAMPLE004 is 6", "148 for 60 gold", "9 of 43".
- `notebooks/Graph_and_Vector_Store.ipynb`. Fresh_Build replaced it.

## The model

**Model:** `Qwen/Qwen3.8-27B-FP8`
- 27.8 GB.
- It runs on one A100. The A100 has no FP8 maths, so vLLM keeps the weights in 8 bits and computes in 16 bits.
- Only the language part is loaded (`--language-model-only`).

**Server:** vLLM 0.31.0, in its own environment (`/content/vllm_env`).
- vLLM needs a newer torch than the retrieval stack uses.
- In its own environment, it cannot replace the retrieval stack's packages.

**Settings:**
- Thinking is on, with reasoning effort "medium".
- Sampling uses the model card's thinking settings: temperature 1.0, top-p 0.95, top-k 20.

**Repeatable runs:**
- seed 42 on every request;
- one request at a time;
- no prefix caching;
- every reply is cached on Drive (`parser_runs/model_cache/`). Each cached file holds the prompt, the reply and the model's thinking.

## What the model is told, and where it comes from

The model is told only three things:
1. The paper's description of compilation (§3.1):
   - the four steps;
   - the seven obligation types;
   - the four structure rules;
   - the paper's own example: "if a provision applies only to a particular class, requires two independent conditions to be satisfied, and contains a separate exception ...".
2. The manual's own definitions of Standard, Guidance, Option and Support.
3. How the checkers and the merges work in this code:
   - which hint types the calculator reads;
   - how a conjunction, an alternative and an exception merge are applied.

**Removed:** the old block that listed four "usual" dependency shapes, such as "the controlling value is max(A, B)". A shape listed because questions have it is a shape learned from questions.

There are no worked examples, and no section, table or figure numbers.

**Leak scan of every new file:** I looked for 4-, 5- and 6-word phrases that appear in the test material but not in the manual. The test material is:
- the 10 sample questions;
- their gold answers, notes, answer elements, error conditions and gold obligation claims;
- all 150 MUTCD-150 records.

The scan found 0 such phrases in the instructions and 0 in the code. The notebook holds the 10 question texts in CELL 4, on purpose, so that it can run them. That cell holds nothing else.

## What the model reads

The model reads everything retrieval returned, grouped by section, each item with its id. Some items are labelled:
- **Support:** "information only; never an obligation".
- **Table rows:** "printed table content, not a provision".
- **Figure descriptions:** "written by a reader, not the manual's words; it may contain mistakes; not a provision".
- **Heading inferred:** a note whose heading was read from its verb is marked "heading inferred".

The model also sees a list of the figures the vision model can be given.

## What is checked before a plan is accepted (no model)

**Structure** (as before): ids, dependencies, cycles, merges, and a terminal that can be reached.

**New checks against the manual:**
- Every obligation names the provision it comes from, and that provision was shown to the model.
- That provision is a Standard, Guidance or Option. It is never Support, a table row or a figure description.
- The obligation's authority matches the provision's printed heading.
- Every table, figure and section in a hint exists in the manual.
- A column, chart or sheet named for a table is one the table prints.
- There is no `threshold` merge. The executor has no comparator for one, so it could only ever come out UNKNOWN.
- A guard reads only results that its item already waits for. Without this, a "not" guard could open before the check it reads had even run.

If a plan fails a check, it goes back to the model with the problems, written with the ids the model used. The model gets at most 3 tries. There is no fallback in this test: a failure is reported as a failure.

## What the notebook measures (no gold anywhere)

| Measure | What it says |
|---|---|
| outcome | valid first time, valid after repair, or failed |
| shape | obligations, dependencies, guards, merges, depth, checkers assigned |
| numbers | where each number in a claim came from: the question, the source provision, other retrieved text, or nowhere |
| repeat | the same input, asked again without the cache, gives the same plan (3 cases) |
| DEV only | does the plan use the provision the case was written from |

**DEV:** 11 cases written from random MUTCD provisions. The cases were picked by a fixed rule: the first scenario case of each Part, plus the first two-section case of each kind.

**TEST:** the 10 sample questions, parsed once, in CELL 12. Their plans are saved to `parser_runs/run_*/test_plans.json` and downloaded, so they can be scored outside the pipeline.

## Closed guards (decided 8 October 2026)

**The problem was:** a guard can stay closed. When it did, the executor never ran that item. A merge that listed the item as an input then never ran either, and the answer came out UNKNOWN.

**Decided:** a closed guard means "this branch does not apply". The executor now marks such a branch NOT_APPLICABLE and merges leave it out (dead-path elimination). A guard that depends on an UNKNOWN result leaves the branch UNKNOWN. See `docs/EXECUTOR_NOT_APPLICABLE_2026-10-08.md`.

The notebook still counts how often plans have this shape ("plans with a guarded item as a merge input").

## How to run

1. Push the files above, and delete the two notebooks listed under **Delete from the repo**.
2. In Colab, choose Runtime, then Change runtime type, then **A100**.
3. Run `notebooks/Parser_Test.ipynb`, CELL 1 to CELL 12. It takes about 2 hours.
   - **Stop after CELL 9** and read the plan it prints.
   - **CELL 12 runs the test questions.** Run it once.
4. **If the runtime restarts after CELL 5:** run CELL 1, CELL 4 and CELL 5, then CELL 6 onward.
   - CELL 5 reads the saved retrieval results.
   - CELL 6 stops any model server still holding the GPU.

## Results of the run on 7 October 2026 (Colab A100 40 GB)

**Setup that worked:**
- vLLM 0.31.0, torch 2.13 (CUDA 13.2), driver 580.82.
- Model revision `017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`.
- The model takes 28 GB. There is room for about 75,000 tokens of working memory.
- It writes about 39 tokens a second.

**Two setup fixes, both in the notebook now:**
- The model is downloaded to Colab's own disk. Our config had sent the download to Drive.
- vLLM's FlashInfer sampler is switched off (`VLLM_USE_FLASHINFER_SAMPLER=0`). It failed to build on Colab, and seeded requests never use it anyway.

**Repeat check:** the same input, asked again with no cache, gave an identical plan in 3 of 3 cases.

### DEV runs (11 cases written from MUTCD provisions)

| Run | Instructions | Valid first time | Notes |
|---|---|---|---|
| 1 | as first written | 11/11 | In 5 plans, true and false were turned around. For example, a claim said "the rule applies" where it should have said "the rule is met". |
| 2 | fix3 (commit 32fedfb) | 11/11 | Every claim reads TRUE = the provision is met, in the same direction as the merge it feeds. A claim written as a question is sent back. |
| 3 | fix4 (commit e7ae691), **frozen** | 10/11, plus 1 after a repair | For questions about what the manual requires or allows, each claim says what the manual requires or allows in that situation. |

In every run, the plan used the target provision whenever it reached the parser (6 of 6).

Each run still has 2 or 3 slips, and they are different each time. Examples:
- a base rule written as "the rule applies";
- a gate on a condition the question never states;
- a wrong type, so the check goes to the wrong checker.

These come from sampling noise, not from a pattern. The instructions were frozen at fix4, so that the DEV cases would not be overfitted.

### TEST run (the 10 sample questions, run once with fix4; not scored against gold)

**Outcome:**
- All 10 plans were valid: 9 first time, 1 after a repair.
- The repair came from the check that a guard may read only what its item requires.
- Every model call finished normally.

**Size and speed:**
- 235 seconds and 9,200 thinking tokens per question on average.
- 8.5 obligations per plan on average, with an average depth of 4.5.

**Structure:**

| | Plans |
|---|---|
| with dependencies | 8 of 10 |
| with guards | 6 of 10 |
| with merges | 10 of 10 |

**Checkers assigned:**

| Checker | Obligations |
|---|---|
| language model | 45 |
| rule evaluator | 32 |
| vision model | 7 |
| resolver | 1 |

**Slips that can be seen without gold:**
- **The parser does arithmetic and writes conclusions into claims.** SAMPLE002 works out the threshold and the legend itself; SAMPLE003 works out 2.5 × 30 = 75. The instructions say not to do this.
- **True and false still turned around in some claims.** In SAMPLE006, claims are written as "the display does not ..." but feed a merge that means "acceptable".
- **Some terminal merges are written as a whole narrative answer** rather than one true/false statement (SAMPLE006, SAMPLE009, SAMPLE011).
- **In 6 of 10 plans, a guarded item is an input to a merge.** In SAMPLE005, when the exception applies, the guarded check never runs, so the merge never runs either. This makes the executor decision in the open question above necessary.

**Counting fix:** the "numbers found in no input" check had counted paragraph references such as "Standard 05" and "Option 13" as quantities. That is fixed in `evaluation/parser_check.py`. After the fix, only 2 numbers were truly worked out by the model: 5.4 and 75.

**Rule from here on:** the 10 sample questions have now been run. Any later change to the parser must be justified by the paper, the manual or the DEV cases, never by these test plans. A final score should come from questions the pipeline has never seen.

### TEST2: 10 more sample questions (SAMPLE012–SAMPLE021), added 7 October 2026

**What is in the notebook:**
- CELL 4 holds the 10 new question texts, and nothing else about them.
- CELL 13 parses them once, with the same frozen parser (fix4). The plans are saved to `run_*/test2_plans.json`.

**Retrieval is not redone.** CELL 5 now names its retrieval file after the code that does retrieval and the vector store it reads, not after the whole repo. So:
- the existing `kq_a75a7c2.json` is reused;
- only the 10 new questions are retrieved.

**Leak scan:**
- The new questions' authored text and gold answers were added to the probe set.
- Result: 0 matches at 5 and 6 words.
- At 4 words there is 1 match: the plan format's own field names (`"obligations": [{"id": "o1", "claim": ...`). That format comes from `compile.py` and was written before this batch existed.

**Gold check:** the gold answers were checked against the manual, outside the pipeline.
- All 41 quoted passages match the manual word for word, with the right paragraph numbers and headings.
- All 10 answers are correct. 3 have small wording points that do not change their results.
