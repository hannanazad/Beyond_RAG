# Notices

## Licensing status

**This repository does not yet carry a software license.** A license has not
been chosen, and none is implied by publication. Anyone intending to reuse,
redistribute, or build on this code should contact the author first, or wait
for a license file to be added.

If you are the author reading this: add a `LICENSE` file before any public or
archival submission. MIT and Apache-2.0 are the usual choices for research
code. This file should then be updated to point at it.

## The MUTCD manual

`benchmark/source/mutcd11theditionr1hl.pdf` is the Manual on Uniform Traffic
Control Devices, 11th Edition, published by the US Federal Highway
Administration. It is included so the benchmark can be reproduced against the
exact source used. Its publication terms are separate from any software
license covering this repository, and should be verified independently for the
intended channel.

Every derived artifact in `benchmark/`, `validation/`, and `results/` — the
cropped figures, page images, extracted text chunks, and the knowledge graph —
originates from that manual.

## Third-party software

The baseline comparison under `comparison/` bundles source from Microsoft
GraphRAG (MIT) and FutureHouse PaperQA (Apache-2.0). Their licenses are
retained in their source directories and summarised in
`comparison/THIRD_PARTY_NOTICES.md`. Credit those projects alongside this work
when reporting comparison results.

Model weights used at runtime — BGE-M3, ColQwen2, and mxbai-rerank-large-v2 —
are downloaded from Hugging Face at first use and carry their own licenses.
None of them were modified or fine-tuned here.
