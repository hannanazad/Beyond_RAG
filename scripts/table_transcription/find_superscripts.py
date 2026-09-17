"""Find superscript markers printed in table CAPTIONS and COLUMN HEADINGS.

Markers inside data cells are easy to see; markers on a heading or in the
caption are small, sit above the grid, and were being missed by eye. A marker
there governs a whole column or the whole table, so missing one drops the
condition from every value beneath it.

A marker is a run set noticeably smaller than the largest run on its own line.
"""
import json, re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # this folder
from paths import PDF, FIGURES, TABLES_OUT, REPO, RENDER_OUT  # noqa: E402

sys.path.insert(0, str(REPO))

from mrag.font_index import get_font_index  # noqa: E402

fi = get_font_index(str(PDF))
crops = [json.loads(l) for l in open(FIGURES)
         if json.loads(l).get("kind") == "Table"]

def lines_in(crop):
    pno = crop["page_pdf"]
    runs = [(t, l, w, h, fam, size, txt)
            for (txt, fam, size, t, l, w, h) in fi.page_runs_with_boxes(pno)]
    if not runs:
        return []
    # crop bbox is in points; the run boxes come from the same index the
    # table bounds use, so scale by the ratio the extractor uses
    xs = [r[1] for r in runs]; ys = [r[0] for r in runs]
    sx = max(xs) / 612.0 if xs else 1.0
    sy = max(ys) / 792.0 if ys else 1.0
    x0, y0, x1, y1 = crop["bbox"]
    sel = [r for r in runs
           if y0 * sy - 12 <= r[0] <= y1 * sy and x0 * sx - 12 <= r[1] <= x1 * sx]
    by_line = {}
    for r in sel:
        by_line.setdefault(round(r[0] / 6), []).append(r)
    return [sorted(v, key=lambda r: r[1]) for _, v in sorted(by_line.items())]

MARKERS = re.compile(r"^[*\u2020\u2021\u00a7\u00b9\u00b2\u00b3\d,a-e\s]+$")

out = {}
for c in crops:
    key = f"{c['figure_id']}" + (f" s{c['sheet']}" if c.get("sheet") else "")
    hits = []
    for line in lines_in(c):
        if not line:
            continue
        big = max(r[5] for r in line)
        words = " ".join(r[6] for r in line)
        if len(words.split()) < 2:
            continue
        for r in line:
            txt = r[6].strip()
            if not txt:
                continue
            # a superscript is smaller than its line...
            small = r[5] < 0.85 * big
            # ...but an asterisk is often set at full size, so take it on sight
            star = txt in ("*", "**", "***")
            if (small or star) and MARKERS.match(txt):
                hits.append((txt, words[:90]))
    if hits:
        out[key] = hits

for k, v in out.items():
    print(f"\n{k}")
    for marker, ctx in v:
        print(f"    marker {marker!r:>8}  in: {ctx}")
print(f"\ntables with a marker in the caption or a heading: {len(out)}")
