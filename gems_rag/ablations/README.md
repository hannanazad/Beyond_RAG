# MRAG Ablation Study — Data Collection Harness (v3)

Runs six leave-one-out ablations against the MUTCD-150 gold set and packages
raw RAG outputs into per-ablation zips on Drive. **Does no scoring, no
interpretation, no GPT calls.** Zips are handed to GPT-5.6 separately for
judgment.

## What's new in v3

- **Retrieval traces captured correctly.** v2 used the wrong dict keys for
  `chunks_used` and `pages_used` against `mrag.ask()`'s return — those fields
  came back empty across all v2 runs. v3 uses proper key fallbacks and also
  ships a post-processing script (`postprocess_retrieval.py`) that backfills
  existing v2 outputs without re-running generation.
- **Qdrant client workaround baked in.** `init_pipeline()` sometimes leaves
  `pipeline.store._client` bound to an empty view of the persisted store. v3
  auto-detects this and force-replaces with a fresh `QdrantClient` before the
  sweep begins.
- **Silent by design.** IPython display + stdout + stderr all captured around
  `ask()` calls. Only the per-question progress line surfaces.
- **Pipeline is initialized once and reused** across all six ablations
  (avoids ~6× model reload).
- **Per-question output in benchmark format**:
  `[N/M] RUN  <ablation_id> <qa_id> r1   OK <ms> ms — <first 80 chars of answer>`

## Ablations

| id | component off | mechanism |
|----|---------------|-----------|
| A1 | question router | `CFG.use_question_router = False` |
| A2 | VLM figure filter | `CFG.use_vlm_figure_filter = False` |
| A3 | graph proximity | `CFG.w_graph = 0.0` |
| A4 | rule-type weight | `CFG.w_ruletype = 0.0` |
| A5 | hierarchy prior | `CFG.w_hierarchy = 0.0` |
| A6 | reranker | swap `pipeline.rerank` + `pipeline.retriever.rerank` for `NoOpReranker` |

The `mrag/` package is not modified. All toggles happen at runtime.

## Layout

```
ablations/
├── README.md                  this file
├── run_ablations.ipynb        Colab driver — 40 cells, one per ablation
├── ablation_shims.py          runtime toggles + NoOpReranker
├── run_ablation.py            sweep 150 Qs → runs_<id>.jsonl
├── postprocess_retrieval.py   NEW — backfill chunks/pages by re-calling retriever
├── package_results.py         zip runs.jsonl + meta.json + README.txt
├── configs/                   one YAML per ablation
└── results/                   populated at runtime (gitignored)
```

## Running

Open `run_ablations.ipynb` in Colab. Cell order:

1. Environment setup (mount + clone, idempotent)
2. Install deps (`requirements.txt` + `anthropic` + `pyyaml`)
3. API keys (VLM providers only; no OpenAI key needed)
4. Configuration (paths + VLM alias)
5. Sanity check gold file
6. **Restore Qdrant from tar** (idempotent — skips if store already populated)
7. Pipeline init + Qdrant client health check
8. Silence library noise + `mrag.ask` display output
9. Helper: `run_and_package`
10. Smoke test (optional)
11–16. Ablation A1–A6 cells (each independently re-runnable)
17. Run all remaining (convenience)
18. **Post-process: backfill retrieval metrics** on existing runs
19. Re-package zips with backfilled data
20. Handoff notes

Each cell is idempotent and resume-safe.

## Post-processing (v3 addition)

If you have completed runs from v2 with empty `chunks_used` / `pages_used`,
cell 18 backfills them without re-running generation:

```python
from ablations.postprocess_retrieval import postprocess_all
results = postprocess_all(ablations_dir=LOCAL_RESULTS_DIR, pipeline=pipeline)
```

This calls `pipeline.retriever.retrieve(question)` once per non-errored
record — retrieval only, no VLM call. ~200 ms per question, so ~3 min for
six ablations of 150 questions each.

The ablation is applied to the pipeline BEFORE each ablation's post-processing
run, so retrieval traces reflect the ablation config (e.g., `A3_no_graph`
retrieval trace is computed with `CFG.w_graph = 0`).

## Cost

| step | wallclock |
|------|-----------|
| A1–A6 each (150 Qs × ~28s median) | ~70 min |
| six total | ~7 h |
| **Post-processing all six** | **~3 min** |

Resume-safe throughout.

## Per-ablation zip contents

Each `mrag_ablation_<id>.zip` on Drive contains:

- `runs_<id>.jsonl` — one row per question:
  - `qa_id`, `question`, `answer`
  - `chunks_used`, `pages_used`, `figures_used` (with retrieval traces)
  - `debug`, `latency_s`, `error`
- `meta.json` — ablation config, timestamp, VLM alias, git sha, counters
- `README.txt` — brief handoff note

Hand each zip to GPT-5.6 with your MUTCD-150 rubric prompt.
