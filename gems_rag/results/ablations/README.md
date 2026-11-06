# MUTCD-150 Ablation Study v4

This package reevaluates the six updated Claude Fable 5 ablation archives
against the attached original RAG baseline.

Key outputs:

- `MUTCD_ABLATION_STUDY_REPORT_v4.md`: detailed results and interpretation
- `MUTCD_ABLATION_EVALUATION_METHOD_v4.md`: reproducible evaluation procedure
- `MUTCD_ABLATION_PAPER_SECTION_v4.md`: manuscript-ready ablation section
- `MUTCD_ABLATION_STUDY_v4.docx`: formatted Word report
- `01_ablation_summary_with_original_rag.csv`: aggregate metrics
- `02_ablation_item_scores.csv`: answer and retrieval scores for all 900 items
- `06_paired_bootstrap_intervals.csv`: question-level uncertainty intervals
- `figures/`: 10 × 8 inch, 300 DPI figures

Baseline full score: 88.08/100  
No-reranker full score: 83.43/100  
No-router full score: not defined because router confidence is absent
