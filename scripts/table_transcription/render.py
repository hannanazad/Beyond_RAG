"""Render a table region straight from the PDF at high DPI.

The PNG crops are rasterised at 220 dpi; the PDF is vector, so a 400 dpi
render of the same region has ~20x the pixels. The first transcription error
found (W*; G >= 7 read as W >= 7) was a few pixels of ";  G" lost at crop
resolution.
"""
import json, os
import pymupdf

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # this folder
from paths import PDF, FIGURES, TABLES_OUT, REPO, RENDER_OUT  # noqa: E402

sys.path.insert(0, str(REPO))

_doc = pymupdf.open(str(PDF))
_crops = {os.path.basename(c["image_path"]): c
          for c in map(json.loads, open(FIGURES))
          if c.get("kind") == "Table"}

def render(name, dpi=400, pad=6, clip=None, out=None):
    c = _crops[name]
    x0, y0, x1, y1 = c["bbox"]
    r = pymupdf.Rect(max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad)
    if clip:                       # fractional sub-region (l, t, r, b) of the table
        w, h = r.width, r.height
        r = pymupdf.Rect(r.x0 + clip[0]*w, r.y0 + clip[1]*h,
                         r.x0 + clip[2]*w, r.y0 + clip[3]*h)
    pix = _doc.load_page(c["page_pdf"] - 1).get_pixmap(dpi=dpi, clip=r)
    RENDER_OUT.mkdir(parents=True, exist_ok=True)
    out = out or str(RENDER_OUT / f"{name.replace('.png','')}_{dpi}.png")
    pix.save(out)
    return out, pix.width, pix.height

if __name__ == "__main__":
    name = sys.argv[1]
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    clip = tuple(float(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    print(render(name, dpi, clip=clip))
