#!/usr/bin/env python3
"""One-shot MUTCD ingestion (v3): chunks + figures + sign codes + KG + Qdrant.

Run once on a login node or as a SLURM job. Idempotent — caches intermediate
artefacts so re-runs only do the missing pieces.

Outputs (under $SCRATCH/MRAG/):
  page_images/page_NNNN.png          - fallback page renders for ColPali / display
  figures/<figure_id>_pNNNN.png      - one PNG per real Figure/Table
  mmrag_cache_v3/chunks.jsonl        - typed paragraph chunks (one row each)
  mmrag_cache_v3/figures.jsonl       - figure metadata
  mmrag_cache_v3/sign_codes.json     - sign-code dictionary
  mmrag_cache_v3/graph.gpickle       - NetworkX MultiDiGraph
  qdrant_db/                          - Qdrant local-file collections
"""
from __future__ import annotations

import argparse
import numpy as np
import logging
import sys
from pathlib import Path

# Add the workspace root to sys.path so `import mrag` works when run from anywhere.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mrag.config   import CFG
from mrag          import parsing as P
from mrag          import figures as F
from mrag          import sign_codes as SC
from mrag          import kg as KGM
from mrag.embeddings import TextEmbedder, ImageEmbedder
from mrag.vector_store import VectorStore, ChunkRow, FigureRow, PageRow, chunk_id_to_int

import fitz
from PIL import Image
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
)
log = logging.getLogger("ingest_v3")


# --------------------------------------------------------------------------- #
def step_render_pages():
    n = F.render_pages(CFG.pdf_path, CFG.page_images_dir, dpi=CFG.page_dpi)
    log.info("Rendered %d new page PNGs (DPI=%d)", n, CFG.page_dpi)


def step_extract_figures():
    if CFG.figures_jsonl.exists():
        log.info("figures.jsonl exists; skipping extraction (delete to redo)")
        return F.read_jsonl(CFG.figures_jsonl)
    figs = F.extract_figures(CFG.pdf_path, CFG.figures_dir, dpi=CFG.figure_dpi)
    F.write_jsonl(figs, CFG.figures_jsonl)
    log.info("Wrote %d figure crops -> %s", len(figs), CFG.figures_jsonl)
    return figs


def step_parse_chunks():
    if CFG.chunks_jsonl.exists():
        log.info("chunks.jsonl exists; skipping parse (delete to redo)")
        return P.read_chunks_jsonl(CFG.chunks_jsonl)
    doc = fitz.open(str(CFG.pdf_path))
    toc = doc.get_toc()
    # Bootstrap sign-code dictionary from outline first so the parser can tag chunks.
    outline_codes = SC.mine_from_outline(toc)
    log.info("Bootstrapped %d sign codes from outline", len(outline_codes))
    sign_re = SC.get_sign_code_re()
    chunks = P.parse_chunks(CFG.pdf_path, sign_code_re=sign_re)
    P.write_chunks_jsonl(chunks, CFG.chunks_jsonl)
    log.info("Parsed %d chunks -> %s", len(chunks), CFG.chunks_jsonl)
    return chunks


def step_sign_codes(chunks):
    if CFG.sign_codes_json.exists():
        log.info("sign_codes.json exists; skipping (delete to redo)")
        return SC.read_json(CFG.sign_codes_json)
    doc = fitz.open(str(CFG.pdf_path))
    toc = doc.get_toc()
    entries = SC.mine_from_outline(toc)
    entries = SC.mine_from_chunks(chunks, entries)
    # Backfill sign_codes_depicted for figures from their captions.
    SC.write_json(entries, CFG.sign_codes_json)
    log.info("Wrote %d sign-code entries -> %s", len(entries), CFG.sign_codes_json)
    return entries


def step_enrich_figures(figures, sign_codes_dict):
    """Mine sign codes depicted in each figure's caption / title text."""
    sign_re = SC.get_sign_code_re()
    for f in figures:
        codes = set()
        for blob in (f.caption, f.title):
            for m in sign_re.finditer(blob or ""):
                codes.add(m.group(1).upper())
        f.sign_codes_depicted = sorted(codes)
    F.write_jsonl(figures, CFG.figures_jsonl)
    return figures


def step_build_kg(chunks, figures, sign_codes_dict):
    if CFG.graph_pickle.exists():
        log.info("graph.gpickle exists; skipping KG build (delete to redo)")
        return KGM.read(CFG.graph_pickle)
    g = KGM.build(chunks, figures, sign_codes_dict)
    KGM.write(g, CFG.graph_pickle)
    log.info("KG built: %d nodes, %d edges -> %s",
             g.number_of_nodes(), g.number_of_edges(), CFG.graph_pickle)
    return g


def _texts_fingerprint(texts) -> str:
    """sha256 over the exact strings that get embedded, in order."""
    import hashlib
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def step_text_embeddings(chunks, figures):
    """BGE-M3 chunks (dense + sparse) and figure captions (dense).

    Caches under cache_dir so re-runs skip encoding. The cache is now
    CHECKED before use. The old version loaded any cache file it found, so
    after the crops were redone it paired 727 old caption vectors with 648
    new figures, by position. Chunk and caption caches are checked
    separately, so a stale caption cache re-encodes only the captions.

    A manifest (text_embeddings_manifest.json) records a fingerprint of the
    exact texts embedded and which encoder mode produced them.
    """
    import json
    cache_chunk_dense  = CFG.cache_dir / "chunks_dense.npy"
    cache_chunk_sparse = CFG.cache_dir / "chunks_sparse.json"
    cache_fig_dense    = CFG.cache_dir / "figures_dense.npy"
    manifest_path      = CFG.cache_dir / "text_embeddings_manifest.json"

    chunk_texts = [
        f"[{c.content_type}] Section {c.section_id} — {c.section_title}. {c.text}"
        for c in chunks
    ]
    figure_texts = [
        f"{f.figure_id}. {f.title or f.caption}. Depicts: "
        f"{', '.join(f.sign_codes_depicted) or '—'}."
        for f in figures
    ]
    fp_chunks, fp_figs = _texts_fingerprint(chunk_texts), _texts_fingerprint(figure_texts)

    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            log.warning("unreadable %s (%r); treating caches as unverified", manifest_path.name, e)

    # ---- chunks -------------------------------------------------------------
    dense_c = sparse_c = None
    if cache_chunk_dense.exists() and cache_chunk_sparse.exists():
        d = np.load(cache_chunk_dense)
        with open(cache_chunk_sparse, "r") as fh:
            sraw = json.load(fh)
        rec = manifest.get("chunks", {})
        if len(d) != len(chunks) or len(sraw) != len(chunks):
            log.warning("chunk embedding cache is STALE: %d dense / %d sparse rows for %d chunks; re-encoding",
                        len(d), len(sraw), len(chunks))
        elif rec and rec.get("sha256") != fp_chunks:
            log.warning("chunk embedding cache is STALE: chunk texts changed since it was built; re-encoding")
        else:
            if not rec:
                # Caches from before the manifest existed: row counts match, so
                # accept them rather than force a long re-encode, and say so.
                log.warning("chunk embedding cache has no manifest; accepting on row count (%d)", len(d))
            dense_c = d
            sparse_c = [{int(k): float(v) for k, v in x.items()} for x in sraw]
            log.info("chunk embeddings: cache OK (%d rows)", len(d))

    # ---- figure captions ----------------------------------------------------
    dense_f = None
    if cache_fig_dense.exists():
        d = np.load(cache_fig_dense)
        rec = manifest.get("figures", {})
        if len(d) != len(figures):
            log.warning("caption embedding cache is STALE: %d rows for %d figures; re-encoding captions only",
                        len(d), len(figures))
        elif rec.get("sha256") != fp_figs:
            # No manifest, or captions changed. Captions are short, so
            # re-encoding is cheap; never trust an unverified caption cache.
            log.warning("caption embedding cache is unverified or changed; re-encoding captions only")
        else:
            dense_f = d
            log.info("caption embeddings: cache OK (%d rows)", len(d))

    if dense_c is not None and dense_f is not None:
        _warn_if_sparse_empty(sparse_c, manifest.get("chunks", {}).get("encoder_mode"))
        return (dense_c, sparse_c, dense_f)

    log.info("Loading BGE-M3 text embedder ...")
    te = TextEmbedder(CFG.bge_m3_model).load()
    mode = getattr(te, "_mode", None)
    if mode != "bge-m3":
        log.error("TextEmbedder is in %r mode, NOT bge-m3: sparse (keyword) vectors "
                  "produced now will be EMPTY", mode)

    if dense_c is None:
        log.info("Encoding %d chunks (dense + sparse) ...", len(chunk_texts))
        dense_c, sparse_c = te.encode_both(chunk_texts, batch_size=16)
        np.save(cache_chunk_dense, dense_c)
        with open(cache_chunk_sparse, "w") as fh:
            json.dump([{str(k): v for k, v in x.items()} for x in sparse_c], fh)
        manifest["chunks"] = {"n": len(chunks), "sha256": fp_chunks, "encoder_mode": mode}

    if dense_f is None:
        log.info("Encoding %d figure captions ...", len(figure_texts))
        dense_f = te.encode_dense(figure_texts, batch_size=32)
        np.save(cache_fig_dense, dense_f)
        manifest["figures"] = {"n": len(figures), "sha256": fp_figs, "encoder_mode": mode}

    if "chunks" not in manifest:
        # chunk cache was accepted on row count; record what it now matches
        manifest["chunks"] = {"n": len(chunks), "sha256": fp_chunks, "encoder_mode": "unknown (pre-manifest)"}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("  cached -> %s", manifest_path.name)

    _warn_if_sparse_empty(sparse_c, manifest.get("chunks", {}).get("encoder_mode"))
    return (dense_c, sparse_c, dense_f)


def _warn_if_sparse_empty(sparse_c, mode) -> None:
    n_nonempty = sum(1 for x in sparse_c if x)
    if n_nonempty == 0:
        log.error("ALL %d chunk sparse (keyword) vectors are EMPTY (encoder mode: %s). "
                  "Hybrid search is running dense-only.", len(sparse_c), mode)
    else:
        log.info("chunk sparse vectors: %d of %d non-empty", n_nonempty, len(sparse_c))

_IMAGE_EMBEDDER = None


def _get_image_embedder() -> ImageEmbedder:
    """Load ColQwen2 once per ingest run and share it between the page step
    and the figure-crop step (they used to load it twice)."""
    global _IMAGE_EMBEDDER
    if _IMAGE_EMBEDDER is None:
        _IMAGE_EMBEDDER = ImageEmbedder(
            CFG.colqwen_model, revision=getattr(CFG, "colqwen_revision", None),
        ).load()
    return _IMAGE_EMBEDDER


def step_page_embeddings(out_dir: Path):
    """Encode page PNGs with ColQwen2. Returns list[(page_num, path, vectors)].

    Caches each page's multi-vector as <cache_dir>/colqwen_pages/<page_num>.npy
    so re-runs after a session death only re-encode missing pages.
    """
    cache = CFG.cache_dir / "colqwen_pages"
    cache.mkdir(parents=True, exist_ok=True)

    pngs = sorted(CFG.page_images_dir.glob("page_*.png"))
    if not pngs:
        log.warning("No page PNGs to embed; skipping.")
        return None

    # Skip pages we've already encoded.
    todo = [p for p in pngs if not (cache / f"{int(p.stem.split('_')[1]):04d}.npy").exists()]
    log.info("ColPali pages: %d total, %d already cached, %d to encode",
             len(pngs), len(pngs) - len(todo), len(todo))

    if todo:
        log.info("Loading ColQwen2 image embedder ...")
        try:
            ie = _get_image_embedder()
        except Exception as e:
            log.warning("ColQwen2 unavailable (%r); skipping page embeddings.", e)
            return None

        batch = 2
        for i in tqdm(range(0, len(todo), batch), desc="colqwen pages"):
            batch_paths = todo[i:i+batch]
            imgs = [Image.open(p).convert("RGB") for p in batch_paths]
            vecs = ie.encode_images(imgs, batch_size=batch)
            for path, v in zip(batch_paths, vecs):
                page_num = int(path.stem.split("_")[1])
                np.save(cache / f"{page_num:04d}.npy", v)

    # Now collect everything (newly-encoded + previously-cached) for the upsert.
    out = []
    for p in pngs:
        page_num = int(p.stem.split("_")[1])
        vec = np.load(cache / f"{page_num:04d}.npy")
        out.append((page_num, str(p), vec))
    log.info("ColPali pages: %d page vectors ready", len(out))
    return out


def _figure_cache_name(figure_id: str) -> str:
    """Filesystem-safe slug for a figure_id like 'Figure 2B-1'."""
    return (
        figure_id.replace(" ", "_").replace("/", "_").replace(".", "_")
        .replace(":", "_")
    )


def step_figure_visual_embeddings(figures):
    """Encode each figure CROP with ColQwen2 — added in v5.

    Mirrors step_page_embeddings but operates on figure crops instead of
    full-page renders, and caches under colqwen_figures/. Returns
    list[(figure_id, image_path, vectors)] for the upsert step, or None
    if ColQwen2 can't load or there are no figures.

    Reuses any ColQwen2 instance loaded earlier in this run by returning
    via a module-level cache, so we don't pay the model-load cost twice.
    """
    if not figures:
        log.warning("No figures to embed visually; skipping.")
        return None

    cache = CFG.cache_dir / "colqwen_figures"
    cache.mkdir(parents=True, exist_ok=True)

    # ONE ENTRY PER CROP, keyed by the crop's file name. Keying by figure_id
    # made every sheet of a multi-sheet figure (116 of 553 ids) write to the
    # same cache file, so only the last sheet survived. Crop file names are
    # unique (648 crops, 648 names).
    pairs: list[tuple[str, str, Path]] = []  # (figure_id, image_path, cache_path)
    for f in figures:
        ip = getattr(f, "image_path", "") or ""
        if not ip or not Path(ip).exists():
            continue
        cp = cache / f"crop__{_figure_cache_name(Path(ip).stem)}.npy"
        pairs.append((f.figure_id, ip, cp))

    todo = [(fid, ip, cp) for fid, ip, cp in pairs if not cp.exists()]
    log.info("ColPali figures: %d total, %d already cached, %d to encode",
             len(pairs), len(pairs) - len(todo), len(todo))

    if todo:
        log.info("Loading ColQwen2 image embedder (for figure crops) ...")
        try:
            ie = _get_image_embedder()
        except Exception as e:
            log.warning("ColQwen2 unavailable (%r); skipping figure-visual embeddings.", e)
            return None

        batch = 2
        for i in tqdm(range(0, len(todo), batch), desc="colqwen figures"):
            sub = todo[i:i+batch]
            imgs = [Image.open(ip).convert("RGB") for _fid, ip, _cp in sub]
            vecs = ie.encode_images(imgs, batch_size=batch)
            for (fid, ip, cp), v in zip(sub, vecs):
                np.save(cp, v)

    out = []
    for fid, ip, cp in pairs:
        v = np.load(cp)
        out.append((fid, ip, v))
    log.info("ColPali figures: %d figure-image vectors ready", len(out))
    return out


def step_upsert_qdrant(chunks, figures, dense_c, sparse_c, dense_f, page_data,
                       figure_visual_data=None):
    store = VectorStore(CFG.qdrant_dir)
    page_dim = page_data[0][2].shape[1] if page_data else 128
    # figure-visual uses the same ColPali dim as pages
    fig_visual_dim = (
        figure_visual_data[0][2].shape[1] if figure_visual_data else page_dim
    )
    store.init_collections(
        CFG.coll_chunks, CFG.coll_figures, CFG.coll_pages,
        text_dim=dense_c.shape[1],
        page_patch_dim=page_dim,
        use_binary_quantization_for_pages=CFG.colqwen_use_binary_quantization,
        coll_figures_visual=CFG.coll_figures_visual,
        figure_patch_dim=fig_visual_dim,
    )

    # Chunks
    chunk_rows = []
    for c, dv, sv in zip(chunks, dense_c, sparse_c):
        payload = {
            "chunk_id":      c.chunk_id,
            "part":          c.part,
            "chapter":       c.chapter,
            "section_id":    c.section_id,
            "section_title": c.section_title,
            "content_type":  c.content_type,
            "ordinal":       c.ordinal,
            "page_pdf":      c.page_pdf,
            "page_printed":  c.page_printed,
            "figure_refs":   c.figure_refs,
            "table_refs":    c.table_refs,
            "section_refs":  c.section_refs,
            "sign_codes":    c.sign_codes,
            "modal_verbs":   c.modal_verbs,
            "text":          c.text,
        }
        chunk_rows.append(ChunkRow(
            id=chunk_id_to_int(c.chunk_id), dense=dv, sparse=sv, payload=payload
        ))
    log.info("Upserting %d chunks to Qdrant ...", len(chunk_rows))
    store.upsert_chunks(CFG.coll_chunks, chunk_rows)

    # Figures
    fig_rows = []
    for f, dv in zip(figures, dense_f):
        payload = {
            "figure_id":           f.figure_id,
            "kind":                f.kind,
            "page_pdf":            f.page_pdf,
            "page_printed":        f.page_printed,
            "caption":             f.caption,
            "title":               f.title,
            "image_path":          f.image_path,
            "sign_codes_depicted": f.sign_codes_depicted,
        }
        fig_rows.append(FigureRow(
            # one point per crop; chunk_id_to_int(f.figure_id) made the sheets
            # of a multi-sheet figure overwrite each other
            id=chunk_id_to_int(f"figcap:{Path(f.image_path).name}"), dense=dv, payload=payload
        ))
    log.info("Upserting %d figures to Qdrant ...", len(fig_rows))
    store.upsert_figures(CFG.coll_figures, fig_rows)

    # Pages (multivector)
    if page_data:
        page_rows = []
        for page_num, path, vecs in page_data:
            payload = {"page_pdf": page_num, "page_printed": str(page_num),
                       "image_path": path}
            page_rows.append(PageRow(
                id=int(page_num), vectors=vecs, payload=payload
            ))
        log.info("Upserting %d pages (ColPali multivectors) to Qdrant ...", len(page_rows))
        store.upsert_pages(CFG.coll_pages, page_rows)

    # Figures-visual (multivector, ColPali on figure crops) -----------------
    if figure_visual_data:
        # Build a quick map from figure_id -> figures.jsonl payload so we
        # can attach caption / page / sign_codes alongside the vector.
        # Look up by CROP path, not figure_id: several crops share an id.
        fig_lookup = {getattr(f, "image_path", ""): f for f in figures}
        fv_rows = []
        for fid, ip, vecs in figure_visual_data:
            f = fig_lookup.get(ip)
            payload = {
                "figure_id":           fid,
                "kind":                getattr(f, "kind", "") if f else "",
                "page_pdf":            getattr(f, "page_pdf", None) if f else None,
                "page_printed":        getattr(f, "page_printed", None) if f else None,
                "caption":             getattr(f, "caption", "") if f else "",
                "title":               getattr(f, "title", "") if f else "",
                "image_path":          ip,
                "sign_codes_depicted": list(getattr(f, "sign_codes_depicted", []) or [])
                                       if f else [],
                "sheet":               getattr(f, "sheet", None) if f else None,
            }
            fv_rows.append(PageRow(
                # one Qdrant point per crop; "figvis:<figure_id>" collided
                id=chunk_id_to_int(f"figvis:{Path(ip).name}"),
                vectors=vecs,
                payload=payload,
            ))
        log.info("Upserting %d figure-visual rows (ColPali on crops) to Qdrant ...",
                 len(fv_rows))
        store.upsert_figures_visual(CFG.coll_figures_visual, fv_rows)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pages",      action="store_true",
                    help="Skip ColPali page-embedding step")
    ap.add_argument("--skip-render",     action="store_true",
                    help="Skip page rendering")
    ap.add_argument("--skip-figures",    action="store_true",
                    help="Skip figure crop extraction")
    ap.add_argument("--skip-figure-visual", action="store_true",
                    help="Skip ColPali embedding of figure CROPS (v5+ feature)")
    args = ap.parse_args()

    log.info("MUTCD MRAG ingestion v3")
    log.info("PDF: %s", CFG.pdf_path)
    log.info("Out: %s", CFG.base_dir)

    assert CFG.pdf_path.exists(), f"PDF not found at {CFG.pdf_path}"

    if not args.skip_render:
        step_render_pages()
    figures = []
    if not args.skip_figures:
        figures = step_extract_figures()
    else:
        figures = F.read_jsonl(CFG.figures_jsonl) if CFG.figures_jsonl.exists() else []

    chunks = step_parse_chunks()
    sign_codes_dict = step_sign_codes(chunks)
    figures = step_enrich_figures(figures, sign_codes_dict)
    step_build_kg(chunks, figures, sign_codes_dict)

    dense_c, sparse_c, dense_f = step_text_embeddings(chunks, figures)
    page_data = None if args.skip_pages else step_page_embeddings(CFG.page_images_dir)
    figure_visual_data = (
        None if args.skip_figure_visual
        else step_figure_visual_embeddings(figures)
    )

    step_upsert_qdrant(chunks, figures, dense_c, sparse_c, dense_f, page_data,
                       figure_visual_data=figure_visual_data)
    log.info("Done. Qdrant at %s | KG at %s", CFG.qdrant_dir, CFG.graph_pickle)

    # Auto-snapshot to Drive on Colab so a session death never wipes the work.
    if CFG.environment == "colab":
        try:
            from mrag.colab_setup import snapshot_qdrant_to_drive
            log.info("Auto-snapshotting Qdrant to Drive ...")
            snapshot_qdrant_to_drive(drive_subdir=CFG.base_dir.name)
            log.info("Snapshot saved. Next session restores in ~30 s.")
        except Exception as e:
            log.warning(
                "Auto-snapshot failed (%r). Run `from mrag.colab_setup "
                "import snapshot_qdrant_to_drive; snapshot_qdrant_to_drive()` "
                "manually before the session dies.", e
            )


if __name__ == "__main__":
    main()
