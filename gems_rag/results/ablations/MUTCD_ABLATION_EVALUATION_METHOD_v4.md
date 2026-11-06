# MUTCD-150 Ablation Evaluation Method

## 1. Inputs

The evaluation used:

- `ablations-20260725T213139Z-1-001.zip`, containing six nested ablation archives;
- the attached original RAG bundle, `claude_fable5_complete_analysis_bundle`;
- `mutcd_benchmark_gold_v1_1_msdi.jsonl`;
- the previous item-level ablation audit, used only when an updated answer matched byte for byte.

The baseline run was `mutcd150_v9_frontier_claude_merged_adapterfix_final`. The ablations used `claude-fable-5`, alias `frontier_claude`, with the few-shot prompt.

## 2. Runtime validation

For every ablation record, the evaluator checked:

- the complete set of 150 benchmark IDs;
- no duplicate IDs;
- exact agreement with the locked question text;
- a non-empty answer;
- no provider, quota, package, or runtime error in the answer payload;
- a normal provider stop reason;
- six logged chunks;
- four logged page candidates.

All 900 updated records passed these checks.

## 3. Answer-change audit

The evaluator compared each updated answer with the corresponding answer from the prior ablation submission.

- A2 through A6 matched on all 150 questions.
- A1 matched on 132 questions.
- A1 supplied new valid responses for T001 through T018.

The evaluator retained prior item scores only for byte-identical answers. GPT-5.6 applied the locked rubric to the 18 recovered A1 answers.

## 4. Text-retrieval relevance

A retrieved chunk counted as relevant when at least one condition held:

- its PDF page matched a locked source page;
- its section matched a locked section;
- its table references intersected the locked tables;
- its figure references intersected the locked figures.

The section matcher expanded inclusive range annotations such as `4L.01-4L.03`.

For the six ranked chunks, the evaluator calculated:

```text
Recall@5 = 1 when at least one relevant chunk occurs in ranks 1-5

MRR = reciprocal rank of the first relevant chunk

nDCG@6 = binary discounted cumulative gain over the six chunks,
         normalized by the ideal ordering of the retrieved relevant chunks

Context Precision@6 = relevant chunks / 6
```

## 5. Routing and evidence sufficiency

A question required visual routing when the gold record listed at least one table or figure.

- A2 through A6 used `debug.figure_router.needs_figures`.
- A1 disabled the router and sent every question through the visual path, so its effective routing decision was `True` for all 150 questions.

Evidence sufficiency equaled 1 when the retrieved package contained at least one relevant text chunk, a required page within the four page candidates, or an exact required visual entity.

## 6. Visual retrieval

The updated postprocessor can append figure and table mentions to `figures_used`. The evaluator recovered the entities actually supplied to the VLM as follows:

```text
actual figure/table entity count
= debug.vlm_response.image_count - len(pages_used)
```

The evaluator took that number of leading entities from `figures_used`. It then calculated, over the 85 questions with locked visual identifiers:

- exact visual hit;
- visual recall;
- visual precision;
- mean retrieved visual count;
- required page hit@1, hit@3, and hit@4.

## 7. Retrieval score

```text
Retrieval points
= 10 × Recall@5
+ 5 × (MRR + nDCG@6) / 2
+ 5 × Context Precision@6
+ 3 × Routing Accuracy
+ 2 × Evidence Sufficiency
```

Maximum: 25 points.

## 8. Answer evaluation

GPT-5.6 applied four item-level dimensions:

- correctness;
- completeness;
- faithfulness;
- citation and evidence localization.

Each dimension used the existing 0-1 rubric. Strict full credit required all four dimensions to equal 1.00.

The model-level generation score was:

```text
Generation points
= 22 × mean correctness
+ 10 × mean completeness
+ 12 × mean faithfulness
+ 6 × mean citation localization
+ 7 × visual reasoning
+ 3 × relevance and concision
```

Visual reasoning equals mean correctness across table-, figure-, and mixed-primary questions. Relevance and concision remained fixed at `0.696`, matching the main model comparison.

## 9. Reliability

Unanswerable success equals strict full credit on the 30 unanswerable questions.

For A2 through A6:

```text
Calibration points
= 6 × [1 - (Brier score + 10-bin ECE) / 2]

Reliability points
= 6 × unanswerable success
+ calibration points
```

The calibration signal comes from router confidence, not a direct answer-model probability.

A1 removes the router and has no comparable confidence value. The evaluator therefore leaves Brier score, ECE, calibration points, reliability /12, and the 97-point full score undefined for A1.

## 10. Composite scores

For the baseline and A2 through A6:

```text
Full provisional score
= (Retrieval + Generation + Reliability) / 97 × 100
```

For all conditions, including A1:

```text
Common ablation score
= (Retrieval + Generation + Unanswerable points) / 91 × 100
```

The common score excludes calibration and repeatability. It supports comparison with A1 but does not replace the 97-point end-to-end result.

## 11. Paired bootstrap

The evaluator drew 800 paired bootstrap samples of the 150 question IDs. For each sample, it recomputed the baseline and ablation scores and stored the ablation-minus-baseline difference. The report gives percentile 95% intervals.

This procedure estimates uncertainty from the benchmark question sample. It does not estimate generation variability across repeated model calls.

## 12. Publication conditions

Before final publication:

1. ask a second MUTCD-informed annotator to review every changed answer;
2. report inter-rater agreement and adjudicate disagreements;
3. repeat each condition under matched provider load;
4. rerun the full original RAG with the same `ablations_v3` harness to remove version confounding;
5. retain visual precision as a separate reported metric or add a justified visual-noise penalty to the composite score.
