"""Read a MUTCD table's cells and footnotes out of the PDF text layer.

WHY FONT, NOT GEOMETRY
----------------------
Earlier attempts drew a box around a table and hoped the footnotes fell inside
it. They do not, and no single box works:

    Table 2J-2   one note line, INSIDE the ruled border
    Table 3G-1   six numbered notes, OUTSIDE the border
    Table 2C-3   seven paragraphs, taller than the table itself

Font is stable where geometry is not. MUTCD sets:

    body prose     Times 17
    caption        Helvetica 14 / 18
    table content  HelveticaNeueLTPro-Md 11     <-- headers, cells AND footnotes

So font isolates the table's own text, and the remaining problem is separating
cells from notes within it.

CELLS vs NOTES
--------------
Measured on pages 193, 540, 662:

    cells      width 11-52 px,  1-4 words,   0% stopwords
    footnotes  width 205-746 px, 6-26 words, 25-56% stopwords

Width alone fails on continuation lines ("nearest 5 feet." is 76px). What holds
everywhere is position: MUTCD always places notes BELOW the last data row,
whether or not the border encloses them. So the split is vertical, and the
width/stopword signal is only used to find where the data rows stop.

WHY FOOTNOTES MATTER
--------------------
They are frequently obligations, not decoration:

    3G-1 note 2  "The minimum spacing should be 20 feet"        Guidance
    3G-1 note 3  spacing on curves "should not exceed 300 feet" a ceiling that
                 overrides every value in the table
    4C-7 note    defines a high-occupancy bus as >= 20 people;  without it the
                 percentage rows mean nothing
    6B-4 note    the L / W / S variable key -- verified absent from every chunk
                 in the corpus, so it exists ONLY inside the cropped image

Markers survive extraction: on 2C-3 a cell reads "N/A" followed by a separate
"5" token, so the pointer from cell to note is recoverable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

TABLE_FONT_RE = re.compile(r"^HelveticaNeue", re.IGNORECASE)
TABLE_FONT_MIN, TABLE_FONT_MAX = 6.0, 12.0
# Superscript footnote references are the SAME family at ~7pt. On Table 2C-3
# the cell "N/A" is 11pt at x=350 and the marker "5" is 7pt at x=370, so the
# size alone identifies the reference -- no regex on the text needed.
MARKER_FONT_MAX = 9.0
# how far right of the note block a marker may sit and still open a note
MARKER_LEFT_TOL = 14

STOPWORDS = set("""the of to a in is be that for with as are on or by an it this
which shall should may not from at all and if where when than
""".split())

# a leading marker: "*", "1.", "2.", "Note:", "Notes:"
MARKER_RE = re.compile(r"^\s*(?:(\*+|\u2020|\u2021)|(\d+)\s*[.)]|Notes?\s*:)\s*")


@dataclass
class Cell:
    text: str
    row: int
    col: int
    marker: Optional[str] = None       # footnote reference on this cell


@dataclass
class TableContent:
    table_id: str
    page_pdf: int
    header_rows: List[List[str]] = field(default_factory=list)
    cells: List[Cell] = field(default_factory=list)
    footnotes: List[Dict] = field(default_factory=list)
    n_cols: int = 0

    def to_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "page_pdf": self.page_pdf,
            "n_cols": self.n_cols,
            "header_rows": self.header_rows,
            "rows": self._as_rows(),
            "footnotes": self.footnotes,
        }

    def _as_rows(self) -> List[List[dict]]:
        by_row: Dict[int, List[Cell]] = {}
        for c in self.cells:
            by_row.setdefault(c.row, []).append(c)
        out = []
        for r in sorted(by_row):
            row = []
            for c in sorted(by_row[r], key=lambda c: c.col):
                d = {"text": c.text}
                if c.marker:
                    d["footnote_ref"] = c.marker
                row.append(d)
            out.append(row)
        return out


# MUTCD numbers every paragraph ("01", "02", ...) in the far-left margin, in
# the same font as table content. A full-width table bbox swallows them and
# they land in the cells, or get appended to a footnote.
PARA_NUM_RE = re.compile(r"^\d{2}$")
PARA_NUM_MAX_LEFT = 160


def _is_paragraph_number(run) -> bool:
    return bool(PARA_NUM_RE.match(run[6].strip())) and run[1] < PARA_NUM_MAX_LEFT


def _is_table_font(family: str, size: float) -> bool:
    return bool(TABLE_FONT_RE.match(family)) and TABLE_FONT_MIN <= size <= TABLE_FONT_MAX


def _stop_ratio(text: str) -> float:
    w = text.split()
    if not w:
        return 0.0
    return sum(1 for x in w if x.lower().strip(".,;:()") in STOPWORDS) / len(w)


def _looks_like_prose(text: str, width: int) -> bool:
    """A note line: wide, several words, function words present."""
    return width > 150 and len(text.split()) >= 5 and _stop_ratio(text) >= 0.15


def extract(runs: Sequence[Tuple[int, int, int, int, str, float]],
            table_id: str, page_pdf: int,
            x_lo: float = 0.0, x_hi: float = 10_000.0,
            y_lo: float = 0.0, y_hi: float = 10_000.0,
            row_tol: int = 6, col_gap: int = 12) -> TableContent:
    """
    `runs` = [(top, left, width, height, family, size), ...] plus the text as
    element [6] -- i.e. (top, left, width, height, family, size, text).

    x_lo/x_hi/y_lo/y_hi bound the table region on the page, so paragraph
    numbers in the margin and a neighbouring column's text are excluded.
    """
    tc = TableContent(table_id=table_id, page_pdf=page_pdf)

    keep = [r for r in runs
            if _is_table_font(r[4], r[5])
            and x_lo - 2 <= r[1] and r[1] + r[2] <= x_hi + 2
            and y_lo - 2 <= r[0] <= y_hi + 2
            and not _is_paragraph_number(r)]
    if not keep:
        return tc

    # ---- where do the data rows stop? --------------------------------
    # Scan UPWARD from the bottom. Taking the first prose-looking line from the
    # top instead was wrong: Table 4C-1's header ("Number of lanes for moving
    # traffic / Vehicles per hour on major street") is long and full of
    # function words, so it read as prose and the whole table became notes.
    # Notes are always at the END, so the bottom-up boundary is unambiguous.
    ys = sorted({r[0] for r in keep})
    note_top = None
    for y in reversed(ys):
        line = [r for r in keep if abs(r[0] - y) <= row_tol]
        if any(_looks_like_prose(r[6], r[2]) for r in line):
            note_top = y
        elif (note_top is not None and len(line) == 1
              and re.search(r"[A-Za-z]{3}", line[0][6])
              and line[0][2] > 60):
            # a wrapped continuation of a note ("nearest 5 feet."): ONE
            # continuous run. A two-column data row like "50 feet | 20 feet"
            # is two runs and must not be swallowed -- that emptied Table 3G-1.
            note_top = y
        elif note_top is not None:
            break                 # hit a real data row -- stop climbing

    data = [r for r in keep if note_top is None or r[0] < note_top - 2]
    notes = [r for r in keep if note_top is not None and r[0] >= note_top - 2]

    # ---- cells -------------------------------------------------------
    rows: Dict[int, List] = {}
    for r in sorted(data, key=lambda r: (r[0], r[1])):
        key = next((k for k in rows if abs(k - r[0]) <= row_tol), r[0])
        rows.setdefault(key, []).append(r)

    ordered = [rows[k] for k in sorted(rows)]
    widths = [len(row) for row in ordered]
    tc.n_cols = max(widths) if widths else 0

    for ri, row in enumerate(ordered):
        row = sorted(row, key=lambda r: r[1])
        merged, cur = [], [row[0]]
        for r in row[1:]:
            prev = cur[-1]
            if r[1] - (prev[1] + prev[2]) > col_gap:
                merged.append(cur); cur = [r]
            else:
                cur.append(r)
        merged.append(cur)
        for ci, group in enumerate(merged):
            # size separates the value from its footnote reference
            body = [g for g in group if g[5] > MARKER_FONT_MAX]
            refs = [g for g in group if g[5] <= MARKER_FONT_MAX]
            txt = " ".join(g[6] for g in body).strip()
            marker = "".join(g[6] for g in refs).strip() or None
            if not txt and marker:          # a lone superscript is not a cell
                txt, marker = marker, None
            if txt:
                tc.cells.append(Cell(text=txt, row=ri, col=ci, marker=marker))

    # ---- footnotes ---------------------------------------------------
    # Group note lines into notes: a new note starts at a marker.
    # A note's marker is often a superscript run of its own (2C-3), exactly
    # like a cell reference. Detect it by size first; only fall back to the
    # text pattern for notes that spell the marker inline ("2. The minimum...").
    block_left = min((r[1] for r in notes), default=0)
    saw_superscript = any(r[5] <= MARKER_FONT_MAX and len(r[6].strip()) <= 3
                          and r[1] <= block_left + MARKER_LEFT_TOL for r in notes)
    cur_note: Optional[Dict] = None
    for r in sorted(notes, key=lambda r: (r[0], r[1])):
        text = r[6].strip()
        if not text:
            continue
        # A marker that STARTS a note sits at the left edge of the note block.
        # The same superscript appearing mid-text ("feet/second2", or a note
        # referring to another note) must not open a new note -- that split
        # Table 2C-3's notes mid-sentence and invented empty ones.
        if (r[5] <= MARKER_FONT_MAX and len(text) <= 3
                and r[1] <= block_left + MARKER_LEFT_TOL):
            if cur_note:
                tc.footnotes.append(cur_note)
            cur_note = {"marker": text, "text": "", "top": r[0]}
            continue
        if r[5] <= MARKER_FONT_MAX and cur_note is not None:
            cur_note["text"] += text        # superscript inside running text
            continue
        m = None if saw_superscript else MARKER_RE.match(text)
        if m or cur_note is None:
            if cur_note:
                tc.footnotes.append(cur_note)
            marker = (m.group(1) or m.group(2)) if m else None
            body = MARKER_RE.sub("", text) if m else text
            cur_note = {"marker": marker, "text": body, "top": r[0]}
        elif not cur_note["text"]:
            cur_note["text"] = text
        else:
            cur_note["text"] += " " + text
    if cur_note:
        tc.footnotes.append(cur_note)
    for n in tc.footnotes:
        n.pop("top", None)
        n["text"] = re.sub(r"\s+", " ", n["text"]).strip()

    return tc


# --------------------------------------------------------------------------- #
# Bounds come from the crop step, which already computed them                  #
# --------------------------------------------------------------------------- #

PDF_TO_HTML_SCALE = 1.5      # pdftohtml renders at 1.5x PDF points


def extract_for_crop(runs, crop_record: dict, pad: float = 6.0) -> TableContent:
    """Read a table using the bbox the crop step already produced.

    `regions_for_page` computes where the table sits in order to cut the image;
    that same rectangle is stored on every record in figures.jsonl. There is no
    need to locate the table a second time -- only to convert PDF points to
    pdftohtml pixels, which differ by a fixed 1.5x.

    Getting these bounds wrong fails silently: in testing, an x_lo of 300
    instead of 230 made Table 3G-1's six footnotes disappear and the extractor
    reported zero notes rather than an error.
    """
    x0, y0, x1, y1 = crop_record["bbox"]
    s = PDF_TO_HTML_SCALE
    return extract(
        runs,
        table_id=crop_record.get("canonical_id", "?"),
        page_pdf=crop_record["page_pdf"],
        x_lo=(x0 - pad) * s, x_hi=(x1 + pad) * s,
        y_lo=(y0 - pad) * s, y_hi=(y1 + pad) * s,
    )
