# Beyond RAG

Graph-grounded multimodal retrieval over engineering standards, built on the
MUTCD 11th Edition, plus the MUTCD-150 benchmark and an ablation harness.

The pipeline parses the manual by its native hierarchy, crops captioned figures
and tables, links provisions, figures, tables, sign codes and cross-references
into a knowledge graph, retrieves text and visual evidence, and generates an
answer whose citations are verified against the graph.

## Quick start

Open `notebooks/Beyond_RAG_Colab.ipynb` in Colab and run it top to bottom.

You need:

- **Colab Pro+** and an **A100** runtime. Pro alone rarely allocates one.
- The **MUTCD PDF** in `Drive/MyDrive/MRAG/` — any `*.pdf` filename works. It is
  not in this repo; download it from FHWA.
- At least one **API key** in Colab Secrets: `ANTHROPIC_API_KEY`,
  `GEMINI_API_KEY`, or `DASHSCOPE_API_KEY`.
- About **6 GB of Drive**. The 35 GB model cache stays session-local by default.

First run ingests the manual: roughly 30–45 minutes on an A100. Snapshot Qdrant
to Drive afterwards and later sessions restore in about 30 seconds.

## Layout

```
mrag/                     the pipeline package
  config.py               all paths, weights and model selection
  parsing.py              hierarchy-aware chunking, typed paragraphs
  figures.py              caption-anchored figure and table extraction
  figure_core.py          crop geometry
  sign_codes.py           sign-code mining from titles, text and captions
  kg.py                   knowledge graph construction and queries
  embeddings.py           BGE-M3 text, ColQwen2 visual
  vector_store.py         Qdrant collections, hybrid search, RRF
  question_router.py      whether a query needs visual evidence
  retrieval.py            fused scoring, reranking, figure paths
  vlm.py                  prompt assembly and generation
  ask.py                  pipeline singleton and the ask() entry point
  colab_setup.py          Drive mounting and path resolution

scripts/
  ingest_v4.py            full ingest: parse, crop, embed, upsert
  extract_figures.py      figure and table cropping only
  repair_chunk_ids.py     repair colliding chunk IDs without re-embedding
  verify_mutcd_benchmark_assets.sh
  ingest.slurm            HPRC batch script

benchmarks/mutcd150/v1/   150 questions, runner, runtime manifest
evaluation/               gold answers, per-model scores, cross-model tables
ablations/                six ablation configs and the runner
validation/              figure and table coverage reports
docs/                     architecture notes
notebooks/                the Colab notebook
```

## Retrieval

Text retrieval fuses dense and sparse rankings with reciprocal rank fusion, then
scores candidates as

```
S = w_dense * S_RRF + w_graph * S_graph + w_ruletype * (w(r) - 1) + w_hierarchy * S_hier
```

`S_RRF` is the fused rank score, `S_graph` is inverse shortest-path distance to
any graph node named in the query, `w(r)` weights Standard above Guidance above
Option above Support, and `S_hier` rewards a part, chapter or section the query
names explicitly. A cross-encoder reranks the top candidates.

Visual evidence is gated per query: an explicit figure or table ID or a visual
phrase forces it on, a definitional question forces it off, and everything else
goes through a lexical score plus a prior over whether the top sections cite any
figures. When it is on, figures arrive by two paths — cited by the top chunks,
and direct late-interaction search over the crop index — then a vision-language
filter keeps only what a reader must actually look at.

**Note:** the sparse leg has never produced a signal in practice; see
`CHANGES.md`. Graph expansion is also a placeholder — only proximity re-scoring
of the already-fused candidates happens today.

## Knowledge base

| Component | Count |
|---|---|
| Sections | 678 |
| Text chunks | 5,705 |
| Figures | 485 |
| Tables | 68 |
| Graph nodes | 8,240 |
| Graph edges | 18,245 |

Edge labels: `contains`, `mentions`, `depicts`, `cites_figure`, `cites_section`,
`cited_in`, `defines`, `kind_of`, `belongs_to_chapter`, `anchored_in`,
`on_page_of`, `cites_table`.

Figure and table coverage is complete: 485/485 and 68/68, with Tables 3-1 and
3-3 excluded as references to external documents.

## MUTCD-150

150 questions over the 11th Edition, each with a locked gold answer and gold
evidence identifying the required sections, pages, figures, tables and visual
crops. 85 need figure or table evidence. 120 are answerable and 30 are
deliberately unanswerable. Modality splits 60 text, 30 table, 30 figure,
30 mixed.

Questions also carry M-SDI annotations — localization, modality integration,
reasoning, answer composition and normative precision burdens — with a revised
difficulty derived from them. See `evaluation/annotations/`.

Run it from the notebook, section 6. Results land under
`Drive/MyDrive/MRAG/benchmark_runs/`.

## Ablations

Six configs in `ablations/configs/`: router, VLM figure filter, graph proximity,
rule-type weight, hierarchy prior, reranker. The last four can run
retrieval-only, which needs no generation model and costs nothing in API calls.
`ablations/results/` ships empty.

## Running on HPRC

Skip the Colab-only cells. Set `MRAG_BASE_DIR` to your data directory and use
`scripts/ingest.slurm`. Everything else is identical.
