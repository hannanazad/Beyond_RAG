# MUTCD-150 Flagship Post-Retry Evaluation

**Model:** `qwen3-vl-235b-a22b-instruct`  
**Primary run:** `mutcd150_v1_primary`  
**Retry run:** `mutcd150_v1_flagship_retry_01`  
**Benchmark:** `MUTCD-150-v1.0` with `M-SDI-v1.0` annotation revision

## Retry validation

The retry manifest reports 5 planned records, 5 successful records, and 0 errors.  
All five completed on the first attempt. The error JSONL is empty.

| Question | Result | Retrieval | Evaluation |
|---|---|---|---|
| TB016 | Full credit | Exact Table 4C-1 and source page retrieved | Correct: 600 vph major street and 150 vph critical minor approach |
| TB022 | Full credit | Exact Table 6B-2 and source page retrieved | Correct: 495 feet |
| F007 | Full credit | Exact Figure 2A-5 and source page retrieved | Correct visual distinction between crossing and non-crossing left-turn paths |
| M006 | Partial completeness | Both governing sections and source page retrieved | Correct crash and volume thresholds; omitted the 70% high-speed adjustment |
| M021 | Full credit | Exact Figure 6L-3 and source page retrieved | Correct size, legibility, element count, and display-mode categories |

## Effect of replacing the five provider failures

- Provider/VLM errors remaining: **0**
- Fully correct items: **111/150 (74.0%)**, up from 107/150
- Mean correctness: **93.0%**
- Mean completeness: **89.9%**
- Mean faithfulness: **92.3%**
- Mean citation/evidence localization: **86.2%**
- Visual/table/layout reasoning: **90.3%**
- Conservative answer-generation score: **54.11/60**

The answer-generation score is conservative because the original aggregate relevance/conciseness score (0.696) was retained. Its item-level values were not persisted in the first evaluation, so no unsupported adjustment was made.

## Retrieval result for the five retries

- Task-sufficient evidence: **5/5**
- Required source page retrieved: **5/5**
- Exact required figure/table crop retrieved where applicable: **4/4**
- Retry errors: **0**

## Calibration after merge

- Brier score against binary full credit: **0.214**, improved from 0.240
- Standard 10-bin equal-width ECE: **0.163**
- Unanswerable handling remains **96.7%**
- Repeatability remains pending

## Decision

The flagship run is now complete for all 150 benchmark questions. No additional flagship rerun is required. M006 remains a substantive incompleteness rather than a provider failure.
