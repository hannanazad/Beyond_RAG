#!/bin/bash
# compare40/visrag_setup.sh -- once, on a Grace (or FASTER) LOGIN node: it needs the internet.
#
#   bash compare40/visrag_setup.sh
#
# 1. Makes the VisRAG retrieval environment, $SCRATCH/vine/envs/visrag: Python 3.11 and the
#    exact library versions VisRAG's authors use (transformers 4.40.2, torch 2.1.2), as in
#    the VisRAG run of 27 Oct. It is separate, so no other environment is touched.
# 2. Downloads the VisRAG-Ret model (openbmb/VisRAG-Ret, a few GB) into $SCRATCH/hf_cache
#    and writes the commit it got to $SCRATCH/vine/visrag_ret_revision, so the job loads
#    exactly that commit, offline.
# Nothing is written to $HOME. Run it again: what is there and works is kept.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"
fail() { echo "STOPPED: $*" >&2; exit 1; }

VISRAG_ENV="$VINE_HOME/envs/visrag"
VP="$VISRAG_ENV/bin/python"
REVFILE="$VINE_HOME/visrag_ret_revision"
[ -z "${SLURM_JOB_ID:-}" ] || fail "run this on a login node, not in a job"
[ "$(command -v uv || true)" = "$VINE_HOME/bin/uv" ] || fail "uv is not in $VINE_HOME/bin (hprc/setup.sh installs it)"
curl -sSfI --max-time 30 https://pypi.org/simple/ >/dev/null || fail "no internet here: run it on a login node"
curl -sSfI --max-time 30 https://huggingface.co >/dev/null || fail "huggingface.co cannot be reached from here"

# the versions of VisRAG's own requirements.txt; tokenizers, huggingface_hub, timm,
# safetensors and PyMuPDF matched to transformers 4.40.2 (as in the 27 Oct run)
PINS=(transformers==4.40.2 tokenizers==0.19.1 huggingface_hub==0.23.4 timm==0.9.10
      sentencepiece==0.1.99 accelerate==0.27.0 protobuf==4.25.0 safetensors==0.4.3
      numpy==1.26.4 Pillow==10.1.0 PyMuPDF==1.24.10)
CHECK="import torch, transformers, timm, fitz, sentencepiece; print('torch', torch.__version__, '| transformers', transformers.__version__, '| timm', timm.__version__)"

if [ -x "$VP" ] && "$VP" -I -c "$CHECK" 2>/dev/null; then
    echo "the VisRAG environment is there and imports: kept"
else
    echo "making the VisRAG environment in $VISRAG_ENV (Python 3.11) ..."
    uv python install 3.11
    PY_FOUND="$(uv python find 3.11)"
    case "$PY_FOUND" in "$VINE_HOME"/*) ;; *) fail "uv picked a Python outside $VINE_HOME: $PY_FOUND" ;; esac
    rm -rf "$VISRAG_ENV"
    uv venv "$VISRAG_ENV" --python 3.11
    uv pip install --python "$VP" --torch-backend=cu121 "torch==2.1.2" "torchvision==0.16.2"
    uv pip install --python "$VP" "${PINS[@]}"
    "$VP" -I -c "$CHECK" || fail "the VisRAG environment does not import"
fi
case "$("$VP" -I -c 'import sys; print(sys.prefix)')" in "$VINE_HOME"/*) ;; *) fail "the environment is outside $VINE_HOME" ;; esac

echo "downloading openbmb/VisRAG-Ret into $HF_HUB_CACHE ..."
"$VP" -I - "$REVFILE" <<'PY'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
path = Path(snapshot_download("openbmb/VisRAG-Ret"))
rev = path.name                      # the snapshot folder is named by the commit
assert len(rev) == 40, path
Path(sys.argv[1]).write_text(rev + "\n")
print("VisRAG-Ret commit", rev, "->", path)
PY
echo
echo "done. VisRAG-Ret commit: $(cat "$REVFILE")"
echo "next: bash compare40/run_visrag.sh 132692299628 smoke"
