#!/bin/bash
# hprc/run.sh -- submit the VINE run on FASTER: three Slurm jobs, each starting
# only when the one before it finished well.
#
#   bash hprc/run.sh ACCOUNT [GPUS] [FIRST_STAGE] [alibaba|api]
#   bash hprc/run.sh ACCOUNT GPUS repeat NAME [alibaba|api]
#   bash hprc/run.sh ACCOUNT 4 probe NAME
#
#   ACCOUNT      your project account number (the `myproject` command shows it)
#   GPUS         A100s for the parse stage (default 8; at most 10)
#   FIRST_STAGE  retrieval (default), parse or execute: start from there
#   alibaba      the plans are written by Qwen3.8-Max over the Alibaba Cloud
#                Model Studio API, not by the Qwen servers: the parse stage takes
#                1 GPU and no servers, and every stage of this call uses that
#                plan-writer's run folder. Give the word again when submitting a
#                later stage of that run. The key: $SCRATCH/vine/alibaba_key; its
#                region: VINE_ALIBABA_REGION or $SCRATCH/vine/alibaba_region
#                (singapore if neither; see hprc/README.md).
#   api          the same, with the checkers' own model (Claude Sonnet 5.5) writing
#                the plans: a comparison run only, not the setup.
#   repeat NAME [alibaba|api]  the repeat test. With alibaba or api: every question
#                planned again by that API model and answered, with empty reply
#                caches (parse + execute).
#                Without: the parse stage only, the 11 DEV questions,
#                into parser_runs_faster/repeat_NAME/ with its own empty model
#                cache (so every reply is a new model call). Then compare:
#                $SCRATCH/vine/envs/retrieval/bin/python hprc/compare_plans.py NAME
#   probe NAME   do servers started separately give the same reply? One job on
#                4 GPUs (hprc/repeat_probe.py, with hprc/pin_tuning); the result
#                is at the end of its log, and in parser_runs_faster/probe_NAME/
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
REPEAT=""
PROBE=""
PARSER=""
case "$FIRST" in
    retrieval|parse|execute)
        case "${4:-}" in
            "") ;;
            alibaba|api) PARSER="$4" ;;
            *) echo "the 4th word may only be alibaba (plans by Qwen3.8-Max over the API) or api: bash hprc/run.sh ACCOUNT 1 parse alibaba"; exit 1 ;;
        esac ;;
esac
if [ "$FIRST" = probe ]; then
    PROBE="${4:-}"
    [[ "$PROBE" =~ ^[A-Za-z0-9_-]{1,40}$ ]] || { echo "usage: bash hprc/run.sh ACCOUNT 4 probe NAME   (NAME: letters, digits, - and _ only)"; exit 1; }
    [ "$NGPU" = 4 ] || { echo "the probe uses exactly 4 GPUs: bash hprc/run.sh ACCOUNT 4 probe $PROBE"; exit 1; }
fi
if [ "$FIRST" = repeat ]; then
    REPEAT="${4:-}"
    [[ "$REPEAT" =~ ^[A-Za-z0-9_-]{1,40}$ ]] || { echo "usage: bash hprc/run.sh ACCOUNT GPUS repeat NAME   (NAME: letters, digits, - and _ only)"; exit 1; }
    [ -z "${VINE_QUESTIONS:-}" ] || { echo "a repeat run never takes VINE_QUESTIONS -- unset it first"; exit 1; }
    case "${5:-}" in
        "") ;;
        alibaba|api) PARSER="$5" ;;
        *) echo "the 5th word may only be alibaba or api: bash hprc/run.sh ACCOUNT 1 repeat NAME alibaba"; exit 1 ;;
    esac
fi
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"

[ -f "$VINE_HOME/.done_models" ] || { echo "the setup has not finished -- run hprc/setup.sh first"; exit 1; }
case "$FIRST" in retrieval|parse|execute|repeat|probe) ;; *) echo "FIRST_STAGE must be retrieval, parse, execute, repeat or probe"; exit 1 ;; esac
if { [ -z "$REPEAT$PROBE" ] || [ -n "$PARSER" ]; } && [ ! -s "$VINE_HOME/anthropic_key" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "the Anthropic key is missing; save it once with (it asks for the key, it is not shown):"
    echo '  read -rs -p "Anthropic key: " K; echo; printf "%s" "$K" > $SCRATCH/vine/anthropic_key; chmod 600 $SCRATCH/vine/anthropic_key; unset K'
    exit 1
fi
REGION=""
if [ "$PARSER" = alibaba ]; then
    if [ "$FIRST" != execute ] && [ ! -s "$VINE_HOME/alibaba_key" ] && [ -z "${DASHSCOPE_API_KEY:-}" ]; then
        echo "the Model Studio (Alibaba) key is missing; save it once with (it asks for the key, it is not shown):"
        echo '  read -rs -p "Model Studio key: " K; echo; printf "%s" "$K" > $SCRATCH/vine/alibaba_key; chmod 600 $SCRATCH/vine/alibaba_key; unset K'
        exit 1
    fi
    REGION="${VINE_ALIBABA_REGION:-}"
    if [ -z "$REGION" ] && [ -s "$VINE_HOME/alibaba_region" ]; then REGION="$(tr -d '[:space:]' < "$VINE_HOME/alibaba_region")"; fi
    REGION="${REGION,,}"
    case "$REGION" in
        ""|singapore|us|beijing|hongkong) ;;
        *) echo "the Model Studio region '$REGION' is not one of singapore, us, beijing, hongkong"; exit 1 ;;
    esac
    echo "Model Studio region: ${REGION:-singapore}  (the region the key was made in; see hprc/README.md)"
fi
[ "$NGPU" -ge 1 ] && [ "$NGPU" -le 10 ] || { echo "GPUS must be 1 to 10"; exit 1; }
CPUS=$(( NGPU * 4 )); MEM=$(( NGPU * 24 + 16 )); [ "$MEM" -le 240 ] || MEM=240

cd "$REPO"
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
# VINE_REPEAT and VINE_PARSER are always set (empty for a normal run), so a value
# left in this shell can never turn a normal run into a repeat run or an API run
EXPORT="ALL,VINE_REPO=$REPO,VINE_QUESTIONS=${VINE_QUESTIONS:-},VINE_REPEAT=$REPEAT,VINE_PROBE=$PROBE,VINE_PARSER=$PARSER,VINE_ALIBABA_REGION=$REGION"
dep=()
submit() {   # stage gpus cpus mem time
    local id
    id=$(sbatch --parsable --account="$ACCT" --job-name="vine_$1" --export="$EXPORT,STAGE=$1" \
         --gres="gpu:a100:$2" --cpus-per-task="$3" --mem="$4G" --time="$5" \
         --output="$LOG/vine_$1_%j.log" "${dep[@]}" hprc/vine_job.slurm)
    if ! [[ "$id" =~ ^[0-9]+ ]]; then
        echo "  $1: Slurm did not return a job number. The job may still have been made (a 'Socket timed out'" >&2
        echo "  error can do that): look with  squeue -u $USER  before submitting again." >&2
        exit 1
    fi
    echo "  $1: job $id  (log: $LOG/vine_$1_$id.log)" >&2
    dep=(--dependency="afterok:$id" --kill-on-invalid-dep=yes)
    echo "$id"
}
if [ -n "$PROBE" ]; then
    echo "submitting the probe '$PROBE' (account $ACCT, 4 GPUs): 4 servers with the tuning pin, about 25-35 minutes"
    if [ -d "$MRAG_BASE_DIR/parser_runs_faster/probe_$PROBE" ]; then
        echo "probe_$PROBE has been used already -- choose a new NAME"; exit 1
    fi
    submit probe 4 16 112 03:00:00 >/dev/null
    echo
    echo "watch it   : squeue -u $USER"
    echo "read a log : tail -n 30 \$(ls -t $LOG/vine_probe_*.log | head -1)"
    echo "the result is at the end of that log, after the line RESULT"
    exit 0
fi
if [ "$PARSER" = alibaba ]; then PARSE_TIME=04:00:00; else PARSE_TIME=02:00:00; fi
if [ -n "$REPEAT" ] && [ -n "$PARSER" ]; then
    echo "submitting the repeat test '$REPEAT' (account $ACCT): every plan made again by the API model ($PARSER)"
    echo "with an empty reply cache, then answered with an empty checker cache"
    if [ -d "$MRAG_BASE_DIR/parser_runs_faster/repeat_$REPEAT" ]; then
        echo "  note: repeat_$REPEAT already exists -- the jobs carry on in it. For a new test, use a new NAME."
    fi
    submit parse 1 8 64 "$PARSE_TIME" >/dev/null
    submit execute 1 8 64 03:00:00 >/dev/null
    echo
    echo "watch them : squeue -u $USER"
    echo "read a log : tail -n 30 $LOG/vine_<stage>_<job>.log"
    exit 0
fi
if [ -n "$REPEAT" ]; then
    echo "submitting the repeat test '$REPEAT' (account $ACCT, $NGPU GPUs): the 11 DEV plans again"
    if [ -d "$MRAG_BASE_DIR/parser_runs_faster/repeat_$REPEAT" ]; then
        echo "  note: repeat_$REPEAT already exists -- the job carries on in it. For a new test, use a new NAME."
    fi
    submit parse "$NGPU" "$CPUS" "$MEM" 04:00:00 >/dev/null
    echo
    echo "watch it   : squeue -u $USER"
    echo "read a log : tail -n 20 \$(ls -t $LOG/vine_parse_*.log | head -1)"
    echo "when done  : $SCRATCH/vine/envs/retrieval/bin/python hprc/compare_plans.py $REPEAT"
    exit 0
fi
if [ -n "$PARSER" ]; then
    echo "submitting (account $ACCT, plans written by the API model ($PARSER), no parser servers), from the $FIRST stage:"
else
    echo "submitting (account $ACCT, $NGPU GPUs for the parser), from the $FIRST stage:"
fi
started=0
for st in retrieval parse execute; do
    [ "$st" = "$FIRST" ] && started=1
    [ "$started" = 1 ] || continue
    case "$st" in
        retrieval) submit retrieval 1 8 64 03:00:00 >/dev/null ;;
        parse)     if [ -n "$PARSER" ]; then submit parse 1 8 64 "$PARSE_TIME" >/dev/null
                   else submit parse "$NGPU" "$CPUS" "$MEM" 04:00:00 >/dev/null; fi ;;
        execute)   submit execute 1 8 64 03:00:00 >/dev/null ;;
    esac
done
echo
echo "watch them : squeue -u $USER"
echo "read a log : tail -f $LOG/vine_<stage>_<job>.log"
