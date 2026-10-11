# hprc/env.sh -- where everything lives on FASTER (TAMU HPRC).
#
# Every script in hprc/ starts by reading this file. You can also read it in
# your own terminal:   source $SCRATCH/Beyond_RAG_repo/hprc/env.sh
#
# Everything goes in $SCRATCH. NOTHING is written to $HOME: home has room for
# only 10 GB and 10,000 files, and a Python install alone is tens of thousands
# of files. So the tools, Python itself, both environments and every cache
# (uv, pip, Hugging Face, vLLM, torch, Triton, CUDA) are pointed at $SCRATCH.

if [ -z "${SCRATCH:-}" ] || [ ! -d "${SCRATCH:-/nonexistent}" ]; then
    echo "hprc/env.sh: \$SCRATCH is not set or does not exist -- run this on FASTER" >&2
    return 1 2>/dev/null || exit 1
fi

# ---- the three places ------------------------------------------------------
export VINE_HOME="$SCRATCH/vine"                          # tools, Python, environments, caches, logs
export MRAG_BASE_DIR="$SCRATCH/Beyond_RAG"                # the data copied from Google Drive
export VINE_REPO="${VINE_REPO:-$SCRATCH/Beyond_RAG_repo}" # the code (git clone)
export MRAG_ENV=hprc                                      # mrag/config.py: the HPRC paths

export RETR_ENV="$VINE_HOME/envs/retrieval"   # Python 3.12 + torch 2.6 + the retrieval stack
export VLLM_ENV="$VINE_HOME/envs/vllm"        # Python 3.12 + vLLM 0.31.0 (the parser's server)

# ---- no module may change Python or its libraries --------------------------
# (a loaded module can set PYTHONPATH or LD_LIBRARY_PATH and pull in other
#  libraries). Job scripts load WebProxy again after this.
if type module >/dev/null 2>&1; then
    module purge >/dev/null 2>&1 || true
fi
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP VIRTUAL_ENV CONDA_PREFIX
export PYTHONNOUSERSITE=1                     # never read packages from ~/.local
export PYTHONUSERBASE="$VINE_HOME/pyuser"

# ---- uv (the installer) and the Python it installs: in scratch ---------------
export UV_INSTALL_DIR="$VINE_HOME/bin"
export UV_NO_MODIFY_PATH=1                    # the uv installer must not edit ~/.bashrc
export UV_PYTHON_INSTALL_DIR="$VINE_HOME/python"
export UV_PYTHON_BIN_DIR="$VINE_HOME/bin"
export UV_PYTHON_PREFERENCE=only-managed      # never use the system's or a module's Python
export UV_CACHE_DIR="$VINE_HOME/cache/uv"
export UV_TOOL_DIR="$VINE_HOME/uv_tools"
export UV_TOOL_BIN_DIR="$VINE_HOME/bin"
case ":$PATH:" in *":$VINE_HOME/bin:"*) ;; *) export PATH="$VINE_HOME/bin:$PATH" ;; esac

# ---- every cache: in scratch ---------------------------------------------------
export XDG_CACHE_HOME="$VINE_HOME/cache"
export XDG_DATA_HOME="$VINE_HOME/share"
export PIP_CACHE_DIR="$VINE_HOME/cache/pip"
# Hugging Face: ONE cache, the same folder mrag/config.py uses on HPRC
export HF_HOME="$SCRATCH/hf_cache"
export HF_HUB_CACHE="$SCRATCH/hf_cache"
export HUGGINGFACE_HUB_CACHE="$SCRATCH/hf_cache"
export TRANSFORMERS_CACHE="$SCRATCH/hf_cache"
export HF_HUB_DISABLE_TELEMETRY=1
# vLLM, torch, Triton, FlashInfer, CUDA
export VLLM_CACHE_ROOT="$VINE_HOME/cache/vllm"
export VLLM_CONFIG_ROOT="$VINE_HOME/config/vllm"
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1
export TRITON_HOME="$VINE_HOME/cache"
export TRITON_CACHE_DIR="$VINE_HOME/cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$VINE_HOME/cache/inductor"
export TORCH_EXTENSIONS_DIR="$VINE_HOME/cache/torch_extensions"
export TORCH_HOME="$VINE_HOME/cache/torch"
export FLASHINFER_WORKSPACE_BASE="$VINE_HOME"
export CUDA_CACHE_PATH="$VINE_HOME/cache/nv"
# small ones that also default to $HOME
export NUMBA_CACHE_DIR="$VINE_HOME/cache/numba"
export MPLCONFIGDIR="$VINE_HOME/cache/matplotlib"
export TIKTOKEN_CACHE_DIR="$VINE_HOME/cache/tiktoken"
export OUTLINES_CACHE_DIR="$VINE_HOME/cache/outlines"
export IPYTHONDIR="$VINE_HOME/config/ipython"
export TOKENIZERS_PARALLELISM=false

mkdir -p "$VINE_HOME/bin" "$VINE_HOME/envs" "$VINE_HOME/cache" "$VINE_HOME/logs" "$HF_HOME"
