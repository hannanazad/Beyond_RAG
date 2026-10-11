#!/bin/bash
# hprc/setup.sh -- one-time setup of the VINE pipeline on FASTER (TAMU HPRC).
#
# Run it on a LOGIN node (it needs the internet), in the background, so it keeps
# going if your terminal closes:
#
#   mkdir -p $SCRATCH/vine/logs
#   nohup bash $SCRATCH/Beyond_RAG_repo/hprc/setup.sh > $SCRATCH/vine/logs/setup.log 2>&1 &
#   tail -f $SCRATCH/vine/logs/setup.log          (Ctrl+C stops watching, not the setup)
#
# It is safe to run again: finished steps are skipped, and a step that broke
# starts again from the beginning. About 30-60 minutes, most of it downloads.
#
# What it makes (ALL in $SCRATCH, nothing in $HOME -- see hprc/env.sh):
#   $SCRATCH/vine/bin, python      uv (the installer) and Python 3.12
#   $SCRATCH/vine/envs/retrieval   torch 2.6.0 + the retrieval stack, as on Colab
#   $SCRATCH/vine/envs/vllm        vLLM 0.31.0 (torch 2.13, CUDA 13.2), as on Colab
#   $SCRATCH/hf_cache              the three models, at the exact revisions used on Colab
#   $SCRATCH/Beyond_RAG/qdrant_db  the vector store, unpacked from qdrant_db.tar
#   $SCRATCH/vine/setup_summary.txt  every version and revision, for the run records

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$HERE/env.sh"
VINE_REPO="$(cd "$HERE/.." && pwd)"     # the clone this script is in
export VINE_REPO

PY_VERSION=3.12
VLLM_VERSION=0.31.0
# On Colab (driver 580.82) the vLLM install chose torch 2.13 built for CUDA 13.2
# (docs/PARSER_TEST_2026-10-07.md). FASTER's driver is 580.126.20, so the same
# build runs here. The login node has no GPU to choose from, so it is named here.
VLLM_TORCH_BACKEND=cu132
VLLM_TORCH_PREFIX=2.13
VLLM_TORCH_CUDA=13.2
# The retrieval stack, pinned as in the notebooks (torch 2.6.0 for CUDA 12.4).
RETR_TORCH_BACKEND=cu124

# The model revisions used on Colab (the parser: docs/PARSER_TEST_2026-10-07.md;
# the encoder and reranker: the refs and snapshots in Drive's Beyond_RAG/hf_cache).
MODEL_PINS="Qwen/Qwen3.8-27B-FP8=017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
BAAI/bge-m3=5617a9f61b028005a4858fdac845db406aefb181
mixedbread-ai/mxbai-rerank-large-v2=ca7e1ee484c37c0ddd8d178a9a5c33cec575c5e6"
export MODEL_PINS

STEP="start"
step() { STEP="$1"; echo; echo "=== STEP $1: $2 ($(date '+%H:%M:%S')) ==="; }
fail() {
    echo
    echo "STOPPED in STEP $STEP: $*"
    echo "Nothing is lost: run the same command again after the fix; finished steps are skipped."
    echo "Send me the end of this log: $VINE_HOME/logs/setup.log"
    exit 1
}
trap 'fail "the command on line $LINENO failed (see the lines just above)"' ERR
is_done() { [ -f "$VINE_HOME/.done_$1" ]; }
mark_done() { touch "$VINE_HOME/.done_$1"; }

echo "VINE setup on FASTER | $(date) | host $(hostname) | user $(whoami)"
echo "repo   : $VINE_REPO ($(git -C "$VINE_REPO" log -1 --format='%h %s' 2>/dev/null || echo 'not a git clone'))"
echo "data   : $MRAG_BASE_DIR"
echo "install: $VINE_HOME"
MARK="$VINE_HOME/.setup_started"
touch "$MARK"                      # to list anything that lands in $HOME during this run

# --------------------------------------------------------------------------- #
step 0 "checks before anything is installed"
# --------------------------------------------------------------------------- #
if [ -n "${SLURM_JOB_ID:-}" ]; then
    echo "running inside Slurm job $SLURM_JOB_ID: loading WebProxy for the internet"
    module load WebProxy || fail "module load WebProxy failed"
fi
[ -f "$VINE_REPO/requirements.txt" ] && [ -f "$VINE_REPO/mrag/config.py" ] \
    || fail "$VINE_REPO is not the Beyond_RAG repo (no requirements.txt / mrag/config.py)"
curl -sSfI --max-time 30 https://pypi.org/simple/ >/dev/null \
    || fail "no internet from this machine. Run this on a login node (faster1 or faster2)."
missing=0
for f in mutcd11theditionr1hl.pdf \
         vine_data/graph_cache.pkl vine_data/vine_items.jsonl vine_data/text_store_manifest.json \
         mmrag_cache_v3/chunks.jsonl mmrag_cache_v3/figures.jsonl \
         mmrag_cache_v3/mutcd_tables.jsonl mmrag_cache_v3/sign_codes.json; do
    if [ -s "$MRAG_BASE_DIR/$f" ]; then
        printf '  ok       %-42s %s\n' "$f" "$(du -h "$MRAG_BASE_DIR/$f" | cut -f1)"
    else
        printf '  MISSING  %s\n' "$f"; missing=1
    fi
done
n_fig=$(find "$MRAG_BASE_DIR/figures" -type f 2>/dev/null | wc -l || true)
echo "  figures  $n_fig files"
[ -f "$MRAG_BASE_DIR/qdrant_db.tar" ] || [ -f "$MRAG_BASE_DIR/qdrant_db/meta.json" ] || {
    echo "  MISSING  qdrant_db.tar"; missing=1; }
[ "$missing" = 0 ] || fail "data files are missing in $MRAG_BASE_DIR (copy them from Drive again)"
[ "$n_fig" -gt 0 ] || fail "no figure images in $MRAG_BASE_DIR/figures"
if command -v showquota >/dev/null 2>&1; then showquota || true; fi

# --------------------------------------------------------------------------- #
step 1 "unpack the vector store"
# --------------------------------------------------------------------------- #
check_store() {
    for c in mutcd_chunks mutcd_figures mutcd_figures_visual mutcd_pages; do
        [ -s "$MRAG_BASE_DIR/qdrant_db/collection/$c/storage.sqlite" ] || fail "collection $c is missing in qdrant_db"
    done
    [ -f "$MRAG_BASE_DIR/qdrant_db/meta.json" ] || fail "qdrant_db/meta.json is missing"
}
if is_done qdrant; then
    echo "already done"
elif [ ! -f "$MRAG_BASE_DIR/qdrant_db.tar" ]; then
    echo "no qdrant_db.tar; using the folder that is already unpacked"
    check_store; mark_done qdrant
else
    # an unpack that broke halfway is removed and done again
    rm -rf "$MRAG_BASE_DIR/qdrant_db"
    tar -xf "$MRAG_BASE_DIR/qdrant_db.tar" -C "$MRAG_BASE_DIR"
    check_store; mark_done qdrant
fi
du -sh "$MRAG_BASE_DIR/qdrant_db"/collection/* | sed 's/^/  /'
echo "  (qdrant_db.tar is kept as the master copy)"

# --------------------------------------------------------------------------- #
step 2 "uv, the installer (one program, into $VINE_HOME/bin)"
# --------------------------------------------------------------------------- #
# Taken straight from uv's GitHub release, not through its install script, so
# nothing touches ~/.bashrc or ~/.config.
if [ ! -x "$VINE_HOME/bin/uv" ]; then
    tmp="$VINE_HOME/tmp_uv"; rm -rf "$tmp"; mkdir -p "$tmp"
    curl -LsSf --retry 3 -o "$tmp/uv.tar.gz" \
        https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf "$tmp/uv.tar.gz" -C "$tmp"
    install -m 755 "$tmp"/uv-x86_64-unknown-linux-gnu/uv "$tmp"/uv-x86_64-unknown-linux-gnu/uvx "$VINE_HOME/bin/"
    rm -rf "$tmp"
fi
[ "$(command -v uv)" = "$VINE_HOME/bin/uv" ] || fail "the uv found is $(command -v uv), not $VINE_HOME/bin/uv"
uv --version

# --------------------------------------------------------------------------- #
step 3 "Python $PY_VERSION (into $VINE_HOME/python)"
# --------------------------------------------------------------------------- #
uv python install "$PY_VERSION"
PY_FOUND="$(uv python find "$PY_VERSION")"
echo "python: $PY_FOUND ($("$PY_FOUND" --version))"
case "$PY_FOUND" in "$VINE_HOME"/*) ;; *) fail "uv picked a Python outside $VINE_HOME: $PY_FOUND" ;; esac

# --------------------------------------------------------------------------- #
step 4 "the retrieval environment (torch 2.6.0 + requirements.txt), $RETR_ENV"
# --------------------------------------------------------------------------- #
if is_done retrieval_env; then
    echo "already done"
else
    rm -rf "$RETR_ENV"                 # a half-made environment is made again
    uv venv "$RETR_ENV" --python "$PY_VERSION"
    RP="$RETR_ENV/bin/python"
    # same order as the notebooks (see the top of requirements.txt):
    # torch and torchvision from PyTorch's CUDA 12.4 index, then everything else
    # from PyPI. (The PyTorch index must NOT be used for the rest: it has only
    # old torchao builds, up to 0.9.0, and requirements.txt needs 0.13.)
    uv pip install --python "$RP" --torch-backend="$RETR_TORCH_BACKEND" "torch==2.6.0" "torchvision==0.21.0"
    uv pip install --python "$RP" -r "$VINE_REPO/requirements.txt"
    # the notebooks' last step: these four at the newest version inside their ranges
    uv pip install --python "$RP" --no-deps --upgrade \
        "transformers>=4.49,<4.55" "huggingface_hub>=0.34,<0.35" "tokenizers>=0.21,<0.22" "torchao>=0.13,<0.14"
    "$RP" - <<'PY'
import importlib
from importlib.metadata import version
from packaging.version import Version as V
import torch
print(f"  torch {torch.__version__} (CUDA {torch.version.cuda})")
assert torch.__version__.startswith("2.6.0") and torch.version.cuda == "12.4", "not torch 2.6.0 for CUDA 12.4"
ranges = {"transformers": ("4.49", "4.55"), "huggingface_hub": ("0.34", "0.35"),
          "tokenizers": ("0.21", "0.22"), "torchao": ("0.13", "0.14")}
for pkg, (lo, hi) in ranges.items():
    v = version(pkg)
    print(f"  {pkg} {v}")
    assert V(lo) <= V(v) < V(hi), f"{pkg} {v} is outside [{lo}, {hi})"
for pkg in ("FlagEmbedding", "sentence-transformers", "mxbai-rerank", "qdrant-client", "colpali-engine",
            "accelerate", "networkx", "pymupdf", "numpy", "anthropic", "openai", "pillow"):
    print(f"  {pkg} {version(pkg)}")
for mod in ("FlagEmbedding", "sentence_transformers", "mxbai_rerank", "qdrant_client", "networkx",
            "fitz", "anthropic", "openai", "PIL"):
    importlib.import_module(mod)
from transformers import PreTrainedModel  # noqa: F401  (the import that breaks with the wrong versions)
print("  every retrieval package imports")
PY
    uv pip freeze --python "$RP" > "$VINE_HOME/envs/retrieval_packages.txt"
    mark_done retrieval_env
fi

# --------------------------------------------------------------------------- #
step 5 "the parser's environment (vLLM $VLLM_VERSION), $VLLM_ENV"
# --------------------------------------------------------------------------- #
if is_done vllm_env; then
    echo "already done"
else
    rm -rf "$VLLM_ENV"
    uv venv "$VLLM_ENV" --python "$PY_VERSION"
    uv pip install --python "$VLLM_ENV/bin/python" --torch-backend="$VLLM_TORCH_BACKEND" "vllm==$VLLM_VERSION"
    VLLM_VERSION="$VLLM_VERSION" VLLM_TORCH_PREFIX="$VLLM_TORCH_PREFIX" VLLM_TORCH_CUDA="$VLLM_TORCH_CUDA" \
    "$VLLM_ENV/bin/python" - <<'PY'
import os
import torch, transformers, vllm
print(f"  vllm {vllm.__version__} | torch {torch.__version__} (CUDA {torch.version.cuda}) | transformers {transformers.__version__}")
assert vllm.__version__ == os.environ["VLLM_VERSION"], "wrong vLLM version"
assert torch.__version__.startswith(os.environ["VLLM_TORCH_PREFIX"]) and torch.version.cuda == os.environ["VLLM_TORCH_CUDA"], (
    f"Colab ran torch {os.environ['VLLM_TORCH_PREFIX']} for CUDA {os.environ['VLLM_TORCH_CUDA']}; this is a different build")
PY
    [ -x "$VLLM_ENV/bin/vllm" ] || fail "$VLLM_ENV/bin/vllm is missing"
    uv pip freeze --python "$VLLM_ENV/bin/python" > "$VINE_HOME/envs/vllm_packages.txt"
    mark_done vllm_env
fi

# --------------------------------------------------------------------------- #
step 6 "the three models, at Colab's revisions (into $HF_HUB_CACHE)"
# --------------------------------------------------------------------------- #
# The parser about 28 GB, the encoder about 4.5 GB, the reranker about 3 GB.
# A download that stopped carries on where it stopped.
if is_done models; then
    echo "already done"
else
    "$VLLM_ENV/bin/python" - <<'PY'
import os
from pathlib import Path
from huggingface_hub import snapshot_download
cache = Path(os.environ["HF_HUB_CACHE"])
# the encoder: the files FlagEmbedding itself would fetch
ignore = {"BAAI/bge-m3": ["flax_model.msgpack", "rust_model.ot", "tf_model.h5"]}
for line in os.environ["MODEL_PINS"].split():
    repo, rev = line.split("=")
    print(f"  {repo} @ {rev[:12]} ...", flush=True)
    path = Path(snapshot_download(repo, revision=rev, cache_dir=cache, ignore_patterns=ignore.get(repo)))
    assert path.name == rev, f"{repo}: got snapshot {path.name}, wanted {rev}"
    # the code asks for "main"; jobs run offline, so "main" must point at this revision
    ref = cache / ("models--" + repo.replace("/", "--")) / "refs" / "main"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(rev)
    files = [f for f in path.rglob("*") if f.is_file()]
    print(f"    {len(files)} files, {sum(f.stat().st_size for f in files) / 2**30:.1f} GB -> {path}")
PY
    mark_done models
fi

# --------------------------------------------------------------------------- #
step 7 "final checks"
# --------------------------------------------------------------------------- #
cd "$VINE_REPO"
"$RETR_ENV/bin/python" - <<'PY'
import os
from pathlib import Path
from mrag.config import CFG
S = Path(os.environ["SCRATCH"])
print(f"  mrag sees: environment {CFG.environment} | data {CFG.base_dir} | vector store {CFG.qdrant_dir} | models {CFG.hf_home}")
assert CFG.environment == "hprc"
assert Path(CFG.base_dir) == S / "Beyond_RAG"
assert Path(CFG.qdrant_dir) == S / "Beyond_RAG" / "qdrant_db"
assert Path(CFG.hf_home) == S / "hf_cache"
assert Path(CFG.vine_graph).exists() and Path(CFG.figures_jsonl).exists()
print("  the code finds the data, the vector store and the models in scratch")
PY

{
    echo "VINE setup on FASTER, finished $(date '+%Y-%m-%d %H:%M')"
    echo "repo commit      : $(git -C "$VINE_REPO" log -1 --format=%h 2>/dev/null || echo none)"
    echo "uv               : $(uv --version)"
    echo "python           : $("$RETR_ENV/bin/python" --version 2>&1) (both environments)"
    echo "retrieval env    : $(grep -iE '^(torch|transformers|flagembedding|sentence-transformers|mxbai-rerank|qdrant-client)==' "$VINE_HOME/envs/retrieval_packages.txt" | tr '\n' ' ')"
    echo "parser env       : $(grep -iE '^(vllm|torch|transformers)==' "$VINE_HOME/envs/vllm_packages.txt" | tr '\n' ' ')"
    echo "model revisions  : $(echo "$MODEL_PINS" | tr '\n' ' ')"
    echo "full package lists: $VINE_HOME/envs/retrieval_packages.txt, $VINE_HOME/envs/vllm_packages.txt"
} | tee "$VINE_HOME/setup_summary.txt"

# the downloaded package files are no longer needed (the environments keep theirs)
uv cache clean >/dev/null 2>&1 || true

echo
echo "anything new in your home folder during this run:"
NEW="$(find "$HOME" -xdev -newer "$MARK" 2>/dev/null \
        | grep -vxE "$HOME|$HOME/\.bash_history|$HOME/\.lesshst|$HOME/\.viminfo|$HOME/\.Xauthority" || true)"
if [ -z "$NEW" ]; then echo "  nothing"; else echo "$NEW" | head -50 | sed 's/^/  /'; fi
if command -v showquota >/dev/null 2>&1; then echo; showquota || true; fi
echo
echo "SETUP FINISHED $(date '+%H:%M:%S'). Send me everything from 'STEP 7' down."
