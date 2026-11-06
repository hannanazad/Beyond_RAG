# Third-party notices

This release contains the source subsets required to build and query two
external projects:

- Microsoft GraphRAG, distributed under the MIT License. Its license and
  attribution files are retained under `third_party/graphrag/`. The upstream
  source is [microsoft/graphrag](https://github.com/microsoft/graphrag); our
  extracted study adapter is in
  [GEMS-RAG/graphrag](https://github.com/GEMS-RAG/graphrag).
- PaperQA, distributed under the Apache License 2.0. Its license and citation
  files are retained under `third_party/paperqa/`. The upstream source is
  [Future-House/paper-qa](https://github.com/Future-House/paper-qa); our extracted
  study adapter is in [GEMS-RAG/paperqa](https://github.com/GEMS-RAG/paperqa).

The original method citations and study-implementation citations are supplied
in [references.bib](references.bib) and [docs/IMPLEMENTATIONS.md](docs/IMPLEMENTATIONS.md).

The MUTCD manual and derived benchmark/index artifacts are separate from those
software licenses. Review the applicable federal publication terms before
redistributing the manual itself.

The supplied GEMS-RAG source snapshot did not contain a license file. This
bundle therefore does not infer or grant an additional license for that
source. Its extracted study implementation is in
[GEMS-RAG/gems-rag](https://github.com/GEMS-RAG/gems-rag). The study-authored BM25
baseline is in [GEMS-RAG/bm25](https://github.com/GEMS-RAG/bm25).
