# MUTCD Structural Difficulty Index (M-SDI) v1.0

## Purpose

M-SDI is a model-independent structural annotation for the MUTCD-150 benchmark.
It classifies the work required by an item, not the observed success of any one
VLM. The index is fixed before future model comparisons.

## Formula

`M-SDI = L + M + R + A + N`, where each component is scored 0, 1, or 2.
The total ranges from 0 to 10.

- 0–3: easy
- 4–6: medium
- 7–10: hard

Answerability is an orthogonal field. An unanswerable question is scored for the
work required to establish non-answerability; it is not automatically hard.

## Components

### L — Evidence-localization burden

- **0:** One clearly identified page, paragraph, table, or figure.
- **1:** Two nearby pages/source objects or bounded selection among several elements.
- **2:** Three or more source locations, cross-section comparison, or broad document-level verification.

### M — Modality-integration burden

- **0:** Text only.
- **1:** One non-text modality, such as one table or figure.
- **2:** Integration of text/layout with one or more visual modalities.

### R — Reasoning-operation burden

- **0:** Direct extraction or identification.
- **1:** One interpretation, comparison, threshold application, or bounded absence check.
- **2:** Multiple linked operations, exceptions, calculations, multi-condition reasoning, or broad presupposition testing.

### A — Answer-composition burden

- **0:** One atomic answer element. Unanswerable items use this score when one abstention conclusion is required.
- **1:** Two or three required answer elements.
- **2:** Four or more required elements or multiple conditional branches.

### N — Normative/exactness burden

- **0:** Descriptive information with no required normative distinction or exact technical value.
- **1:** One exact value/code or one MUTCD force category (Standard, Guidance, or Option).
- **2:** Multiple force categories, a material exception, prohibition, or exact preservation of normative force.

## Answerability subtypes

- `absent_information`
- `false_presupposition`
- `unsupported_precision`
- `out_of_scope`
- `contradicted_premise`

## Publication status

The included primary annotations are complete and reproducible from the rubric.
For a publication claiming inter-annotator reliability, a second MUTCD-informed
annotator must independently complete the blinded sheet. Report agreement before
adjudication and preserve both original ratings.
