#!/bin/bash
# compare40/visrag_retrieve_job.slurm -- job 1 of the VisRAG baseline: VisRAG-Ret ranks the
# MUTCD pages for every question of VISRAG_QUESTIONS. Submitted by
# compare40/run_visrag_grace.sh. Not meant to be submitted by hand. No API, no proxy.
#SBATCH --job-name=visrag_retr
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${VISRAG_QUESTIONS:?submit with compare40/run_visrag_grace.sh}"
: "${VISRAG_STEM:?submit with compare40/run_visrag_grace.sh}"
VISRAG_ENV="$VINE_HOME/envs/visrag"
REV="$(tr -d '[:space:]' < "$VINE_HOME/visrag_ret_revision")"
OUT="$MRAG_BASE_DIR/compare40_runs/visrag"
RETR="$OUT/retrieval_$VISRAG_STEM"
mkdir -p "$RETR/page_embeddings"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY

echo "job $SLURM_JOB_ID | VisRAG retrieval | $VISRAG_STEM | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
echo "questions $VISRAG_QUESTIONS | sha256 $(sha256sum "$VISRAG_QUESTIONS" | cut -c1-12)"
echo "code sha256: visrag_retrieve.py $(sha256sum "$REPO/compare40/visrag_retrieve.py" | cut -c1-12) | VisRAG-Ret $REV"
nvidia-smi -L || true
# the page vectors of the 40-question run, reused: same pages, same model commit (the
# file names carry it), and visrag_retrieve.py checks each block's shape before using it
if compgen -G "$OUT/retrieval/page_embeddings/*.npy" > /dev/null; then
    for f in "$OUT/retrieval/page_embeddings/"*.npy; do       # copied, never moved; nothing overwritten
        d="$RETR/page_embeddings/$(basename "$f")"
        [ -e "$d" ] || { cp "$f" "$d.part" && mv "$d.part" "$d"; }   # a stopped copy leaves no half file
    done
    n=$( (compgen -G "$RETR/page_embeddings/ret_${REV:0:12}_pages_*.npy" || true) | wc -l)
    echo "page vectors reused from $OUT/retrieval/page_embeddings: $n blocks for VisRAG-Ret ${REV:0:12} (24 = all 1,162 pages)"
    [ "$n" -eq 24 ] || echo "WARNING: not all 24 blocks are for this model commit: the missing pages are embedded now (slower)"
else
    echo "no saved page vectors: all 1,162 pages are embedded now (slower)"
fi
cd "$REPO"
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
    "$VISRAG_ENV/bin/python" -I -u compare40/visrag_retrieve.py \
    --pdf "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" --questions "$VISRAG_QUESTIONS" \
    --pages_dir "$OUT/pages" --out_dir "$RETR" --revision "$REV" --save_top 20
echo; echo "retrieval done | $(date '+%Y-%m-%d %H:%M:%S')"
