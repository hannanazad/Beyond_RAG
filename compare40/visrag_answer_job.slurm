#!/bin/bash
# compare40/visrag_answer_job.slurm -- job 2 of the VisRAG baseline: Sonnet 5.5 answers each
# question of VISRAG_QUESTIONS from its top VISRAG_PAGES page images (compare40/run_visrag.py,
# unchanged). Submitted by compare40/run_visrag_grace.sh, to start after job 1. CPU only.
#SBATCH --job-name=visrag_answer
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${VISRAG_QUESTIONS:?submit with compare40/run_visrag_grace.sh}"
: "${VISRAG_STEM:?submit with compare40/run_visrag_grace.sh}"
: "${VISRAG_PAGES:?submit with compare40/run_visrag_grace.sh}"
OUT="$MRAG_BASE_DIR/compare40_runs/visrag"
RETR="$OUT/retrieval_$VISRAG_STEM"

echo "job $SLURM_JOB_ID | VisRAG answers | $VISRAG_STEM | $VISRAG_PAGES pages | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
# a second answer job would ask (and pay for) every question again
sq=$(squeue -h -u "$USER" -t RUNNING -o "%i %j") || { echo "STOPPED: squeue failed"; exit 1; }
dup=$(grep -E " visrag_answer_" <<<"$sq" | grep -v "^$SLURM_JOB_ID " || true)
[ -z "$dup" ] || { echo "STOPPED: another VisRAG answer job is running:"; echo "$dup"; exit 1; }
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- compare40/run_visrag.py compare40/run_gems_rag.py gems_rag/mrag)" ]; then
    echo "STOPPED: run_visrag.py or GEMS-RAG is changed locally"; exit 1
fi
echo "questions $VISRAG_QUESTIONS | sha256 $(sha256sum "$VISRAG_QUESTIONS" | cut -c1-12)"
echo "code sha256: run_visrag.py $(sha256sum "$REPO/compare40/run_visrag.py" | cut -c1-12)"
[ -s "$RETR/retrieval.jsonl" ] || { echo "STOPPED: no retrieval in $RETR: look at the retrieval job's log"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
module load WebProxy                         # the answer model is called over the API
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key (\$VINE_HOME/anthropic_key)"; exit 1; }
ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
export ANTHROPIC_API_KEY
cd "$REPO"
set +e
"$RETR_ENV/bin/python" -u compare40/run_visrag.py --retrieval "$RETR" --pages "$VISRAG_PAGES" \
    --questions "$VISRAG_QUESTIONS" --tag "$VISRAG_STEM"
RC=$?
set -e
echo; echo "VisRAG answers exit $RC | $(date '+%Y-%m-%d %H:%M:%S')"
exit "$RC"
