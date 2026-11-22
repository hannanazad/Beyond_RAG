#!/bin/bash
# vine2/vis_setup.sh -- once per system, on a Grace LOGIN node (it needs the internet).
#
#   bash vine2/vis_setup.sh m3docrag|vidorag|regionrag
#
# Gets everything one visual RAG system's retrieval needs, so its jobs run offline:
#   1. its code: a copy of its GitHub repository at the pinned commit, in $SCRATCH/vine/ext/,
#      never changed;
#   2. its Python environment, in $SCRATCH/vine/envs/ (separate, so nothing else is touched),
#      with the library versions its authors give:
#        m3docrag   colpali-engine 0.3.1 (its pyproject.toml), its other pins
#        vidorag    the exact versions of its uv.lock; plus a small OCR environment for its
#                   OCR script (FastDeploy PP-OCRv3) and the OCR model files
#        regionrag  its requirements.txt (torch 2.5.1, transformers 4.51.2, ...)
#   3. its models, into $SCRATCH/hf_cache; the commit of each is written to
#      $SCRATCH/vine/vis/SYSTEM_revisions.json, and the jobs load exactly those, offline.
#      A model already in the cache is used as it is (not downloaded again, so nothing VINE
#      uses changes). RegionRAG's model is gated: agree to its terms on huggingface.co with your
#      account and put a read token in $SCRATCH/vine/hf_token (chmod 600) first; the token is
#      read from that file only, never printed.
# Nothing is written to $HOME. Run it again: what is there and works is kept.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO/hprc/env.sh"
fail() { echo "STOPPED: $*" >&2; exit 1; }
SYSTEM="${1:-}"
case "$SYSTEM" in m3docrag|vidorag|regionrag) ;; *) fail "usage: bash vine2/vis_setup.sh m3docrag|vidorag|regionrag" ;; esac
[ -z "${SLURM_JOB_ID:-}" ] || fail "run this on a login node, not in a job"
[ "$(command -v uv || true)" = "$VINE_HOME/bin/uv" ] || fail "uv is not in $VINE_HOME/bin (hprc/setup.sh installs it)"
for u in https://pypi.org/simple/ https://huggingface.co https://github.com; do
    curl -sSfI --max-time 30 "$u" >/dev/null || fail "$u cannot be reached from here: run it on a login node"
done
mkdir -p "$VINE_HOME/ext" "$VINE_HOME/vis"
REVFILE="$VINE_HOME/vis/${SYSTEM}_revisions.json"

# ---- 1. the code, at the pinned commit (the same commits as the Python scripts) -------------
pinned() { sed -n 's/^PINNED = "\([0-9a-f]\{40\}\)".*/\1/p' "$REPO/vine2/$1"; }
case "$SYSTEM" in
    m3docrag)  URL=https://github.com/bloomberg/m3docrag;    COMMIT="$(pinned m3docrag_retrieve.py)" ;;
    vidorag)   URL=https://github.com/Alibaba-NLP/ViDoRAG;   COMMIT="$(pinned vidorag_ocr.py)" ;;
    regionrag) URL=https://github.com/Aeryn666/RegionRAG;    COMMIT="$(pinned regionrag_retrieve.py)" ;;
esac
[ ${#COMMIT} -eq 40 ] || fail "no pinned commit found in vine2/ for $SYSTEM"
CODE="$VINE_HOME/ext/$SYSTEM"
if [ -d "$CODE/.git" ]; then
    [ "$(git -C "$CODE" rev-parse HEAD)" = "$COMMIT" ] || fail "$CODE is at another commit; move it away and run again"
    [ -z "$(git -C "$CODE" status --porcelain --untracked-files=no)" ] || fail "$CODE is changed locally; move it away and run again"
    echo "code: $CODE at $COMMIT (kept)"
else
    [ ! -e "$CODE" ] || fail "$CODE exists but is not a git copy; move it away and run again"
    git init -q "$CODE"
    git -C "$CODE" remote add origin "$URL"
    GIT_LFS_SKIP_SMUDGE=1 git -C "$CODE" fetch -q --depth 1 origin "$COMMIT"
    GIT_LFS_SKIP_SMUDGE=1 git -C "$CODE" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
    [ "$(git -C "$CODE" rev-parse HEAD)" = "$COMMIT" ] || fail "could not get $URL at $COMMIT"
    echo "code: $URL at $COMMIT -> $CODE"
fi

# ---- 2. the environment(s) ---------------------------------------------------------------
make_env() {   # NAME PYTHON CHECK -- then the install commands as the rest of the arguments
    local name="$1" py="$2" check="$3"; shift 3
    local env="$VINE_HOME/envs/$name" vp="$VINE_HOME/envs/$name/bin/python"
    if [ -x "$vp" ] && "$vp" -I -c "$check" 2>/dev/null; then
        echo "environment $name: there and imports (kept)"; return 0
    fi
    echo "making environment $name (Python $py) in $env ..."
    uv python install "$py"
    local found; found="$(uv python find "$py")"
    case "$found" in "$VINE_HOME"/*) ;; *) fail "uv picked a Python outside $VINE_HOME: $found" ;; esac
    rm -rf "$env"
    uv venv -q "$env" --python "$py"
    "$@"
    "$vp" -I -c "$check" || fail "environment $name does not import"
    case "$("$vp" -I -c 'import sys; print(sys.prefix)')" in "$VINE_HOME"/*) ;; *) fail "$env is outside $VINE_HOME" ;; esac
}
case "$SYSTEM" in
  m3docrag)
    VP="$VINE_HOME/envs/m3docrag/bin/python"
    inst_m3() {
        uv pip install -q --python "$VP" --torch-backend=cu121 "torch==2.4.1" "torchvision==0.19.1"
        # M3DocRAG's pins (pyproject.toml): colpali-engine 0.3.1, accelerate 1.1.0, numpy 1.26.4;
        # transformers is not pinned there: 4.45.2, the release colpali-engine 0.3.1 came out with
        uv pip install -q --python "$VP" "colpali-engine==0.3.1" "transformers==4.45.2" "peft==0.11.1" \
            "accelerate==1.1.0" "numpy==1.26.4" "pillow==10.4.0" "pdf2image==1.17.0" "loguru==0.7.2" \
            "safetensors" "tqdm" "GPUtil" "requests" "sentencepiece"
    }
    make_env m3docrag 3.11 "import sys; assert sys.version_info[:2] == (3, 11); import torch, transformers, pdf2image, loguru, safetensors; from colpali_engine.models import ColPali, ColPaliProcessor, ColQwen2, ColQwen2Processor; print('torch', torch.__version__, '| transformers', transformers.__version__)" inst_m3
    MODELS="vidore/colpaligemma-3b-pt-448-base vidore/colpali-v1.2"
    ;;
  vidorag)
    VP="$VINE_HOME/envs/vidorag/bin/python"
    REQ="$VINE_HOME/vis/vidorag_requirements.txt"
    inst_vid() {
        # exactly the versions of ViDoRAG's uv.lock, installed from PyPI
        uv export -q --project "$CODE" --frozen --no-hashes --no-emit-project --no-dev --format requirements-txt -o "$REQ"
        uv pip install -q --python "$VP" --index-url https://pypi.org/simple -r "$REQ"
    }
    make_env vidorag 3.10 "import sys; assert sys.version_info[:2] == (3, 10); import torch, transformers, colpali_engine, sklearn, llama_index.core, llama_index.embeddings.huggingface, llama_index.readers.file; print('torch', torch.__version__, '| transformers', transformers.__version__)" inst_vid
    OP="$VINE_HOME/envs/vidorag_ocr/bin/python"
    inst_ocr() {
        uv pip install -q --python "$OP" --find-links https://www.paddlepaddle.org.cn/whl/fastdeploy.html \
            "fastdeploy-python==1.0.7" "numpy<2" "pillow" "pdf2image==1.17.0" "tqdm"
    }
    make_env vidorag_ocr 3.10 "import sys; assert sys.version_info[:2] == (3, 10); import fastdeploy, cv2, numpy, PIL, pdf2image; print('fastdeploy imports')" inst_ocr
    OCRM="$VINE_HOME/ext/vidorag_ocr_models"
    mkdir -p "$OCRM"
    for t in https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_det_infer.tar \
             https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_rec_infer.tar \
             https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar; do
        d="$OCRM/$(basename "$t" .tar)"
        if [ -s "$d/inference.pdmodel" ] && [ -s "$d/inference.pdiparams" ]; then continue; fi
        curl -sSfL --max-time 600 -o "$OCRM/.part.tar" "$t" || fail "could not download $t"
        tar -xf "$OCRM/.part.tar" -C "$OCRM" && rm -f "$OCRM/.part.tar"
        [ -s "$d/inference.pdmodel" ] || fail "$t did not give $d/inference.pdmodel"
    done
    if [ ! -s "$OCRM/en_dict.txt" ]; then
        curl -sSfL --max-time 120 -o "$OCRM/.en_dict.part" \
            https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/release/2.6/ppocr/utils/en_dict.txt \
            || fail "could not download en_dict.txt"
        mv "$OCRM/.en_dict.part" "$OCRM/en_dict.txt"
    fi
    echo "OCR models: $OCRM ($(cd "$OCRM" && sha256sum */inference.pdiparams en_dict.txt | cut -c1-12 | tr '\n' ' '))"
    command -v pdftoppm >/dev/null || fail "pdftoppm (poppler) is missing: ViDoRAG's pdf2image needs it"
    MODELS="vidore/colqwen2-v1.0 BAAI/bge-m3"
    VIDORAG_SMOKE=1
    ;;
  regionrag)
    VP="$VINE_HOME/envs/regionrag/bin/python"
    inst_reg() {
        # its README: torch 2.5.1 (CUDA 12.1), numpy 1.26.4, then requirements.txt
        uv pip install -q --python "$VP" --torch-backend=cu121 "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1"
        uv pip install -q --python "$VP" "numpy==1.26.4"
        uv pip install -q --python "$VP" -r "$CODE/requirements.txt"
        # its colpali_engine.evaluation package imports matplotlib (region_sim_evaluator.py), which
        # requirements.txt leaves out: its own pin (pyproject.toml, "interpretability")
        uv pip install -q --python "$VP" "matplotlib>=3.9.0,<4.0.0"
    }
    # every library its colpali_engine.evaluation package imports (vllm itself is only looked up
    # here: it is imported for real on the GPU node, where it is meant to run)
    make_env regionrag 3.10 "import sys, importlib.util; assert sys.version_info[:2] == (3, 10); import torch, transformers, peft, pytrec_eval, datasets, pandas, openai, cv2, matplotlib.pyplot, qwen_vl_utils, scipy; assert importlib.util.find_spec('vllm'); print('torch', torch.__version__, '| transformers', transformers.__version__)" inst_reg
    MODELS="Aeryn666/RegionRet"
    ;;
esac
[ "$SYSTEM" != m3docrag ] || command -v pdftoppm >/dev/null || fail "pdftoppm (poppler) is missing: M3DocRAG's pdf2image needs it"

# ---- 3. the models, and the commit of each (adapters: also the base they name) ------------
echo "models: $MODELS"
"$VP" -I - "$REVFILE" "$SYSTEM" "$COMMIT" "$VINE_HOME/hf_token" $MODELS <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
out, system, commit, token_file, repos = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5:]
token = token_file.read_text().strip() if token_file.is_file() else None
models, bases = {}, {}
# a base an adapter names by its authors' own folder (their training config): its Hugging Face id
LOCAL_BASES = {"colqwen2.5-base": "vidore/colqwen2.5-base"}

def complete(path):
    """A snapshot with its config and at least one weights file."""
    names = {f.name for f in path.iterdir()}
    cfg = bool(names & {"config.json", "adapter_config.json", "modules.json"})
    weights = any(n.endswith((".safetensors", ".bin")) for n in names) or any(
        f.suffix in (".safetensors", ".bin") for f in path.rglob("*"))
    return cfg and weights

def get(repo, revision=None):
    path = None
    if revision is None:
        try:
            path = Path(snapshot_download(repo, local_files_only=True))
            how = "already in the cache (kept)"
            if not complete(path):
                sys.exit(f"STOPPED: {repo} in the cache ({path}) has no config or no weights: tell Claude")
        except SystemExit:
            raise
        except Exception:                               # noqa: BLE001
            path = None
    if path is None:
        try:
            path = Path(snapshot_download(repo, revision=revision, token=token))
        except Exception as e:                          # noqa: BLE001
            gated = "gated" in str(e).lower() or "401" in str(e) or "403" in str(e)
            sys.exit(f"STOPPED: could not download {repo}: {type(e).__name__}"
                     + (" (gated: agree to its terms on huggingface.co and put a read token in "
                        f"{token_file})" if gated else ""))
        how = "downloaded" + (f" at {revision[:12]}" if revision else "")
    assert len(path.name) == 40 and complete(path), path
    models[repo] = path.name
    print(f"  {repo} @ {path.name[:12]}: {how}")
    cfg = path / "adapter_config.json"
    if cfg.is_file():
        conf = json.loads(cfg.read_text())
        base = conf.get("base_model_name_or_path") or ""
        print(f"  {repo} is an adapter on '{base}' (modules_to_save: {conf.get('modules_to_save')})")
        if base.startswith((".", "/")) or base.count("/") != 1:
            if base.startswith("/") or ".." in Path(base).parts:
                sys.exit(f"STOPPED: {repo} is an adapter on '{base}', not a plain relative path: tell Claude")
            hub = LOCAL_BASES.get(Path(base).name)
            if not hub:
                sys.exit(f"STOPPED: {repo} is an adapter on '{base}', which is not a Hugging Face model id: "
                         f"tell Claude")
            # the base as it was when the adapter was uploaded: its newest commit before that
            api = HfApi()
            first = min(c.created_at for c in api.list_repo_commits(repo, token=token))
            older = [c for c in api.list_repo_commits(hub, token=token) if c.created_at <= first]
            if not older:
                sys.exit(f"STOPPED: {hub} has no commit before {repo} was uploaded ({first}): tell Claude")
            rev = max(older, key=lambda c: c.created_at).commit_id
            bases[repo] = {"declared": base, "repo": hub, "local": True, "adapter_uploaded": str(first)}
            get(hub, revision=rev)
        else:
            bases[repo] = {"declared": base, "repo": base, "local": False}
            if base not in models:
                get(base)

for r in repos:
    get(r)
Path(out).write_text(json.dumps({"system": system, "code_commit": commit, "models": models, "bases": bases,
                                 "made_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2))
print(f"model commits -> {out}")
PY

# ---- 4. ViDoRAG's text side offline, with the job's settings (llama-index's own caches) ------
if [ "${VIDORAG_SMOKE:-0}" = 1 ]; then
    echo "offline check of ViDoRAG's text side (sentence splitter, BGE-M3 on CPU) ..."
    ( unset TIKTOKEN_CACHE_DIR
      export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLAMA_INDEX_CACHE_DIR="$HF_HUB_CACHE"
      "$VP" -I -c "
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
n = SentenceSplitter(chunk_size=1024, chunk_overlap=0).split_text('Zorb markers shall be wide. ' * 50)
e = HuggingFaceEmbedding(model_name='BAAI/bge-m3', device='cpu', trust_remote_code=True)
print('splitter chunks', len(n), '| BGE-M3 vector', len(e.get_text_embedding('zorb marker')))
" ) || fail "ViDoRAG's text side does not load offline: tell Claude"
fi
echo
echo "done: $SYSTEM is ready. Next:  bash vine2/run_vine2_vis_grace.sh 132692299628 QUESTIONS_FILE $SYSTEM"
