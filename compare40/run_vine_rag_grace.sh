#!/bin/bash
# compare40/run_vine_rag_grace.sh -- submit "VINE as plain RAG" on Grace, for any question file.
#
#   bash compare40/run_vine_rag_grace.sh ACCOUNT QUESTIONS_FILE [MAX_IMAGES]
#
#   ACCOUNT         your project account number (the `myproject` command shows it; Grace: 132692299628)
#   QUESTIONS_FILE  {id: question text}, the same file VINE's retrieval stage read
#                   (VINE_QUESTIONS), so every question already has VINE's evidence
#   MAX_IMAGES      optional, 1 to 20: VINE's figure pictures a question, in VINE's order
#                   (default 4, VINE's checkers' limit; then nothing changes). With another
#                   number the answers go to their own file (TAG ends in _img<N>), and
#                   before submitting this prints how many pictures the questions have.
#
# The system is the one of the 40-question comparison (compare40/README.md, system 2):
# VINE's own evidence (Kq), whole, given to the answer model in ONE call with GEMS-RAG's
# answer prompt. No plan-maker, no checker. compare40/run_vine_rag.py does the work and is
# not changed; this launcher only runs it on Grace with Sonnet 5.5 alone.
#
# The evidence is full VINE's own file, kq_r4299665_s0c3805.json, and nothing else. Before
# anything is submitted, this script checks that every question is in it with exactly the
# same text and that every image it names exists.
#
# API calls only, so the job asks for no GPU: 2 CPUs, 16 GB, the `short` CPU partition,
# 2 hours. On the 40 questions Sonnet took 14 s a question (median).
# The log is $SCRATCH/vine/logs/vine_rag_TAG_JOBID.log and the answers
# $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_TAG.jsonl, where TAG is
# "sonnet_" + the question file's name (+ "_img<N>" with MAX_IMAGES). The same command again answers only the
# questions that have no answer yet. The key is always read from $VINE_HOME/anthropic_key.
set -euo pipefail
USAGE="usage: bash compare40/run_vine_rag_grace.sh ACCOUNT QUESTIONS_FILE [MAX_IMAGES]"
KQ_FILE_NAME="kq_r4299665_s0c3805.json"          # full VINE's evidence file, and no other
[ $# -eq 2 ] || [ $# -eq 3 ] || { echo "$USAGE"; exit 1; }
ACCT="$1"
QFILE="$2"
IMAGES="${3:-4}"
[[ "$ACCT" =~ ^[0-9]+$ ]] || { echo "ACCOUNT must be a number: $ACCT"; exit 1; }
[[ "$IMAGES" =~ ^[0-9]+$ ]] && [ "$IMAGES" -ge 1 ] && [ "$IMAGES" -le 20 ] || { echo "MAX_IMAGES must be 1 to 20: $IMAGES"; exit 1; }
IMAGES=$((10#$IMAGES))
QDIR="$(cd "$(dirname "$QFILE")" 2>/dev/null && pwd)" || { echo "no such folder: $(dirname "$QFILE")"; exit 1; }
QFILE="$QDIR/$(basename "$QFILE")"
[ -f "$QFILE" ] && [ -s "$QFILE" ] || { echo "the question file is missing or empty: $QFILE"; exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$QFILE$REPO" != *,* ]] || { echo "the paths must not contain a comma: $QFILE $REPO"; exit 1; }
source "$REPO/hprc/env.sh"
case "$QFILE" in
    "$SCRATCH"/*) ;;
    *) echo "the question file must be under \$SCRATCH (the compute node must see it): $QFILE"; exit 1 ;;
esac
KQ="$MRAG_BASE_DIR/parser_runs_faster/$KQ_FILE_NAME"
[ -x "$RETR_ENV/bin/python" ] || { echo "the retrieval environment is missing: $RETR_ENV"; exit 1; }
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
[ -s "$MRAG_BASE_DIR/mmrag_cache_v3/figures.jsonl" ] || { echo "VINE's figure records are missing: $MRAG_BASE_DIR/mmrag_cache_v3/figures.jsonl"; exit 1; }
[ -s "$KQ" ] || { echo "full VINE's evidence file is missing: $KQ"; exit 1; }
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- compare40/run_vine_rag.py gems_rag/mrag)" ]; then
    echo "run_vine_rag.py or gems_rag/mrag is changed in $REPO: the prompt would not be the 40-question one"; exit 1
fi
"$RETR_ENV/bin/python" -I - "$QFILE" "$KQ" "$IMAGES" <<'PY' || exit 1
import json, os, sys
try:
    q = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    sys.exit(f"the question file is not JSON: {e}")
if not isinstance(q, dict) or not q or not all(isinstance(v, str) and v.strip() for v in q.values()):
    sys.exit("the question file must be {id: question text}")
kq = json.load(open(sys.argv[2], encoding="utf-8"))
absent = [i for i in q if i not in kq]
other = [i for i in q if i in kq and kq[i].get("question") != q[i]]
images = [p for i in q if i in kq for f in (kq[i].get("figures") or [])
          for p in (f.get("image_paths") or [f.get("image_path")]) if p and not os.path.exists(p)]
if absent or other or images:
    sys.exit(f"STOPPED: not in the evidence file {len(absent)} {absent[:5]}; other text {len(other)} {other[:5]}; "
             f"image files missing {len(images)} {images[:3]}")
print(f"question file: {len(q)} questions, {next(iter(q))} ... {list(q)[-1]}; all in "
      f"{os.path.basename(sys.argv[2])} with the same text; every image found")
cap = int(sys.argv[3])
if cap != 4:
    n = sorted(len([p for f in (kq[i].get("figures") or []) for p in (f.get("image_paths") or [f.get("image_path")]) if p])
               for i in q)
    print(f"figure pictures a question: {n[0]} to {n[-1]} (median {n[len(n) // 2]}); more than 4 in {sum(x > 4 for x in n)}, "
          f"more than {cap} in {sum(x > cap for x in n)} (those send their first {cap})")
PY
STEM="$(basename "$QFILE" .json)"
TAG="sonnet_${STEM//[^A-Za-z0-9_]/_}"
[ "$IMAGES" -eq 4 ] || TAG="${TAG}_img$IMAGES"
# two of these jobs would ask (and pay for) every question twice
sq=$(squeue -h -u "$USER" -o "%i %j") || { echo "squeue failed; try again in a minute"; exit 1; }
other=$(grep -E " vine_rag_" <<<"$sq" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
unset ANTHROPIC_API_KEY                          # the job reads the key file, never this shell's key
id=$(sbatch --parsable --account="$ACCT" --job-name="vine_rag_$TAG" --partition=short \
     --export="ALL,VINE_REPO=$REPO,VR_QUESTIONS=$QFILE,VR_TAG=$TAG,VR_KQ=$KQ,VR_IMAGES=$IMAGES" \
     --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=16G --time=02:00:00 \
     --output="$LOG/vine_rag_${TAG}_%j.log" compare40/vine_rag_job.slurm)
id="${id%%;*}"
if ! [[ "$id" =~ ^[0-9]+$ ]]; then
    echo "Slurm did not return a job number. Look with  squeue -u $USER  before submitting again." >&2
    exit 1
fi
echo "job $id  (VINE as plain RAG, Sonnet 5.5, up to $IMAGES figure pictures a question, tag $TAG, time limit 2 h)"
echo "watch it:  tail -f $LOG/vine_rag_${TAG}_$id.log"
