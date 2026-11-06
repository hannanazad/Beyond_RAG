# MUTCD-150 Gemini 3.1 Flash-Lite Evaluation

**Model:** `gemini-3.1-flash-lite`  
**Alias:** `fast_gemini`  
**Uploaded run:** `mutcd150_smoke_fast_gemini_02`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Run validation

Although the run ID contains the word `smoke`, the manifest selected all 150
benchmark questions and the archive contains 150 answers and 150 retrieval
records. The runner resumed the five existing smoke records and completed the
remaining 145 questions in the same run directory.

All 150 records completed successfully on the first attempt. The error file was
empty, all provider stop reasons were `stop`, and no figure-filter/runtime
warnings were found. No retry is required.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **54.21/60** |
| Reliability currently measurable | **10.76/12** |
| Current total | **84.31/97** |
| Normalized provisional score | **86.92/100** |

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
- Mean visual-crop precision: **70.1%**

## Answer generation

- Correctness: **89.9%**
- Completeness: **87.8%**
- Faithfulness: **97.7%**
- Citation/evidence localization: **93.5%**
- Visual/table/layout reasoning: **89.0%**
- Fully correct items: **115/150 (76.7%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.198**
- ECE, 10 equal-width bins: **0.150**
- Mean latency: **9.36 seconds**
- Median latency: **9.21 seconds**
- 90th-percentile latency: **14.68 seconds**

## Principal substantive failures

- T005 and T006 abstained on answerable Part 1 definitions.
- T024 omitted the 300/200 all-way-stop volume thresholds.
- T030 abstained instead of listing the five pavement-marking colors.
- TB008 failed to return the three STOP-sign sizes.
- TB010 and TB011 returned incorrect Table 2C-3 distances.
- F005 misread the 2-foot island-nose dimension.
- F006 and F009 failed because the required figures were not retrieved.
- F013 substituted the optional yellow edge line for the wide dotted extension.
- M008 reversed the 35-mph sign-size exception and omitted the 36×36 STOP size.
- M009 returned 275 feet instead of 495 feet.
- M011–M014 omitted required quantitative values.

## Interpretation

Gemini 3.1 Flash-Lite achieves a strong fast-model result with a normalized
provisional score of **86.92/100** and a median latency of
**9.21 seconds**. It ties the strict
full-credit rate obtained by Qwen3.7 Max and Qwen3.7 Plus, while remaining much
faster. Its main weaknesses are retrieval-sensitive numerical extraction and a
small number of figure-identification failures.
