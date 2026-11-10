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

## System 2 with Qwen3.8-27B as the answer model (10 Nov)

The same as system 2: the same evidence, GEMS-RAG's answer prompt and up to 4 images. The prompt text and the image files are the same as Sonnet 5.5 and Fable 5 got (the same SHA-256 of the prompt). Only the answer model changes: Qwen3.8-27B, the model that writes VINE's plans, on FASTER's own A100s. No API is called.

Two small differences come from GEMS-RAG's own code for each kind of server, not from this test:
- the order in the message: for Claude it puts the images first; for an OpenAI-style server, the text first;
- the image size the model sees: Anthropic shrinks large images; vLLM uses Qwen's own image processor.

- `run_qwen_rag.py` (in the job) does the following:
  - It uses the parser's model files: the same model and revision, read from `hprc/vine_hprc.py`. It stops if they have no vision part.
  - It starts one vLLM server per GPU, with the parser's flags and environment, except that **vision is ON**. The parser uses `--language-model-only`, which leaves the vision part out. Here the server takes up to 4 images and no video.
  - It asks each server what colour a small red picture is. A server that cannot see it is not used.
  - It shares the questions among the servers, one at a time. Each question is one run of `run_vine_rag.py --local-server`.
- `qwen_local.py` holds the request settings. They are the parser's settings with this model:
  - thinking on, effort `xhigh` (the model's own default);
  - the model card's sampling;
  - seed 42.

  The output limit is all the room the window leaves after the prompt, so the limit never cuts the thinking short. Claude's limit (16,000, then 32,000) was never reached; its longest answer used 2,748 tokens. A reply cut off at the window is not asked again, since the same seed gives the same reply.
- **The window:** the server asks for 131,072 tokens at 0.95 of the GPU's memory. vLLM says how much fits, and the server starts again with that, as long as it is at least 49,152. If memory runs out at start, it uses 0.90. Every question gets the smallest window of the servers, so the room to think does not depend on which server takes it.
- `qwen_rag_job.slurm` and `run_qwen_rag.sh` submit the job.

```
cd $SCRATCH/Beyond_RAG_repo
bash compare40/run_qwen_rag.sh ACCOUNT smoke      # 2 questions, 1 GPU (optional; up to 2 hours)
bash compare40/run_qwen_rag.sh ACCOUNT full       # all 40 questions, 4 GPUs (a third word: 1-6 GPUs)
```

**Outputs** (in `$SCRATCH/Beyond_RAG/compare40_runs/vine_rag/`):
- `answers_qwen_v1.jsonl`: one line per question. Each line includes `local_server.calls`: the prompt's tokens, the limit sent, the tokens out, the finish reason and the time.
- `reasoning_qwen_v1_s*.jsonl`: the model's thinking.
- `qwen_rag_qwen_v1_manifest.json`: the server commands, windows, the picture test and the settings.
- `server_logs_qwen_v1/`: the server logs.

The same command again answers only the questions that have no answer yet.
