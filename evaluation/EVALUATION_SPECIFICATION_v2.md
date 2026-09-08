---
title: "MUTCD-150 Multimodal RAG Evaluation Specification"
version: "1.1"
benchmark_id: "MUTCD-150-v1.0"
annotation_revision: "MUTCD-150-annotations-v1.1-MSDI"
question_count: 150
evaluated_model_configurations: 12
status: "provisional; repeatability and second-annotator validation pending"
---

# Correction in version 1.1

The raw Qwen3-VL 235B outputs supplied the detailed retrieval fields that were
missing from the earlier final artifact. We recomputed those fields with the
same definitions used for the other model runs.

| Metric | Corrected value |
|---|---:|
| Retrieval score | 19.35/25 |
| Recall@5 | 86.7% |
| MRR | 82.6% |
| nDCG@6 | 81.3% |
| Context precision@6 | 47.6% |
| Modality routing | 78.0% |
| Evidence sufficiency | 93.3% |
| Exact visual crop hit | 77.6% |
| Visual crop precision | 62.7% |
| Recalculated normalized score | 86.73/100 |

The earlier 19.63 retrieval component and 87.02 overall score came from a
reconstruction performed before the detailed raw retrieval output was
available. Version 1.1 replaces that reconstruction with a direct calculation.

# Corrected cross-model results

|   Rank | Model                  |   Overall score (/100) |   Retrieval (/25) |   Generation (/60) |   Reliability (/12) | Correctness   | Completeness   | Faithfulness   | Citation localization   | Full-credit rate   | Unanswerable success   |   Median latency (s) |
|-------:|:-----------------------|-----------------------:|------------------:|-------------------:|--------------------:|:--------------|:---------------|:---------------|:------------------------|:-------------------|:-----------------------|---------------------:|
|      1 | Claude Fable 5         |                  88.08 |             19.35 |              55.18 |               10.9  | 92.0%         | 90.2%          | 98.4%          | 94.5%                   | 80.0%              | 96.7%                  |                28.41 |
|      2 | Claude Sonnet 5        |                  87.81 |             19.35 |              55.18 |               10.66 | 92.4%         | 89.9%          | 98.1%          | 94.2%                   | 74.7%              | 96.7%                  |                10.97 |
|      3 | Qwen3.7 Max            |                  87.35 |             19.63 |              54.33 |               10.78 | 90.0%         | 88.1%          | 97.3%          | 93.7%                   | 76.7%              | 96.7%                  |                68.07 |
|      4 | Gemini 3.1 Pro Preview |                  87.25 |             19.35 |              54.34 |               10.94 | 89.9%         | 87.8%          | 98.7%          | 92.8%                   | 76.0%              | 100.0%                 |                21.71 |
|      5 | Qwen3.6 Flash          |                  86.96 |             19.35 |              54.38 |               10.63 | 90.4%         | 87.8%          | 97.2%          | 94.2%                   | 74.0%              | 96.7%                  |                32.72 |
|      6 | Qwen3.5 Omni Plus      |                  86.95 |             19.63 |              54.45 |               10.27 | 92.0%         | 88.1%          | 96.2%          | 90.8%                   | 71.3%              | 90.0%                  |                10.67 |
|      7 | Gemini 3.1 Flash-Lite  |                  86.92 |             19.35 |              54.21 |               10.76 | 89.9%         | 87.8%          | 97.7%          | 93.5%                   | 76.7%              | 96.7%                  |                 9.21 |
|      8 | Qwen3.7 Plus           |                  86.89 |             19.35 |              54.16 |               10.78 | 89.9%         | 87.5%          | 97.8%          | 92.3%                   | 76.7%              | 96.7%                  |                72.64 |
|      9 | Qwen3-VL 235B          |                  86.73 |             19.35 |              54.11 |               10.67 | 93.0%         | 89.9%          | 92.3%          | 86.2%                   | 74.0%              | 96.7%                  |                17.31 |
|     10 | Gemini 3.5 Flash       |                  86.6  |             19.35 |              53.92 |               10.74 | 89.1%         | 87.4%          | 98.1%          | 91.7%                   | 76.0%              | 96.7%                  |                22.53 |
|     11 | Claude Haiku 4.5       |                  86.47 |             19.35 |              53.64 |               10.89 | 88.9%         | 87.0%          | 97.6%          | 92.8%                   | 75.3%              | 100.0%                 |                10.43 |
|     12 | Qwen3-VL Flash         |                  85.08 |             19.63 |              53    |                9.9  | 88.5%         | 87.6%          | 92.0%          | 91.7%                   | 68.7%              | 86.7%                  |                16.29 |

# Interpretation rules

- Treat all scores as provisional until repeatability is added.
- Do not claim statistical superiority from small score differences.
- Use the corrected Qwen3-VL 235B retrieval and overall values above.
- Use final canonical or merged outputs when retries replaced invalid records.
- Preserve answerability as a separate dimension from M-SDI difficulty.
