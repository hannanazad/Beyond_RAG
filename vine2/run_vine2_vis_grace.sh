#!/bin/bash
# vine2/run_vine2_vis_grace.sh -- VINE answer-then-check on another visual RAG system's
# retrieval (M3DocRAG, ViDoRAG or RegionRAG), on Grace.
#
#   bash vine2/run_vine2_vis_grace.sh ACCOUNT QUESTIONS_FILE SYSTEM [PIECES]
#
#   ACCOUNT         your project account number (Grace: 132692299628)
#   QUESTIONS_FILE  {id: question text}, under $SCRATCH
#   SYSTEM          m3docrag | vidorag | regionrag  (first: bash vine2/vis_setup.sh SYSTEM)
#   PIECES          pages (regions for RegionRAG) a question, 1 to 20 (default 20, as the VisRAG
#                   run); the first 4 also as pictures (the writer's limit). ViDoRAG decides
#                   its own number of pages (5 to 20); PIECES is then the most it may keep.
#
# The same pipeline as vine2/run_vine2_visrag_grace.sh, with this system's retrieval in place of
# VisRAG's: the evidence is what the system found, and nothing of VINE's (no VINE piece,
# label, type or section number). Jobs, each waiting for the one before:
#   0. (ViDoRAG only, CPU, up to 8 h) ViDoRAG's page pictures and OCR text: vine2/vidorag_ocr_job.slurm
#   1. the system's retrieval and the evidence (1 A100, up to 4 h): vine2/vis_retrieve_job.slurm
#      -> $SCRATCH/Beyond_RAG/compare40_runs/SYSTEM/pieces_STEM_pPIECES.json
#   2. the writer (2 A100s, up to 16 h): vine2/pages_answer_job.slurm, unchanged -> drafts
#      $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_qwen_STEM_SYSTEM_pPIECES.jsonl
#   3. the checker (CPU, up to 8 h): vine2/check_job.slurm, unchanged
#      -> $SCRATCH/Beyond_RAG/vine2_runs/STEM_SYSTEM_pPIECES/  (grade answers_final_clean.md)
# STEM is the question file's name without .json. The same command again does only what is
# not done yet. Runs of different systems may wait in the queue at the same time.
set -euo pipefail
USAGE="usage: bash vine2/run_vine2_vis_grace.sh ACCOUNT QUESTIONS_FILE m3docrag|vidorag|regionrag [PIECES]"
[ $# -ge 3 ] && [ $# -le 4 ] || { echo "$USAGE"; exit 1; }
ACCT="$1"; QFILE="$2"; SYSTEM="$3"; PAGES="${4:-20}"
[[ "$ACCT" =~ ^[0-9]+$ ]] || { echo "ACCOUNT must be a number: $ACCT"; exit 1; }
case "$SYSTEM" in m3docrag|vidorag|regionrag) ;; *) echo "$USAGE"; exit 1 ;; esac
[[ "$PAGES" =~ ^[0-9]+$ ]] && [ "$((10#$PAGES))" -ge 1 ] && [ "$((10#$PAGES))" -le 20 ] || { echo "PIECES must be 1 to 20"; exit 1; }
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
[ -x "$VINE_HOME/envs/visrag/bin/python" ] || { echo "the VisRAG environment is missing (it reads the PDF): run  bash compare40/visrag_setup.sh"; exit 1; }
[ -x "$VINE_HOME/envs/$SYSTEM/bin/python" ] || { echo "the $SYSTEM environment is missing: run  bash vine2/vis_setup.sh $SYSTEM"; exit 1; }
[ -s "$VINE_HOME/vis/${SYSTEM}_revisions.json" ] || { echo "the $SYSTEM models are not recorded: run  bash vine2/vis_setup.sh $SYSTEM"; exit 1; }
[ -d "$VINE_HOME/ext/$SYSTEM/.git" ] || { echo "the $SYSTEM code is missing: run  bash vine2/vis_setup.sh $SYSTEM"; exit 1; }
if [ "$SYSTEM" = vidorag ]; then
    [ -x "$VINE_HOME/envs/vidorag_ocr/bin/python" ] || { echo "ViDoRAG's OCR environment is missing: run  bash vine2/vis_setup.sh vidorag"; exit 1; }
fi
if [ "$SYSTEM" = regionrag ]; then
    [ -s "$MRAG_BASE_DIR/compare40_runs/visrag/pages/page_0001.png" ] || { echo "the VisRAG run's page pictures are missing"; exit 1; }
fi
[ -s "$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf" ] || { echo "the MUTCD PDF is missing: $MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"; exit 1; }
[ -s "$VINE_HOME/anthropic_key" ] || { echo "no Anthropic key in \$VINE_HOME/anthropic_key"; exit 1; }
[ -d "$REPO/gems_rag/mrag" ] || { echo "the GEMS-RAG copy is missing: $REPO/gems_rag"; exit 1; }
[ -d "$MRAG_BASE_DIR/gems_rag" ] || { echo "GEMS-RAG's data is missing: $MRAG_BASE_DIR/gems_rag"; exit 1; }
GUARDED="vine2 compare40/run_qwen_rag.py compare40/qwen_local.py compare40/run_visrag.py
         gems_rag/mrag mrag/vine/anthropic_client.py mrag/vine/vllm_client.py hprc/vine_hprc.py hprc/pin_tuning"
# shellcheck disable=SC2086
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- $GUARDED)" ]; then
    echo "the code is changed locally in $REPO (vine2, the Qwen runner, GEMS-RAG, the clients or the model"
    echo "settings): undo it first (git checkout -- FILE), so the run is exactly the pushed code"; exit 1
fi
for f in vine2/core.py vine2/check.py vine2/check_job.slurm vine2/visrag_pages.py vine2/pages_writer.py \
         vine2/run_qwen_pages.py vine2/pages_answer_job.slurm vine2/vis_common.py vine2/vis_evidence.py \
         vine2/m3docrag_retrieve.py vine2/vidorag_ocr.py vine2/vidorag_retrieve.py vine2/regionrag_retrieve.py \
         vine2/vis_retrieve_job.slurm vine2/vidorag_ocr_job.slurm vine2/run_vine2_vis_grace.sh; do
    git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1 \
        || { echo "$f is not committed in $REPO: pull the pushed code first"; exit 1; }
done
QSTEM="$(basename "$QFILE" .json)"; QSTEM="${QSTEM//[^A-Za-z0-9_]/_}"
STEM="${QSTEM}_${SYSTEM}_p$PAGES"
KQ="$MRAG_BASE_DIR/compare40_runs/$SYSTEM/pieces_${QSTEM}_p$PAGES.json"
DRAFTS="$MRAG_BASE_DIR/compare40_runs/vine_rag/answers_qwen_$STEM.jsonl"
OCRDIR="$MRAG_BASE_DIR/compare40_runs/vidorag/work/data/MUTCD"
mkdir -p "$(dirname "$KQ")"
# what is done already: the evidence for exactly these texts, the OCR (ViDoRAG), the drafts
STATE=$("$RETR_ENV/bin/python" -I - "$QFILE" "$KQ" "$DRAFTS" "$PAGES" "$SYSTEM" "$OCRDIR" <<'PY'
import json, re, sys
from pathlib import Path
try:
    q = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    sys.exit(f"the question file is not JSON: {e}")
if not isinstance(q, dict) or not q or not all(isinstance(v, str) and v.strip() for v in q.values()):
    sys.exit("the question file must be {id: question text}, and nothing else")
kq_path, merged, pages, system, ocr = Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]), sys.argv[5], Path(sys.argv[6])
source = {"m3docrag": "m3docrag_page", "vidorag": "vidorag_page", "regionrag": "regionrag_region"}[system]
try:
    kq = json.loads(kq_path.read_text(encoding="utf-8"))
except (FileNotFoundError, ValueError):
    kq = {}
def count_ok(n):
    return 1 <= n <= pages if system == "vidorag" else n == pages
evidence_ok = all(i in kq and kq[i].get("question") == t and count_ok(len(kq[i].get("chunks") or []))
                  and all(c.get("source") == source for c in kq[i]["chunks"]) for i, t in q.items())
ocr_ok = True
if system == "vidorag":
    try:
        n = int(json.loads((ocr / "ocr_manifest.json").read_text())["n_pages"])
        ocr_ok = all(len(list((ocr / d).glob(f"MUTCD_*.{e}"))) == n for d, e in (("img", "jpg"), ("ppocr", "txt")))
    except (FileNotFoundError, ValueError, KeyError):
        ocr_ok = False
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
    sys.exit(f"STOPPED: the evidence {kq_path.name} would be made again, but drafts from an earlier one "
             f"exist. Move every {merged.stem}*.jsonl file in {merged.parent} into another folder, then run again.")
missing = sum(1 for i in q if i not in good)
print(f"question file: {len(q)} questions, {next(iter(q))} ... {list(q)[-1]} | {system} evidence "
      f"{'ready' if evidence_ok else 'to be made'}{'' if system != 'vidorag' else ' | OCR ' + ('done' if ocr_ok else 'to be done')}"
      f" | writer drafts missing: {missing}", file=sys.stderr)
print(f"{'yes' if not evidence_ok else 'no'} {'yes' if not ocr_ok and not evidence_ok else 'no'} {missing}")
PY
)
read -r NEED_EV NEED_OCR MISSING <<<"$STATE"
sq=$(squeue -h -u "$USER" -o "%i %j") || { echo "squeue failed; try again in a minute"; exit 1; }
BUSY=" (vis_ocr|vis_ev)_${QSTEM}_${SYSTEM}\$| vine2_(answer|check)_${STEM}\$"
# M3DocRAG's page pictures and ViDoRAG's work folder are shared by all question files: one
# retrieval of that system at a time (RegionRAG's files are per question file)
[ "$SYSTEM" = regionrag ] || BUSY="$BUSY| vis_ev_.*_${SYSTEM}\$"
[ "$SYSTEM" != vidorag ] || BUSY="$BUSY| vis_ocr_"
other=$(grep -E "$BUSY" <<<"$sq" || true)
[ -z "$other" ] || { echo "wait for this job to end first:"; echo "$other"; exit 1; }
LOG="$VINE_HOME/logs"; mkdir -p "$LOG"
cd "$REPO"
unset ANTHROPIC_API_KEY HF_TOKEN                 # job 3 reads the key file, never this shell's key
unset V2_ONLY                                    # job 3 checks every question (it reads V2_ONLY)
EXP="ALL,VINE_REPO=$REPO,V2_SYSTEM=$SYSTEM,V2_QUESTIONS=$QFILE,V2_QSTEM=$QSTEM,V2_STEM=$STEM,V2_KQ=$KQ,V2_PAGES=$PAGES"
job() {                                          # sbatch ... -> the job number, or stop
    local j; j=$(sbatch --parsable "$@"); j="${j%%;*}"
    [[ "$j" =~ ^[0-9]+$ ]] || { echo "Slurm did not return a job number. Look with  squeue -u $USER" >&2; exit 1; }
    echo "$j"
}
DEP=""; j0=""
if [ "$NEED_OCR" = "yes" ]; then
    j0=$(job --account="$ACCT" --job-name="vis_ocr_${QSTEM}_$SYSTEM" --partition=medium --export="$EXP" \
          --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=08:00:00 \
          --output="$LOG/vis_ocr_${QSTEM}_${SYSTEM}_%j.log" vine2/vidorag_ocr_job.slurm)
    DEP="--dependency=afterok:$j0 --kill-on-invalid-dep=yes"
    echo "0. ViDoRAG's page pictures and OCR (CPU, up to 8 h): job $j0"
    echo "   watch:  tail -f $LOG/vis_ocr_${QSTEM}_${SYSTEM}_$j0.log"
fi
if [ "$NEED_EV" = "yes" ]; then
    # shellcheck disable=SC2086
    j1=$(job --account="$ACCT" --job-name="vis_ev_${QSTEM}_$SYSTEM" --partition=gpu $DEP --export="$EXP" \
          --gres="gpu:a100:1" --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=96G --time=04:00:00 \
          --output="$LOG/vis_ev_${QSTEM}_${SYSTEM}_%j.log" vine2/vis_retrieve_job.slurm)
    DEP="--dependency=afterok:$j1 --kill-on-invalid-dep=yes"
    echo "1. $SYSTEM retrieval and evidence (1 A100, up to 4 h${j0:+, after job 0 ends without error}): job $j1"
    echo "   watch:  tail -f $LOG/vis_ev_${QSTEM}_${SYSTEM}_$j1.log"
else
    echo "1. the evidence is ready: $KQ"
fi
DEP3=""
if [ "$NEED_EV" = "yes" ] || [ "$MISSING" != "0" ]; then
    # shellcheck disable=SC2086
    j2=$(job --account="$ACCT" --job-name="vine2_answer_$STEM" --partition=gpu $DEP --export="$EXP" \
          --gres="gpu:a100:2" --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=64G --time=16:00:00 \
          --output="$LOG/vine2_answer_${STEM}_%j.log" vine2/pages_answer_job.slurm)
    DEP3="--dependency=afterany:$j2"
    echo "2. the writer (2 A100s, up to 16 h${DEP:+, after job 1 ends without error}): job $j2"
    echo "   watch:  tail -f $LOG/vine2_answer_${STEM}_$j2.log"
else
    echo "2. every question already has a writer draft: the writer is not needed"
fi
# a checker job stops if another checker is running (it would pay twice for the same answers):
# this one waits for every vine2 checker already in the queue, of any run
CHK=$(grep -E " vine2_check_" <<<"$sq" | awk '{print $1}' | paste -sd: - || true)
if [ -n "$CHK" ]; then
    DEP3="--dependency=afterany:${DEP3#--dependency=afterany:}${DEP3:+:}$CHK"
    echo "   (the checker also waits for the checker job(s) already queued: ${CHK//:/, })"
fi
# shellcheck disable=SC2086
j3=$(job --account="$ACCT" --job-name="vine2_check_$STEM" --partition=medium $DEP3 \
      --kill-on-invalid-dep=yes --export="$EXP" --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=24G --time=08:00:00 \
      --output="$LOG/vine2_check_${STEM}_%j.log" vine2/check_job.slurm)
echo "3. the checker (CPU, up to 8 h${DEP3:+, after job 2}): job $j3"
echo "   watch:  tail -f $LOG/vine2_check_${STEM}_$j3.log"
echo "   output -> $SCRATCH/Beyond_RAG/vine2_runs/$STEM/  (grade answers_final_clean.md)"
[ -z "$DEP" ] || echo "   (if job 0 or 1 fails, Slurm cancels the writer, and job 3 stops at once: it finds no drafts)"
