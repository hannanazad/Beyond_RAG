# MUTCD-150 Claude Haiku 4.5 Evaluation

**Model:** `claude-haiku-4-5-20251001`  
**Run:** `mutcd150_v7_primary`  
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
| Answer generation | **53.64/60** |
| Reliability currently measurable | **10.89/12** |
| Current total | **83.87/97** |
| Normalized provisional score | **86.47/100** |

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

- Exact required visual crop retrieved: **77.6%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **71.2%**

## Answer generation

- Correctness: **88.9%**
- Completeness: **87.0%**
- Faithfulness: **97.6%**
- Citation/evidence localization: **92.8%**
- Visual/table/layout reasoning: **85.7%**
- Fully correct items: **113/150 (75.3%)**

## Reliability and latency

- Strict unanswerable-question success: **100.0%**
- Brier score: **0.208**
- ECE, 10 equal-width bins: **0.163**
- Mean latency: **9.82 seconds**
- Median latency: **10.43 seconds**
- 90th-percentile latency: **15.84 seconds**

## Principal failures

- **T024:** abstains instead of returning the 300/200-unit thresholds and
  70-percent adjustment.
- **T026:** rejects the required ONE WAY, DO NOT ENTER, and WRONG WAY treatment.
- **T030:** abstains instead of listing the five permitted pavement-marking
  colors.
- **TB006:** assigns the wrong temporary-traffic-control background color.
- **TB008 and TB009:** abstain on directly answerable regulatory-sign size rows.
- **TB011:** returns 275 feet instead of 200 feet.
- **F005, F006, F009, and F020:** fail visual-identification questions because
  the required figure content was absent or rejected.
- **M008:** abstains on the 35-mph sign-size exception.
- **M011:** uses 495 feet instead of the 900-foot no-passing threshold.
- **M014:** returns 325 feet instead of 460 feet.
- **M019:** does not complete the taper-length calculation.
- **M024:** incorrectly states that no turn-on-red rule is specified for a
  bicycle box.

## Comparison

Claude Haiku 4.5 obtains a strong strict full-credit rate and perfect handling
of the 30 unanswerable questions. Its median latency is among the lowest of the
tested configurations. Its overall score is reduced mainly by table/figure
abstentions and several quantitative extraction errors, rather than by
hallucination or unsupported answering.
