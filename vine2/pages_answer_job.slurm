#!/bin/bash
# vine2/pages_answer_job.slurm -- job 2 of VINE answer-then-check on VisRAG's pages: the writer
# (Qwen3.8-27B) answers every question from its page evidence. Submitted by
# vine2/run_vine2_visrag_grace.sh, after job 1. Not meant to be submitted by hand.
#
# Runs vine2/run_qwen_pages.py: compare40/run_qwen_rag.py unchanged (the same servers, settings
# and picture check as stage A of the run on VINE's evidence), each question answered by
# vine2/pages_writer.py. Nothing is sent off the node: no API, no proxy.
#SBATCH --job-name=vine2_answer
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${V2_QUESTIONS:?submit with vine2/run_vine2_visrag_grace.sh}"
: "${V2_STEM:?submit with vine2/run_vine2_visrag_grace.sh}"
: "${V2_KQ:?submit with vine2/run_vine2_visrag_grace.sh}"

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY

echo "job $SLURM_JOB_ID | stage A (writer, VisRAG's pages) | $V2_STEM | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- vine2 compare40/run_qwen_rag.py compare40/qwen_local.py gems_rag/mrag mrag/vine/vllm_client.py hprc/vine_hprc.py hprc/pin_tuning)" ]; then
    echo "STOPPED: vine2, the Qwen runner, GEMS-RAG or the model settings are changed locally"; exit 1
fi
[ -s "$V2_KQ" ] || { echo "STOPPED: no page evidence ($V2_KQ): look at job 1's log"; exit 1; }
echo "questions $V2_QUESTIONS | sha256 $(sha256sum "$V2_QUESTIONS" | cut -c1-12)"
echo "page evidence $V2_KQ | sha256 $(sha256sum "$V2_KQ" | cut -c1-12)"
echo "code sha256: run_qwen_rag.py $(sha256sum "$REPO/compare40/run_qwen_rag.py" | cut -c1-12)" \
     "| run_qwen_pages.py $(sha256sum "$REPO/vine2/run_qwen_pages.py" | cut -c1-12)" \
     "| pages_writer.py $(sha256sum "$REPO/vine2/pages_writer.py" | cut -c1-12)" \
     "| qwen_local.py $(sha256sum "$REPO/compare40/qwen_local.py" | cut -c1-12)"
nvidia-smi -L || true
cd "$REPO"
"$RETR_ENV/bin/python" -u vine2/run_qwen_pages.py --kq "$V2_KQ" --questions "$V2_QUESTIONS" \
    --tag "qwen_$V2_STEM"
