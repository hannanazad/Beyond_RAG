# Reproduction Guide

This guide walks you from an empty machine to reproducing the published results. It assumes no prior knowledge of the project. Follow it top to bottom, or jump to the part you need.

Everything here has been written so that a person who has never seen this project can get it running.

---

## Before you start: what you are reproducing

There are four separate experiments in this repository. They are independent — you can run one without running the others.

| Experiment | What it answers | Time | Cost |
|---|---|---|---|
| **A. Ask a question** | Does the system work? | 30 min | cents |
| **B. Model comparison** | Which answering model is best? | 2–4 h per model, 12 models | tens of dollars |
| **C. Ablation study** | Which parts of the system actually matter? | ~7 h | tens of dollars |
| **D. Baseline comparison** | Is GEMS-RAG better than BM25, GraphRAG, PaperQA? | 2–3 h | tens of dollars |

Start with A. It proves your setup works before you spend money on the others.

---

## Step 0 — What you need

**Hardware.** A GPU with at least 16 GB of memory. Google Colab with an A100 or L4 runtime is what we used and is the easiest path. A T4 works but is noticeably slower. CPU-only will technically run but is impractically slow.

**Disk.** About 10 GB free: roughly 500 MB for the index, 8 GB for model weights, and the rest for results.

**Python.** Version 3.12.

**API keys.** At least one, from Anthropic, Google, or Alibaba DashScope. See "Step 2".

**A Google account**, if you use Colab.

---

## Step 1 — Get the code

### On Google Colab (recommended)

Do nothing yet. The first cell of every notebook clones this repository for you. Skip to Step 2.

### On your own machine

```bash
git clone https://github.com/hannanazad/gemsrag.git
cd gemsrag
```

Then install the dependencies, **in this exact order**:

```bash
# 1. PyTorch built for CUDA 12.4
pip install --index-url https://download.pytorch.org/whl/cu124 \
    torch==2.6.0 torchvision==0.21.0

# 2. Everything else
pip install -r requirements.txt

# 3. Pin the four packages that pip will otherwise leave too new
pip install --no-deps --force-reinstall \
    "transformers>=4.49,<4.55" \
    "huggingface_hub>=0.34,<0.35" \
    "tokenizers>=0.21,<0.22" \
    "torchao>=0.13,<0.14"
```

**Why step 3 exists.** When `pip install -r` sees a package that already meets the minimum version, it does not downgrade it to respect a maximum. Colab and most GPU images ship newer versions of these four than the project allows. If you skip step 3, the embedding model fails at import with the message `cannot import PreTrainedModel`, which does not hint at the real cause. Step 3 forces the right versions.

Check it worked:

```bash
python -c "import transformers.modeling_utils as m; print(m.PreTrainedModel)"
```

If that prints a class, you are fine. If it raises, step 3 did not take effect — run it again and restart your Python session.

---

## Step 2 — Add your API key

You need one key for the model that writes the answers. Pick a provider:

| Provider | Environment variable | Example models |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `frontier_claude`, `balanced_claude`, `fast_claude` |
| Google | `GEMINI_API_KEY` | `frontier_gemini`, `balanced_gemini`, `fast_gemini` |
| Alibaba DashScope | `DASHSCOPE_API_KEY` | `frontier_qwen`, `flagship`, `flash_pinned` |

**On Colab:** click the key icon in the left sidebar → "Add new secret" → name it exactly as in the table → paste your key → switch on "Notebook access". The notebooks read it automatically.

**On your own machine:**

```bash
cp .env.example .env
# edit .env and paste your key
set -a; source .env; set +a
```

**No key is in this repository, and none is needed to read the results.** See the README section "Do the notebooks contain API keys?" for the full breakdown.

---

## Step 3 — Get the search index

GEMS-RAG searches a prebuilt index, not the PDF directly. Choose one option.

### Option A — download the prebuilt index (recommended)

483 MB, roughly 15 minutes. Contains the vector store, the knowledge graph, figure metadata, and the source PDF.

```
https://github.com/GEMS-RAG/rag/releases/download/v1.0.0/mutcd-rag-prebuilt-indexes-v1.zip
```

The notebooks fetch and verify this automatically. To do it by hand:

```bash
cd comparison
python scripts/initialize_indexes.py
```

The download resumes if interrupted, the SHA-256 is checked before anything is extracted, and the finished index is swapped into place atomically. A broken download can never quietly replace a working index.

### Option B — build the index yourself

4 to 8 hours on a GPU. Do this if you want to verify the pipeline end to end, or if you are indexing a different document.

```bash
python scripts/ingest_v4.py
```

What it does, in order: crops every figure and table from the PDF, runs a rescue pass for any it missed, **refuses to continue if coverage is below 99 percent**, re-parses the text into provision-level chunks, builds the knowledge graph, computes the embeddings, and loads the vector store.

That coverage gate is the important part. It means an incomplete index cannot be produced silently. Our run finished at 485 of 485 figures and 68 of 68 tables; the evidence is in `validation/coverage_report.json`.

---

## Experiment A — Ask a question (start here)

Open `notebooks/01_quickstart_ask.ipynb`.

1. Run the setup cells at the top. They clone the repo, install dependencies, and read your key.
2. Run the index cell. It restores the prebuilt store, or builds one if you chose Option B.
3. Run the pipeline initialisation cell. This loads the models and takes 30 to 60 seconds.
4. Go to the "Ask" section, edit the question, and run it.

A correct answer looks like this: a direct answer first, then the exact Standard and Support text quoted from the manual, a note about which figure was used, and citations down to the section, provision, and page.

**If it fails:** see Troubleshooting at the bottom of this guide.

---

## Experiment B — Model comparison

Open `notebooks/02_benchmark_multi_model.ipynb`.

1. Run the setup and index cells as before.
2. In section 5, choose your models:
   ```python
   SELECTED_MODELS = ["balanced_gemini"]
   ```
   Add more aliases to the list to run several in sequence. `CFG.list_vlm_models()` prints the full catalog.
3. Run the five-question smoke test in section 10. **Do not skip this.** It costs almost nothing and catches a bad key or a missing index before you spend hours.
4. If the smoke test passes, run the full 150 questions in section 11.
5. Sections 12 to 14 check the finished run for errors, retry only the failed questions, and package the output.

Expect 2 to 4 hours per model. The run is resumable — if it stops, restart the cell and it picks up where it left off rather than starting over.

**Grading is a separate step.** This notebook produces answers and records the evidence used. It does not score them. Scoring follows the written rubric in `benchmark/EVALUATION_SPECIFICATION.md`, applied by a GPT judge with human supervision. That grading harness is deliberately not part of this repository, so that the system being measured and the thing doing the measuring stay separate. Our 1,050 completed grading records are in `results/grading_rationales/` if you want to see exactly how answers were judged.

---

## Experiment C — Ablation study

Open `notebooks/03_ablation_study.ipynb`.

This turns off one component at a time and re-runs the benchmark, so you can see what each part contributes.

| Run | Component switched off |
|---|---|
| A1 | the question router |
| A2 | the figure filter |
| A3 | the knowledge-graph score |
| A4 | the rule-type weight |
| A5 | the hierarchy prior |
| A6 | the reranker |

1. Run cells 1 to 9 (setup, index, pipeline, helper functions).
2. Run the smoke test in cell 10.
3. Run cells 11 to 16 — one per ablation. **Each cell is independent.** If A3 fails, re-run only A3. Nothing else is affected.
4. Cell 18 fills in the retrieval traces afterwards. Takes about 3 minutes for all six.
5. Cell 19 packages each ablation into its own zip.

Roughly 70 minutes per ablation, about 7 hours for all six. Every cell is resumable.

**For a cheap first pass**, set `RETRIEVAL_ONLY = True` in the configuration cell. That skips answer generation entirely and gives you retrieval metrics in minutes per ablation instead of over an hour, which is enough to see which components move the needle before you commit to the full run.

---

## Experiment D — Baseline comparison

This one lives in `comparison/` and uses different tooling, because GraphRAG and PaperQA need their own Python environments.

```bash
cd comparison

# one environment per method, because their dependencies conflict
bash scripts/setup_environments.sh all

# run three methods across all 150 questions
python pipelines/run_comparison.py \
  --methods bm25,graphrag,paperqa \
  --output runs/comparison \
  --top-k 10 \
  --base-url https://api.openai.com/v1

# add GEMS-RAG
python pipelines/run_comparison.py \
  --methods bm25,graphrag,paperqa,gems-rag \
  --output runs/comparison-with-gems-rag \
  --top-k 10 \
  --base-url https://api.openai.com/v1

# score what came out
python pipelines/score_retrieval.py \
  --results runs/comparison/results.jsonl \
  --output runs/comparison/retrieval_metrics
```

You need `OPENAI_API_KEY` for GraphRAG and PaperQA. BM25 needs no key and no build step.

This comparison measures **retrieval only** — Recall@10, MRR@10, and binary nDCG@10. It does not measure answer quality. Answer quality is Experiment B.

Every completed question-and-method pair is written to its own file, so a crash costs you only the pair in flight. Re-running the same command skips what is already done.

---

## Troubleshooting

**`cannot import PreTrainedModel`**
Step 3 of the install did not take. Run the `--no-deps --force-reinstall` command again, then restart your Python session or Colab runtime.

**`Collection mutcd_chunks not found`**
The vector store is missing or empty. On Colab this usually means the runtime restarted and wiped local disk. Re-run the index cell. If it persists, check that the folder actually contains a `collection/` subdirectory with data in it.

**The vector store is on disk but the system says it is empty**
A stale client is holding an old, empty view. Delete the pipeline object, run `gc.collect()`, then re-initialise:
```python
del pipeline; import gc; gc.collect()
pipeline = init_pipeline()
```

**`No module named 'anthropic'`** (or `google-generativeai`, or `dashscope`)
Install the client for the provider you picked: `pip install anthropic`.

**Questions fail with no error message**
Check your API key is set and has credit. Look at `/content/ablation_results/ablation.log` — the notebooks send detailed logs there and keep the notebook display clean.

**The run stopped partway through**
Restart the same cell. Every runner in this repository is resumable and will skip completed work.

**Out of memory**
Use a bigger GPU, or reduce `CFG.top_k_figures`. The visual models are the memory-hungry part.

---

## What good output looks like

After Experiment B you should have, per model:

- `answers_final.jsonl` — one record per question with the answer and the evidence used
- `retrieval_final.jsonl` — what was retrieved for each question
- `standardized_summary.json` — the run's settings and counters
- a packaged archive of the whole run

Compare yours against ours in `results/model_comparison/per_model/`. Exact numbers will not match to the decimal — these are non-deterministic API models — but the ordering and the broad picture should hold. If your best model scores around 88 out of 100 and roughly 80 percent of answers earn strict full credit, you have reproduced our result.

---

## Getting help

1. Check the troubleshooting list above.
2. Read `docs/01_SYSTEM_ARCHITECTURE.md` to understand what the failing stage is supposed to do.
3. Open an issue on the repository with the failing cell and the full error message.
