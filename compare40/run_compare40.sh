#!/bin/bash
# compare40/run_compare40.sh -- submit the 40-question comparison (systems 1 and 2) on FASTER.
#
#   bash compare40/run_compare40.sh ACCOUNT smoke    2 questions (SAMPLE002, SAMPLE022), both models
#   bash compare40/run_compare40.sh ACCOUNT full     all 40 questions, both models
#
#   ACCOUNT  your project account number (the `myproject` command shows it)
#
# One job: 1 A100, 8 CPUs, 64 GB. The log is in $SCRATCH/vine/logs/compare40_MODE_JOBID.log,
# the answers in $SCRATCH/Beyond_RAG/compare40_runs/. Both runs carry on where they
# stopped, so the same command again finishes a run that stopped.
set -euo pipefail
ACCT="${1:?usage: bash compare40/run_compare40.sh ACCOUNT smoke|full}"
MODE="${2:?usage: bash compare40/run_compare40.sh ACCOUNT smoke|full}"
case "$MODE" in
    smoke) TIME=01:30:00 ;;
    full)  TIME=08:00:00 ;;
    *) echo "the second word is smoke or full"; exit 1 ;;
esac
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"
[ -f "$VINE_HOME/.done_models" ] || { echo "the VINE setup has not finished (hprc/setup.sh)"; exit 1; }
D="$SCRATCH/Beyond_RAG/gems_rag"
for f in mmrag_cache_v3/chunks.jsonl mmrag_cache_v3/graph.gpickle mmrag_cache_v3/figures.jsonl qdrant_db/meta.json; do
    [ -s "$D/$f" ] || { echo "GEMS-RAG's data is missing: $D/$f"; exit 1; }
done
for m in models--vidore--colqwen2-v0.1 models--vidore--colqwen2-base; do
    [ -s "$HF_HUB_CACHE/$m/refs/main" ] || { echo "ColQwen2 is missing from $HF_HUB_CACHE ($m)"; exit 1; }
done
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
# both systems open their vector store in local mode, which locks it: one job at a time,
# and not next to a VINE job (wait for the smoke job to end before the full one)
other=$(squeue -h -u "$USER" -o "%i %j" 2>/dev/null | grep -E " (compare40_|vine_)" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
id=$(sbatch --parsable --account="$ACCT" --job-name="compare40_$MODE" \
     --export="ALL,VINE_REPO=$REPO,COMPARE40_MODE=$MODE" \
     --gres="gpu:a100:1" --cpus-per-task=8 --mem=64G --time="$TIME" \
     --output="$LOG/compare40_${MODE}_%j.log" compare40/compare40_job.slurm)
echo "job $id  (log: $LOG/compare40_${MODE}_$id.log)"
echo "watch it:  tail -f $LOG/compare40_${MODE}_$id.log"
