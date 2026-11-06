# MUTCD-150 Claude Fable 5 Final Evaluation

**Model:** `claude-fable-5`  
**Alias:** `frontier_claude`  
**Merged run:** `mutcd150_v9_frontier_claude_merged_adapterfix_final`  
**Benchmark:** MUTCD-150-v1.0 with M-SDI-v1.0 annotation revision

## Runtime and merge validation

The final dataset uses only the two adapter-fixed runs:

| Source run | Records |
|---|---:|
| Adapter-fixed retry 01 | 47 |
| Adapter-fixed remaining-questions run | 103 |
| **Canonical total** | **150** |

All 150 records contain non-empty final answers. Every Anthropic response ended
with `stop_reason="end_turn"`. There are no notebook-heading substitutions,
truncated provider responses, or unresolved provider errors in the canonical
merge.

## Composite score

| Component | Score |
|---|---:|
| Retrieval | **19.35/25** |
| Answer generation | **55.18/60** |
| Reliability currently measurable | **10.90/12** |
| Current total | **85.43/97** |
| Normalized provisional score | **88.08/100** |

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

- Correctness: **92.0%**
- Completeness: **90.2%**
- Faithfulness: **98.4%**
- Citation/evidence localization: **94.5%**
- Visual/table/layout reasoning: **90.9%**
- Fully correct items: **120/150 (80.0%)**

## Reliability and latency

- Strict unanswerable-question success: **96.7%**
- Brier score: **0.169**
- ECE, 10 equal-width bins: **0.130**
- Mean latency: **26.97 seconds**
- Median latency: **28.41 seconds**
- 90th-percentile latency: **38.08 seconds**

## Principal substantive failures

- T024 omitted the 300/200 all-way-stop volume thresholds and same-eight-hours basis.
- T030 abstained instead of listing the five permitted pavement-marking colors.
- T034 abstained instead of stating that the roundabout yield line is optional.
- TB008 failed to return the three STOP-sign sizes.
- TB011 returned 275 feet instead of 200 feet.
- F005 misread the island-nose offset in Figure 2A-3.
- F006 and F009 failed because the required figures were not retrieved.
- M008 reversed the 35-mph sign-size exception and omitted the 36 x 36-inch STOP size.
- M011–M014 omitted required quantitative values despite recovering the governing rule.

## Interpretation

Claude Fable 5 currently has the highest normalized provisional score among the
nine evaluated configurations: **88.08/100**. It combines high
faithfulness and citation localization with the strongest strict full-credit
rate obtained so far. Its remaining errors are concentrated in retrieval-bound
numeric and figure-identification questions rather than unsupported generation.
