"""Embedding model wrappers.

- TextEmbedder: BGE-M3 dense (1024-d) + sparse (BM25-style token weights).
- ImageEmbedder: ColQwen2-v0.1 multi-vector page embeddings (ColPali family).
- Reranker:     mxbai-rerank-large-v2 (cross-encoder).

These are thin wrappers so we can swap any of them without changing the
ingestion or retrieval modules.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

log = logging.getLogger("mrag.embeddings")


# --------------------------------------------------------------------------- #
# Text embedder: BGE-M3 (dense + sparse)                                      #
# --------------------------------------------------------------------------- #

def _pool_token_weights(token_ids, weights, special_ids) -> Dict[int, float]:
    """One weight per DISTINCT token id: the largest across its positions.

    Repeats matter — "sign" occurring five times is one sparse dimension, not
    five. FlagEmbedding max-pools and drops CLS/EOS/PAD/UNK; this mirrors that.
    Zero weights are dropped: relu makes them exactly 0 and a stored 0 would
    waste an index in Qdrant.
    """
    out: Dict[int, float] = {}
    for tid, w in zip(token_ids, weights):
        tid, w = int(tid), float(w)
        if tid in special_ids or w <= 0.0:
            continue
        if w > out.get(tid, 0.0):
            out[tid] = w
    return out


class TextEmbedder:
    """BGE-M3 returning dense (1024-d) + sparse (token id -> weight) per text.

    Three loading paths, tried in order:

      1. FlagEmbedding's BGEM3FlagModel — the reference implementation.
      2. "direct": the same maths run on plain transformers (see below).
      3. sentence-transformers — DENSE ONLY, sparse silently empty.

    Path 2 exists because 1 and 3 were the only options and 1 could not load,
    so every run silently took 3 and the sparse leg was dead: all 5,812 chunk
    sparse vectors were empty, while both papers describe retrieval as dense +
    learned sparse fused by RRF.

    The cause is a version deadlock, already documented in requirements.txt:

        transformers  must be <4.55   (4.55+ has circular-import regressions
                                       that break `from transformers import
                                       PreTrainedModel`)
        FlagEmbedding must be >=1.4   (1.3.x hard-pins transformers==4.44.2,
                                       which makes pip unsolvable)
        but FlagEmbedding >=1.4 calls AutoModel.from_pretrained(dtype=...),
        and transformers 4.54.x rejects `dtype` on XLMRobertaModel:
        TypeError: XLMRobertaModel.__init__() got an unexpected keyword
        argument 'dtype'

    No pinning resolves that, so path 2 drops the dependency instead. BGE-M3's
    sparse head is public and small: a Linear(1024 -> 1) stored as
    sparse_linear.pt in the model repo. Per the BGE-M3 paper and the model
    card, the token weight is relu(W_lex . H[i]) over the encoder's last
    hidden state, max-pooled per token id, with the special tokens dropped;
    the dense vector is the L2-normalised CLS token. Verified against the
    weights published on the model card (see notebook 3.0).
    """

    DIM = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3", device: Optional[str] = None,
                 max_length: int = 8192) -> None:
        self.model_name = model_name
        self.device = device or _auto_device()
        self.max_length = max_length
        self._model = None
        self._mode = None       # "bge-m3" | "bge-m3-direct" | "st-fallback"
        self._tokenizer = None
        self._sparse_linear = None
        self._special_ids: set = set()

    # ----- lifecycle --------------------------------------------------------
    def load(self) -> "TextEmbedder":
        try:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(
                self.model_name, use_fp16=("cuda" in self.device), device=self.device,
            )
            self._mode = "bge-m3"
            log.info("TextEmbedder loaded: BGE-M3 via FlagEmbedding (dense+sparse)")
            return self
        except Exception as e:
            log.warning("FlagEmbedding unavailable (%r); trying the direct "
                        "transformers path", e)
        try:
            self._load_direct()
            self._mode = "bge-m3-direct"
            log.info("TextEmbedder loaded: BGE-M3 direct on transformers (dense+sparse)")
            return self
        except Exception as e:
            log.error("BGE-M3 direct path failed (%r); falling back to "
                      "sentence-transformers. SPARSE VECTORS WILL BE EMPTY and "
                      "retrieval will be dense-only.", e)
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self.model_name, device=self.device)
        self._mode = "st-fallback"
        return self

    def _load_direct(self) -> None:
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoModel, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModel.from_pretrained(self.model_name).to(self.device).eval()
        if "cuda" in self.device:
            self._model = self._model.half()

        weights_path = hf_hub_download(self.model_name, "sparse_linear.pt")
        state = torch.load(weights_path, map_location="cpu")
        linear = torch.nn.Linear(self._model.config.hidden_size, 1)
        linear.load_state_dict(state)
        self._sparse_linear = linear.to(self.device).eval()
        if "cuda" in self.device:
            self._sparse_linear = self._sparse_linear.half()

        tok = self._tokenizer
        # FlagEmbedding drops exactly these from the lexical weights.
        self._special_ids = {i for i in (tok.cls_token_id, tok.eos_token_id,
                                         tok.pad_token_id, tok.unk_token_id)
                             if i is not None}

    # ----- direct forward ---------------------------------------------------
    def _forward_direct(self, texts: List[str], batch_size: int,
                        want_dense: bool, want_sparse: bool):
        import torch
        dense_out, sparse_out = [], []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = self._tokenizer(batch, padding=True, truncation=True,
                                  max_length=self.max_length, return_tensors="pt")
            enc = {k: v.to(self.device) for k, v in enc.items()}
            with torch.no_grad():
                hidden = self._model(**enc, return_dict=True).last_hidden_state
                if want_dense:
                    cls = torch.nn.functional.normalize(hidden[:, 0], dim=-1)
                    dense_out.append(cls.float().cpu().numpy())
                if want_sparse:
                    w = torch.relu(self._sparse_linear(hidden)).squeeze(-1)  # (B, L)
                    w = w * enc["attention_mask"]            # ignore padding
                    ids = enc["input_ids"].cpu().numpy()
                    wv = w.float().cpu().numpy()
                    for row_ids, row_w in zip(ids, wv):
                        sparse_out.append(
                            _pool_token_weights(row_ids, row_w, self._special_ids))
        dense = np.concatenate(dense_out, axis=0).astype(np.float32) if want_dense else None
        return dense, sparse_out

    # ----- encoding --------------------------------------------------------
    def encode_dense(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        if self._mode == "bge-m3":
            out = self._model.encode(
                texts, batch_size=batch_size,
                return_dense=True, return_sparse=False, return_colbert_vecs=False,
            )
            return np.asarray(out["dense_vecs"], dtype=np.float32)
        if self._mode == "bge-m3-direct":
            dense, _ = self._forward_direct(texts, batch_size, True, False)
            return dense
        return self._model.encode(
            texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=True,
        ).astype(np.float32)

    def encode_sparse(self, texts: List[str], batch_size: int = 16) -> List[Dict[int, float]]:
        """{token_id: weight} per text. Empty dicts on the dense-only fallback."""
        if self._mode == "bge-m3":
            out = self._model.encode(
                texts, batch_size=batch_size,
                return_dense=False, return_sparse=True, return_colbert_vecs=False,
            )
            return [{int(k): float(v) for k, v in d.items()}
                    for d in out["lexical_weights"]]
        if self._mode == "bge-m3-direct":
            _, sparse = self._forward_direct(texts, batch_size, False, True)
            return sparse
        return [dict() for _ in texts]

    def encode_both(self, texts: List[str], batch_size: int = 16):
        if self._mode == "bge-m3":
            out = self._model.encode(
                texts, batch_size=batch_size,
                return_dense=True, return_sparse=True, return_colbert_vecs=False,
            )
            dense = np.asarray(out["dense_vecs"], dtype=np.float32)
            sparse = [{int(k): float(v) for k, v in d.items()}
                      for d in out["lexical_weights"]]
            return dense, sparse
        if self._mode == "bge-m3-direct":
            return self._forward_direct(texts, batch_size, True, True)
        return self.encode_dense(texts, batch_size), [dict() for _ in texts]

    def token_of(self, token_id: int) -> str:
        """Readable token for a sparse key — for checking, not for retrieval."""
        if self._tokenizer is None:
            return str(token_id)
        return self._tokenizer.convert_ids_to_tokens(int(token_id))


# --------------------------------------------------------------------------- #
# Image embedder: ColQwen2 (multi-vector via colpali-engine)                   #
# --------------------------------------------------------------------------- #

class ImageEmbedder:
    """ColQwen2 page-image embedder.

    Encodes a PIL Image (or a list of them) into a (num_patches, dim) array.
    Queries are encoded to (num_query_tokens, dim).
    """

    def __init__(
        self,
        model_name: str = "vidore/colqwen2-v0.1",
        device: Optional[str] = None,
        torch_dtype: Optional[str] = "bfloat16",
        revision: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.device = device or _auto_device()
        self.torch_dtype = torch_dtype
        # Pinned repo commit for the PROCESSOR. See CFG.colqwen_revision.
        self.revision = revision
        self._model = None
        self._processor = None

    def load(self) -> "ImageEmbedder":
        import torch
        from colpali_engine.models import ColQwen2, ColQwen2Processor
        dtype = getattr(torch, self.torch_dtype) if isinstance(self.torch_dtype, str) else self.torch_dtype
        # The MODEL is NOT given `revision`. ColQwen2 is a PEFT adapter; on
        # adapter repos transformers can apply `revision` to the BASE model
        # repo (vidore/colqwen2-base), where this commit does not exist. The
        # model already loads at main, and adapter_model.safetensors and
        # adapter_config.json at main are byte-identical to the pinned commit
        # (checked in Colab via blob ids). Only the processor needs the pin.
        self._model = ColQwen2.from_pretrained(
            self.model_name, torch_dtype=dtype, device_map=self.device,
        ).eval()
        self._processor = ColQwen2Processor.from_pretrained(
            self.model_name, revision=self.revision,
        )
        log.info("ImageEmbedder loaded: %s (model @ main, processor @ %s)",
                 self.model_name, self.revision or "main")
        return self

    def encode_images(self, images, batch_size: int = 2) -> List[np.ndarray]:
        import torch
        out: List[np.ndarray] = []
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            inputs = self._processor.process_images(batch).to(self._model.device)
            with torch.no_grad():
                emb = self._model(**inputs)
            for vec in emb:
                # vec: (n_patches, dim) tensor → numpy float32
                out.append(vec.detach().to(torch.float32).cpu().numpy())
        return out

    def encode_queries(self, queries: List[str]) -> List[np.ndarray]:
        import torch
        inputs = self._processor.process_queries(queries).to(self._model.device)
        with torch.no_grad():
            emb = self._model(**inputs)
        return [v.detach().to(torch.float32).cpu().numpy() for v in emb]


def maxsim(q_emb: np.ndarray, doc_emb: np.ndarray) -> float:
    """ColBERT-style late-interaction score: sum over query tokens of the max
    similarity to any document patch.

    Inputs are L2-normalised float32 arrays:
      q_emb:   (q, d)
      doc_emb: (p, d)
    """
    # (q, p) similarity matrix; sum over q of per-query max over p.
    sim = q_emb @ doc_emb.T
    return float(sim.max(axis=1).sum())


# --------------------------------------------------------------------------- #
# Reranker: mxbai-rerank-large-v2                                              #
# --------------------------------------------------------------------------- #

class Reranker:
    """Cross-encoder reranker."""

    def __init__(
        self,
        model_name: str = "mixedbread-ai/mxbai-rerank-large-v2",
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.device = device or _auto_device()
        self._model = None

    def load(self) -> "Reranker":
        try:
            from mxbai_rerank import MxbaiRerankV2
            self._model = MxbaiRerankV2(self.model_name)
            log.info("Reranker loaded: %s", self.model_name)
        except Exception as e:
            log.warning("mxbai-rerank not available (%r); falling back to BGE reranker", e)
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder("BAAI/bge-reranker-v2-m3", device=self.device)
        return self

    def rank(self, query: str, docs: List[str], top_k: int = 6) -> List[Tuple[int, float]]:
        """Return [(doc_index, score), ...] sorted descending."""
        if hasattr(self._model, "rank"):
            # mxbai-rerank's `rank()` kwarg for the candidate documents is
            # named `documents` in 0.1.x+ (the released API on PyPI today).
            # Earlier internal pre-release builds used `input`; we keep that
            # as a fallback so we don't break if someone pins an old build.
            try:
                res = self._model.rank(query=query, documents=docs, top_k=top_k)
            except TypeError:
                res = self._model.rank(query=query, input=docs, top_k=top_k)
            return [(r.index, float(r.score)) for r in res]
        # CrossEncoder fallback
        pairs = [(query, d) for d in docs]
        scores = self._model.predict(pairs)
        order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(i, float(scores[i])) for i in order]


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #

def _auto_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
