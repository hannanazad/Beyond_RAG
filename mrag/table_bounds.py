"""Compute a table's true extent on the page, footnotes included.

WHY THE OLD BOUNDARY FAILED
---------------------------
`regions_for_page` cropped from a caption down to the next caption. In a
two-column layout a body-text mention of a table in the LEFT column becomes a
boundary that cuts across the real table in the RIGHT column. Table 2A-3 came
out 36 points tall -- a sliver of its own header. And where no caption followed,
the crop ran to the page footer and swallowed paragraphs of unrelated prose.

Footnotes were the other casualty. A crop bounded by the ruled border misses
notes printed outside it, and those notes are frequently obligations:

    3G-1 note 3  spacing on curves "should not exceed 300 feet" -- a ceiling
                 that overrides every value in the table
    4C-7 note    defines a high-occupancy bus as 20+ people
    6B-4 note    the L / W / S variable key, absent from every chunk in the
                 corpus, so it exists only inside the cropped image

WHAT REPLACES IT
----------------
MUTCD uses a different typeface for each layer, so the table's extent can be
read off the fonts rather than guessed from geometry:

    caption title       HelveticaNeueLTPro-Bd 18   "Table 3G-1. Approximate..."
    column headers      HelveticaNeueLTPro-Bd 14
    cells AND footnotes HelveticaNeueLTPro-Md 11
    footnote markers    same family at 7
    body prose          Times 17

A table therefore runs from its caption down to the last table-layer run before
body prose resumes. Footnotes are in the table layer, so they are included by
construction -- no rule about borders, and no guess about how far below the grid
to reach.

Horizontally it is bounded by the column the caption sits over, which keeps the
neighbouring text column out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# (top, left, width, height, family, size, text)
Run = Tuple[int, int, int, int, str, float, str]

CAPTION_ID_RE = re.compile(
    r"^(Figure|Table)\s+(\d+[A-Z]?[\u2010-\u2015-]\d+)\s*\.", re.IGNORECASE)

CAPTION_TITLE_MIN = 16.0    # the "Table X-Y." line; column headers are 14
CAPTION_ANY_MIN = 13.0
TABLE_SIZE_LO, TABLE_SIZE_HI = 6.0, 12.0
# superscript footnote markers are the same family at ~7-9pt
MARKER_SIZE_MAX = 9.0
MARKER_MAX_WIDTH = 22     # a lone "1" beside a caption is ~8px wide
MARKER_MAX_CHARS = 2
# largest vertical gap still considered "inside" one table
MAX_INTERNAL_GAP = 110
# a blank run this wide means the table has ended horizontally
WHITE_GAP = 26


def _is_marker(run: Run) -> bool:
    """A footnote reference, not table content. Usually a 7pt superscript, but
    Table 2A-5's is rendered at full 11pt -- what identifies it there is that it
    is a one-character run 8px wide."""
    if run[5] <= MARKER_SIZE_MAX:
        return True
    return len(run[6].strip()) <= MARKER_MAX_CHARS and run[2] <= MARKER_MAX_WIDTH
BODY_MIN = 15.0

PAGE_W = 918                # pdftohtml renders US Letter at 1.5x -> 918 x 1188
FOOTER_TOP = 1120


# MUTCD numbers every paragraph ("04", "05", ...) in the far-left margin, in
# the SAME font as table cells. They sort first by y, so the "stop at the first
# vertical gap" rule cut the table off immediately and the crop became the
# paragraph number -- Table 3B-1 came out 25x21 points.
PARA_NUM_RE = re.compile(r"^\d{2}$")
PARA_NUM_MAX_LEFT = 160


def _is_paragraph_number(run: Run) -> bool:
    return bool(PARA_NUM_RE.match(run[6].strip())) and run[1] < PARA_NUM_MAX_LEFT


def _layer(family: str, size: float) -> str:
    if family.startswith("Helvetica") and size >= CAPTION_ANY_MIN:
        return "cap"
    if family.startswith("Helvetica") and TABLE_SIZE_LO <= size <= TABLE_SIZE_HI:
        return "tab"
    if family.startswith("Times") and size >= BODY_MIN:
        return "body"
    return "other"


@dataclass
class TableBounds:
    table_id: str
    title: str
    top: int
    left: int
    right: int
    bottom: int
    side_by_side: bool = False

    def as_pdf_points(self, scale: float = 1.5) -> Tuple[float, float, float, float]:
        return (self.left / scale, self.top / scale,
                self.right / scale, self.bottom / scale)


def find_tables(runs: Sequence[Run], pad: int = 10) -> List[TableBounds]:
    """One TableBounds per table caption on the page."""
    caps = []
    for r in runs:
        if _layer(r[4], r[5]) != "cap" or r[5] < CAPTION_TITLE_MIN:
            continue
        m = CAPTION_ID_RE.match(r[6].strip())
        if m and m.group(1).lower() == "table":
            caps.append({"id": m.group(2).replace("\u2010", "-").replace("\u2011", "-"),
                         "top": r[0], "left": r[1], "right": r[1] + r[2],
                         "title": r[6].strip()})
    if not caps:
        return []
    caps.sort(key=lambda c: (c["top"], c["left"]))

    # captions on the same horizontal band sit side by side (p706 has three)
    bands: List[List[dict]] = []
    for c in caps:
        if bands and abs(c["top"] - bands[-1][0]["top"]) < 40:
            bands[-1].append(c)
        else:
            bands.append([c])

    out: List[TableBounds] = []
    for bi, band in enumerate(bands):
        band.sort(key=lambda c: c["left"])
        next_band_top = bands[bi + 1][0]["top"] if bi + 1 < len(bands) else FOOTER_TOP
        for ci, c in enumerate(band):
            if len(band) > 1:
                x_lo = 0 if ci == 0 else (band[ci - 1]["right"] + c["left"]) // 2
                x_hi = PAGE_W if ci == len(band) - 1 else (c["right"] + band[ci + 1]["left"]) // 2
            else:
                x_lo, x_hi = 0, PAGE_W

            # The table LAYER (11pt) is the reliable core. Section headings are
            # also Helvetica bold, so the caption layer alone would drag in
            # "Section 2A.22 Maintaining Minimum Retroreflectivity" from the
            # other column and the crop would be prose.
            in_slice = [r for r in runs
                        if c["top"] - 4 <= r[0] < next_band_top
                        and x_lo - 2 <= r[1] and r[1] + r[2] <= x_hi + 2]
            core = [r for r in in_slice
                    if _layer(r[4], r[5]) == "tab" and not _is_paragraph_number(r)]
            if not core:
                # Table 6P-2 is a symbol legend: icons with labels set in the
                # caption face, no 11pt content at all. Fall back to the caption
                # layer or the table is simply lost.
                core = [r for r in in_slice
                        if _layer(r[4], r[5]) == "cap" and not _is_paragraph_number(r)]
            if not core:
                continue

            # Stop at the first vertical gap wider than a blank line: that is
            # where the table and its notes end.
            # Walk down over SUBSTANTIVE runs only. Superscript footnote
            # markers are the same font family at ~7-9pt and one often sits
            # beside the caption (Table 2A-5 has a "1" at top=77, caption at 76,
            # first data row at 169). Including them in the walk made the next
            # gap look like 79pt, so the crop stopped dead and 2A-5 and 2C-4
            # came out ~40pt tall. Markers are added back afterwards -- they
            # fall inside the resulting box anyway.
            # Walk over BOTH the table layer and the caption layer. A table's
            # trailing note or worked example is often set in the caption face
            # (Table 2L-2's "USE ROUTE 46 / TO NEW YORK" phase boxes are 17pt
            # Helvetica), so a tab-layer-only walk stopped above them.
            walk = [r for r in in_slice
                    if _layer(r[4], r[5]) in ("cap", "tab")
                    and not _is_paragraph_number(r) and not _is_marker(r)]
            walk = _caption_column(walk, c["left"], c["right"]) or walk
            if not walk:
                walk = core
            walk.sort(key=lambda r: r[0])
            kept = [walk[0]]
            for r in walk[1:]:
                # 60pt was too tight: Table 1D-1's "Days of the Week" sub-block
                # sits 80pt below the main grid and was being cut off. Body
                # prose is Times and already excluded, so a wider gap is safe.
                if r[0] - (kept[-1][0] + kept[-1][3]) > MAX_INTERNAL_GAP:
                    break
                kept.append(r)
            y_hi = max(r[0] + r[3] for r in kept)
            kept += [r for r in core if _is_marker(r) and r[0] <= y_hi + 4]

            # The table occupies one text column. Cluster the core runs by x and
            # keep the cluster the caption sits over -- otherwise a full-page
            # x-range pulls in the neighbouring column.
            kept = _caption_column(kept, c["left"], c["right"])
            if not kept:
                continue

            # Now add back the caption/header runs that fall inside that box.
            y0, y1 = min(r[0] for r in kept), max(r[0] + r[3] for r in kept)
            x0, x1 = min(r[1] for r in kept), max(r[1] + r[2] for r in kept)
            heads = [r for r in runs
                     if _layer(r[4], r[5]) == "cap"
                     and c["top"] - 4 <= r[0] <= y1
                     and r[1] + r[2] >= x0 - 30 and r[1] <= x1 + 30]
            kept = kept + heads

            out.append(TableBounds(
                table_id=c["id"], title=c["title"],
                top=min(r[0] for r in kept) - pad,
                left=min(r[1] for r in kept) - pad,
                right=max(r[1] + r[2] for r in kept) + pad,
                bottom=max(r[0] + r[3] for r in kept) + pad,
                side_by_side=len(band) > 1,
            ))
    return out


def _caption_column(runs: Sequence[Run], cap_left: int, cap_right: int,
                    gap: int = 40) -> List[Run]:
    """Keep the x-cluster the caption spans. A table sits in one text column;
    without this a full-page x-range drags in the column beside it."""
    if not runs:
        return []
    xs = sorted(runs, key=lambda r: r[1])
    clusters, cur, edge = [], [xs[0]], xs[0][1] + xs[0][2]
    for r in xs[1:]:
        if r[1] - edge > gap:
            clusters.append(cur); cur = [r]
        else:
            cur.append(r)
        edge = max(edge, r[1] + r[2])
    clusters.append(cur)
    if len(clusters) == 1:
        return runs
    # Keep EVERY cluster the caption spans. Taking only the best one clipped
    # Table 1B-1's right-hand column, because a wide table can break into more
    # than one x-cluster.
    spans = [(min(r[1] for r in cl), max(r[1] + r[2] for r in cl), cl)
             for cl in clusters]
    chosen = [i for i, (lo, hi, _) in enumerate(spans)
              if min(hi, cap_right) - max(lo, cap_left) > 0]
    if not chosen:
        return max(clusters, key=len)

    # Grow outward: absorb any neighbouring cluster that is close to the
    # selected extent. A wide table's rightmost column can form its own cluster
    # that the caption does not span -- Table 1D-2's "Example" column and Table
    # 2D-2's "Greater than 40 mph" column were both clipped off this way.
    lo = min(spans[i][0] for i in chosen)
    hi = max(spans[i][1] for i in chosen)
    changed = True
    while changed:
        changed = False
        for i, (clo, chi, _) in enumerate(spans):
            if i in chosen:
                continue
            if clo - hi <= gap * 2 and chi >= lo - gap * 2 and clo >= lo - gap * 2:
                chosen.append(i)
                lo, hi = min(lo, clo), max(hi, chi)
                changed = True
    keep: List[Run] = []
    for i in chosen:
        keep.extend(spans[i][2])
    return keep


def refine_with_ink(tb: "TableBounds", page_png, page_w_px: int,
                    runs: Optional[Sequence[Run]] = None,
                    pad: int = 10, margin: int = 6):
    """Grow the box sideways to cover graphics that carry no text.

    Table 6P-2 is a symbol legend: each row is an icon beside a label. The icons
    are vector drawings, so they appear nowhere in the text layer and a
    text-derived box clipped every one of them off. Ink does show them.

    Only the horizontal extent is grown, and only within the rows the table
    already occupies, so this cannot reach into a neighbouring column's prose --
    that text is Times and was excluded before we got here.
    """
    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return tb

    im = Image.open(page_png).convert("L")
    s = im.width / float(page_w_px)
    a = np.asarray(im)
    y0, y1 = int(tb.top * s), int(tb.bottom * s)
    y0, y1 = max(0, y0), min(a.shape[0], y1)
    if y1 - y0 < 4:
        return tb

    band = a[y0:y1] < 160                      # ink
    cols = np.where(band.any(axis=0))[0]
    if cols.size == 0:
        return tb

    # Walk outward from each edge and stop at the first sustained blank gap.
    # Taking the furthest ink instead grabbed the neighbouring column: Table
    # 2L-2 jumped from x=376 to x=89, swallowing an unrelated figure that
    # happens to sit on the same rows.
    has_ink = band.any(axis=0)
    gap_px = max(4, int(WHITE_GAP * s))

    def walk(start_px: int, step: int) -> int:
        edge = start_px
        i = start_px
        while 0 <= i < has_ink.size:
            if has_ink[i]:
                edge = i
                i += step
                continue
            j, blank = i, 0
            while 0 <= j < has_ink.size and not has_ink[j]:
                blank += 1
                j += step
            if blank >= gap_px:
                break
            i = j
        return edge

    left_px = walk(max(0, min(int(tb.left * s), has_ink.size - 1)), -1)
    right_px = walk(max(0, min(int(tb.right * s), has_ink.size - 1)), 1)
    new_left = min(tb.left, int(left_px / s) - margin)
    new_right = max(tb.right, int(right_px / s) + margin)

    # Only expand into space that holds NO TEXT. Ink alone cannot tell a symbol
    # belonging to this table from a neighbour's content: Table 2L-2 reached
    # across into an unrelated figure, and Tables 4C-6 and 4C-7 -- side by side
    # on one page -- expanded into each other and became identical. A region
    # with text in it belongs to something else.
    if runs:
        def text_between(a: int, b: int) -> bool:
            return any(r[1] + r[2] > a and r[1] < b
                       and r[0] + r[3] > tb.top and r[0] < tb.bottom
                       for r in runs)
        if new_left < tb.left and text_between(new_left, tb.left - 2):
            new_left = tb.left
        if new_right > tb.right and text_between(tb.right + 2, new_right):
            new_right = tb.right
    if new_left == tb.left and new_right == tb.right:
        return tb
    return TableBounds(tb.table_id, tb.title, tb.top, new_left, new_right,
                       tb.bottom, tb.side_by_side)
