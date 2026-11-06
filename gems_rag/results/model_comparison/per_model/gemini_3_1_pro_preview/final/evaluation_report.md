# MUTCD-150 Gemini 3.1 Pro Preview Evaluation

**Model:** `gemini-3.1-pro-preview`  
**Alias:** `frontier_gemini`  
**Primary run:** `mutcd150_primary_fast_gemini_01`  
**Retry run:** `retry_frontier_gemini_01`  
**Canonical run:** `mutcd150_v11_frontier_gemini_final`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Runtime and merge validation

The primary run completed 136 questions and recorded quota failures for
`M017` through `M030`. The retry run subsequently completed all 14 missing
questions. The canonical dataset therefore contains:

| Source | Canonical records |
|---|---:|
| Primary run | 136 |
| Retry run | 14 |
| **Total** | **150** |

The canonical output contains 150 non-empty answers and 150 retrieval records,
with no unresolved provider errors or truncated responses. All final Gemini
responses ended with `stop`.

The retry source archive retains three historical quota-error events from an
earlier interrupted execution. Those events are not unresolved because the
corresponding questions have successful final records; the canonical errors
file is empty.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **54.34/60** |
| Reliability currently measurable | **10.94/12** |
| Current total | **84.63/97** |
| Normalized provisional score | **87.25/100** |

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
- Mean visual-crop precision: **73.8%**

## Answer generation

- Correctness: **89.9%**
- Completeness: **87.8%**
- Faithfulness: **98.7%**
- Citation/evidence localization: **92.8%**
- Visual/table/layout reasoning: **89.8%**
- Fully correct items: **114/150 (76.0%)**

## Reliability and latency

- Strict unanswerable-question success: **100.0%**
- Brier score: **0.198**
- ECE, 10 equal-width bins: **0.156**
- Mean latency: **25.97 seconds**
- Median latency: **21.71 seconds**
- 90th-percentile latency: **45.38 seconds**

## Principal substantive failures

- T006 abstained on the engineering-study versus engineering-judgment definition.
- T024 omitted the 300/200 all-way-stop volume thresholds.
- T026 and T030 abstained despite answerable evidence.
- T034 abstained instead of stating that the roundabout yield line is optional.
- TB008 failed to return the three STOP-sign sizes.
- TB011 returned 275 feet instead of 200 feet.
- F005 failed to identify the 2-foot island-nose dimension.
- F006 and F009 failed because the required figures were not retrieved.
- F013 omitted the optional wide dotted roundabout marking.
- M008 abstained on the 35-mph sign-size exception.
- M011–M014 omitted required quantitative values.

## Interpretation

Gemini 3.1 Pro Preview obtains a normalized provisional score of
**87.25/100**. It handled all 30 unanswerable questions
correctly and provided strong faithfulness and citation localization. Its main
losses came from retrieval-bound numeric and figure-identification questions,
not from systematic unsupported generation.
