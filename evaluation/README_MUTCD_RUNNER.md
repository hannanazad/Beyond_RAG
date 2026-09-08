# MUTCD-150 model-loop runner

This package runs any current or future VLM exposed through the existing MUTCD RAG notebook over the fixed **MUTCD-150-v1.0** question set. It does not read the evaluator gold file and does not require disclosure of the RAG pipeline internals.

## Files

- `mutcd_benchmark_runner.py` — resumable sequential runner and output validator.
- `MUTCD_updated_kg_with_benchmark_runner.ipynb` — the supplied RAG notebook with a benchmark section appended.
- `model_registry_template.json` — editable model registry.
- `mutcd_benchmark_questions_v1.jsonl` — question-only benchmark; safe to expose to the RAG at execution time.

The runner package intentionally excludes `mutcd_benchmark_gold_v1.jsonl`.

## Before running in Colab

Place these three files in `MyDrive/MRAG/benchmarks/` or upload them when the appended notebook cell asks:

1. `mutcd_benchmark_runner.py`
2. `mutcd_benchmark_questions_v1.jsonl`
3. `model_registry_template.json`

Run the original notebook cells through pipeline initialization first. The following names must exist:

```python
CFG
pipeline
ask
```

## Model registry

A model is independent of the benchmark:

```json
{
  "alias": "descriptive_unique_name",
  "selector": "CFG-catalog-alias-or-exact-provider-model-id",
  "provider": "dashscope",
  "enabled": true
}
```

`selector` is passed directly to `CFG.set_vlm_model(...)`. Adding a new model later does not modify the questions or gold answers.

Use a distinct alias for each experimental configuration. If the model or prompt configuration changes materially, start a new `run_id`.

## Recommended execution sequence

### 1. Smoke test

Run 3 questions with one inexpensive model. Confirm that:

- all three answer records have `status: "ok"`;
- `answer_extraction_method` is not `not_found`;
- the retrieval JSONL contains captured text or display records;
- the manifest identifies the expected model and benchmark hash.

### 2. Full primary run

Run all 150 questions once for every enabled model using the same prompt style and RAG configuration.

Recommended settings:

```python
replicates=1
prompt_style="fewshot"
show_scores=True
show_text=True
resume=True
```

### 3. Consistency run later

After the primary evaluation, repeat a locked stratified subset three times per model. Do not substitute this for the full primary run.

## Canonical output files

Each run directory contains:

- `answers_<run_id>.jsonl` — exact model answers, status, timing, usage when available, model ID, question, and generic serialized return object.
- `retrieval_<run_id>.jsonl` — captured retrieval/debug text and notebook display outputs. Binary images are not embedded; only their byte count and SHA-256 are retained.
- `manifest_<run_id>.json` — benchmark and PDF hashes, public configuration snapshot, repository commit when available, model registry, runtime, and progress.
- `errors_<run_id>.jsonl` — model-switch and runner-level failures, if any.

Every answer record is flushed and fsynced immediately. An interrupted Colab job can be resumed with the same `run_id` and `resume=True`.

## Leakage safeguards

The runner:

- accepts only the question-only benchmark;
- verifies its SHA-256 by default;
- rejects evaluator-only fields such as `gold_answer`, source pages, required evidence, answerability, and scoring metadata;
- never opens the gold JSONL;
- preserves the model answer without rewriting or normalization.

Expected question-only SHA-256:

```text
3a04b1d620a80704eefac34c565449a0cb8814e781dd6d73b8afb77318b954b2
```

## Resuming and adding future models

Reuse the same `run_id` to continue an interrupted run or append newly enabled models. Completed records are matched by the exact resolved model ID, question ID, and replicate number.

Start a new `run_id` when changing any condition that could affect results, including:

- source PDF or index;
- retriever configuration;
- system or answer prompt;
- prompt style;
- decoding settings;
- RAG repository version;
- substantive preprocessing or figure extraction.

## What to return for evaluation

After validation, zip the run directory and provide the archive containing at least:

1. answers JSONL;
2. retrieval JSONL;
3. manifest JSON;
4. errors JSONL, when present.

Do not modify the JSONL files after the run. The validator reports SHA-256 hashes that will be included in the evaluation record.
