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
BODY_MIN = 15.0

PAGE_W = 918                # pdftohtml renders US Letter at 1.5x -> 918 x 1188
FOOTER_TOP = 1120


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
            core = [r for r in in_slice if _layer(r[4], r[5]) == "tab"]
            if not core:
                # Table 6P-2 is a symbol legend: icons with labels set in the
                # caption face, no 11pt content at all. Fall back to the caption
                # layer or the table is simply lost.
                core = [r for r in in_slice if _layer(r[4], r[5]) == "cap"]
            if not core:
                continue

            # Stop at the first vertical gap wider than a blank line: that is
            # where the table and its notes end.
            core.sort(key=lambda r: r[0])
            kept = [core[0]]
            for r in core[1:]:
                if r[0] - (kept[-1][0] + kept[-1][3]) > 60:
                    break
                kept.append(r)

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
    keep: List[Run] = []
    for cl in clusters:
        lo, hi = min(r[1] for r in cl), max(r[1] + r[2] for r in cl)
        if min(hi, cap_right) - max(lo, cap_left) > 0:
            keep.extend(cl)
    return keep if keep else max(clusters, key=len)
