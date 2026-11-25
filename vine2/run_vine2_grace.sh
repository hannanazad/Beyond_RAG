#!/bin/bash
# vine2/run_vine2_grace.sh -- run VINE answer-then-check on Grace, for any question file.
#
#   bash vine2/run_vine2_grace.sh ACCOUNT QUESTIONS_FILE [GPUS [MAX_IMAGES]]
#
#   ACCOUNT         your project account number (Grace: 132692299628)
#   QUESTIONS_FILE  {id: question text}, the same file VINE's retrieval stage read, so every
#                   question already has VINE's evidence in kq_r4299665_s0c3805.json
#   GPUS            A100s for stage A, 1 or 2 (default 2: one Grace node)
#   MAX_IMAGES      optional, 1 to 20: VINE's figure pictures a question, in VINE's order,
#                   for the writer and the checker (default 4, VINE's checkers' limit; then
#                   nothing changes). With another number STEM ends in _img<N>, so the
#                   drafts, the run folder and the job names are its own; before submitting
#                   this prints how many pictures the questions have.
#   V2_ONLY=VQ001,VQ002 (optional, in front of the command): stage B checks only these questions.
#                   Stage A is skipped if these have drafts; if not, it answers every question
#                   still without a draft, so the drafts file is always whole.
#
# Two jobs, the second waiting for the first:
#   A. the writer: Qwen3.8-27B on our own GPUs answers every question from ALL of VINE's
#      evidence (compare40/run_qwen_rag.py, unchanged: plain RAG with GEMS-RAG's answer
#      prompt and up to 4 images). No API. Answers:
#      $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_qwen_STEM.jsonl
#   B. the checker: Claude Sonnet 5.5 checks every statement of every answer (vine2/check.py),
#      on a CPU node. It runs even if A did not finish every question: a question with no
#      draft is answered by the checker model and marked unchecked.
#      Output: $SCRATCH/Beyond_RAG/vine2_runs/STEM/ (final.jsonl, answers_final.md,
#      answers_draft.md, manifest.json)
# STEM is the question file's name without .json. The same command again does only what is
# not done yet: answered questions are not asked again, saved checker replies are reused.
set -euo pipefail
USAGE="usage: bash vine2/run_vine2_grace.sh ACCOUNT QUESTIONS_FILE [GPUS [MAX_IMAGES]]"
KQ_FILE_NAME="kq_r4299665_s0c3805.json"          # full VINE's evidence file, and no other
[ $# -ge 2 ] && [ $# -le 4 ] || { echo "$USAGE"; exit 1; }
ACCT="$1"; QFILE="$2"; NGPU="${3:-2}"; IMAGES="${4:-4}"
[[ "$ACCT" =~ ^[0-9]+$ ]] || { echo "ACCOUNT must be a number: $ACCT"; exit 1; }
[[ "$NGPU" =~ ^[12]$ ]] || { echo "GPUS must be 1 or 2 (one Grace node)"; exit 1; }
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
    *) echo "the question file must be under \$SCRATCH (the compute nodes must see it): $QFILE"; exit 1 ;;
esac
KQ="$MRAG_BASE_DIR/parser_runs_faster/$KQ_FILE_NAME"
[ -x "$RETR_ENV/bin/python" ] || { echo "the retrieval environment is missing: $RETR_ENV"; exit 1; }
[ -x "$VLLM_ENV/bin/vllm" ] || { echo "vLLM is missing: $VLLM_ENV/bin/vllm"; exit 1; }
[ -f "$VINE_HOME/.done_models" ] || { echo "the VINE setup has not finished (hprc/setup.sh)"; exit 1; }
REV="$(sed -n 's/^REVISION = "\([0-9a-f]*\)"$/\1/p' "$REPO/hprc/vine_hprc.py")"
[ -s "$HF_HUB_CACHE/models--Qwen--Qwen3.8-27B-FP8/snapshots/$REV/config.json" ] \
    || { echo "the Qwen model is missing (revision $REV)"; exit 1; }
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
[ -s "$MRAG_BASE_DIR/mmrag_cache_v3/figures.jsonl" ] || { echo "VINE's figure records are missing"; exit 1; }
[ -s "$KQ" ] || { echo "full VINE's evidence file is missing: $KQ"; exit 1; }
GUARDED="vine2 compare40/run_qwen_rag.py compare40/run_vine_rag.py compare40/qwen_local.py gems_rag/mrag
         mrag/vine/anthropic_client.py mrag/vine/vllm_client.py hprc/vine_hprc.py hprc/pin_tuning"
# shellcheck disable=SC2086
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- $GUARDED)" ]; then
    echo "the code is changed locally in $REPO (vine2, the plain-RAG runner, GEMS-RAG, the clients or the"
    echo "model settings): undo it first (git checkout -- FILE), so the run is exactly the pushed code"; exit 1
fi
for f in vine2/core.py vine2/check.py vine2/run_vine2_grace.sh vine2/answer_job.slurm vine2/check_job.slurm; do
    git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1 \
        || { echo "$f is not committed in $REPO: pull the pushed branch first"; exit 1; }
done
"$RETR_ENV/bin/python" -I - "$QFILE" "$KQ" "$IMAGES" <<'PY' || exit 1
import json, os, sys
q = json.load(open(sys.argv[1], encoding="utf-8"))
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
STEM="$(basename "$QFILE" .json)"; STEM="${STEM//[^A-Za-z0-9_]/_}"
[ "$IMAGES" -eq 4 ] || STEM="${STEM}_img$IMAGES"     # its own drafts, run folder and job names
DRAFTS="$MRAG_BASE_DIR/compare40_runs/vine_rag/answers_qwen_$STEM.jsonl"
[[ "${V2_ONLY:-}" =~ ^[A-Za-z0-9_,]*$ ]] || { echo "V2_ONLY must be ids separated by commas"; exit 1; }
# stage A is skipped when every question (or every V2_ONLY question) already has a good draft
# from this evidence file. A draft to another question text with the same id (an old file,
# merged or one server's part file) stops here: the writer would take it as done.
MISSING=$("$RETR_ENV/bin/python" -I - "$QFILE" "$DRAFTS" "$KQ_FILE_NAME" "${V2_ONLY:-}" <<'PY'
import json, re, sys
from pathlib import Path
q = json.load(open(sys.argv[1], encoding="utf-8"))
merged = Path(sys.argv[2])
rx = re.compile(re.escape(merged.stem) + r"_s\d+\.jsonl")
parts = sorted(f for f in merged.parent.glob(merged.stem + "_s*.jsonl") if rx.fullmatch(f.name))
only = [i for i in sys.argv[4].split(",") if i]
unknown = [i for i in only if i not in q]
if unknown:
    sys.exit(f"STOPPED: V2_ONLY ids not in the question file: {unknown[:5]}")
good, other, stale = set(), set(), set()
for f in [merged] + parts:
    if not f.exists():
        continue
    for line in open(f, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        if r.get("status") == "ok" and r.get("kq_file") == sys.argv[3] and str(r.get("answer") or "").strip():
            i = r.get("question_id")
            if i in q and r.get("question") != q[i]:
                other.add(str(i))
                stale.add(f.name)
            elif f == merged:
                good.add(i)
if other:
    sys.exit(f"STOPPED: {len(other)} old drafts answer another question text with the same id, e.g. "
             f"{sorted(other)[:5]}, in {sorted(stale)}. Move every {merged.stem}*.jsonl file in "
             f"{merged.parent} into another folder, then run again.")
print(sum(1 for i in (only or q) if i not in good))
PY
)
sq=$(squeue -h -u "$USER" -o "%i %j") || { echo "squeue failed; try again in a minute"; exit 1; }
other=$(grep -E " vine2_| compare40_qwen" <<<"$sq" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
unset ANTHROPIC_API_KEY                          # job B reads the key file, never this shell's key
CPUS=$(( NGPU * 4 )); MEM=$(( NGPU * 24 + 16 ))
DEP=""
[ -z "${V2_ONLY:-}" ] || { export V2_ONLY; echo "stage B will check only: $V2_ONLY"; }   # passed by --export=ALL
if [ "$MISSING" = "0" ]; then
    echo "every question${V2_ONLY:+ in V2_ONLY} already has a writer draft: stage A is not needed, only stage B is submitted"
else
    echo "questions${V2_ONLY:+ in V2_ONLY} without a writer draft: $MISSING (stage A answers every question still without one)"
    a=$(sbatch --parsable --account="$ACCT" --job-name="vine2_answer_$STEM" --partition=gpu \
         --export="ALL,VINE_REPO=$REPO,V2_QUESTIONS=$QFILE,V2_STEM=$STEM,V2_KQ=$KQ,V2_IMAGES=$IMAGES" \
         --gres="gpu:a100:$NGPU" --nodes=1 --ntasks=1 --cpus-per-task="$CPUS" --mem="${MEM}G" --time=16:00:00 \
         --output="$LOG/vine2_answer_${STEM}_%j.log" vine2/answer_job.slurm)
    a="${a%%;*}"
    [[ "$a" =~ ^[0-9]+$ ]] || { echo "Slurm did not return a job number for stage A. Look with  squeue -u $USER" >&2; exit 1; }
    DEP="--dependency=afterany:$a"
    echo "stage A (writer, $NGPU A100s, up to 16 h, up to $IMAGES pictures a question): job $a"
    echo "watch A:  tail -f $LOG/vine2_answer_${STEM}_$a.log"
fi
# shellcheck disable=SC2086
b=$(sbatch --parsable --account="$ACCT" --job-name="vine2_check_$STEM" --partition=medium $DEP \
     --export="ALL,VINE_REPO=$REPO,V2_QUESTIONS=$QFILE,V2_STEM=$STEM,V2_KQ=$KQ,V2_IMAGES=$IMAGES" \
     --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=24G --time=08:00:00 \
     --output="$LOG/vine2_check_${STEM}_%j.log" vine2/check_job.slurm)
b="${b%%;*}"
if ! [[ "$b" =~ ^[0-9]+$ ]]; then
    echo "Slurm did not return a job number for stage B. Look with  squeue -u $USER" >&2
    echo "When stage A (if any) is done, the same command submits only stage B." >&2
    exit 1
fi
echo "stage B (checker, CPU, ${DEP:+after A, }up to 8 h): job $b"
echo "watch B:  tail -f $LOG/vine2_check_${STEM}_$b.log"
