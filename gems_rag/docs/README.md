# Documentation

| Document | Read it when you want to |
|---|---|
| **`REPRODUCTION_GUIDE.md`** | **Run any of this yourself. Start here.** |
| `01_SYSTEM_ARCHITECTURE.md` | Understand how GEMS-RAG works and how it was built |
| `02_TRAINED_VS_RULES.md` | Know what was trained and what is hand-written rules |
| `03_FIGURE_EXTRACTION_REBUILD.md` | See how figures were cropped and verified complete |
| `04_ARCHITECTURE_NOTES.md` | Read the original design notes |
| `setup/COLAB_SETUP.md` | Set up on Google Colab specifically |
| `setup/HPRC_SETUP.md` | Set up on a university HPC cluster (SLURM) |

`01_SYSTEM_ARCHITECTURE.docx` is the same content as the `.md`, for readers
who prefer Word.

---

## Suggested reading order

**If you are evaluating this project:** the top-level `../README.md`, then
`../results/README.md` for the numbers, then `02_TRAINED_VS_RULES.md` — that
last one answers the question reviewers ask first, which is how much of this is
a model and how much is engineering.

**If you are running it:** `REPRODUCTION_GUIDE.md`, and nothing else until
something breaks.

**If you are extending it:** `01_SYSTEM_ARCHITECTURE.md` end to end, then the
code in `../mrag/`. The architecture document names which file does what.

---

## Two things the documents are deliberate about

**The knowledge graph re-scores; it does not expand.** The expansion step in
`mrag/retrieval.py` is a placeholder that does nothing. The graph influences
ranking through a scoring term only. Both `01_SYSTEM_ARCHITECTURE.md` and
`02_TRAINED_VS_RULES.md` say so, and any write-up should describe it as
re-ranking rather than retrieval expansion.

**Nothing was trained.** Every component is either deterministic code or a
frozen off-the-shelf model that is prompted but never fine-tuned.
`02_TRAINED_VS_RULES.md` goes component by component.
