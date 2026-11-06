# MUTCD per-response grading rationales

This package contains one grading rationale for each of the 900 Claude Fable 5
ablation responses and each of the 150 original-RAG baseline responses.

## Main files

- `master/ablation_900_response_rationales.csv`
- `master/ablation_900_response_rationales.jsonl`
- `master/baseline_150_response_rationales.csv`
- `master/baseline_150_response_rationales.jsonl`
- `master/all_1050_response_rationales.csv`
- `master/all_1050_response_rationales.jsonl`
- `per_response/<condition>/<question_id>.json`
- `per_condition/<condition>.md`

## Official item grade

The official item grade retains four separate scores:

- correctness
- completeness
- faithfulness
- citation and evidence localization

Each score ranges from 0.00 to 1.00. Strict full credit requires all four scores
to equal 1.00.

The `descriptive_mean_percent` field averages the four item scores for easier
reading. It is not an additional benchmark metric and does not replace the
weighted model-level generation score.

## Rationale provenance

The package separates official grades from rationale wording.

1. The 18 repaired A1 no-router responses use direct GPT-5.6 differential-audit notes.
2. Original-RAG partial-credit items retain their original adjudication notes.
3. A baseline note is reused for an ablation response only when the question and
   all four official item scores match.
4. The remaining rationale text uses a structured reconstruction from the saved
   official scores, model answer, gold answer, citations, and retrieval trace.

The structured reconstruction identifies likely covered and missing gold-answer
clauses through token-level comparison. Those clause lists support auditing but
do not replace the official dimension scores.

## Evaluation confidence

`evaluation_confidence` records confidence in the audit explanation, not model
self-confidence and not a statistical probability.

- 0.90: explicit adjudication note
- 0.88: strict full-credit record reconstructed from accepted scores and evidence
- 0.82: repaired A1 response reviewed by GPT-5.6
- 0.76: partial-credit rationale reconstructed from retained official scores

## Privacy and reasoning

The rationales provide evidence-based grading summaries. They do not contain
private hidden chain-of-thought. Each record states the answer, gold answer,
official scores, detected citations, relevant retrieval measures, and the
specific accepted or missing answer elements used to explain the grade.
