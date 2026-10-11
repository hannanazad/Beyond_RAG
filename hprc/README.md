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
4. Builds the parser's environment: vLLM 0.31.0, with torch 2.13 for CUDA 13.2, the build Colab used.
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
