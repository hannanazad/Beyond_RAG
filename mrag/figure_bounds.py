"""A figure's true extent on the page, caption included.

WHY THE OLD BOUNDARY FAILED
---------------------------
`regions_for_page` crops from just BELOW a caption down to the next caption.
For figures that produced two systematic faults, measured over all 560 figure
crops in figures.jsonl:

    caption outside the crop   559 of 560   (tables: 12 of 88)
    body prose inside the crop routine      Figure 8D-3's real extent is a
                                            drawn box 137 pt tall; its crop was
                                            478 pt tall and covered five
                                            ordinary paragraphs of Section 8D.15

A crop with no caption reaches the VLM with no title, and a crop full of
neighbouring prose dilutes the image embedding.

WHAT REPLACES IT
----------------
Tables are bounded by their font layer (see table_bounds.py). Figures have no
font layer -- which is why they were left alone -- but they do have an ARTWORK
layer, and the MUTCD keeps the layers apart just as cleanly:

    caption           Helvetica face, >= 11.5 pt
    labels, notes     Helvetica / Helvetica Neue
    the drawing       vector paths and embedded images
    body prose        Times            <-- never part of a figure

So a figure runs from its caption through the connected artwork, and stops
where Times body prose resumes in that column. Measured over 560 crops:

    caption inside the crop     558 of 558 (2 figures have no caption set in
                                the caption face; those keep the old region)
    crops holding body prose    4
    crop area                   median 76% of the old crop, tightest 36%
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Sequence, Tuple

log = logging.getLogger("mrag.figure_bounds")

CAPTION_RE = re.compile(
    r"^(Figure|Table)\s+(\d+[A-Z]?[\u2010-\u2015-]\d+)\s*[.\u2010-\u2015]", re.IGNORECASE)
DASHES = {0x2010: 45, 0x2011: 45, 0x2012: 45, 0x2013: 45, 0x2014: 45}

CAPTION_MIN_SIZE = 11.5     # body mentions ("see Table 3E-2") are Times 11
HEADER_BAND, FOOTER_BAND = 0.06, 0.935      # running header / footer
# Artwork may legitimately sit lower than the body-text band: several
# figures print their closing note just above the footer rule
# (Figure 6G-1 at y736 of 792). The footer itself is Times, so it is
# classed as body and cannot be swept in by the wider band.
ART_HEADER_BAND, ART_FOOTER_BAND = 0.04, 0.955
GROW_GAP = 18.0             # pt; connects a label to the art it annotates
SEED_PAD = 25.0             # art may start slightly above the caption line
EDGE_MARGIN = 18.0          # keep margin rules and revision bars out
MIN_COLUMN_OVERLAP = 0.3


def _is_paragraph_number(span: dict, text: str) -> bool:
    """Margin paragraph numbers ("06") are HelveticaNeueLTPro-MdCn ~7pt. They
    are not Times, so without this they pull a box into the left margin."""
    return ("MdCn" in span.get("font", "") and span.get("size", 99) <= 8.5
            and text.strip().isdigit())


def page_layers(page) -> Tuple[list, list, list]:
    """(artwork rects, Times body-line rects, [(\"Figure 2B-3\", rect), ...])."""
    import pymupdf
    h, w = page.rect.height, page.rect.width
    art, body, caps = [], [], []
    for blk in page.get_text("dict")["blocks"]:
        if blk.get("type") == 1:                       # embedded image
            art.append(pymupdf.Rect(blk["bbox"]))
            continue
        for line in blk.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not text:
                continue
            rect = pymupdf.Rect(line["bbox"])
            span = max(line["spans"], key=lambda s: len(s["text"]))
            is_body = span["font"].startswith("Times")
            lo, hi = ((HEADER_BAND, FOOTER_BAND) if is_body
                      else (ART_HEADER_BAND, ART_FOOTER_BAND))
            if rect.y1 < lo * h or rect.y0 > hi * h:
                continue
            m = CAPTION_RE.match(text)
            if (m and not span["font"].startswith("Times")
                    and span["size"] >= CAPTION_MIN_SIZE):
                caps.append((f"{m.group(1).title()} {m.group(2).translate(DASHES)}", rect))
            if is_body:
                body.append(rect)
            elif text != "Rev. 1" and not _is_paragraph_number(span, text):
                art.append(rect)
    for d in page.get_drawings():
        r = d["rect"]
        if r.width < 1 and r.height < 1:
            continue
        if r.y1 < ART_HEADER_BAND * h or r.y0 > ART_FOOTER_BAND * h:
            continue
        if r.width > 0.95 * w and r.height > 0.9 * h:      # page frame
            continue
        if r.x1 < EDGE_MARGIN + 7 or r.x0 > w - EDGE_MARGIN - 7:   # margin rules
            continue
        art.append(r)
    return art, body, caps


def _grow(seed, rects, gap: float = GROW_GAP, max_iter: int = 40):
    import pymupdf
    region = pymupdf.Rect(seed)
    used = [False] * len(rects)
    for _ in range(max_iter):
        changed = False
        probe = pymupdf.Rect(region.x0 - gap, region.y0 - gap,
                             region.x1 + gap, region.y1 + gap)
        for i, r in enumerate(rects):
            if not used[i] and probe.intersects(r):
                region |= r
                used[i] = True
                changed = True
        if not changed:
            break
    return region


def _mine(rects, own, others):
    """Keep the rects this caption owns.

    A caption heads its figure, so an item belongs to the NEAREST CAPTION
    ABOVE it. Assigning by absolute distance instead handed the notes printed
    under a figure to the next figure's caption, which dropped 29 note chunks
    (Figure 2G-14's eight notes among them).
    """
    keep = []
    for r in rects:
        c = (r.y0 + r.y1) / 2
        above = [o.y0 for o in others if o.y0 <= c]
        if above and max(above) > own.y0:
            continue                       # a later caption starts before this
        if c < own.y0 - SEED_PAD:
            continue                       # sits above this caption entirely
        keep.append(r)
    return keep


def figure_box(page, key: str, caption_rect=None):
    """Extent of figure `key` (e.g. "Figure 2B-3") on `page`, or None."""
    import pymupdf
    art, body, caps = page_layers(page)
    crect = caption_rect
    if crect is None:
        crect = next((r for k, r in caps if k == key), None)
    if crect is None:
        return None
    others = [r for k, r in caps if k != key]
    mine = _mine(art, crect, others)
    core = _grow(crect, mine)

    def overlaps(r, x0, x1):
        return (min(r.x1, x1) - max(r.x0, x0)) > MIN_COLUMN_OVERLAP * min(r.width, x1 - x0)

    # Stop where Times body prose resumes in this column, or at the next caption.
    stops = [r.y0 for r in body if r.y0 > crect.y1 + 2 and overlaps(r, core.x0, core.x1)]
    stops += [r.y0 for r in others if r.y0 > crect.y1 + 2]
    has_stop = bool(stops)
    y_stop = min(stops) if has_stop else page.rect.height

    box = pymupdf.Rect(crect)
    for r in mine:
        # No x filter: Times prose is already excluded, and clipping to the
        # core's x-range cut the right-hand column off wide figures (6G-1).
        if crect.y0 - SEED_PAD < (r.y0 + r.y1) / 2 < y_stop:
            box |= r
    # Clip only against a REAL stop. Clipping to the footer band as well cut
    # the closing note off figures that print one just above the footer rule.
    if has_stop:
        box.y1 = min(box.y1, y_stop - 2)
    box.x0 = max(box.x0, EDGE_MARGIN)
    box.x1 = min(box.x1, page.rect.width - EDGE_MARGIN)
    return box if box.height > 8 and box.width > 8 else None


def figure_regions_by_artwork(pdf_path, pno: int, caps: Sequence, regions: List,
                              pad: float = 3.0) -> List:
    """Replace every FIGURE region on page `pno` with its artwork extent.

    `caps` are CaptionHit objects; `regions` is [(cap, (x0,y0,x1,y1))].
    Table regions are returned untouched -- they already come from
    table_bounds.py. A figure whose caption is not set in the caption face
    keeps its original region.
    """
    try:
        import pymupdf
    except ImportError:                       # pragma: no cover
        log.warning("pymupdf missing; figure bounds left as caption-to-caption")
        return regions
    doc = pymupdf.open(str(pdf_path))
    try:
        page = doc.load_page(pno - 1)
        _, _, caps_on_page = page_layers(page)
        out = []
        for cap, box in regions:
            if getattr(cap, "kind", "") != "Figure":
                out.append((cap, box))
                continue
            key = f"Figure {str(getattr(cap, 'canonical_id', '')).translate(DASHES)}"
            # Prefer the caption rect nearest this region's top: a multi-sheet
            # figure prints the same caption several times on one page.
            cands = [r for k, r in caps_on_page if k == key]
            crect = min(cands, key=lambda r: abs(r.y0 - getattr(cap, "y_top", box[1]))) if cands else None
            new = figure_box(page, key, caption_rect=crect)
            if new is None:
                log.debug("p%d %s: no caption in the caption face; region kept", pno, key)
                out.append((cap, box))
                continue
            out.append((cap, (max(0.0, new.x0 - pad), max(0.0, new.y0 - pad),
                              min(page.rect.width, new.x1 + pad),
                              min(page.rect.height, new.y1 + pad))))
        return out
    finally:
        doc.close()
