#!/bin/bash
# vine2/visrag_job.slurm -- job 1 of VINE answer-then-check on VisRAG's pages: VisRAG's
# retrieval, then the page evidence. Submitted by vine2/run_vine2_visrag_grace.sh. Not meant
# to be submitted by hand. 1 A100 (VisRAG-Ret needs bfloat16). No API, no proxy.
#   1. compare40/visrag_retrieve.py (unchanged): VisRAG-Ret ranks the 1,162 pages for every
#      question. The page vectors of the 40-question VisRAG run are copied and reused (named
#      by the model commit, and checked by shape before use). Skipped when a retrieval for
#      exactly these question texts is there already.
#   2. vine2/visrag_pages.py: the top V2_PAGES pages of each question, as the words printed
#      on them (from the PDF) and, for the first 4, their pictures. Nothing of VINE's.
#SBATCH --job-name=visrag_ev
#SBATCH --nodes=1
#SBATCH --ntasks=1

set -eo pipefail
REPO="${VINE_REPO:-$SLURM_SUBMIT_DIR}"
source "$REPO/hprc/env.sh"
: "${V2_QUESTIONS:?submit with vine2/run_vine2_visrag_grace.sh}"
: "${V2_QSTEM:?submit with vine2/run_vine2_visrag_grace.sh}"
: "${V2_PAGES:?submit with vine2/run_vine2_visrag_grace.sh}"
: "${V2_KQ:?submit with vine2/run_vine2_visrag_grace.sh}"
VISRAG_ENV="$VINE_HOME/envs/visrag"
REV="$(tr -d '[:space:]' < "$VINE_HOME/visrag_ret_revision")"
OUT="$MRAG_BASE_DIR/compare40_runs/visrag"
RETR="$OUT/retrieval_$V2_QSTEM"
PDF="$MRAG_BASE_DIR/mutcd11theditionr1hl.pdf"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ANTHROPIC_API_KEY
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1

echo "job $SLURM_JOB_ID | VisRAG retrieval and page evidence | $V2_QSTEM | $V2_PAGES pages | node $(hostname) | $(date '+%Y-%m-%d %H:%M:%S')"
echo "repo $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no -- vine2 compare40/visrag_retrieve.py compare40/run_visrag.py)" ]; then
    echo "STOPPED: vine2 or the VisRAG code is changed locally"; exit 1
fi
echo "questions $V2_QUESTIONS | sha256 $(sha256sum "$V2_QUESTIONS" | cut -c1-12)"
echo "code sha256: visrag_retrieve.py $(sha256sum "$REPO/compare40/visrag_retrieve.py" | cut -c1-12)" \
     "| visrag_pages.py $(sha256sum "$REPO/vine2/visrag_pages.py" | cut -c1-12) | VisRAG-Ret $REV"
nvidia-smi -L || true
cd "$REPO"

echo; echo "===== 1. VisRAG retrieval ====="
if "$RETR_ENV/bin/python" -I - "$V2_QUESTIONS" "$RETR" <<'PY'
import hashlib, json, os, sys
q = json.load(open(sys.argv[1], encoding="utf-8"))
try:
    man = json.load(open(os.path.join(sys.argv[2], "retrieval_manifest.json")))
    have = {}
    for line in open(os.path.join(sys.argv[2], "retrieval.jsonl"), encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            have[r["question_id"]] = r.get("question_sha256")
except (FileNotFoundError, ValueError, KeyError):
    sys.exit(1)
ok = not man.get("dry_run") and int(man.get("save_top", 0)) >= 20 and \
    all(have.get(i) == hashlib.sha256(t.encode()).hexdigest() for i, t in q.items())
sys.exit(0 if ok else 1)
PY
then
    echo "a retrieval for exactly these question texts is there already: $RETR"
else
    mkdir -p "$RETR/page_embeddings"
    if compgen -G "$OUT/retrieval/page_embeddings/*.npy" > /dev/null; then
        for f in "$OUT/retrieval/page_embeddings/"*.npy; do       # copied, never moved; nothing overwritten
            d="$RETR/page_embeddings/$(basename "$f")"
            [ -e "$d" ] || { cp "$f" "$d.part" && mv "$d.part" "$d"; }   # a stopped copy leaves no half file
        done
        n=$( (compgen -G "$RETR/page_embeddings/ret_${REV:0:12}_pages_*.npy" || true) | wc -l)
        echo "page vectors reused from $OUT/retrieval/page_embeddings: $n blocks for VisRAG-Ret ${REV:0:12} (24 = all 1,162 pages)"
        [ "$n" -eq 24 ] || echo "WARNING: not all 24 blocks are for this model commit: the missing pages are embedded now (slower)"
    else
        echo "no saved page vectors: all 1,162 pages are embedded now (slower)"
    fi
    "$VISRAG_ENV/bin/python" -I -u compare40/visrag_retrieve.py --pdf "$PDF" --questions "$V2_QUESTIONS" \
        --pages_dir "$OUT/pages" --out_dir "$RETR" --revision "$REV" --save_top 20
fi

echo; echo "===== 2. the page evidence ====="
"$VISRAG_ENV/bin/python" -I -u vine2/visrag_pages.py --retrieval "$RETR" --questions "$V2_QUESTIONS" \
    --pdf "$PDF" --pages-dir "$OUT/pages" --out "$V2_KQ" --pages "$V2_PAGES" --images "$(( V2_PAGES < 4 ? V2_PAGES : 4 ))"
echo; echo "job 1 done | $(date '+%Y-%m-%d %H:%M:%S')"
