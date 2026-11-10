#!/bin/bash
# compare40/run_qwen_rag.sh -- submit "VINE as plain RAG" with Qwen3.8-27B as the answer model.
#
#   bash compare40/run_qwen_rag.sh ACCOUNT smoke [GPUS]   2 questions (SAMPLE002, SAMPLE022)
#   bash compare40/run_qwen_rag.sh ACCOUNT full  [GPUS]   all 40 questions
#
#   ACCOUNT  your project account number (the `myproject` command shows it)
#   GPUS     A100s: one Qwen server on each, the questions shared among them.
#            Default 4 (full) and 1 (smoke); 1 to 6.
#
# One job: GPUS A100s, 4 CPUs and 24 GB of memory per GPU (as the parser's jobs).
# The log is in $SCRATCH/vine/logs/compare40_qwen_MODE_JOBID.log, the answers in
# $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_qwen_v1.jsonl (smoke: qwen_smoke).
# The same command again answers only the questions that have no answer yet.
set -euo pipefail
USAGE="usage: bash compare40/run_qwen_rag.sh ACCOUNT smoke|full [GPUS]"
ACCT="${1:?$USAGE}"
MODE="${2:?$USAGE}"
case "$MODE" in
    smoke) NGPU="${3:-1}"; TIME=02:00:00 ;;
    full)  NGPU="${3:-4}"; TIME=05:00:00 ;;
    *) echo "the second word is smoke or full"; exit 1 ;;
esac
[[ "$NGPU" =~ ^[1-6]$ ]] || { echo "GPUS must be 1 to 6"; exit 1; }
CPUS=$(( NGPU * 4 )); MEM=$(( NGPU * 24 + 16 ))
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"
[ -f "$VINE_HOME/.done_models" ] || { echo "the VINE setup has not finished (hprc/setup.sh)"; exit 1; }
[ -x "$VLLM_ENV/bin/vllm" ] || { echo "vLLM is missing: $VLLM_ENV/bin/vllm"; exit 1; }
REV="$(sed -n 's/^REVISION = "\([0-9a-f]*\)"$/\1/p' "$REPO/hprc/vine_hprc.py")"
SNAP="$HF_HUB_CACHE/models--Qwen--Qwen3.8-27B-FP8/snapshots/$REV"
[ -s "$SNAP/config.json" ] || { echo "the Qwen model is missing: $SNAP"; exit 1; }
ls "$MRAG_BASE_DIR"/parser_runs_faster/kq_r4299665_s*.json >/dev/null 2>&1 \
    || { echo "VINE's evidence file of the 40 questions is missing (the compare40 job makes it)"; exit 1; }
# two of these jobs would write the same answer files
other=$(squeue -h -u "$USER" -o "%i %j" 2>/dev/null | grep -E " compare40_qwen" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
id=$(sbatch --parsable --account="$ACCT" --job-name="compare40_qwen_$MODE" \
     --export="ALL,VINE_REPO=$REPO,QWEN_RAG_MODE=$MODE" \
     --gres="gpu:a100:$NGPU" --cpus-per-task="$CPUS" --mem="${MEM}G" --time="$TIME" \
     --output="$LOG/compare40_qwen_${MODE}_%j.log" compare40/qwen_rag_job.slurm)
if ! [[ "$id" =~ ^[0-9]+ ]]; then
    echo "Slurm did not return a job number. Look with  squeue -u $USER  before submitting again." >&2
    exit 1
fi
echo "job $id  ($NGPU A100s, time limit $TIME)"
echo "watch it:  tail -f $LOG/compare40_qwen_${MODE}_$id.log"
