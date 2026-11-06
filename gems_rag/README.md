# GEMS-RAG

**A retrieval system that answers questions about the MUTCD traffic-control manual using its text, tables, and figures together — plus the full benchmark and evaluation used to measure it.**

The MUTCD (Manual on Uniform Traffic Control Devices, 11th Edition) is a roughly 1,100-page US federal standards manual. Answering a real question about it usually means combining a written rule with a diagram, a table, and a cross-reference to another section. GEMS-RAG is built to do that, and this repository contains everything needed to run it, measure it, and check the numbers.

---

## What is in this repository

| Folder | What it holds |
|---|---|
| `mrag/` | The GEMS-RAG system itself. This is the Python package you import. |
| `scripts/` | The ingest pipeline that turns the MUTCD PDF into a searchable index. |
| `notebooks/` | Jupyter notebooks for running everything. **Start here.** |
| `benchmark/` | MUTCD-150: 150 questions, locked gold answers, the source PDF, and the grading specification. |
| `ablations/` | The leave-one-out ablation study harness (six experiments). |
| `comparison/` | Comparison against three other retrieval methods: BM25, GraphRAG, and PaperQA. |
| `results/` | Every result we produced: 12 models compared, the ablation study, and 1,050 per-answer grading records. |
| `validation/` | Proof that figure extraction was complete (485 of 485 figures, 68 of 68 tables). |
| `docs/` | How the system works, how it was built, and a step-by-step reproduction guide. |

---

## Three ways to use this repository

**1. You just want to see the results.** Open `results/` — nothing to install. Start with `results/README.md`.

**2. You want to ask the system a question.** Open `notebooks/01_quickstart_ask.ipynb` in Google Colab. You need one API key and about 20 minutes.

**3. You want to reproduce the study.** Follow `docs/REPRODUCTION_GUIDE.md` from top to bottom.

---

## Do the notebooks contain API keys?

**No. There are no API keys anywhere in this repository, and there never will be.**

Every notebook reads keys at runtime from either Google Colab's Secrets panel or an environment variable. Nothing is written into the files. We scanned every file in this repository before publishing and found zero credentials.

**You supply your own keys.** Which ones depends on what you want to do:

| What you want to do | Keys you need |
|---|---|
| Read the results | **None** |
| Build the search index from the PDF | **None** (runs locally on your own GPU) |
| Search the index, no answers generated | **None** |
| Ask questions and get answers | **One** of `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or `DASHSCOPE_API_KEY`, matching the model you pick |
| Reproduce all 12 models in the comparison | **All three** of the above |
| Run the ablation study | Same as "ask questions" — one key for the model you choose |
| Run the BM25 / GraphRAG / PaperQA comparison | `OPENAI_API_KEY` (GraphRAG and PaperQA call OpenAI; BM25 needs nothing) |
| Grade the answers | **None in this repo.** Grading is done separately by a human-supervised GPT judge following `benchmark/EVALUATION_SPECIFICATION.md`. No grading code runs here. |

### How to add your keys

**In Google Colab (easiest):** click the key icon in the left sidebar, press "Add new secret", and enter the name exactly as written above (for example `ANTHROPIC_API_KEY`) with your key as the value. Turn on "Notebook access". The notebooks pick it up automatically.

**On your own machine:** copy `.env.example` to `.env`, paste your keys in, then run:

```bash
set -a; source .env; set +a
```

`.env` is listed in `.gitignore`, so it will never be committed by accident.

---

## Quick start: ask the system a question

1. Open `notebooks/01_quickstart_ask.ipynb` in [Google Colab](https://colab.research.google.com/). Choose a GPU runtime (A100 or L4 is ideal; T4 works but is slower).
2. Add one API key as a Colab secret (see above).
3. Run the cells from the top. The notebook clones this repository, installs the dependencies, and downloads the prebuilt search index.
4. In the "Ask" section, type your question and run the cell.

First run takes roughly 20 to 30 minutes, almost all of it downloading the index and loading the models. After that each question takes about 30 seconds.

---

## The search index

GEMS-RAG searches a prebuilt index rather than the raw PDF. You have two options.

**Option A — download it (recommended, about 15 minutes).** A prebuilt index is published as a release asset:

```
https://github.com/GEMS-RAG/rag/releases/download/v1.0.0/mutcd-rag-prebuilt-indexes-v1.zip
```

It is 483 MB and contains the vector store, the knowledge graph, figure metadata, and the source PDF. The notebooks download and verify it for you. It is checksum-locked, so a corrupted or interrupted download is detected rather than silently used.

**Option B — build it yourself (4 to 8 hours on a GPU).** Run the ingest pipeline:

```bash
python scripts/ingest_v4.py
```

This parses the PDF, crops every figure and table, builds the knowledge graph, computes the embeddings, and loads the vector store. It refuses to finish if figure coverage drops below 99 percent, so a silent gap is impossible. Full details in `docs/03_FIGURE_EXTRACTION_REBUILD.md`.

---

## Installing

Python 3.12 is required. A GPU is needed for the embedding models.

```bash
git clone https://github.com/hannanazad/gemsrag.git
cd gemsrag

pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.6.0 torchvision==0.21.0
pip install -r requirements.txt
pip install --no-deps --force-reinstall \
    "transformers>=4.49,<4.55" \
    "huggingface_hub>=0.34,<0.35" \
    "tokenizers>=0.21,<0.22" \
    "torchao>=0.13,<0.14"
```

**The third command is not optional.** `pip install -r` does not enforce upper version limits when a newer package is already installed, which is the normal situation on Colab. Skip it and the embedding model fails with a confusing `cannot import PreTrainedModel` error. The notebooks run these three steps for you in the right order.

---

## What the notebooks do

| Notebook | What it does | How long |
|---|---|---|
| `01_quickstart_ask.ipynb` | Set up, load the index, ask questions, look at what was retrieved | 30 min first run |
| `02_benchmark_multi_model.ipynb` | Run all 150 benchmark questions across one or more models, then package the run | 2 to 4 hours per model |
| `03_ablation_study.ipynb` | Turn off one component at a time and re-run the benchmark, six times | about 7 hours for all six |
| `04_knowledge_graph_explorer.ipynb` | Draw and explore the knowledge graph, plus the original benchmark run cells | 30 min |

`notebooks/archive/` holds two earlier notebooks, kept for provenance. You do not need them.

All notebooks have their outputs stripped so the repository stays small and diffs stay readable. The real outputs are preserved as data files in `results/`.

---

## What the results show

The headline numbers, all on the 150-question benchmark:

- **Best model: Claude Fable 5, scoring 88.08 out of 100**, with 80.0 percent of answers earning strict full credit. Twelve model configurations were compared across three providers.
- **The reranker matters most.** Removing it costs 4.65 points, and it is the only component whose confidence interval sits entirely below zero.
- **The figure filter is a precision tool.** Removing it causes visual precision to collapse from 72.5 percent to 23.5 percent, but it costs about 12 seconds per question.
- **Retrieval is stable across models.** Scores land between 19.35 and 19.63 out of 25 regardless of which model answers, which means the differences between models come from how they use the evidence, not from what they are given.

Full detail in `results/README.md`.

---

## Honest limitations

These are real, and they are stated here rather than buried.

1. **Context precision is below 50 percent.** Too much irrelevant text reaches the answering model. The cause is a degraded sparse-retrieval path, documented in `docs/01_SYSTEM_ARCHITECTURE.md`.
2. **The knowledge graph re-scores candidates; it does not add new ones.** The expansion step in `mrag/retrieval.py` is a placeholder. Describe it as re-ranking, not retrieval expansion.
3. **Nothing in this project was trained.** Every component is either hand-written deterministic code or a frozen off-the-shelf model that is prompted, never fine-tuned. `docs/02_TRAINED_VS_RULES.md` explains exactly which is which.
4. **Grading is not automated here.** Answers were graded by a GPT-5.6 judge following a fixed written rubric, supervised by a human. That rubric is included; the grading harness is not part of this repository.
5. **Each condition was generated once.** Repeatability across repeated model calls has not been measured. The reported confidence intervals describe uncertainty from the 150-question sample only.
6. **Licensing is not yet settled.** See `NOTICE.md`.

---

## Citing this work

See `CITATION.cff`. The MUTCD manual itself and the third-party methods used in the comparison carry their own terms, recorded in `comparison/THIRD_PARTY_NOTICES.md`.

---

## Where to go next

- Never seen this before → `docs/REPRODUCTION_GUIDE.md`
- Want to understand the design → `docs/01_SYSTEM_ARCHITECTURE.md`
- Want to know what was trained → `docs/02_TRAINED_VS_RULES.md`
- Want the numbers → `results/README.md`
- Want the benchmark → `benchmark/README.md`
