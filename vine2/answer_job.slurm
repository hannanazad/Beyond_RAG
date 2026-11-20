#!/bin/bash
# vine2/answer_job.slurm -- stage A of VINE answer-then-check: the writer (Qwen3.8-27B).
# Submitted by vine2/run_vine2_grace.sh (account, GPUs, time, log, V2_QUESTIONS, V2_STEM,
# V2_KQ). Not meant to be submitted by hand.
#
# Runs compare40/run_qwen_rag.py unchanged: one Qwen server per GPU with its vision part on,
# each question answered from ALL of VINE's evidence with GEMS-RAG's answer prompt and up to
# 4 images. Nothing is sent off the node: no API, no proxy.
#SBATCH --job-name=vine2_answer
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${V2_QUESTIONS:?submit with vine2/run_vine2_grace.sh}"
: "${V2_STEM:?submit with vine2/run_vine2_grace.sh}"
: "${V2_KQ:?submit with vine2/run_vine2_grace.sh}"

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY

echo "job $SLURM_JOB_ID | stage A (writer) | $V2_STEM | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
echo "questions $V2_QUESTIONS | sha256 $(sha256sum "$V2_QUESTIONS" | cut -c1-12)"
echo "evidence $V2_KQ | sha256 $(sha256sum "$V2_KQ" | cut -c1-12)"
echo "code sha256: run_qwen_rag.py $(sha256sum "$REPO/compare40/run_qwen_rag.py" | cut -c1-12)" \
     "| run_vine_rag.py $(sha256sum "$REPO/compare40/run_vine_rag.py" | cut -c1-12)" \
     "| qwen_local.py $(sha256sum "$REPO/compare40/qwen_local.py" | cut -c1-12)"
nvidia-smi -L || true
cd "$REPO"
"$RETR_ENV/bin/python" -u compare40/run_qwen_rag.py --kq "$V2_KQ" --questions "$V2_QUESTIONS" \
    --tag "qwen_$V2_STEM"
