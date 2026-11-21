#!/bin/bash
# vine2/run_vine2_visrag_grace.sh -- VINE answer-then-check on VisRAG's pages, on Grace.
#
#   bash vine2/run_vine2_visrag_grace.sh ACCOUNT QUESTIONS_FILE [PAGES]
#
#   ACCOUNT         your project account number (Grace: 132692299628)
#   QUESTIONS_FILE  {id: question text}, under $SCRATCH
#   PAGES           VisRAG's top pages a question, 1 to 20 (default 20); the first 4 also as
#                   pictures (the writer's limit)
#
# The same pipeline as vine2/run_vine2_grace.sh, with VisRAG's retrieval in place of VINE's:
# the evidence is VisRAG's pages and nothing of VINE's (no VINE piece, label, type or section
# number): each page is the words printed on it, read from the manual PDF, and the first 4
# are also sent as pictures. Three jobs, each waiting for the one before:
#   1. VisRAG (1 A100, up to 2 h): VisRAG-Ret ranks the pages (compare40/visrag_retrieve.py,
#      unchanged; the page vectors of the 40-question run are reused), then
#      vine2/visrag_pages.py writes the page evidence:
#      $SCRATCH/Beyond_RAG/compare40_runs/visrag/pages_STEM_pPAGES.json
#   2. the writer (2 A100s, up to 16 h): Qwen3.8-27B answers from the page evidence
#      (vine2/run_qwen_pages.py: compare40/run_qwen_rag.py unchanged, with
#      vine2/pages_writer.py as the writer). Answers:
#      $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_qwen_STEM_visrag_pPAGES.jsonl
#   3. the checker (CPU, up to 8 h): Claude Sonnet 5.5 checks every statement, and code
#      checks the checker: vine2/check_job.slurm and vine2/check.py, unchanged in how they
#      work. Output: $SCRATCH/Beyond_RAG/vine2_runs/STEM_visrag_pPAGES/
# STEM is the question file's name without .json. The same command again does only what is
# not done yet. The run on VINE's own evidence (vine2_runs/STEM/) is not touched.
set -euo pipefail
USAGE="usage: bash vine2/run_vine2_visrag_grace.sh ACCOUNT QUESTIONS_FILE [PAGES]"
[ $# -ge 2 ] && [ $# -le 3 ] || { echo "$USAGE"; exit 1; }
ACCT="$1"; QFILE="$2"; PAGES="${3:-20}"
[[ "$ACCT" =~ ^[0-9]+$ ]] || { echo "ACCOUNT must be a number: $ACCT"; exit 1; }
[[ "$PAGES" =~ ^[0-9]+$ ]] && [ "$((10#$PAGES))" -ge 1 ] && [ "$((10#$PAGES))" -le 20 ] || { echo "PAGES must be 1 to 20"; exit 1; }
PAGES=$((10#$PAGES))
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
[ -x "$RETR_ENV/bin/python" ] || { echo "the retrieval environment is missing: $RETR_ENV"; exit 1; }
[ -x "$VLLM_ENV/bin/vllm" ] || { echo "vLLM is missing: $VLLM_ENV/bin/vllm"; exit 1; }
[ -f "$VINE_HOME/.done_models" ] || { echo "the VINE setup has not finished (hprc/setup.sh)"; exit 1; }
REV="$(sed -n 's/^REVISION = "\([0-9a-f]*\)"$/\1/p' "$REPO/hprc/vine_hprc.py")"
[ -s "$HF_HUB_CACHE/models--Qwen--Qwen3.8-27B-FP8/snapshots/$REV/config.json" ] \
    || { echo "the Qwen model is missing (revision $REV)"; exit 1; }
[ -x "$VINE_HOME/envs/visrag/bin/python" ] || { echo "the VisRAG environment is missing: run  bash compare40/visrag_setup.sh"; exit 1; }
[ -s "$VINE_HOME/visrag_ret_revision" ] || { echo "VisRAG-Ret is not downloaded: run  bash compare40/visrag_setup.sh"; exit 1; }
[ -s "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" ] || { echo "the MUTCD PDF is missing: $MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"; exit 1; }
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
GUARDED="vine2 compare40/run_qwen_rag.py compare40/qwen_local.py compare40/visrag_retrieve.py compare40/run_visrag.py
         gems_rag/mrag mrag/vine/anthropic_client.py mrag/vine/vllm_client.py hprc/vine_hprc.py hprc/pin_tuning"
# shellcheck disable=SC2086
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- $GUARDED)" ]; then
    echo "the code is changed locally in $REPO (vine2, the Qwen runner, the VisRAG code, GEMS-RAG, the clients"
    echo "or the model settings): undo it first (git checkout -- FILE), so the run is exactly the pushed code"; exit 1
fi
for f in vine2/core.py vine2/check.py vine2/check_job.slurm vine2/visrag_pages.py vine2/pages_writer.py \
         vine2/run_qwen_pages.py vine2/visrag_job.slurm vine2/pages_answer_job.slurm vine2/run_vine2_visrag_grace.sh; do
    git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1 \
        || { echo "$f is not committed in $REPO: pull the pushed code first"; exit 1; }
done
QSTEM="$(basename "$QFILE" .json)"; QSTEM="${QSTEM//[^A-Za-z0-9_]/_}"
STEM="${QSTEM}_visrag_p$PAGES"
KQ="$MRAG_BASE_DIR/compare40_runs/visrag/pages_${QSTEM}_p$PAGES.json"
DRAFTS="$MRAG_BASE_DIR/compare40_runs/vine_rag/answers_qwen_$STEM.jsonl"
# what is done already: the page evidence for exactly these texts, and the writer's drafts
STATE=$("$RETR_ENV/bin/python" -I - "$QFILE" "$KQ" "$DRAFTS" "$PAGES" <<'PY'
import json, re, sys
from pathlib import Path
try:
    q = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    sys.exit(f"the question file is not JSON: {e}")
if not isinstance(q, dict) or not q or not all(isinstance(v, str) and v.strip() for v in q.values()):
    sys.exit("the question file must be {id: question text}, and nothing else")
kq_path, merged, pages = Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
try:
    kq = json.loads(kq_path.read_text(encoding="utf-8"))
except (FileNotFoundError, ValueError):
    kq = {}
evidence_ok = all(i in kq and kq[i].get("question") == t and len(kq[i].get("chunks") or []) == pages
                  and all(c.get("source") == "visrag_page" for c in kq[i]["chunks"]) for i, t in q.items())
rx = re.compile(re.escape(merged.stem) + r"_s\d+\.jsonl")
parts = sorted(f for f in merged.parent.glob(merged.stem + "_s*.jsonl") if rx.fullmatch(f.name))
good, other, any_draft = set(), set(), False
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
        any_draft = True
        if r.get("status") == "ok" and r.get("kq_file") == kq_path.name and str(r.get("answer") or "").strip():
            i = r.get("question_id")
            if i in q and r.get("question") != q[i]:
                other.add(str(i))
            elif f == merged:
                good.add(i)
if other:
    sys.exit(f"STOPPED: {len(other)} old drafts answer another question text with the same id, e.g. "
             f"{sorted(other)[:5]}. Move every {merged.stem}*.jsonl file in {merged.parent} into another "
             f"folder, then run again.")
if not evidence_ok and any_draft:
    sys.exit(f"STOPPED: the page evidence {kq_path.name} would be made again, but drafts from an earlier one "
             f"exist. Move every {merged.stem}*.jsonl file in {merged.parent} into another folder, then run again.")
missing = sum(1 for i in q if i not in good)
print(f"question file: {len(q)} questions, {next(iter(q))} ... {list(q)[-1]} | page evidence "
      f"{'ready' if evidence_ok else 'to be made'} | writer drafts missing: {missing}", file=sys.stderr)
print(f"{'yes' if not evidence_ok else 'no'} {missing}")
PY
)
read -r NEED_EV MISSING <<<"$STATE"
sq=$(squeue -h -u "$USER" -o "%i %j") || { echo "squeue failed; try again in a minute"; exit 1; }
other=$(grep -E " vine2_| visrag_| compare40_qwen| compare40_visrag" <<<"$sq" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
unset ANTHROPIC_API_KEY                          # job 3 reads the key file, never this shell's key
unset V2_ONLY                                    # job 3 checks every question (it reads V2_ONLY)
EXP="ALL,VINE_REPO=$REPO,V2_QUESTIONS=$QFILE,V2_QSTEM=$QSTEM,V2_STEM=$STEM,V2_KQ=$KQ,V2_PAGES=$PAGES"
DEP=""
if [ "$NEED_EV" = "yes" ]; then
    j1=$(sbatch --parsable --account="$ACCT" --job-name="visrag_ev_$QSTEM" --partition=gpu --export="$EXP" \
          --gres="gpu:a100:1" --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=64G --time=02:00:00 \
          --output="$LOG/visrag_ev_${QSTEM}_%j.log" vine2/visrag_job.slurm)
    j1="${j1%%;*}"
    [[ "$j1" =~ ^[0-9]+$ ]] || { echo "Slurm did not return a job number for job 1. Look with  squeue -u $USER" >&2; exit 1; }
    DEP="--dependency=afterok:$j1 --kill-on-invalid-dep=yes"
    echo "1. VisRAG retrieval and page evidence (1 A100, up to 2 h): job $j1"
    echo "   watch:  tail -f $LOG/visrag_ev_${QSTEM}_$j1.log"
else
    echo "1. the page evidence is ready: $KQ"
fi
DEP3=""
if [ "$NEED_EV" = "yes" ] || [ "$MISSING" != "0" ]; then
    # shellcheck disable=SC2086
    j2=$(sbatch --parsable --account="$ACCT" --job-name="vine2_answer_$STEM" --partition=gpu $DEP --export="$EXP" \
          --gres="gpu:a100:2" --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=64G --time=16:00:00 \
          --output="$LOG/vine2_answer_${STEM}_%j.log" vine2/pages_answer_job.slurm)
    j2="${j2%%;*}"
    [[ "$j2" =~ ^[0-9]+$ ]] || { echo "Slurm did not return a job number for job 2. Look with  squeue -u $USER" >&2; exit 1; }
    DEP3="--dependency=afterany:$j2"
    echo "2. the writer (2 A100s, up to 16 h${DEP:+, after job 1 ends without error}): job $j2"
    echo "   watch:  tail -f $LOG/vine2_answer_${STEM}_$j2.log"
else
    echo "2. every question already has a writer draft: the writer is not needed"
fi
# shellcheck disable=SC2086
j3=$(sbatch --parsable --account="$ACCT" --job-name="vine2_check_$STEM" --partition=medium $DEP3 \
      --kill-on-invalid-dep=yes --export="$EXP" --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=24G --time=08:00:00 \
      --output="$LOG/vine2_check_${STEM}_%j.log" vine2/check_job.slurm)
j3="${j3%%;*}"
if ! [[ "$j3" =~ ^[0-9]+$ ]]; then
    echo "Slurm did not return a job number for job 3. Look with  squeue -u $USER" >&2
    echo "When the jobs before it are done, the same command submits only what is left." >&2
    exit 1
fi
echo "3. the checker (CPU, up to 8 h${DEP3:+, after job 2}): job $j3"
echo "   watch:  tail -f $LOG/vine2_check_${STEM}_$j3.log"
echo "   output -> $SCRATCH/Beyond_RAG/vine2_runs/$STEM/  (grade answers_final_clean.md)"
[ -z "$DEP" ] || echo "   (if job 1 fails, Slurm cancels job 2, and job 3 stops at once: it finds no drafts)"
