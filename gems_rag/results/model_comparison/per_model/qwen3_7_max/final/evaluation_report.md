# MUTCD-150 Qwen3.7-Max Evaluation

**Model:** `qwen3.7-max-2026-06-08`  
**Run:** `mutcd150_v4_primary`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation

The uploaded archive contained 150 answer records and 150 retrieval records.
All 150 records completed successfully on the first attempt. No unresolved
provider/VLM error responses were detected, so no retry run is required.

The retrieved text chunks, page images, and visual crops were verified to have
the same identities and ordering as the earlier challenger run for all 150
questions. Differences in answer quality therefore reflect model behavior
rather than different retrieved evidence.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.63/25** |
| Answer generation | **54.33/60** |
| Reliability currently measurable | **10.78/12** |
| Current total | **84.73/97** |
| Normalized provisional score | **87.35/100** |

Repeatability remains pending and is not included in the present denominator.

## Retrieval

- Required-evidence recall@5: **88.0%**
- Mean reciprocal rank: **83.6%**
- nDCG@6: **82.4%**
- Context precision@6: **49.4%**
- Correct modality routing: **78.0%**
- Evidence sufficiency: **93.3%**

## Image retrieval and multimodality

Across 85 questions requiring an explicit table or figure image:

- Exact required visual crop retrieved: **83.5%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **79.8%**

## Answer generation

- Correctness: **90.0%**
- Completeness: **88.1%**
- Faithfulness: **97.3%**
- Citation/evidence localization: **93.7%**
- Visual/table/layout reasoning: **90.3%**
- Fully correct items: **115/150 (76.7%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.191**
- ECE, 10 equal-width bins: **0.150**
- Mean latency: **89.64 seconds**
- Median latency: **68.07 seconds**
- 90th-percentile latency: **189.82 seconds**

## Principal failures

- **T006:** abstained instead of distinguishing engineering judgment from a
  written engineering study.
- **T024:** abstained instead of returning the 300/200-unit thresholds and
  70-percent high-speed adjustment.
- **T026:** treated WRONG WAY signing as optional and substituted STOP/YIELD.
- **T030 and T034:** abstained on answerable pavement-color and roundabout
  yield-line questions.
- **TB008:** failed to return the three STOP-sign sizes.
- **TB011:** read 275 feet instead of 200 feet.
- **F006 and F009:** failed to answer from the required figures.
- **M008:** reversed the 35-mph sign-size exception.
- **M012 and M014:** abstained on answerable quantitative table questions.

## Comparison with previous Qwen configurations

| Model | Correctness | Completeness | Faithfulness | Full credit | Provisional score |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL 235B | **93.0%** | **89.9%** | **92.3%** | **74.0%** | **87.02/100** |
| Qwen3.5 Omni Plus | **92.0%** | **88.1%** | **96.2%** | **71.3%** | **86.95/100** |
| Qwen3-VL Flash | **88.5%** | **87.6%** | **92.0%** | **68.7%** | **85.08/100** |
| Qwen3.7 Max | **90.0%** | **88.1%** | **97.3%** | **76.7%** | **87.35/100** |

Qwen3.7-Max obtains the highest provisional composite score and the highest
strict full-credit rate among the four tested Qwen configurations. Its principal
trade-off is latency: it is substantially slower than the previously tested
models, and its mean accuracy is reduced by several complete retrieval-sensitive
abstentions.
