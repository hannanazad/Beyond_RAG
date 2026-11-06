# MUTCD-150 Flash-Pinned Evaluation

**Model:** `qwen3-vl-flash-2026-01-22`  
**Primary run:** `mutcd150_v2_primary`  
**Retry run:** `mutcd150_v2_flash_pinned_retry_01`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation

The primary run produced 150 successful answer records. Four questions experienced
transient generation failures and were later rerun successfully:

- TB015
- TB030
- F009
- F027

The retry run produced 4 successful records and no unresolved errors. The retry
answers replaced the corresponding primary-run records for evaluation.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.63/25** |
| Answer generation | **53.00/60** |
| Reliability currently measurable | **9.90/12** |
| Current total | **82.52/97** |
| Normalized provisional score | **85.08/100** |

Repeatability remains pending and therefore is not included in the denominator.

## Retrieval metrics

- Required-evidence recall@5: **88.0%**
- Mean reciprocal rank: **83.6%**
- nDCG@6: **82.4%**
- Context precision@6: **49.4%**
- Correct modality routing: **78.0%**
- Evidence sufficiency: **93.3%**

## Multimodal and image retrieval

The benchmark contains 85 questions requiring an explicit figure or table image.

- Exact required figure/table crop retrieved: **82.4%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean precision of retrieved visual crops: **68.0%**

## Answer-generation metrics

- Correctness: **88.5%**
- Completeness: **87.6%**
- Faithfulness: **92.0%**
- Citation/evidence localization: **91.7%**
- Visual/table/layout reasoning: **87.8%**
- Fully correct items: **103/150 (68.7%)**

The relevance/conciseness value was conservatively held at the same fixed value
used in the earlier flagship report because item-level relevance scores were not
persisted for that run.

## Reliability

- Unanswerable-question success: **86.7%**
- Brier score: **0.250**
- Expected Calibration Error, 10 equal-width bins: **0.184**

## Most important failures

- **TB025:** fabricated replacement intervals and a nonexistent governing table.
- **TB028:** fabricated a 95% VLM-recognition benchmark.
- **TB011:** returned 275 feet instead of 200 feet.
- **T030:** gave incorrect pavement-marking colors.
- **F006 and F009:** failed because the required figures were not retrieved.
- **M008:** failed the STOP-sign size exception and cited an unrelated table.
- **M014:** gave 325 feet instead of the required 460-foot signal-visibility distance.
- **T025 and T037:** reversed important MUTCD prohibitions involving advisory-speed
  use and pre-yellow countdown displays.

## Comparison with the flagship model

Using the same 97-point available-score framework:

| Model | Current points | Normalized |
|---|---:|---:|
| Flagship | **84.41/97** | **87.02/100** |
| Flash pinned | **82.52/97** | **85.08/100** |

The flash-pinned model is faster and generally well grounded, but the flagship
retains an advantage in factual correctness, completeness, unanswerable handling,
and full-credit rate.
