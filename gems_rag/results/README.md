# Results

Everything measured in this project. Nothing here needs installing — these are finished data files you can open and read.

All numbers come from the same 150-question benchmark (`../benchmark/`), graded with the same written rubric (`../benchmark/EVALUATION_SPECIFICATION.md`).

---

## What is in each folder

| Folder | What it holds |
|---|---|
| `model_comparison/` | Twelve answering models run across all 150 questions, scored and compared |
| `ablations/` | Six experiments, each with one part of the system switched off |
| `grading_rationales/` | 1,050 records showing exactly why each answer got the score it got |
| `paper_outputs/` | The written results sections and their figures |

---

## 1. Model comparison

**The question: which answering model is best, holding everything else fixed?**

The retrieval stack never changed between models. Only the model that writes the final answer changed. That is what makes the differences meaningful.

### Final standings, score out of 100

| Rank | Model | Score | Full credit | Median latency |
|---|---|---|---|---|
| 1 | **Claude Fable 5** | **88.08** | 80.0% | 28.4 s |
| 2 | Claude Sonnet 5 | 87.81 | 74.7% | 11.0 s |
| 3 | Qwen3.7 Max | 87.35 | 76.7% | 68.1 s |
| 4 | Gemini 3.1 Pro Preview | 87.25 | 76.0% | 21.7 s |
| 5 | Qwen3.6 Flash | 86.96 | 74.0% | 32.7 s |
| 6 | Qwen3.5 Omni Plus | 86.95 | 71.3% | 10.7 s |
| 7 | Gemini 3.1 Flash-Lite | 86.92 | 76.7% | 9.2 s |
| 8 | Qwen3.7 Plus | 86.89 | 76.7% | 72.6 s |
| 9 | Qwen3-VL 235B | 86.73 | 74.0% | 17.3 s |
| 10 | Gemini 3.5 Flash | 86.60 | 76.0% | 22.5 s |
| 11 | Claude Haiku 4.5 | 86.47 | 75.3% | 10.4 s |
| 12 | Qwen3-VL Flash | 85.08 | 68.7% | 16.3 s |

"Full credit" means the answer was perfect on all four graded dimensions at once: correctness, completeness, faithfulness, and citation accuracy. It is a deliberately harsh measure, and it separates the models far more than the headline score does.

### Three things worth noticing

**The spread is narrow but the ranking is not noise.** Three points separate first from last. But full-credit rate ranges from 68.7 to 80.0 percent, which is a much wider gap — models differ most in how often they get *everything* right at once, not in average quality.

**Retrieval barely moves.** Every model scored between 19.35 and 19.63 out of 25 on retrieval. That is expected, because they all received identical retrieved evidence. It confirms the comparison is measuring what it claims to.

**Speed and quality are only loosely related.** Gemini 3.1 Flash-Lite placed seventh at 9.2 seconds per question. Qwen3.7 Plus placed eighth at 72.6 seconds — almost eight times slower for a slightly worse score. If you are choosing a model for deployment, the latency column matters as much as the score.

### Files

- `cross_model/03_paper_comparison_table_v2.csv` — the table above, full precision
- `cross_model/02_all_models_full_metrics_v2.csv` — every metric for every model
- `cross_model/figure_*.png` — five heatmaps used in the write-up
- `combined/` — all models' questions and answers in one place, scored
- `per_model/<model>/final/` — per-model answers, retrieval traces, item scores, and a report
- `MODEL_INDEX.csv` — which folder corresponds to which model

---

## 2. Ablation study

**The question: which parts of the system are actually doing work?**

One component is switched off per run, everything else held fixed, all 150 questions re-answered with Claude Fable 5. Confidence intervals come from 800 paired bootstrap resamples over the 150 questions.

| Run | Switched off | Effect |
|---|---|---|
| **A6** | **the reranker** | **Worst damage: −4.65 points.** Recall@5 falls from 86.7% to 76.0%. The only run whose confidence interval lies entirely below zero. |
| **A2** | the figure filter | Visual precision collapses from 72.5% to 23.5%. But it also runs ~12 s faster per question — the filter is a deliberate speed-for-precision trade. |
| **A5** | the hierarchy prior | Average correctness barely moves, but full-credit rate drops 7.3 points. It protects completeness, not correctness. |
| **A1** | the question router | Correctness actually rises slightly. The router earns its place through speed and calibration, not accuracy. |
| **A3** | the graph score | Within noise at this sample size. |
| **A4** | the rule-type weight | Within noise at this sample size. |

**How to read this honestly.** Only A6 is statistically clean. A3 and A4 sit so close to zero that this benchmark cannot tell whether they help, hurt, or do nothing — that is a limit of 150 questions and a single generation run, not evidence that they are useless. A1 is reported on a separate scale because switching off the router removes the confidence signal the full score depends on.

### Files

- `MUTCD_ABLATION_STUDY_REPORT_v4.md` — the full write-up, start here
- `MUTCD_ABLATION_PAPER_SECTION_v4.md` — the condensed version for a paper
- `MUTCD_ABLATION_EVALUATION_METHOD_v4.md` — exactly how it was measured
- `01_ablation_summary_with_original_rag.csv` — headline numbers per run
- `06_paired_bootstrap_intervals.csv` — the confidence intervals
- `02_ablation_item_scores.csv`, `03_ablation_retrieval_item_scores.csv` — per-question detail
- `07_ablation_by_modality.csv`, `08_ablation_by_difficulty.csv` — broken down by question type
- `04_runtime_validation.csv` — confirms all 900 runs completed cleanly
- `source_archives/` — the raw run output for each ablation

---

## 3. Grading rationales

**The question: can you check the grading rather than take it on trust?**

1,050 records — 150 questions across 7 conditions — each showing the four dimension scores, which required answer elements were missing, and the reasoning behind the score.

Read `grading_rationales/README.md` first. It is honest about an important detail: roughly 82 percent of these records are structured reconstructions generated from the scores, not independently written reasoning. The remaining ~185 contain case-specific adjudication notes. The file labels which is which, so you can weigh them accordingly.

- `master/all_1050_response_rationales.jsonl` — everything in one file
- `per_response/<condition>/<question_id>.json` — one file per answer
- `per_condition/` — per-condition summaries
- `GRADING_RUBRIC.md` — the scoring rules
- `audit/` — provenance counts and consistency checks

---

## 4. Paper outputs

The written results sections and their figures.

- `Retrieval_and_QA_Results_illustrated_v2.md` / `.docx` — the results write-up
- `Retrieval_and_QA_Results_illustrated_v2_files/` — the five figures
- `mutcd_paper_model_evaluation_corrected_bundle.zip` — the packaged bundle

---

## What is deliberately missing

**The baseline comparison results are not here.** The BM25, GraphRAG, and PaperQA comparison lives in `../comparison/` as a runnable harness. Its outputs are generated when you run it, not shipped pre-computed.

**No scoring code.** Answers were graded by a GPT judge following the written rubric, with human supervision. The rubric is published; the grading harness is kept separate on purpose, so that nothing in the system being measured can influence the measurement.

**Notebook outputs are stripped.** The notebooks in `../notebooks/` are saved without their run output, which keeps the repository small and the diffs readable. Nothing was lost — everything those runs produced is in this folder as data.
