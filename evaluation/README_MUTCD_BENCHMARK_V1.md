# MUTCD-150-v1.0 Benchmark

This benchmark contains 150 model-agnostic questions derived independently from the uploaded MUTCD 11th Edition with Revision 1 incorporated.

## Composition

- 150 total questions
- 120 answerable questions
- 30 deliberately unanswerable or insufficient-evidence questions
- 60 text-primary questions
- 30 table-primary questions
- 30 figure-primary questions
- 30 mixed-evidence questions
- 30 development/calibration items
- 120 test items

## Files

### `mutcd_benchmark_questions_v1.jsonl`
Safe input for the RAG runner. Each line contains only the benchmark version, question ID, and question. It contains no gold answer, source page, or evaluation hint.

### `mutcd_benchmark_gold_v1.jsonl`
Evaluator-only file. It contains the gold answer, required answer elements, source PDF and printed-manual pages, sections, figures/tables, modality, difficulty, normative class, scoring method, and critical-error conditions.

Do not load this file into the RAG execution environment or include it in prompts.

### `mutcd_benchmark_review_v1.csv`
Human-readable review sheet containing all questions and gold metadata.

### `mutcd_benchmark_manifest_v1.json`
Contains source-document identity, benchmark counts, and SHA-256 hashes for the question, gold, and review files.

## Integrity rule

Use only `mutcd_benchmark_questions_v1.jsonl` during model execution. Preserve the exact file hashes in the manifest so future models can be compared against the same locked benchmark.
