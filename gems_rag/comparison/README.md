# Baseline comparison: GEMS-RAG vs BM25, GraphRAG, and PaperQA

This folder answers one question: **does GEMS-RAG retrieve better evidence
than established alternatives, on the same corpus and the same questions?**

It measures **retrieval only** — whether the right evidence was found. It does
not measure answer quality. Answer quality is measured in
`../notebooks/02_benchmark_multi_model.ipynb` and reported in `../results/`.

---

## The four methods

| Method | What it is | Needs a key? |
|---|---|---|
| **BM25** | Classic keyword search over the same 5,705 chunks. No build step, no model. | No |
| **GraphRAG** | Microsoft's entity-graph method, queried with its `local` algorithm. | OpenAI |
| **PaperQA2** | FutureHouse's evidence-selection method, run in context-only mode. | OpenAI |
| **GEMS-RAG** | This project, in `full` mode. | No (retrieval is local) |

Metrics: Recall@10, MRR@10, and binary nDCG@10.

---

## Running it

The three third-party methods have dependencies that conflict with each other,
so each gets its own virtual environment.

```bash
cd comparison

# one environment per method (do this once)
bash scripts/setup_environments.sh all

# download the prebuilt indexes (483 MB, checksum-verified)
python scripts/initialize_indexes.py

# run the comparison
python pipelines/run_comparison.py \
  --methods bm25,graphrag,paperqa,gems-rag \
  --output runs/comparison \
  --top-k 10 \
  --base-url https://api.openai.com/v1

# score the output
python pipelines/score_retrieval.py \
  --results runs/comparison/results.jsonl \
  --output runs/comparison/retrieval_metrics
```

Every question-and-method pair is written to its own file as it completes, so
a crash costs you only the pair in flight. Re-running the same command skips
what is already finished. Failed pairs can be retried on their own with
`--retry-errors`.

---

## Rebuilding the indexes yourself

The supplied indexes are kept so results can be audited. To build fresh ones
through the OpenAI API instead:

```bash
python pipelines/build_indexes_openai.py --methods bm25,graphrag,paperqa
```

Output goes to `rebuilt_indexes/`, leaving the supplied indexes untouched.
Progress is checkpointed, so re-running skips completed stages.

---

## What is in here

| Path | What it is |
|---|---|
| `pipelines/` | One adapter per method, plus the runner and the scorer |
| `src/comparison_support/` | Shared code: data loading, metrics, the GEMS-RAG reference server |
| `third_party/` | Pinned GraphRAG and PaperQA source, unmodified |
| `benchmark/` | The same 150 questions in the flat format these pipelines read |
| `indexes/corpus/chunks.jsonl` | The shared 5,705-chunk corpus every method searches |
| `configs/comparison.json` | Method registry and retrieval settings |
| `IMPLEMENTATIONS.md`, `IMPLEMENTATIONS.json` | Which commit of each method was used |
| `THIRD_PARTY_NOTICES.md` | Licences and required attribution |

`benchmark/` here duplicates `../benchmark/` in a flatter shape, because these
pipelines read that layout. The questions and gold data are the same.

---

## Attribution

GraphRAG is Microsoft's, under MIT. PaperQA is FutureHouse's, under
Apache-2.0. Both are included unmodified at pinned commits recorded in
`IMPLEMENTATIONS.json`. Cite them alongside this work when reporting any
comparison result. Details in `THIRD_PARTY_NOTICES.md`.

`README_original_release.md` is the README from the standalone comparison
release, kept for its extra operational detail.
