# MUTCD-150 Claude Sonnet 5 Final Merged Evaluation

**Model:** `claude-sonnet-5`  
**Alias:** `balanced_claude`  
**Merged run:** `mutcd150_v8_balanced_claude_merged_final`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Merge validation

All five Sonnet source runs are included in this folder. The canonical merged
files contain exactly 150 answer records and 150 retrieval records.

| Selected source | Final records |
|---|---:|
| Primary run | 122 |
| Retry 01 | 2 |
| Retry 02 | 2 |
| Adapter-fix retry 01 | 11 |
| Adapter-fix retry 02 | 13 |

The merged output contains no empty answers, notebook-heading placeholders, or
unresolved provider errors. Some older records have truncated trailing evidence
or citation sections, but retain a substantive direct answer; those limitations
were reflected in the item-level completeness and citation scores rather than
being treated as additional provider failures.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **55.18/60** |
| Reliability currently measurable | **10.66/12** |
| Current total | **85.18/97** |
| Normalized provisional score | **87.81/100** |

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

- Exact required visual crop retrieved: **76.5%**
- Required source page at rank 1: **64.7%**
- Required source page within top 3: **88.2%**
- Required source page within top 4: **90.6%**
- Mean visual-crop precision: **72.5%**

## Answer generation

- Correctness: **92.4%**
- Completeness: **89.9%**
- Faithfulness: **98.1%**
- Citation/evidence localization: **94.2%**
- Visual/table/layout reasoning: **90.8%**
- Fully correct items: **112/150 (74.7%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.211**
- ECE, 10 equal-width bins: **0.170**
- Mean latency: **11.60 seconds**
- Median latency: **10.97 seconds**
- 90th-percentile latency: **16.16 seconds**

## Principal substantive failures

- T024: omitted the 300/200 volume thresholds and same-eight-hours basis.
- T034: abstained instead of stating that the roundabout yield line is optional.
- TB008: failed to return the three STOP-sign sizes.
- TB011: returned 275 feet instead of 200 feet.
- F005: used the 6–12-foot offset instead of the 2-foot island-nose distance.
- F006: failed to identify the W2-1 Cross Road sign.
- F009: failed to identify DO NOT ENTER above WRONG WAY.
- M008: reversed the 35-mph sign-size exception and omitted the 36×36 STOP size.
- M012–M014: omitted essential quantitative warrant or sight-distance values.
- T017 and T026: answered only part of the required normative rule.

## Current comparison

Claude Sonnet 5's normalized provisional score is **87.81/100**.
Under this audit it ranks above the previously evaluated configurations on the
current 97-point denominator, driven by high faithfulness, strong citation
localization, low latency, and strong answer correctness. Its remaining losses
are concentrated in retrieval-sensitive numeric questions and a small number of
figure-identification failures.
