#!/bin/bash
# compare40/run_visrag_grace.sh -- the VisRAG baseline on Grace, for any question file.
#
#   bash compare40/run_visrag_grace.sh ACCOUNT QUESTIONS_FILE [PAGES]
#
#   ACCOUNT         your project account number (Grace: 132692299628)
#   QUESTIONS_FILE  {id: question text}, under $SCRATCH
#   PAGES           page images sent to the answer model for each question, 1 to 20
#                   (default 20, the better setting on the 40 questions)
#
# The system is the one of the 40-question VisRAG run (compare40/run_visrag.sh, 13 Nov):
# VisRAG-Ret ranks the 1,162 MUTCD pages for each question, and the top PAGES page images
# go to Sonnet 5.5 in ONE call with GEMS-RAG's answer prompt. No text pieces, no plan, no
# checker. compare40/visrag_retrieve.py and compare40/run_visrag.py do the work and are
# not changed; this launcher only runs them for another question file, in two jobs:
#   1. retrieval (1 A100, gpu partition, up to 2 h): ranks the pages for every question.
#      The page vectors made in the 40-question run are copied and reused (they are named
#      by the model commit and checked by shape), so only the questions are encoded.
#      Skipped when a retrieval for exactly these question texts is already there.
#   2. answers (CPU, medium partition, up to 10 h, after job 1 ended without error): one
#      Sonnet call a question. API calls only, so no GPU waits on them.
# Output, with STEM the question file's name without .json:
#   $SCRATCH/Beyond_RAG/compare40_runs/visrag/retrieval_STEM/   (ranked pages)
#   $SCRATCH/Beyond_RAG/compare40_runs/visrag/answers_pPAGES_STEM.jsonl   (the answers)
# The 40-question files (retrieval/, answers_p5_v1.jsonl, answers_p20_v1.jsonl) are not
# touched. The same command again does only what is not done yet. The key is always read
# from $VINE_HOME/anthropic_key.
set -euo pipefail
USAGE="usage: bash compare40/run_visrag_grace.sh ACCOUNT QUESTIONS_FILE [PAGES]"
[ $# -ge 2 ] && [ $# -le 3 ] || { echo "$USAGE"; exit 1; }
ACCT="$1"; QFILE="$2"; PAGES="${3:-20}"
[[ "$ACCT" =~ ^[0-9]+$ ]] || { echo "ACCOUNT must be a number: $ACCT"; exit 1; }
[[ "$PAGES" =~ ^[0-9]+$ ]] && [ "$((10#$PAGES))" -ge 1 ] && [ "$((10#$PAGES))" -le 20 ] || { echo "PAGES must be 1 to 20"; exit 1; }
PAGES=$((10#$PAGES))                            # "08" -> 8, as run_visrag.py names its file
QDIR="$(cd "$(dirname "$QFILE")" 2>/dev/null && pwd)" || { echo "no such folder: $(dirname "$QFILE")"; exit 1; }
QFILE="$QDIR/$(basename "$QFILE")"
[ -f "$QFILE" ] && [ -s "$QFILE" ] || { echo "the question file is missing or empty: $QFILE"; exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$QFILE$REPO" != *,* ]] || { echo "the paths must not contain a comma: $QFILE $REPO"; exit 1; }
source "$REPO/hprc/env.sh"
case "$QFILE" in
    "$SCRATCH"/*) ;;
    *) echo "the question file must be under \$SCRATCH (the compute nodes must see it): $QFILE"; exit 1 ;;
esac
[ -x "$VINE_HOME/envs/visrag/bin/python" ] || { echo "the VisRAG environment is missing: run  bash compare40/visrag_setup.sh"; exit 1; }
[ -s "$VINE_HOME/visrag_ret_revision" ] || { echo "VisRAG-Ret is not downloaded: run  bash compare40/visrag_setup.sh"; exit 1; }
[ -s "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" ] || { echo "the MUTCD PDF is missing: $MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"; exit 1; }
[ -x "$RETR_ENV/bin/python" ] || { echo "the retrieval environment is missing: $RETR_ENV"; exit 1; }
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
GUARDED="compare40/run_visrag.py compare40/visrag_retrieve.py compare40/run_gems_rag.py gems_rag/mrag
         compare40/run_visrag_grace.sh compare40/visrag_retrieve_job.slurm compare40/visrag_answer_job.slurm"
# shellcheck disable=SC2086
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- $GUARDED)" ]; then
    echo "the VisRAG code or GEMS-RAG is changed locally in $REPO: undo it first (git checkout -- FILE),"
    echo "so the run is exactly the pushed code"; exit 1
fi
for f in compare40/run_visrag_grace.sh compare40/visrag_retrieve_job.slurm compare40/visrag_answer_job.slurm; do
    git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1 \
        || { echo "$f is not committed in $REPO: pull the pushed code first"; exit 1; }
done
STEM="$(basename "$QFILE" .json)"; STEM="${STEM//[^A-Za-z0-9_]/_}"
[ "$STEM" != "v1" ] && [ "$STEM" != "smoke" ] || { echo "a question file named $STEM.json would mix with the 40-question files"; exit 1; }
OUT="$MRAG_BASE_DIR/compare40_runs/visrag"
RETR="$OUT/retrieval_$STEM"
# the question file, and whether a retrieval for exactly these texts is there already
NEED_RETR=$("$RETR_ENV/bin/python" -I - "$QFILE" "$RETR" "$PAGES" <<'PY'
import hashlib, json, os, sys
try:
    q = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    sys.exit(f"the question file is not JSON: {e}")
if not isinstance(q, dict) or not q or not all(isinstance(v, str) and v.strip() for v in q.values()):
    sys.exit("the question file must be {id: question text}, and nothing else")
retr = sys.argv[2]
have = {}
try:
    man = json.load(open(os.path.join(retr, "retrieval_manifest.json"), encoding="utf-8"))
    if not man.get("dry_run") and int(man.get("save_top", 0)) >= int(sys.argv[3]):
        for line in open(os.path.join(retr, "retrieval.jsonl"), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                have[r["question_id"]] = r.get("question_sha256")
except (FileNotFoundError, ValueError, KeyError):
    have = {}
missing = [i for i in q if have.get(i) != hashlib.sha256(q[i].encode()).hexdigest()]
print(f"question file: {len(q)} questions, {next(iter(q))} ... {list(q)[-1]}; "
      f"VisRAG retrieval already there for {len(q) - len(missing)}", file=sys.stderr)
print("yes" if missing else "no")
PY
)
# two of these jobs would write the same files, and pay twice
sq=$(squeue -h -u "$USER" -o "%i %j") || { echo "squeue failed; try again in a minute"; exit 1; }
other=$(grep -E " visrag_| compare40_visrag" <<<"$sq" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
unset ANTHROPIC_API_KEY                          # the answer job reads the key file, never this shell's key
EXP="ALL,VINE_REPO=$REPO,VISRAG_QUESTIONS=$QFILE,VISRAG_STEM=$STEM,VISRAG_PAGES=$PAGES"
DEP=""
if [ "$NEED_RETR" = "yes" ]; then
    r=$(sbatch --parsable --account="$ACCT" --job-name="visrag_retr_$STEM" --partition=gpu \
         --export="$EXP" --gres="gpu:a100:1" --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=64G --time=02:00:00 \
         --output="$LOG/visrag_retr_${STEM}_%j.log" compare40/visrag_retrieve_job.slurm)
    r="${r%%;*}"
    [[ "$r" =~ ^[0-9]+$ ]] || { echo "Slurm did not return a job number for the retrieval. Look with  squeue -u $USER" >&2; exit 1; }
    DEP="--dependency=afterok:$r"
    echo "1. retrieval (1 A100, up to 2 h): job $r"
    echo "   watch:  tail -f $LOG/visrag_retr_${STEM}_$r.log"
    echo "   (if it fails, Slurm cancels job 2 by itself)"
else
    echo "1. retrieval: already there for every question, not submitted"
fi
# shellcheck disable=SC2086
a=$(sbatch --parsable --account="$ACCT" --job-name="visrag_answer_$STEM" --partition=medium $DEP --kill-on-invalid-dep=yes \
     --export="$EXP" --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G --time=10:00:00 \
     --output="$LOG/visrag_answer_${STEM}_%j.log" compare40/visrag_answer_job.slurm)
a="${a%%;*}"
if ! [[ "$a" =~ ^[0-9]+$ ]]; then
    echo "Slurm did not return a job number for the answers. Look with  squeue -u $USER" >&2
    echo "When the retrieval (if any) is done, the same command submits only the answers." >&2
    exit 1
fi
echo "2. answers (CPU, ${DEP:+after the retrieval ends without error, }up to 10 h, $PAGES pages a question): job $a"
echo "   watch:  tail -f $LOG/visrag_answer_${STEM}_$a.log"
echo "   answers -> $OUT/answers_p${PAGES}_$STEM.jsonl"
