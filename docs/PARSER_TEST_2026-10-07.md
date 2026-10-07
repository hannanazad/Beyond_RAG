# Parser test with Qwen3.8-27B, 7 October 2026

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

## One open question for you (not changed)

**The problem:** a guard can stay closed. When it does, the executor never runs that item. A merge that lists the item as an input then never runs either, and the answer comes out UNKNOWN.

The paper means a closed guard to say "this branch does not apply".

The notebook counts how often the plans do this ("plans with a guarded item as a merge input"). This has to be decided before the plans are executed. I have not changed it.

## How to run

1. Push the files above, and delete the two notebooks listed under **Delete from the repo**.
2. In Colab, choose Runtime, then Change runtime type, then **A100**.
3. Run `notebooks/Parser_Test.ipynb`, CELL 1 to CELL 12. It takes about 2 hours.
   - **Stop after CELL 9** and read the plan it prints.
   - **CELL 12 runs the test questions.** Run it once.
4. **If the runtime restarts after CELL 5:** run CELL 1, CELL 4 and CELL 5, then CELL 6 onward.
   - CELL 5 reads the saved retrieval results.
   - CELL 6 stops any model server still holding the GPU.
