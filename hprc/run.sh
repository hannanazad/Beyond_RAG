#!/bin/bash
# hprc/run.sh -- submit the VINE run on FASTER: three Slurm jobs, each starting
# only when the one before it finished well.
#
#   bash hprc/run.sh ACCOUNT [GPUS] [FIRST_STAGE]
#
#   ACCOUNT      your project account number (the `myproject` command shows it)
#   GPUS         A100s for the parse stage (default 8; at most 10)
#   FIRST_STAGE  retrieval (default), parse or execute: start from there
#
#   retrieval : 1 A100, the retrieval check on 154 DEV cases (the gate) + Kq
#   parse     : GPUS A100s, one parser server on each, the plans
#   execute   : 1 A100, the checkers (Anthropic API) + the answers
#
# A job that stops cancels the jobs after it. Every stage carries on where it
# stopped, so after a fix, submit again from that stage.
set -euo pipefail
ACCT="${1:?usage: bash hprc/run.sh ACCOUNT [GPUS] [FIRST_STAGE]}"
NGPU="${2:-8}"
FIRST="${3:-retrieval}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"

[ -f "$VINE_HOME/.done_models" ] || { echo "the setup has not finished -- run hprc/setup.sh first"; exit 1; }
case "$FIRST" in retrieval|parse|execute) ;; *) echo "FIRST_STAGE must be retrieval, parse or execute"; exit 1 ;; esac
if [ ! -s "$VINE_HOME/anthropic_key" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "the Anthropic key is missing; save it once with (it asks for the key, it is not shown):"
    echo '  read -rs -p "Anthropic key: " K; echo; printf "%s" "$K" > $SCRATCH/vine/anthropic_key; chmod 600 $SCRATCH/vine/anthropic_key; unset K'
    exit 1
fi
[ "$NGPU" -ge 1 ] && [ "$NGPU" -le 10 ] || { echo "GPUS must be 1 to 10"; exit 1; }
CPUS=$(( NGPU * 4 )); MEM=$(( NGPU * 24 + 16 )); [ "$MEM" -le 240 ] || MEM=240

cd "$REPO"
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
EXPORT="ALL,VINE_REPO=$REPO,VINE_QUESTIONS=${VINE_QUESTIONS:-}"
dep=()
submit() {   # stage gpus cpus mem time
    local id
    id=$(sbatch --parsable --account="$ACCT" --job-name="vine_$1" --export="$EXPORT,STAGE=$1" \
         --gres="gpu:a100:$2" --cpus-per-task="$3" --mem="$4G" --time="$5" \
         --output="$LOG/vine_$1_%j.log" "${dep[@]}" hprc/vine_job.slurm)
    echo "  $1: job $id  (log: $LOG/vine_$1_$id.log)" >&2
    dep=(--dependency="afterok:$id" --kill-on-invalid-dep=yes)
    echo "$id"
}
echo "submitting (account $ACCT, $NGPU GPUs for the parser), from the $FIRST stage:"
started=0
for st in retrieval parse execute; do
    [ "$st" = "$FIRST" ] && started=1
    [ "$started" = 1 ] || continue
    case "$st" in
        retrieval) submit retrieval 1 8 64 03:00:00 >/dev/null ;;
        parse)     submit parse "$NGPU" "$CPUS" "$MEM" 04:00:00 >/dev/null ;;
        execute)   submit execute 1 8 64 03:00:00 >/dev/null ;;
    esac
done
echo
echo "watch them : squeue -u $USER"
echo "read a log : tail -f $LOG/vine_<stage>_<job>.log"
