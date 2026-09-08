# Changes from the previous repository

## Code fixes

**Multi-sheet figures reached the model as sheet 1 only.**
`retrieval.py` always emitted every sheet in `image_paths`, but
`vlm.py::_build_prompt_and_images` read the singular `image_path`. 116 of 553
canonical figures and tables are multi-sheet; 174 sheets were being dropped.
34 of the 150 benchmark questions have gold evidence on one of them, including
Table 2B-1 (8 sheets), which is the gold evidence for TB008, TB009 and TB026.

Fixed in `mrag/vlm.py`. Sheets are now labelled `[sheet N of M]` in the prompt,
and the citation whitelist no longer repeats a figure once per sheet. Two new
settings in `mrag/config.py`: `max_sheets_per_figure` (8, covers 100% of
entities) and `max_images_total` (12).

**Chunk IDs collided and silently overwrote each other.**
`chunk_id` was `section + rule_type + ordinal`, which is not unique — a
paragraph split across a page break re-fires the ordinal. 36 IDs collided
across 107 rows. Because Qdrant upserts by `chunk_id_to_int(chunk_id)`, the
later row overwrote the earlier one, so 5,812 parsed chunks became 5,705
stored points.

Fixed in `mrag/parsing.py`; only repeats get a suffix, so the other 5,705 IDs
are byte-identical to before. For an existing cache, `scripts/repair_chunk_ids.py`
repairs it in place without re-embedding — the dense vectors already exist in
file order, so only the IDs change.

Note: the recovered rows are mostly fragmented figure and table text
(OCR'd sign legends, loose numbers from sign-size tables). The fix prevents
silent data loss; it is not expected to move scores much.

## Known issues, not yet fixed

**Sparse retrieval has never run.** `chunks_sparse.json` holds 5,812 entries and
every one is an empty dict. BGE-M3's dense path works; the sparse path fell back
silently, as the comment in `requirements.txt` warns it can. `vector_store.py`
gates on `if sparse:` and an empty dict is falsy, so the sparse query is skipped
and RRF runs on the dense ranking alone. Fixing this needs a fresh encode with
FlagEmbedding actually loading.

**Graph expansion is a placeholder.** `retrieval.py` step 3 has a `pass` where
candidate-set expansion should be. Only proximity re-scoring of the fused top-30
happens. Note that an expanded chunk has no RRF score, so it cannot outrank a
fused one without an explicit policy — reserved slots, a score floor, or
injection into the reranker. `top_k_after_graph` (40) already exceeds
`top_k_fused` (30), leaving 10 slots that nothing currently fills.

**Gold evidence is incomplete.** 77 of 120 answerable questions have a gold
provision that cross-references a section the answer key does not list — 214
sections in total. This matters most for any metric that requires evidence for
every obligation.

**Documentation drift.** `README.md` and `docs/architecture.md` previously
published `S = a*dense + b*sparse + ...` with separate dense and sparse terms.
The implemented formula has neither: `base` is the already-fused RRF score.
Corrected here. `w_sparse` in `config.py` was never referenced by any code path and has been deleted.

## Repository layout

Removed: a duplicate deployment payload, three superseded notebooks, per-model
archive bundles, generated document exports, and the 31 MB source PDF (it lives
in Drive, per the setup instructions). Kept the package, scripts, benchmark
definition, gold annotations, per-model final scores, cross-model tables,
ablation configs, and validation reports.

108 MB -> 11 MB.
