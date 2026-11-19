#!/bin/bash
# compare40/vine_rag_job.slurm -- "VINE as plain RAG" with Sonnet 5.5, on a CPU node.
# Submitted by compare40/run_vine_rag_grace.sh (which sets the account, partition, time,
# log, VR_QUESTIONS, VR_TAG and VR_KQ). Not meant to be submitted by hand.
#
# It reads full VINE's existing evidence file; it does not run retrieval. It stops if
# that file is not kq_r4299665_s0c3805.json, as named by VINE's own code here, so the
# evidence is exactly what full VINE's plan-maker and checkers read for these questions.
#SBATCH --job-name=vine_rag
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${VR_QUESTIONS:?VR_QUESTIONS is not set -- submit with compare40/run_vine_rag_grace.sh}"
: "${VR_TAG:?VR_TAG is not set -- submit with compare40/run_vine_rag_grace.sh}"
: "${VR_KQ:?VR_KQ is not set -- submit with compare40/run_vine_rag_grace.sh}"

echo "job $SLURM_JOB_ID | tag $VR_TAG | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"

# a second job would ask (and pay for) every question again
sq=$(squeue -h -u "$USER" -t RUNNING -o "%i %j") || { echo "STOPPED: squeue failed"; exit 1; }
dup=$(grep -E " vine_rag_" <<<"$sq" | grep -v "^$SLURM_JOB_ID " || true)
[ -z "$dup" ] || { echo "STOPPED: another vine_rag job is running:"; echo "$dup"; exit 1; }

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
module load WebProxy                         # the answer model is called over the API
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key (\$VINE_HOME/anthropic_key)"; exit 1; }
ANTHROPIC_API_KEY="$(cat "$VINE_HOME/anthropic_key")"
export ANTHROPIC_API_KEY

echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- compare40/run_vine_rag.py gems_rag/mrag)" ]; then
    echo "STOPPED: run_vine_rag.py or gems_rag/mrag is changed locally"; exit 1
fi
echo "code sha256: run_vine_rag.py $(sha256sum "$REPO/compare40/run_vine_rag.py" | cut -c1-12)" \
     "| gems_rag/mrag/vlm.py $(sha256sum "$REPO/gems_rag/mrag/vlm.py" | cut -c1-12)"
echo "questions $VR_QUESTIONS | sha256 $(sha256sum "$VR_QUESTIONS" | cut -c1-12)"
cd "$REPO"

# VINE's evidence file, named by VINE's own code (evaluation/vine_run.py)
KQ_NAME="$("$RETR_ENV/bin/python" - "$REPO" "$MRAG_BASE_DIR" <<'PY'
import sys
repo, base = sys.argv[1], sys.argv[2]
sys.path.insert(0, repo + "/evaluation")
import vine_run as vr
print(f"kq_r{vr.retrieval_commit(repo)}_s{vr.store_tag(base)}.json")
PY
)"
KQ="$MRAG_BASE_DIR/parser_runs_faster/$KQ_NAME"
echo "VINE evidence file: $KQ"
case "$KQ_NAME" in
    kq_r4299665_s0c3805.json) ;;
    *) echo "STOPPED: this is not full VINE's evidence file (kq_r4299665_s0c3805.json): $KQ_NAME"; exit 1 ;;
esac
[ "$KQ" = "$VR_KQ" ] || { echo "STOPPED: the launcher checked $VR_KQ, not $KQ"; exit 1; }
[ -s "$KQ" ] || { echo "STOPPED: VINE's evidence file is missing: $KQ"; exit 1; }
echo "evidence sha256 $(sha256sum "$KQ" | cut -c1-12)"

echo; echo "===== VINE as plain RAG, Sonnet 5.5 ====="
set +e
"$RETR_ENV/bin/python" -u compare40/run_vine_rag.py --kq "$KQ" --questions "$VR_QUESTIONS" \
    --models claude-sonnet-5-5 --tag "$VR_TAG"
RC=$?
set -e
echo; echo "VINE as plain RAG exit $RC | $(date '+%Y-%m-%d %H:%M:%S')"
exit "$RC"
