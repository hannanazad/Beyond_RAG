#!/bin/bash
# vine2/vis_retrieve_job.slurm -- job 1 of VINE answer-then-check on another visual RAG
# system's retrieval (1 A100): the system's own retrieval, then the evidence. Submitted by
# vine2/run_vine2_vis_grace.sh. Not meant to be submitted by hand. No API, no proxy.
#   m3docrag   vine2/m3docrag_retrieve.py  (M3DocRAG's ColPali page retrieval)
#   vidorag    vine2/vidorag_retrieve.py   (ViDoRAG's hybrid retrieval; after job 0's OCR)
#   regionrag  vine2/regionrag_retrieve.py (RegionRAG's region retrieval, on the page pictures
#              of the VisRAG run)
# then vine2/vis_evidence.py: the top V2_PAGES pieces of each question, nothing of VINE's.
# A retrieval for exactly these question texts, code and models is not made again.
#SBATCH --job-name=vis_ev
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${V2_SYSTEM:?submit with vine2/run_vine2_vis_grace.sh}"
: "${V2_QUESTIONS:?submit with vine2/run_vine2_vis_grace.sh}"
: "${V2_QSTEM:?submit with vine2/run_vine2_vis_grace.sh}"
: "${V2_PAGES:?submit with vine2/run_vine2_vis_grace.sh}"
: "${V2_KQ:?submit with vine2/run_vine2_vis_grace.sh}"
OUT="$MRAG_BASE_DIR/compare40_runs/$V2_SYSTEM"
RETR="$OUT/retrieval_$V2_QSTEM"
PDF="$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"
CODE="$VINE_HOME/ext/$V2_SYSTEM"
REVS="$VINE_HOME/vis/${V2_SYSTEM}_revisions.json"
SYSPY="$VINE_HOME/envs/$V2_SYSTEM/bin/python"
VISRAG_PY="$VINE_HOME/envs/visrag/bin/python"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY HF_TOKEN
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1

echo "job $SLURM_JOB_ID | $V2_SYSTEM retrieval and evidence | $V2_QSTEM | $V2_PAGES pieces | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- vine2 compare40/run_visrag.py)" ]; then
    echo "STOPPED: vine2 or compare40/run_visrag.py is changed locally"; exit 1
fi
echo "questions $V2_QUESTIONS | sha256 $(sha256sum "$V2_QUESTIONS" | cut -c1-12)"
echo "code sha256: ${V2_SYSTEM}_retrieve.py $(sha256sum "$REPO/vine2/${V2_SYSTEM}_retrieve.py" | cut -c1-12)" \
     "| vis_evidence.py $(sha256sum "$REPO/vine2/vis_evidence.py" | cut -c1-12)" \
     "| $V2_SYSTEM code $(git -C "$CODE" rev-parse --short=12 HEAD)"
nvidia-smi -L || true
if [ "$V2_SYSTEM" = m3docrag ]; then
    export PATH="$VINE_HOME/vis/poppler_bin:$PATH"     # Grace's poppler module, for pdf2image (vine2/vis_setup.sh)
    [ "$(command -v pdftoppm)" = "$VINE_HOME/vis/poppler_bin/pdftoppm" ] && pdftoppm -v >/dev/null 2>&1 \
        || { echo "STOPPED: poppler does not run on this node: run  bash vine2/vis_setup.sh m3docrag"; exit 1; }
    echo "poppler: $(pdftoppm -v 2>&1 | head -1)"
fi
cd "$REPO"

echo; echo "===== 1. $V2_SYSTEM retrieval ====="
case "$V2_SYSTEM" in
  m3docrag)
    "$SYSPY" -I -u vine2/m3docrag_retrieve.py --pdf "$PDF" --questions "$V2_QUESTIONS" --out-dir "$RETR" \
        --pages-dir "$OUT/pages" --code "$CODE" --revisions "$REVS" ;;
  vidorag)
    # llama-index's own caches, as ViDoRAG's authors have them: its bundled tiktoken file (only
    # used when TIKTOKEN_CACHE_DIR is not set), and the models in the one Hugging Face cache
    # (llama-index would look in /tmp/llama_index)
    ( unset TIKTOKEN_CACHE_DIR
      export LLAMA_INDEX_CACHE_DIR="$HF_HUB_CACHE"
      "$SYSPY" -I -u vine2/vidorag_retrieve.py --questions "$V2_QUESTIONS" --pdf "$PDF" --work "$OUT/work" \
          --code "$CODE" --revisions "$REVS" --out-dir "$RETR" ) ;;
  regionrag)
    NP="$("$VISRAG_PY" -I -c 'import fitz, sys; print(fitz.open(sys.argv[1]).page_count)' "$PDF")"
    "$SYSPY" -I -u vine2/regionrag_retrieve.py --questions "$V2_QUESTIONS" \
        --pages-dir "$MRAG_BASE_DIR/compare40_runs/visrag/pages" --n-pages "$NP" --code "$CODE" \
        --revisions "$REVS" --out-dir "$RETR" ;;
  *) echo "STOPPED: unknown system $V2_SYSTEM"; exit 1 ;;
esac

echo; echo "===== 2. the evidence ====="
"$VISRAG_PY" -I -u vine2/vis_evidence.py --system "$V2_SYSTEM" --retrieval "$RETR" --questions "$V2_QUESTIONS" \
    --pdf "$PDF" --out "$V2_KQ" --pieces "$V2_PAGES" --images "$(( V2_PAGES < 4 ? V2_PAGES : 4 ))"
echo; echo "job 1 done | $(date '+%Y-%m-%d %H:%M:%S')"
