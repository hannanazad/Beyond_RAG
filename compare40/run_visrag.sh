#!/bin/bash
# compare40/run_visrag.sh -- submit the VisRAG baseline on the 40 questions.
#
#   bash compare40/run_visrag.sh ACCOUNT smoke [PAGES]   2 questions (SAMPLE002, SAMPLE022)
#   bash compare40/run_visrag.sh ACCOUNT full  [PAGES]   all 40 questions
#
#   ACCOUNT  your project account number (the `myproject` command shows it; Grace: 132692299628)
#   PAGES    page images sent to the answer model for each question; default 5. 1 to 20.
#
# Once before: bash compare40/visrag_setup.sh (on a login node).
# One job, 1 A100 (VisRAG-Ret needs bfloat16), 8 CPUs, 64 GB. The page vectors are made in
# the first run and reused after that, so the smoke run does most of the GPU work.
# The log is in $SCRATCH/vine/logs/compare40_visrag_MODE_JOBID.log, the answers in
# $SCRATCH/Beyond_RAG/compare40_runs/visrag/answers_pPAGES_v1.jsonl (smoke: _smoke).
# The same command again answers only the questions that have no answer yet.
set -euo pipefail
USAGE="usage: bash compare40/run_visrag.sh ACCOUNT smoke|full [PAGES]"
ACCT="${1:?$USAGE}"
MODE="${2:?$USAGE}"
PAGES="${3:-5}"
case "$MODE" in
    smoke) TIME=02:00:00 ;;
    full)  TIME=03:00:00 ;;
    *) echo "the second word is smoke or full"; exit 1 ;;
esac
[[ "$PAGES" =~ ^[0-9]+$ ]] && [ "$PAGES" -ge 1 ] && [ "$PAGES" -le 20 ] || { echo "PAGES must be 1 to 20"; exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"
VP="$VINE_HOME/envs/visrag/bin/python"
[ -x "$VP" ] || { echo "the VisRAG environment is missing: run  bash compare40/visrag_setup.sh  on a login node"; exit 1; }
[ -s "$VINE_HOME/visrag_ret_revision" ] || { echo "VisRAG-Ret is not downloaded: run  bash compare40/visrag_setup.sh"; exit 1; }
[ -s "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" ] || { echo "the MUTCD PDF is missing: $MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"; exit 1; }
[ -x "$RETR_ENV/bin/python" ] || { echo "the retrieval environment is missing: $RETR_ENV"; exit 1; }
[ -n "${ANTHROPIC_API_KEY:-}" ] || [ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
# two of these jobs would write the same files
other=$(squeue -h -u "$USER" -o "%i %j" 2>/dev/null | grep -E " compare40_visrag" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
id=$(sbatch --parsable --account="$ACCT" --job-name="compare40_visrag_$MODE" \
     --export="ALL,VINE_REPO=$REPO,VISRAG_MODE=$MODE,VISRAG_PAGES=$PAGES" \
     --gres="gpu:a100:1" --cpus-per-task=8 --mem=64G --time="$TIME" \
     --output="$LOG/compare40_visrag_${MODE}_%j.log" compare40/visrag_job.slurm)
if ! [[ "$id" =~ ^[0-9]+ ]]; then
    echo "Slurm did not return a job number. Look with  squeue -u $USER  before submitting again." >&2
    exit 1
fi
echo "job $id  (1 A100, $PAGES pages a question, time limit $TIME)"
echo "watch it:  tail -f $LOG/compare40_visrag_${MODE}_$id.log"
