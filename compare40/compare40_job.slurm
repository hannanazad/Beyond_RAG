#!/bin/bash
# compare40/compare40_job.slurm -- the 40-question comparison, systems 1 and 2, as ONE job.
# Submitted by compare40/run_compare40.sh (which sets the account, GPU, time, log and
# COMPARE40_MODE). Not meant to be submitted by hand.
#
#   1. VINE's retrieval stage (hprc/vine_hprc.py retrieval) with VINE_QUESTIONS = the 40
#      questions: it reuses the 17 Oct evidence of the first 20 and finds the evidence of
#      the 20 new ones (the DEV check it runs first is already done, so it is skipped).
#      It stops first if VINE's retrieval code is not the 17 Oct one (r4299665), so all
#      three systems read the same evidence.
#   2. VINE as plain RAG (compare40/run_vine_rag.py): API calls only, in the background.
#   3. GEMS-RAG as it is (compare40/run_gems_rag.py): on the GPU, at the same time.
#SBATCH --job-name=compare40
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${COMPARE40_MODE:?COMPARE40_MODE is not set -- submit with compare40/run_compare40.sh}"

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
module load WebProxy                         # the answer models are called over the API
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -s "$VINE_HOME/anthropic_key" ]; then
    ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
    export ANTHROPIC_API_KEY
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "no Anthropic key (\$VINE_HOME/anthropic_key)"; exit 1; }

OUT="$SCRATCH/Beyond_RAG/compare40_runs"; mkdir -p "$OUT"
if [ "$COMPARE40_MODE" = smoke ]; then
    ONLY="--only SAMPLE002,SAMPLE022"; GEMS_ID="compare40_gemsrag_smoke"; VR_TAG="smoke"
else
    ONLY=""; GEMS_ID="compare40_gemsrag_v1"; VR_TAG="v1"
fi

echo "job $SLURM_JOB_ID | mode $COMPARE40_MODE | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
nvidia-smi -L || true
cd "$REPO"

# VINE's evidence file, named by VINE's own code (evaluation/vine_run.py)
KQ_NAME="$("$RETR_ENV/bin/python" - "$REPO" "$MRAG_BASE_DIR" <<'PY'
import sys
repo, base = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo + "/evaluation")
import vine_run as vr
print(f"kq_r{vr.retrieval_commit(repo)}_s{vr.store_tag(base)}.json")
PY
)"
KQ="$MRAG_BASE_DIR/parser_runs_faster/$KQ_NAME"
echo "VINE evidence file: $KQ"
case "$KQ_NAME" in
    kq_r4299665_s*) ;;
    *) echo "STOPPED: VINE's retrieval code here is not the 17 Oct one (r4299665): $KQ_NAME"; exit 1 ;;
esac

echo; echo "===== 1. VINE's retrieval for the 40 questions ====="
VINE_QUESTIONS="$REPO/compare40/questions_40.json" VINE_PARSER="" VINE_REPEAT="" VINE_PROBE="" VINE_DEV_ONLY="" \
    "$RETR_ENV/bin/python" -u hprc/vine_hprc.py retrieval

echo; echo "===== 2. VINE as plain RAG (in the background; log: $OUT/vine_rag_$VR_TAG.log) ====="
echo "----- job $SLURM_JOB_ID, $(date '+%Y-%m-%d %H:%M:%S') -----" >> "$OUT/vine_rag_$VR_TAG.log"
"$RETR_ENV/bin/python" -u compare40/run_vine_rag.py --kq "$KQ" $ONLY --tag "$VR_TAG" >> "$OUT/vine_rag_$VR_TAG.log" 2>&1 &
VR_PID=$!

echo; echo "===== 3. GEMS-RAG as it is ====="
set +e
"$RETR_ENV/bin/python" -u compare40/run_gems_rag.py $ONLY --run-id "$GEMS_ID"
GEMS_RC=$?
wait "$VR_PID"
VR_RC=$?
set -e

echo; echo "===== VINE as plain RAG: the end of its log ====="
tail -n 25 "$OUT/vine_rag_$VR_TAG.log"
echo; echo "GEMS-RAG exit $GEMS_RC | VINE as plain RAG exit $VR_RC | $(date '+%Y-%m-%d %H:%M:%S')"
[ "$GEMS_RC" = 0 ] && [ "$VR_RC" = 0 ]
