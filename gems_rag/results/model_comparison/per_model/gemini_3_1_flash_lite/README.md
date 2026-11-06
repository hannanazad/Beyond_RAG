# Gemini 3.1 Flash-Lite

Model ID: `gemini-3.1-flash-lite`

This folder contains the final scored 150-question dataset used in the
cross-model evaluation.

## Final files

- `final/questions_and_answers.csv`
- `final/questions_and_answers.jsonl`
- `final/questions_answers_scored.csv`
- `final/questions_answers_scored.jsonl`
- `final/item_scores_msdi.csv`
- `final/standardized_summary.json`
- `final/evaluation_report.md`

Canonical or merged answer/retrieval files are included when they existed as
standalone final artifacts. The archival evaluation bundle and raw source-run
archives are retained for auditability.

## Important

A valid primary answer was not replaced merely because a later answer was
better. Retry records replaced only operational failures such as missing,
empty, truncated, quota-failed, or corrupted outputs.
