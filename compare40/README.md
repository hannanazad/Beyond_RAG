# compare40: three systems on the same 40 questions

The 40 questions are the sample questions SAMPLE002–SAMPLE041: the 20 used before, plus 20 new ones. This folder holds **question text only**. The gold answers are used only to score the runs, outside the pipeline, and never go into this repo.

| | System | Evidence | Who answers |
|---|---|---|---|
| 1 | **GEMS-RAG, as it is** | GEMS-RAG's own retrieval, graph and data | the answer model (it also filters the figures, as in the paper) |
| 2 | **VINE as plain RAG** | exactly VINE's evidence (Kq): all ~80 pieces, whole; every figure listed; up to 4 images | the answer model, in one call, with GEMS-RAG's answer prompt |
| 3 | **Full VINE** (17 Oct setting, commit `525d3ba`) | the same Kq | Qwen3.8-27B plans, the answer model checks and answers |

Answer models: `claude-sonnet-5-5` and `claude-fable-5`.

- 1 vs 2: same answer prompt and model, different evidence. This shows what VINE's graph and retrieval add.
- 2 vs 3: same evidence and model. This shows what VINE's plan-maker and checkers add.

## Files

- `questions_40.json`: `{id: text}`, for VINE (`VINE_QUESTIONS`). The first 20 have exactly the text VINE read on 17 Oct.
- `questions_40.jsonl`: `{"question_id", "question"}`, for GEMS-RAG's own runner.
- `run_gems_rag.py`: system 1. It uses the untouched copy in `../gems_rag/` (github.com/hannanazad/gemsrag, commit `6b61de1`) and its data copy in `$SCRATCH/Beyond_RAG/gems_rag/`. No GEMS-RAG file is changed.
  - **It stops if:**
    - the copy differs from that commit (a fingerprint check);
    - a part of GEMS-RAG is not set up as for the paper:
      - the text model must be in the paper's mode, the dense-only fallback, because with GEMS-RAG's pinned packages BGE-M3's own loader fails;
      - mxbai-rerank and ColQwen2 must load;
      - ColQwen2 must find pages and figure crops;
    - an image file is missing.
  - It maps GEMS-RAG's Colab image paths (`/content/drive/MyDrive/MRAG/...`) to the same files in the data copy. Without this, GEMS-RAG would quietly answer with no images.
  - It runs GEMS-RAG's own runner with the paper's settings.
  - It ends with exit code 1 if GEMS-RAG reports a failure or a fallback during the run, or if an answer is missing.
- `run_vine_rag.py`: system 2. It reads VINE's evidence file and calls GEMS-RAG's answer step. So that VINE's evidence reaches the model whole, the question's evidence is printed in GEMS-RAG's format with these differences:
  - no 1,400-character cut;
  - table rows and figure readings are kept, with VINE's labels (GEMS-RAG would drop them);
  - each list item keeps its lead-in sentence;
  - every figure in the evidence is listed and can be cited. This is how VINE's checkers see them.
- `compare40_job.slurm` and `run_compare40.sh`: one Slurm job for systems 1 and 2.
  - **Step 1** is VINE's retrieval stage for the 40 questions. It reuses the 17 Oct evidence and adds the 20 new questions. It stops if VINE's retrieval code is not the 17 Oct one (`r4299665`).
  - **Then** system 2 (API only, in the background) and system 1 (on the GPU) run at the same time.

## Run on FASTER

```
cd $SCRATCH/Beyond_RAG_repo
bash compare40/run_compare40.sh ACCOUNT smoke    # 2 questions, both models: check it works
bash compare40/run_compare40.sh ACCOUNT full     # all 40, both models (after the smoke job has ended)
```

A third word picks the GPU: `a100` (the default), `a40`, `a30` or `a10`. The models need about 12 GB and bfloat16, so not `t4`. To see which GPUs are free: `sinfo -p gpu -h -o "%G %t %D" | sort`.

**Before the first run, these must be in place:**
- the data copy in `$SCRATCH/Beyond_RAG/gems_rag/`;
- ColQwen2 in `$SCRATCH/hf_cache`.

The launcher checks both. It also refuses to start while another compare40 or VINE job is queued or running, because both systems lock their vector stores.

**Outputs:**
- answers: `$SCRATCH/Beyond_RAG/compare40_runs/gems_rag/<run id>/` (with `compare40_note.json` and `compare40_warnings.json`) and `.../vine_rag/answers_<tag>.jsonl`;
- logs: `$SCRATCH/vine/logs/compare40_<mode>_<job>.log` and `.../compare40_runs/vine_rag_<tag>.log`.

Both runs carry on where they stopped.

System 3 is run separately, from a checkout of `525d3ba`.
