# MUTCD-150 Qwen3.6-Flash Evaluation

**Model:** `qwen3.6-flash-2026-04-16`  
**Run:** `mutcd150_v6_primary`  
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
| Answer generation | **54.38/60** |
| Reliability currently measurable | **10.63/12** |
| Current total | **84.35/97** |
| Normalized provisional score | **86.96/100** |

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

- Exact required visual crop retrieved: **75.3%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **68.9%**

## Answer generation

- Correctness: **90.4%**
- Completeness: **87.8%**
- Faithfulness: **97.2%**
- Citation/evidence localization: **94.2%**
- Visual/table/layout reasoning: **90.2%**
- Fully correct items: **111/150 (74.0%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.215**
- ECE, 10 equal-width bins: **0.176**
- Mean latency: **54.46 seconds**
- Median latency: **32.72 seconds**
- 90th-percentile latency: **114.28 seconds**

## Principal failures

- **T006:** fails to distinguish the documentation requirement for engineering
  judgment and an engineering study.
- **T024:** omits the 300/200-unit thresholds and same-eight-hours condition.
- **T030:** substitutes green for blue in the five general pavement-marking
  colors.
- **T034:** abstains instead of stating that a roundabout yield line is optional.
- **TB008:** fails to return the three required STOP-sign sizes.
- **TB011:** returns 275 feet instead of 200 feet.
- **F006 and F009:** fail because the required figures were not retrieved.
- **M008:** reverses the 35-mph regulatory-sign size exception.
- **M009:** returns 225 feet instead of the required 495 feet.
- **M012–M014:** omit essential quantitative warrant or sight-distance values.
- **T025:** overstates recommended advisory-speed practice as a prohibition.
- **F013:** identifies only one of the two requested optional roundabout
  markings.

## Current Qwen comparison

| Model | Correctness | Completeness | Faithfulness | Full credit | Provisional score |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL 235B | **93.0%** | **89.9%** | **92.3%** | **74.0%** | **87.02/100** |
| Qwen3.5 Omni Plus | **92.0%** | **88.1%** | **96.2%** | **71.3%** | **86.95/100** |
| Qwen3-VL Flash | **88.5%** | **87.6%** | **92.0%** | **68.7%** | **85.08/100** |
| Qwen3.7 Max | **90.0%** | **88.1%** | **97.3%** | **76.7%** | **87.35/100** |
| Qwen3.7 Plus | **89.9%** | **87.5%** | **97.8%** | **76.7%** | **86.89/100** |
| Qwen3.6 Flash | **90.4%** | **87.8%** | **97.2%** | **74.0%** | **86.96/100** |

Qwen3.6-Flash achieves a strong composite result and matches the original
Qwen3-VL 235B full-credit rate, while remaining materially faster than the
Qwen3.7 Max and Plus models. Its main limitation is weaker exact visual-crop
retrieval, which contributes to several figure- and table-sensitive failures.
