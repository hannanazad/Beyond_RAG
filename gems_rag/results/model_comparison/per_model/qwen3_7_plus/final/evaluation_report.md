# MUTCD-150 Qwen3.7-Plus Evaluation

**Model:** `qwen3.7-plus-2026-05-26`  
**Run:** `mutcd150_v5_primary`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation

The uploaded archive contained 150 answer records and 150 retrieval records.
All 150 questions completed successfully on the first attempt. The error file
was empty and no embedded VLM/provider error response was detected. No retry
run is required.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **54.16/60** |
| Reliability currently measurable | **10.78/12** |
| Current total | **84.28/97** |
| Normalized provisional score | **86.89/100** |

Repeatability remains pending and is not included in the current denominator.

## Retrieval

- Required-evidence recall@5: **86.7%**
- Mean reciprocal rank: **82.6%**
- nDCG@6: **81.3%**
- Context precision@6: **47.6%**
- Correct modality routing: **78.0%**
- Evidence sufficiency: **93.3%**

## Image retrieval and multimodality

Across 85 questions requiring an explicit table or figure image:

- Exact required visual crop retrieved: **78.8%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **71.0%**

## Answer generation

- Correctness: **89.9%**
- Completeness: **87.5%**
- Faithfulness: **97.8%**
- Citation/evidence localization: **92.3%**
- Visual/table/layout reasoning: **89.7%**
- Fully correct items: **115/150 (76.7%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.191**
- ECE, 10 equal-width bins: **0.150**
- Mean latency: **94.06 seconds**
- Median latency: **72.64 seconds**
- 90th-percentile latency: **196.08 seconds**

## Principal failures

- **T006:** abstained instead of distinguishing engineering judgment from a
  written engineering study.
- **T024:** abstained instead of returning the 300/200-unit thresholds and
  70-percent adjustment.
- **T030, T034, and T037:** abstained on answerable pavement-color,
  roundabout-yield-line, and yellow-interval questions.
- **TB008:** failed to return the three STOP-sign sizes.
- **TB011:** returned 275 feet instead of 200 feet.
- **F006 and F009:** failed to answer from the required figures.
- **M008:** reversed the 35-mph sign-size exception.
- **M012, M013, and M014:** abstained on answerable quantitative warrant or
  sight-distance questions.
- **F013:** identified the splitter-island diagonals but not the required
  optional wide dotted edge-line extension.

## Current Qwen comparison

| Model | Correctness | Completeness | Faithfulness | Full credit | Provisional score |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL 235B | **93.0%** | **89.9%** | **92.3%** | **74.0%** | **87.02/100** |
| Qwen3.5 Omni Plus | **92.0%** | **88.1%** | **96.2%** | **71.3%** | **86.95/100** |
| Qwen3-VL Flash | **88.5%** | **87.6%** | **92.0%** | **68.7%** | **85.08/100** |
| Qwen3.7 Max | **90.0%** | **88.1%** | **97.3%** | **76.7%** | **87.35/100** |
| Qwen3.7 Plus | **89.9%** | **87.5%** | **97.8%** | **76.7%** | **86.89/100** |

Qwen3.7-Plus has the same strict full-credit rate as Qwen3.7-Max and very high
faithfulness, but its lower exact visual-crop retrieval rate and several
retrieval-sensitive abstentions reduce its composite score. It is also nearly
as slow as Qwen3.7-Max in this pipeline.
