#!/bin/bash
# vine2/check_job.slurm -- stage B of VINE answer-then-check: the checker (Claude Sonnet 5.5).
# Submitted by vine2/run_vine2_grace.sh, to start after stage A. Not meant to be submitted
# by hand. CPU only: the checker is called over the API.
#SBATCH --job-name=vine2_check
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${V2_QUESTIONS:?submit with vine2/run_vine2_grace.sh}"
: "${V2_STEM:?submit with vine2/run_vine2_grace.sh}"
: "${V2_KQ:?submit with vine2/run_vine2_grace.sh}"

echo "job $SLURM_JOB_ID | stage B (checker) | $V2_STEM | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
# a second checker job on the same answers would ask (and pay for) every question again
sq=$(squeue -h -u "$USER" -t RUNNING -o "%i %j") || { echo "STOPPED: squeue failed"; exit 1; }
dup=$(grep -E " vine2_check_" <<<"$sq" | grep -v "^$SLURM_JOB_ID " || true)
[ -z "$dup" ] || { echo "STOPPED: another vine2 checker job is running:"; echo "$dup"; exit 1; }

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
module load WebProxy                         # the checker is called over the API
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key (\$VINE_HOME/anthropic_key)"; exit 1; }
ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
export ANTHROPIC_API_KEY

echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- vine2 mrag/vine/anthropic_client.py)" ]; then
    echo "STOPPED: vine2 or the Anthropic client is changed locally"; exit 1
fi
for f in vine2/core.py vine2/check.py; do
    git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1 || { echo "STOPPED: $f is not committed"; exit 1; }
done
echo "code sha256: core.py $(sha256sum "$REPO/vine2/core.py" | cut -c1-12)" \
     "| check.py $(sha256sum "$REPO/vine2/check.py" | cut -c1-12)"
echo "questions $V2_QUESTIONS | sha256 $(sha256sum "$V2_QUESTIONS" | cut -c1-12)"
echo "evidence $V2_KQ | sha256 $(sha256sum "$V2_KQ" | cut -c1-12)"
DRAFTS="$MRAG_BASE_DIR/compare40_runs/vine_rag/answers_qwen_$V2_STEM.jsonl"
if [ -s "$DRAFTS" ]; then
    echo "drafts $DRAFTS | $(wc -l < "$DRAFTS") lines"
else
    echo "STOPPED: no drafts file ($DRAFTS): stage A gave no answers. Look at stage A's log,"
    echo "then run the same launcher command again."
    exit 1
fi
cd "$REPO"
set +e
ONLY=()
[ -z "${V2_ONLY:-}" ] || { ONLY=(--only "$V2_ONLY"); echo "only these questions: $V2_ONLY"; }
"$RETR_ENV/bin/python" -u vine2/check.py --kq "$V2_KQ" --questions "$V2_QUESTIONS" \
    --drafts "$DRAFTS" --tag "$V2_STEM" "${ONLY[@]}"
RC=$?
set -e
echo; echo "stage B exit $RC | $(date '+%Y-%m-%d %H:%M:%S')"
exit "$RC"
