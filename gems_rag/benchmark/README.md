# MUTCD-150 benchmark

150 questions about the Manual on Uniform Traffic Control Devices, 11th
Edition, each with a locked gold answer and locked evidence annotations.

Every number reported anywhere in this repository comes from this benchmark.

---

## The short version

- **150 questions**, covering text-only, table, figure, and mixed-evidence reasoning
- **85 questions require a figure or a table** to answer correctly
- **30 questions are deliberately unanswerable** from the MUTCD. A system that
  invents an answer for these is penalised. This is how refusal behaviour is
  measured.
- Every question is tied to specific sections, pages, tables, and figures,
  annotated by hand

---

## What is in here

| Path | What it is |
|---|---|
| `questions/mutcd_benchmark_questions_v1.jsonl` | The 150 questions, nothing else |
| `gold/mutcd_benchmark_gold_v1_1_msdi.jsonl` | Gold answers plus full evidence annotations |
| `source/mutcd11theditionr1hl.pdf` | The exact manual the annotations point into |
| `annotations/` | The annotation codebook, review records, and difficulty scoring sheets |
| `runner/` | A standalone script to run the benchmark outside a notebook |
| `EVALUATION_SPECIFICATION.md` | The grading rubric |
| `GOLD_ANSWER_PUBLICATION_WARNING.md` | Read before publishing gold answers anywhere |

The two JSONL files are joined on `question_id`, **not** on line order.

---

## What each gold record contains

Beyond the answer itself:

- `answerable` — whether the MUTCD actually supports an answer
- `required_answer_elements` — the specific points an answer must contain
- `sections`, `tables`, `figures`, `source_pdf_pages`, `printed_manual_pages` — the evidence
- `primary_modality`, `evidence_modalities` — whether it needs text, a table, a figure, or a mix
- `reasoning_type`, `difficulty`, `normative_type` — how hard and what kind
- `critical_error_conditions` — mistakes that invalidate an answer outright
- `acceptable_answer_variants` — wordings that are also correct

---

## Difficulty scoring

Difficulty is not a guess. Each question is scored 0 to 2 on five dimensions —
evidence localisation, modality integration, reasoning operations, answer
composition, and normative precision — and the total places it in Easy (0–3),
Medium (4–6), or Hard (7–10).

The rules are written out in `annotations/MUTCD_MSDI_CODEBOOK.md`.

---

## How answers are graded

Four dimensions, each scored 0 to 1:

| Dimension | What it asks |
|---|---|
| Correctness | Is the answer right? |
| Completeness | Does it cover every required element? |
| Faithfulness | Is it supported by the retrieved evidence, with nothing invented? |
| Citation localisation | Do the citations point to the right section, provision, and page? |

**Strict full credit** requires all four at maximum simultaneously. It is a
harsh bar on purpose — it is the measure that actually separates systems.

The complete rules are in `EVALUATION_SPECIFICATION.md`. Grading itself is done
by a GPT judge under human supervision, deliberately outside this repository,
so nothing in the system being measured can affect the measurement.

---

## Running the benchmark

Easiest: `../notebooks/02_benchmark_multi_model.ipynb`.

Outside a notebook, use `runner/mutcd_benchmark_runner.py`. See
`runner/README_runner.md`. The runner generates answers and records the
evidence used; it does not score them.

---

## Before you publish anything from here

Read `GOLD_ANSWER_PUBLICATION_WARNING.md`. Gold answers that end up in public
training data make the benchmark worthless for everyone, including you.
