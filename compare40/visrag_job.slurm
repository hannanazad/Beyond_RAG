#!/bin/bash
# compare40/visrag_job.slurm -- the VisRAG baseline on the 40 questions.
# Submitted by compare40/run_visrag.sh (which sets the account, GPU, time, log,
# VISRAG_MODE and VISRAG_PAGES). Not meant to be submitted by hand.
#
#   1. retrieval (GPU, offline): compare40/visrag_retrieve.py in the VisRAG environment
#      renders the 1,162 pages, embeds them with VisRAG-Ret (the vectors are kept and
#      reused by later runs) and ranks the pages for each of the 40 questions;
#   2. answers (the API, through the HPRC web proxy): compare40/run_visrag.py sends the
#      top VISRAG_PAGES page images to the answer model with GEMS-RAG's prompt.
#SBATCH --job-name=compare40_visrag
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${VISRAG_MODE:?VISRAG_MODE is not set -- submit with compare40/run_visrag.sh}"
: "${VISRAG_PAGES:?VISRAG_PAGES is not set -- submit with compare40/run_visrag.sh}"
VISRAG_ENV="$VINE_HOME/envs/visrag"
REV="$(tr -d '[:space:]' < "$VINE_HOME/visrag_ret_revision")"
OUT="$MRAG_BASE_DIR/compare40_runs/visrag"; mkdir -p "$OUT"
if [ "$VISRAG_MODE" = smoke ]; then
    ONLY="--only SAMPLE002,SAMPLE022"; TAG="smoke"
else
    ONLY=""; TAG="v1"
fi

echo "job $SLURM_JOB_ID | mode $VISRAG_MODE | pages $VISRAG_PAGES | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
nvidia-smi -L || true
cd "$REPO"

echo; echo "===== 1. VisRAG retrieval (VisRAG-Ret $REV) ====="
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
    "$VISRAG_ENV/bin/python" -I -u compare40/visrag_retrieve.py \
    --pdf "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" --questions compare40/questions_40.json \
    --pages_dir "$OUT/pages" --out_dir "$OUT/retrieval" --revision "$REV" --save_top 20

echo; echo "===== 2. answers ====="
module load WebProxy                         # the answer model is called over the API
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -s "$VINE_HOME/anthropic_key" ]; then
    ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
    export ANTHROPIC_API_KEY
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "no Anthropic key (\$VINE_HOME/anthropic_key)"; exit 1; }
"$RETR_ENV/bin/python" -u compare40/run_visrag.py --retrieval "$OUT/retrieval" --pages "$VISRAG_PAGES" \
    $ONLY --tag "$TAG"
echo; echo "VisRAG done | $(date '+%Y-%m-%d %H:%M:%S')"
