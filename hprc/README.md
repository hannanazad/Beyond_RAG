# Running VINE on FASTER (TAMU HPRC)

Everything lives in `$SCRATCH` (`/scratch/user/<NetID>`). Nothing is installed in `$HOME`, which has room for only 10 GB and 10,000 files.

| Folder | What |
|---|---|
| `$SCRATCH/Beyond_RAG` | the data, copied from Google Drive (`MRAG_BASE_DIR`) |
| `$SCRATCH/Beyond_RAG_repo` | this repo (git clone) |
| `$SCRATCH/vine` | uv, Python 3.12, the two environments, caches, logs |
| `$SCRATCH/hf_cache` | the three models |

`hprc/env.sh` sets all of these, and points every cache (uv, pip, Hugging Face, vLLM, torch, Triton, CUDA) at scratch. Every script here reads it first.

## 1. Get the code (once)

On a login node:

```bash
git clone https://github.com/hannanazad/Beyond_RAG.git $SCRATCH/Beyond_RAG_repo
```

Later, to get new changes: `cd $SCRATCH/Beyond_RAG_repo && git pull`

## 2. Set up (once, about 30-60 minutes)

On a login node (it needs the internet). It runs in the background, so it keeps going if the terminal closes:

```bash
mkdir -p $SCRATCH/vine/logs
nohup bash $SCRATCH/Beyond_RAG_repo/hprc/setup.sh > $SCRATCH/vine/logs/setup.log 2>&1 &
tail -f $SCRATCH/vine/logs/setup.log
```

`Ctrl+C` stops the watching, not the setup. To look again later: `tail -50 $SCRATCH/vine/logs/setup.log`.

What it does:
1. Checks the data and unpacks the vector store (`qdrant_db.tar`, which is kept).
2. Gets uv (the installer) and Python 3.12, into `$SCRATCH/vine`.
3. Builds the retrieval environment: torch 2.6.0 and `requirements.txt`, in the same order as the notebooks.
4. Builds the parser's environment: vLLM 0.31.0 with the torch, torchvision and torchaudio it asks for, all from PyPI (so all three are built for the same CUDA).
5. Downloads the three models at the revisions Colab used:

   | Model | Revision |
   |---|---|
   | `Qwen/Qwen3.8-27B-FP8` | `017b9c7a` |
   | `BAAI/bge-m3` | `5617a9f6` |
   | `mixedbread-ai/mxbai-rerank-large-v2` | `ca7e1ee4` |
6. Checks that the code finds everything, writes `$SCRATCH/vine/setup_summary.txt` (every version and revision), and lists anything that appeared in `$HOME` (it should be nothing).

It is safe to run again: finished steps are skipped, and a step that broke starts again.

If you want to use the environments in your own terminal:

```bash
source $SCRATCH/Beyond_RAG_repo/hprc/env.sh
```

This also clears any loaded modules.

## 3. Save the Anthropic key (once)

The checkers call the Anthropic API. This asks for the key without showing it, and only you can read the file:

```bash
read -rs -p "Anthropic key: " K; echo; printf "%s" "$K" > $SCRATCH/vine/anthropic_key; chmod 600 $SCRATCH/vine/anthropic_key; unset K
```

## 4. Run

```bash
cd $SCRATCH/Beyond_RAG_repo && git pull
bash hprc/run.sh ACCOUNT 8
```

`ACCOUNT` is your project account number (`myproject` shows it); `8` is how many A100s the parser gets (1 to 10). This submits three Slurm jobs. Each starts only when the one before it finished well; a job that stops cancels the ones after it.

| Stage | GPUs | What | Time |
|---|---|---|---|
| `retrieval` | 1 | the retrieval check on 154 DEV cases (**the gate**), then Kq for every question | 30-60 min |
| `parse` | 8 | one parser server on each GPU (Qwen3.8-27B-FP8, xhigh, seed 42, one question at a time each); the plans | about 7 min a question, shared out over the GPUs |
| `execute` | 1 | the checkers (Claude Sonnet 5.5) execute every plan; the answers | 15-30 min |

- Watch: `squeue -u $USER`. Logs: `$SCRATCH/vine/logs/vine_<stage>_<job>.log`.
- Results: `$SCRATCH/Beyond_RAG/parser_runs_faster/` and `$SCRATCH/Beyond_RAG/retrieval_dev_results_faster/` (apart from the Colab runs). The answers file is `answers_sample_<time>.txt` in the run folder.
- Every stage carries on where it stopped. To start again from one stage: `bash hprc/run.sh ACCOUNT 8 parse` (or `execute`).
- Why one question at a time on each GPU: on Colab, one running server asked the same question twice gave the same plan (3 of 3). That check never started the server again. Across server starts the plans did NOT repeat on 12 October (1 of 11, section 5); section 6 tests why.
- The sealed questions, later: `VINE_QUESTIONS=/path/to/sealed.json bash hprc/run.sh ACCOUNT 8` (a JSON file `{id: text}`).

## 5. The repeat test: does the same question give the same plan?

```bash
bash hprc/run.sh ACCOUNT 6 repeat r1
$SCRATCH/vine/envs/retrieval/bin/python hprc/compare_plans.py r1     # when the job has finished
```

The first line submits the parse stage only, for the 11 DEV questions, into `parser_runs_faster/repeat_r1/`. That folder has its own model cache, which starts empty, so every plan comes from a new model call; Kq is the same file the first run read. The second line compares each plan with the first run's: the prompt, the model's whole reply (reasoning and answer) and the plan must be the same, byte for byte. Which GPU made a plan does not matter. For another test later, use another name (`r2`, ...); the same name carries on in the same folder.

The code is `hprc/vine_hprc.py` (the steps of `notebooks/VINE_Run.ipynb`) and `hprc/vine_job.slurm`.

## 6. The probe: do servers started separately give the same reply?

```bash
bash hprc/run.sh ACCOUNT 4 probe p2
```

One job on 4 GPUs, no API cost (`hprc/repeat_probe.py`). It asks parser servers, each started fresh, the same 3 DEV prompts (the ones the first run sent), and compares the first 4,096 tokens of each reply byte for byte. The result is at the end of the job's log (after `RESULT`), and in `parser_runs_faster/probe_NAME/probe.json`. A name can be used once.

- **probe_p1 (12 Oct):** one server asked twice gave the same reply (3 of 3); two servers started fresh did not (0 of 3), nor did a server started from a copy of another's caches (0 of 3), nor two with `--enforce-eager` (0 of 3, and 3 times slower). `VLLM_BATCH_INVARIANT=1` did not start (an 8-bit weight kernel failed to build). The cause, read in the code: kernels that tune themselves by timing the first time they run (Triton's autotuner, used by vLLM's FLA kernels for the GDN layers, and torch.compile's kernels). Timing noise makes servers keep different options, which round the last bit differently.
- **The fix being tested (p2):** `hprc/pin_tuning/sitecustomize.py`, loaded only by the parser servers (PYTHONPATH, `VINE_PIN_TUNING=1`), makes every such step keep the first working option instead of the fastest. 4 servers with it, each started fresh; their replies, and their Triton choices, must be the same.
