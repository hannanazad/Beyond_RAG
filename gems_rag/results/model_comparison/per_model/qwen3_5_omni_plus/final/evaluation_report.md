# MUTCD-150 Challenger Evaluation

**Model:** `qwen3.5-omni-plus-2026-03-15`  
**Run:** `mutcd150_v3_primary`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation

The uploaded archive contained 150 answer records, 150 retrieval records, an
empty error file, and a completed manifest. All 150 answers were marked
successful. No embedded VLM/provider error responses were detected, and no
record required more than one attempt. No retry run is required.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.63/25** |
| Answer generation | **54.45/60** |
| Reliability currently measurable | **10.27/12** |
| Current total | **84.34/97** |
| Normalized provisional score | **86.95/100** |

Repeatability remains pending and is not included in the current denominator.

## Retrieval

- Required-evidence recall@5: **88.0%**
- Mean reciprocal rank: **83.6%**
- nDCG@6: **82.4%**
- Context precision@6: **49.4%**
- Correct modality routing: **78.0%**
- Evidence sufficiency: **93.3%**

## Image retrieval and multimodality

There were 85 questions requiring an explicit figure or table image.

- Exact required visual crop retrieved: **83.5%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **79.8%**

## Answer generation

- Correctness: **92.0%**
- Completeness: **88.1%**
- Faithfulness: **96.2%**
- Citation/evidence localization: **90.8%**
- Visual/table/layout reasoning: **90.2%**
- Fully correct items: **107/150 (71.3%)**

## Reliability and speed

- Strict unanswerable-question success: **90.0%**
- Brier score: **0.220**
- ECE, 10 equal-width bins: **0.157**
- Mean latency: **10.59 seconds**
- Median latency: **10.67 seconds**
- 90th-percentile latency: **14.93 seconds**

## Principal failures

- **TB008 and TB009:** abstained instead of returning regulatory-sign dimensions.
- **TB011:** returned 275 feet instead of 200 feet.
- **T024:** omitted the 300/200 units-per-hour thresholds and same-eight-hours condition.
- **T030:** substituted green for blue in the permitted pavement-marking colors.
- **F006:** failed to use Figure 2A-4 even though the figure was retrieved.
- **F009:** required Figure 2B-17 was not retrieved.
- **M007:** omitted all white-on-red retroreflectivity thresholds.
- **M008:** reversed the 35-mph sign-size exception and omitted the 36×36-inch STOP size.
- **M014:** returned 325 feet instead of 460 feet.
- **M019:** used the wrong taper calculation, returning 84 feet instead of 245 feet.

## Three-model comparison

| Model | Correctness | Completeness | Faithfulness | Full credit | Median latency | Normalized provisional score |
|---|---:|---:|---:|---:|---:|---:|
| Flagship | **93.0%** | **89.9%** | **92.3%** | **74.0%** | **17.31s** | **87.02/100** |
| Challenger | **92.0%** | **88.1%** | **96.2%** | **71.3%** | **10.67s** | **86.95/100** |
| Flash pinned | **88.5%** | **87.6%** | **92.0%** | **68.7%** | **16.29s** | **85.08/100** |

The challenger is effectively tied with the flagship under the provisional
97-point framework. The flagship retains a small advantage in correctness,
completeness, and full-credit rate. The challenger has higher audited
faithfulness and substantially lower median latency.
