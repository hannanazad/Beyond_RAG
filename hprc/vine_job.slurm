#!/bin/bash
# hprc/vine_job.slurm -- one stage of the VINE run as a Slurm job.
# Submitted by hprc/run.sh, which sets the stage (STAGE), the GPUs, the time
# and the log file. Not meant to be submitted by hand.
#SBATCH --job-name=vine
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${STAGE:?STAGE is not set -- submit with hprc/run.sh}"

# the models are on disk: never reach for the internet for them
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# the parser's servers are on this machine: never send those requests to a proxy
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1

if [ "$STAGE" = execute ]; then
    module load WebProxy                     # the checkers call the Anthropic API
    export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
    if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -s "$VINE_HOME/anthropic_key" ]; then
        ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
        export ANTHROPIC_API_KEY
    fi
fi

echo "job $SLURM_JOB_ID | stage $STAGE | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
nvidia-smi -L || true
cd "$REPO"
"$RETR_ENV/bin/python" -u "$REPO/hprc/vine_hprc.py" "$STAGE"
