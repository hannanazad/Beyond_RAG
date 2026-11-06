# Notebooks

Four notebooks, meant to be used in order. Each one is self-contained: it sets
itself up, so you can open any of them directly without having run the others.

All of them run on Google Colab with a GPU runtime. They also run locally if
you have a CUDA GPU and have installed the requirements.

---

## Which notebook do I want?

| Notebook | Use it when you want to | Time |
|---|---|---|
| **01_quickstart_ask** | Check the system works, then ask it questions | 30 min first run |
| **02_benchmark_multi_model** | Run all 150 benchmark questions across one or more models | 2–4 h per model |
| **03_ablation_study** | Measure what each part of the system contributes | ~7 h for all six |
| **04_knowledge_graph_explorer** | Look inside the knowledge graph and draw it | 30 min |

**New here? Open `01_quickstart_ask.ipynb`.** It is the smallest one and it
proves your setup works before you spend money on the longer runs.

---

## 01_quickstart_ask.ipynb

The entry point. Sets up the environment, restores the search index, loads the
pipeline, and lets you ask questions.

It also has two inspection sections that are worth running once even if you do
not need them: section 4 walks the knowledge graph, and section 5 shows you
what retrieval returned *without* calling a paid model, which is the cheapest
way to debug a bad answer.

**You need:** one API key, for whichever model you choose.

---

## 02_benchmark_multi_model.ipynb

The main evaluation notebook. Runs the full MUTCD-150 benchmark across the
models you pick, then validates and packages the run.

Structure:

- Sections 0–4: setup, keys, index, pipeline
- Section 5: **choose your models here** — edit `SELECTED_MODELS`
- Section 10: five-question smoke test — **always run this first**
- Section 11: the full 150-question run
- Sections 12–14: check for errors, retry only the failures, package the output

The run is resumable. If it stops, re-run the cell and it continues from where
it left off instead of starting again.

**This notebook does not grade answers.** It produces them and records what
evidence was used. Grading is a separate step, described in
`../docs/REPRODUCTION_GUIDE.md`.

**You need:** one API key per provider whose models you selected.

---

## 03_ablation_study.ipynb

Switches off one component at a time and re-runs the benchmark, so you can see
what each part is worth.

The six runs are A1 (question router), A2 (figure filter), A3 (graph score),
A4 (rule-type weight), A5 (hierarchy prior), and A6 (reranker).

**Each ablation has its own cell, cells 11 to 16.** They are independent — if
A3 fails you re-run only A3, and the other five are untouched. Every cell is
also resumable within itself.

Cell 18 fills in the retrieval traces afterwards (about 3 minutes for all six),
and cell 19 packages each ablation into its own archive.

**Tip:** set `RETRIEVAL_ONLY = True` in the config cell for a first pass. That
skips answer generation entirely and gives you retrieval numbers in minutes
rather than hours — enough to see which components matter before committing to
the full run.

**You need:** one API key, for the model you are ablating against.

---

## 04_knowledge_graph_explorer.ipynb

The knowledge graph in visual form. Draws sections, figures, tables, and sign
codes and the links between them, using pyvis and plotly.

It also contains the benchmark cells from the original published run. Those
overlap with notebook 02 — notebook 02 is the cleaner version and the one to
use for new runs. This notebook is kept because it is what produced the
published results and because the graph drawing lives nowhere else.

**You need:** no API key for the graph sections. The benchmark sections need
one.

---

## archive/

Two earlier notebooks, kept for provenance. You do not need either one.

- `benchmark_simple_earlier_variant.ipynb` — an earlier, simpler version of
  notebook 02, before the model registry was added
- `early_development.ipynb` — early exploratory work, no documentation in it

---

## A note on outputs

Every notebook here is saved with its outputs stripped. That keeps the
repository small and makes changes readable in a diff.

Nothing was lost by doing this. Everything those runs produced is preserved as
data files in `../results/` — the answers, the retrieval traces, the scores,
and the figures.
