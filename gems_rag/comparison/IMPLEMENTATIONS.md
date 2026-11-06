# Study implementations

The saved MUTCD answer comparisons used BM25, GraphRAG, PaperQA2, and GEMS-RAG. Each method has its own source repository. This hub supplies the shared corpus, benchmark, prebuilt indexes, comparison runner, and scoring workflow.

| Public method ID | Implementation repository | Name in saved answer runs | Compared retrieval configuration |
| --- | --- | --- | --- |
| `bm25` | [GEMS-RAG/bm25](https://github.com/GEMS-RAG/bm25) | `bm25` | Original BM25 over chunk metadata and raw text; `k1=1.5`, `b=0.75`. |
| `graphrag` | [GEMS-RAG/graphrag](https://github.com/GEMS-RAG/graphrag) | `graphrag_local` | Microsoft GraphRAG `local` query algorithm, with context returned to the common answer harness. |
| `paperqa` | [GEMS-RAG/paperqa](https://github.com/GEMS-RAG/paperqa) | `paperqa2_chunks` | PaperQA `Docs` over canonical chunks, with evidence selection in context-only mode. |
| `gems-rag` | [GEMS-RAG/gems-rag](https://github.com/GEMS-RAG/gems-rag) | `gems_full` | Full text, visual, graph, hierarchy, rule-weighting, and reranking pipeline. |

The saved answer runs contain 150 successful question rows per method for each of four answer-model configurations. They used six retrieved contexts and a 9,600-character injected-context budget. The published retrieval-scoring workflow uses `--top-k 10`. These are separate experiment settings; preserve the retrieval depth and context budget for the experiment being reproduced.

## Source provenance

GraphRAG, PaperQA, and GEMS-RAG are extracted from hub commit [`8e981f2e3ae98a69516206cc19fca010a3f33d4e`](https://github.com/GEMS-RAG/rag/tree/8e981f2e3ae98a69516206cc19fca010a3f33d4e), preserving their retrieval source. BM25's original class and supporting definitions are extracted unchanged from the saved-run experiment harness. Its new CLI reconstructs the original chunk representation from the shared export. Each repository has a `PROVENANCE.json` recording source revisions and file hashes; BM25 also records exact definition spans. The PaperQA repository additionally restores its upstream packaging README from the exact pinned upstream revision.

The standalone BM25 repository reproduces the saved answer-run baseline. The older bundled `pipelines/query_bm25.py` scores the display-formatted export directly, which produces different rankings. That archived entrypoint remains available with the bundled source workflow; use the standalone repository when reproducing the saved answer comparisons.

[IMPLEMENTATIONS.json](../IMPLEMENTATIONS.json) records the initial extracted commit of each repository. Check out those commits to reproduce this extraction. The corpus SHA-256 is `1035540a107be1e6016a98f7543faadd53a187a2cca8bd528fcf7beb3d6f529d`.

The external method sources are pinned to:

- Microsoft GraphRAG: [`6d02c2355c3fed4c49007572fbe951d73258a37f`](https://github.com/microsoft/graphrag/tree/6d02c2355c3fed4c49007572fbe951d73258a37f), MIT license.
- FutureHouse PaperQA: [`d7675d7b7eddeb3535e8c260399c5bbeeb818c50`](https://github.com/Future-House/paper-qa/tree/d7675d7b7eddeb3535e8c260399c5bbeeb818c50), Apache-2.0 license.

The GEMS-RAG source snapshot and study-specific adapters retain the licensing status of the published source. No additional license is inferred. Original attribution and license files are retained with each upstream source.

## Reproduce a method

Clone the method repository and this hub as sibling directories, then follow that method's README. BM25 can read `rag/indexes/corpus/chunks.jsonl` directly. The other methods use the shared indexes installed by `rag/scripts/initialize_indexes.py`. Their standalone setup scripts install only that method's runtime; GEMS-RAG also requires visual-asset materialization.

The bundled adapters, upstream source snapshots, setup commands, and comparison runner in this hub continue to work with their existing paths. The hub's prebuilt-index asset stays associated with this study. Reusing a different upstream release or embedding/query model can require rebuilding indexes.

## Cite the methods and study software

For the original algorithms, cite:

1. Stephen Robertson and Hugo Zaragoza (2009). [The Probabilistic Relevance Framework: BM25 and Beyond](https://doi.org/10.1561/1500000019).
2. Darren Edge et al. (2024). [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130).
3. Michael D. Skarlinski et al. (2024). [Language agents achieve superhuman synthesis of scientific knowledge](https://arxiv.org/abs/2409.13740).

For the study implementation, also cite the relevant method repository and its commit. For the common benchmark and reproduction workflow, cite [GEMS-RAG/rag](https://github.com/GEMS-RAG/rag). [references.bib](../references.bib) contains reusable entries. Each method repository supplies `CITATION.cff`; PaperQA's repository also retains the upstream project's additional requested citations.

## Initial extracted commits

| Implementation | Commit |
| --- | --- |
| [BM25](https://github.com/GEMS-RAG/bm25) | [`b99ea7f52691`](https://github.com/GEMS-RAG/bm25/commit/b99ea7f52691c3792d9ebce73f91e1f1258b294e) |
| [GraphRAG](https://github.com/GEMS-RAG/graphrag) | [`0618a831cf36`](https://github.com/GEMS-RAG/graphrag/commit/0618a831cf3671685f9a01da55563e277b1d7212) |
| [PaperQA2](https://github.com/GEMS-RAG/paperqa) | [`e36cc23d2bbf`](https://github.com/GEMS-RAG/paperqa/commit/e36cc23d2bbf73c73d612d00566af8030c21961c) |
| [GEMS-RAG](https://github.com/GEMS-RAG/gems-rag) | [`4bd15337cd74`](https://github.com/GEMS-RAG/gems-rag/commit/4bd15337cd740bd753cc97990ffb085ed703a9cd) |
