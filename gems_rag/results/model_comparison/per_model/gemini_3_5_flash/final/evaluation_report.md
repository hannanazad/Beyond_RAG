# MUTCD-150 Gemini 3.5 Flash Evaluation

**Model:** `gemini-3.5-flash`  
**Alias:** `balanced_gemini`  
**Primary run:** `mutcd150_primary_balanced_gemini_01`  
**Canonical run:** `mutcd150_v10_balanced_gemini_final`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation and retry treatment

The primary archive contains 150 answer records and 150 retrieval records.
All records completed successfully, the error file is empty, all provider stop
reasons are `stop`, and no provider or figure-filter warning was found.

Three primary records (`T027`, `T038`, and `M026`) required a second internal
attempt but ultimately completed successfully. The separate three-question retry
archive is retained in this analysis folder but is not substituted into the
canonical score because the corresponding primary records were already valid.
Using a later answer would constitute post-hoc resampling rather than recovery
from an unresolved failure.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **53.92/60** |
| Reliability currently measurable | **10.74/12** |
| Current total | **84.00/97** |
| Normalized provisional score | **86.60/100** |

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
- Mean visual-crop precision: **67.1%**

## Answer generation

- Correctness: **89.1%**
- Completeness: **87.4%**
- Faithfulness: **98.1%**
- Citation/evidence localization: **91.7%**
- Visual/table/layout reasoning: **88.8%**
- Fully correct items: **114/150 (76.0%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.198**
- ECE, 10 equal-width bins: **0.156**
- Mean latency: **25.93 seconds**
- Median latency: **22.53 seconds**
- 90th-percentile latency: **50.51 seconds**

## Principal substantive failures

- T024, T030, T034, and T037 abstained on answerable text questions.
- TB008 failed to return the three STOP-sign sizes.
- TB011 returned 275 feet instead of 200 feet.
- F005 misread the island-nose offset in Figure 2A-3.
- F006 and F009 failed because the required figures were not retrieved.
- F013 did not identify the optional wide dotted edge-line extension.
- M008 abstained on the 35-mph sign-size exception.
- M011 omitted the 900-foot threshold at 55 mph.
- M012–M014 abstained on quantitative warrant and sight-distance questions.

## Interpretation

Gemini 3.5 Flash obtains a normalized provisional score of
**86.60/100**. Its strongest qualities are faithfulness,
citation localization, fast latency, and correct handling of 29 of 30
unanswerable questions. Its losses are concentrated in evidence-localization
failures, particularly specific figures and quantitative table entries.
