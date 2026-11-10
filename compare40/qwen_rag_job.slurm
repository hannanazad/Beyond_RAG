#!/bin/bash
# compare40/qwen_rag_job.slurm -- VINE as plain RAG with Qwen3.8-27B as the answer model.
# Submitted by compare40/run_qwen_rag.sh (which sets the account, GPUs, time, log and
# QWEN_RAG_MODE). Not meant to be submitted by hand.
#
# It reads VINE's evidence file of the 40 questions (made by the compare40 job on
# 6 Nov) and runs compare40/run_qwen_rag.py: one Qwen server per GPU, vision on, and
# the questions shared among them. Nothing is sent off the node: no API, no proxy.
#SBATCH --job-name=compare40_qwen
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${QWEN_RAG_MODE:?QWEN_RAG_MODE is not set -- submit with compare40/run_qwen_rag.sh}"

# the model is on disk and the servers are on this node: nothing goes to the internet
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

if [ "$QWEN_RAG_MODE" = smoke ]; then
    ONLY="--only SAMPLE002,SAMPLE022"; TAG="qwen_smoke"
else
    ONLY=""; TAG="qwen_v1"
fi

echo "job $SLURM_JOB_ID | mode $QWEN_RAG_MODE | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
nvidia-smi -L || true
cd "$REPO"

# VINE's evidence file, named by VINE's own code (evaluation/vine_run.py), as in compare40_job.slurm
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
[ -s "$KQ" ] || { echo "STOPPED: $KQ is missing (the compare40 job makes it)"; exit 1; }

"$RETR_ENV/bin/python" -u compare40/run_qwen_rag.py --kq "$KQ" $ONLY --tag "$TAG"
