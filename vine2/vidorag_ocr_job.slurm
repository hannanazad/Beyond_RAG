#!/bin/bash
# vine2/vidorag_ocr_job.slurm -- job 0 of VINE answer-then-check on ViDoRAG's retrieval (CPU):
# ViDoRAG's page pictures and its OCR text of every page (vine2/vidorag_ocr.py). Submitted by
# vine2/run_vine2_vis_grace.sh. Not meant to be submitted by hand. No GPU, no API, no proxy.
# A page already done is kept, so a stopped job is simply submitted again.
#SBATCH --job-name=vis_ocr
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
OUT="$MRAG_BASE_DIR/compare40_runs/vidorag"
PDF="$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY HF_TOKEN
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

echo "job $SLURM_JOB_ID | ViDoRAG pictures and OCR | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- vine2)" ]; then
    echo "STOPPED: vine2 is changed locally"; exit 1
fi
echo "code sha256: vidorag_ocr.py $(sha256sum "$REPO/vine2/vidorag_ocr.py" | cut -c1-12)" \
     "| ViDoRAG $(git -C "$VINE_HOME/ext/vidorag" rev-parse --short=12 HEAD)"
command -v pdftoppm >/dev/null || { echo "STOPPED: pdftoppm (poppler) is missing on this node"; exit 1; }
echo "poppler: $(pdftoppm -v 2>&1 | head -1)"
"$VINE_HOME/envs/vidorag_ocr/bin/python" -I -c "import cv2, fastdeploy" >/dev/null \
    || { echo "STOPPED: the OCR libraries do not load on this node (cv2 or fastdeploy)"; exit 1; }
cd "$REPO"
"$VINE_HOME/envs/vidorag_ocr/bin/python" -I -u vine2/vidorag_ocr.py --pdf "$PDF" --work "$OUT/work" \
    --code "$VINE_HOME/ext/vidorag" --ocr-models "$VINE_HOME/ext/vidorag_ocr_models"
echo; echo "job 0 done | $(date '+%Y-%m-%d %H:%M:%S')"
