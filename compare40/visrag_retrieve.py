#!/usr/bin/env python
"""compare40/visrag_retrieve.py -- VisRAG page retrieval for the 40 compare40 questions.

Run with the Python of the VisRAG environment ($SCRATCH/vine/envs/visrag, made by
compare40/visrag_setup.sh), on a GPU node. compare40/visrag_job.slurm runs it.

What it does (the retrieval of Hannan's VisRAG baseline notebook of 27 Oct, unchanged in
method; only the inputs and outputs differ):
  1. Renders every page of the MUTCD PDF to PNG, as GEMS-RAG does (PyMuPDF, 180 dpi, no
     alpha), and records each page's printed label (page.get_label()).
  2. Embeds every page image with VisRAG-Ret (openbmb/VisRAG-Ret: one 2304-number vector a
     page, weighted mean pooling, L2 normalised), as in the official VisRAG README.
  3. Embeds every question with the official query instruction and ranks all pages by
     cosine similarity.
  4. Writes the top pages of each question and a manifest of versions and settings.

It reads the question text only. It never reads a gold answer or a gold page, never
calls an answer model and never changes a repository. The page vectors are saved in
blocks of 50 pages, so a second run (or a run cut off by the time limit) reuses them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MODEL_ID = "openbmb/VisRAG-Ret"
# official query instruction (VisRAG README, retriever demo and eval.sh)
INSTRUCTION = "Represent this query for retrieving relevant documents: "
EMBED_DIM = 2304
BLOCK = 50                      # pages per saved block of vectors (the unit of reuse)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_questions(path: Path) -> dict[str, str]:
    """compare40/questions_40.json ({id: text}) or a .jsonl of {question_id, question}.
    A gold field in the file stops the run: retrieval must see the question only."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
        for r in rows:
            extra = set(r) - {"question_id", "question"}
            if extra:
                sys.exit(f"STOP: {path} has fields other than the question: {sorted(extra)}")
        return {r["question_id"]: r["question"] for r in rows}
    d = json.loads(text)
    if not all(isinstance(v, str) for v in d.values()):
        sys.exit(f"STOP: {path} must map each question id to its text, nothing else")
    return d


# ---------------------------------------------------------------------------
# 1. page rendering (the settings of GEMS-RAG's mrag/figures.py render_pages)
# ---------------------------------------------------------------------------

def render_pages(pdf_path: Path, out_dir: Path, dpi: int) -> list[dict]:
    import fitz  # PyMuPDF

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pages, rendered = [], 0
    for i in range(doc.page_count):
        out = out_dir / f"page_{i + 1:04d}.png"
        page = doc.load_page(i)
        if not out.exists():
            page.get_pixmap(matrix=mat, alpha=False).save(str(out))
            rendered += 1
        label = page.get_label() or str(i + 1)
        pages.append({"page_pdf": i + 1, "page_printed": str(label), "image_path": str(out)})
        if (i + 1) % 200 == 0:
            log(f"  pages checked: {i + 1}/{doc.page_count}")
    log(f"Pages: {len(pages)} in the PDF, {rendered} newly rendered at {dpi} dpi")
    return pages


# ---------------------------------------------------------------------------
# 2. encoders
# ---------------------------------------------------------------------------

class VisRAGRetEncoder:
    """Official VisRAG-Ret usage (README, 'VisRAG-Ret' section)."""

    def __init__(self, revision: str | None, allow_fp16: bool) -> None:
        import torch
        import torch.nn.functional as F
        from transformers import AutoModel, AutoTokenizer

        if not torch.cuda.is_available():
            sys.exit("ERROR: no CUDA GPU found. This step must run in a GPU job.")
        if torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16
        elif allow_fp16:
            dtype = torch.float16
        else:
            sys.exit("ERROR: this GPU has no bfloat16 support. Use an A100, A40 or H100.")
        self.torch, self.F, self.dtype = torch, F, dtype
        log(f"Loading {MODEL_ID} (revision {revision or 'latest'}) in {dtype} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=revision, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(MODEL_ID, revision=revision, trust_remote_code=True,
                                               attn_implementation="sdpa", torch_dtype=dtype)
        self.model.eval()
        self.model.to("cuda")
        self.commit = getattr(self.model.config, "_commit_hash", None)
        self.gpu = torch.cuda.get_device_name(0)
        log(f"Model ready on {self.gpu}; commit {self.commit}")

    def _pool(self, hidden, attention_mask):
        attention_mask_ = attention_mask * attention_mask.cumsum(dim=1)
        s = self.torch.sum(hidden * attention_mask_.unsqueeze(-1).float(), dim=1)
        d = attention_mask_.sum(dim=1, keepdim=True).float()
        return s / d

    def _encode(self, items) -> np.ndarray:
        with self.torch.no_grad():
            if isinstance(items[0], str):
                inputs = {"text": list(items), "image": [None] * len(items), "tokenizer": self.tokenizer}
            else:
                inputs = {"text": [""] * len(items), "image": list(items), "tokenizer": self.tokenizer}
            outputs = self.model(**inputs)
            reps = self._pool(outputs.last_hidden_state, outputs.attention_mask)
            emb = self.F.normalize(reps, p=2, dim=1).detach().float().cpu().numpy()
        return emb.astype(np.float32)

    def encode_texts(self, texts):
        return self._encode(texts)

    def encode_images(self, images):
        return self._encode(images)

    def versions(self) -> dict:
        import transformers
        out = {"torch": self.torch.__version__, "transformers": transformers.__version__,
               "cuda": self.torch.version.cuda}
        try:
            import timm
            out["timm"] = timm.__version__
        except Exception:                                   # noqa: BLE001
            pass
        return out


class DryRunEncoder:
    """Fixed fake vectors, only to test the plumbing without a GPU (--dry_run)."""

    commit, gpu = "dry-run", "none"

    def _vec(self, key: str) -> np.ndarray:
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        v = np.random.default_rng(seed).standard_normal(EMBED_DIM).astype(np.float32)
        return v / np.linalg.norm(v)

    def encode_texts(self, texts):
        return np.stack([self._vec("q:" + t) for t in texts])

    def encode_images(self, images):
        return np.stack([self._vec("p:" + str(getattr(im, "filename", id(im)))) for im in images])

    def versions(self) -> dict:
        return {"dry_run": True}


# ---------------------------------------------------------------------------
# 3. page vectors, saved in blocks
# ---------------------------------------------------------------------------

def embed_pages(enc, pages: list[dict], emb_dir: Path, batch: int, tag: str) -> np.ndarray:
    from PIL import Image

    emb_dir.mkdir(parents=True, exist_ok=True)
    n, t0, done = len(pages), time.time(), 0
    for start in range(0, n, BLOCK):
        stop = min(start + BLOCK, n)
        block_file = emb_dir / f"{tag}_pages_{start + 1:04d}_{stop:04d}.npy"
        if block_file.exists() and np.load(block_file).shape == (stop - start, EMBED_DIM):
            continue
        vecs = []
        for i in range(start, stop, batch):
            imgs = []
            for p in pages[i:min(i + batch, stop)]:
                im = Image.open(p["image_path"]).convert("RGB")
                im.filename = p["image_path"]
                imgs.append(im)
            vecs.append(enc.encode_images(imgs))
        arr = np.concatenate(vecs, axis=0)
        np.save(block_file, arr)
        done += stop - start
        rate = (time.time() - t0) / max(done, 1)
        log(f"  embedded pages {start + 1}-{stop} of {n} ({rate:.2f} s a page, "
            f"about {rate * (n - stop) / 60:.1f} min left)")
    reps = np.concatenate([np.load(emb_dir / f"{tag}_pages_{s + 1:04d}_{min(s + BLOCK, n):04d}.npy")
                           for s in range(0, n, BLOCK)], axis=0)
    assert reps.shape == (n, EMBED_DIM), reps.shape
    return reps


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--questions", required=True, type=Path, help="compare40/questions_40.json")
    ap.add_argument("--pages_dir", required=True, type=Path, help="where the page PNGs are rendered")
    ap.add_argument("--out_dir", required=True, type=Path, help="where the retrieval files are written")
    ap.add_argument("--dpi", type=int, default=180)
    ap.add_argument("--save_top", type=int, default=20, help="ranked pages kept for each question")
    ap.add_argument("--batch", type=int, default=1, help="pages per forward pass")
    ap.add_argument("--revision", default=None, help="the VisRAG-Ret commit (visrag_setup.sh records it)")
    ap.add_argument("--allow_fp16", action="store_true")
    ap.add_argument("--dry_run", action="store_true", help="fake vectors, no GPU: only to test the plumbing")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    questions = load_questions(args.questions)
    log(f"Questions: {len(questions)} from {args.questions}")

    pages = render_pages(args.pdf, args.pages_dir, args.dpi)
    (args.out_dir / "pages.json").write_text(
        json.dumps([{k: p[k] for k in ("page_pdf", "page_printed")} for p in pages]), encoding="utf-8")

    enc = DryRunEncoder() if args.dry_run else VisRAGRetEncoder(args.revision, args.allow_fp16)
    # the blocks are named by the model commit, so vectors of another model are never reused
    tag = "dryrun" if args.dry_run else f"ret_{str(enc.commit or args.revision or 'unknown')[:12]}"
    reps = embed_pages(enc, pages, args.out_dir / "page_embeddings", args.batch, tag)
    log(f"Page vectors: {reps.shape}")

    ids = list(questions)
    queries = [INSTRUCTION + questions[q] for q in ids]
    q_reps = np.concatenate([enc.encode_texts(queries[i:i + 16]) for i in range(0, len(queries), 16)], axis=0)
    np.save(args.out_dir / "query_reps.npy", q_reps)

    scores = q_reps @ reps.T
    k = min(args.save_top, len(pages))
    with open(args.out_dir / "retrieval.jsonl", "w", encoding="utf-8") as f:
        for qi, qid in enumerate(ids):
            order = np.argsort(-scores[qi], kind="stable")[:k]
            top = [{"rank": r + 1, "page_pdf": pages[int(j)]["page_pdf"],
                    "page_printed": pages[int(j)]["page_printed"],
                    "score": round(float(scores[qi, int(j)]), 6)} for r, j in enumerate(order)]
            f.write(json.dumps({"question_id": qid,
                                "question_sha256": hashlib.sha256(questions[qid].encode()).hexdigest(),
                                "top_pages": top}, ensure_ascii=False) + "\n")
    log(f"Wrote the ranked pages of {len(ids)} questions (top {k})")

    manifest = {
        "method": "VisRAG (VisRAG-Ret page retrieval)", "model_id": MODEL_ID,
        "model_revision_requested": args.revision, "model_commit_loaded": enc.commit,
        "query_instruction": INSTRUCTION,
        "pooling": "weighted mean pooling over the last hidden states, L2 normalised",
        "similarity": "cosine (dot product of normalised vectors)",
        "page_render": {"library": "PyMuPDF", "dpi": args.dpi, "alpha": False},
        "n_pages": len(pages), "n_questions": len(ids), "save_top": k,
        "pdf": str(args.pdf), "pdf_sha256": sha256_file(args.pdf),
        "questions_file": str(args.questions), "questions_sha256": sha256_file(args.questions),
        "gpu": enc.gpu, "versions": {"python": platform.python_version(), **enc.versions()},
        "dry_run": bool(args.dry_run), "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.out_dir / "retrieval_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log("Done.")


if __name__ == "__main__":
    main()
