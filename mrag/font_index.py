"""Font lookup for caption validation.

WHY THIS EXISTS
---------------
The extractor used to decide "is this a caption?" from punctuation: an id
ending in a period was treated as a caption, a bare mention was not. That test
is wrong, because a sentence can end that way too --

    "...advance signing on intersection approaches are illustrated in
     Figure 2A-4."

which produced a crop of that paragraph. 80 crops in the shipped corpus are
body text cropped this way, and 60 of them went on to overwrite their node's
caption, page number and primary image. Table 2B-1's node read
caption='Table 2B-1.', page 108 -- a sentence -- while the real six-sheet table
sits on pages 109-114.

THE SIGNAL
----------
MUTCD sets body text in Times and captions in a Helvetica face. That is a
categorical difference, not a threshold, which is why it works where size and
line position did not:

    body text        Times 17          32,045 of 73,441 text elements
    caption          Helvetica 14/18
    table header     HelveticaNeueLTPro-Md 11
    table cell       HelveticaNeueLTPro-Md 11

Measured against 727 shipped crops with a human-verified junk list:

    junk crops   80 : correctly rejected 78, wrongly kept 1
    good crops  647 : correctly kept    646, wrongly rejected 1

The two it wrongly keeps (2G-15 p472, 8B-5 p1048) have genuine Helvetica
captions -- their crops are bad for a different reason, a boundary problem, not
an anchor problem. The one it wrongly rejects (2E-11 p404) has no caption in
the text layer at all; the caption is part of the figure artwork, so no
text-based rule can see it.

NOTE ON COORDINATES
-------------------
pdftohtml and pdftotext use different coordinate systems. This module does not
try to reconcile them -- it only answers a per-page yes/no question, so no
coordinate matching is needed.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

# A caption is set in some Helvetica face. Body text is Times.
CAPTION_FAMILY_RE = re.compile(r"^Helvetica", re.IGNORECASE)
# Table headers and cells are also Helvetica but small (11pt), so require the
# larger display size used for captions.
CAPTION_MIN_SIZE = 13.0

_FONTSPEC_RE = re.compile(r'<fontspec id="(\d+)" size="([-\d.]+)" family="([^"]*)"')
_TEXT_RE = re.compile(
    r'<text top="(-?\d+)" left="(-?\d+)" width="(-?\d+)" height="(-?\d+)" '
    r'font="(\d+)">(.*?)</text>',
    re.S,
)
_PAGE_RE = re.compile(r'<page number="(\d+)"[^>]*>(.*?)</page>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SUBSET_RE = re.compile(r"^[A-Z]{6}\+")


def _norm_dashes(s: str) -> str:
    for d in "\u2010\u2011\u2012\u2013\u2014\u2015":
        s = s.replace(d, "-")
    return s


class FontIndex:
    """Per-page text with the font family and size each run was set in."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = Path(pdf_path)
        self._pages: Dict[int, List[Tuple[str, str, float]]] = {}
        self._built = False

    def build(self) -> "FontIndex":
        """One pdftohtml pass over the whole document. ~10s for MUTCD."""
        if self._built:
            return self
        out = subprocess.run(
            ["pdftohtml", "-xml", "-i", "-q", "-stdout", str(self.pdf_path)],
            capture_output=True, text=True, errors="ignore",
        ).stdout
        if not out.strip():
            # older poppler has no -stdout; fall back to a temp file
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                pref = Path(td) / "fx"
                subprocess.run(["pdftohtml", "-xml", "-i", "-q",
                                str(self.pdf_path), str(pref)],
                               check=True, capture_output=True)
                out = (pref.with_suffix(".xml")).read_text(errors="ignore")

        # fontspec ids are GLOBAL: declared on first use, not repeated per page
        fonts = {m.group(1): (float(m.group(2)),
                              _SUBSET_RE.sub("", m.group(3)))
                 for m in _FONTSPEC_RE.finditer(out)}

        for pm in _PAGE_RE.finditer(out):
            pno = int(pm.group(1))
            runs = []
            for m in _TEXT_RE.finditer(pm.group(2)):
                txt = _TAG_RE.sub("", m.group(6)).strip()
                if not txt:
                    continue
                size, family = fonts.get(m.group(5), (0.0, "?"))
                runs.append((_norm_dashes(txt), family, size))
            self._pages[pno] = runs
        self._built = True
        return self

    def page_runs(self, pno: int) -> List[Tuple[str, str, float]]:
        if not self._built:
            self.build()
        return self._pages.get(pno, [])

    def has_caption_font(self, pno: int, kind: str, canonical_id: str) -> bool:
        """Does this page carry 'Figure 2A-4' / 'Table 2B-1' set in a caption
        face? If the only occurrences are Times, it is a body-text mention and
        any crop anchored on it is a paragraph, not a figure."""
        cid = _norm_dashes(canonical_id).upper()
        pat = re.compile(rf"\b{re.escape(kind)}\s+{re.escape(cid)}\b", re.I)
        for txt, family, size in self.page_runs(pno):
            if not pat.search(_norm_dashes(txt).upper()):
                continue
            if CAPTION_FAMILY_RE.match(family) and size >= CAPTION_MIN_SIZE:
                return True
        return False

    def pages_with_captions(self) -> List[int]:
        """Pages carrying any caption-face 'Figure/Table X-Y'. Replaces the
        punctuation-based page prefilter."""
        pat = re.compile(r"\b(Figure|Table)\s+\d+[A-Z]?-\d+", re.I)
        out = []
        for pno, runs in sorted(self._pages.items()):
            for txt, family, size in runs:
                if (CAPTION_FAMILY_RE.match(family) and size >= CAPTION_MIN_SIZE
                        and pat.search(txt)):
                    out.append(pno)
                    break
        return out


@lru_cache(maxsize=4)
def get_font_index(pdf_path: str) -> FontIndex:
    """Cached per process -- the pdftohtml pass runs once."""
    return FontIndex(Path(pdf_path)).build()
