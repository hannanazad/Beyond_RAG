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

## What it does not promise

"Checked" means a model compared the statement with the quoted manual text, and code confirmed the quote is really there. It is not a proof. A statement can be checked against the wrong paragraph, and the evidence can miss a paragraph that retrieval did not find. The code checks above limit the damage of a wrong check; they cannot rule it out.

## Tests

```
python3 tests/test_vine2.py
```

The tests use made-up evidence and stand-in models: no GPU, no API, no data.
