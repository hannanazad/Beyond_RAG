"""Outline-driven MUTCD parser.

Uses the PDF's built-in outline (Table of Contents) to find every Section
(L3 entry like "Section 2B.04 STOP Sign (R1-1)..."). For each section,
walks the text blocks of its pages and emits one chunk per numbered
paragraph, tagged with its rule type (Standard / Guidance / Option / Support).

The output of `parse_chunks()` is the *single source of truth* for chunks
used by every downstream stage (embeddings, KG, retrieval, prompt).
"""
from __future__ import annotations

import collections
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, List, Optional

try:
    import fitz  # PyMuPDF — required only by parse_chunks()
except Exception:                                     # pragma: no cover
    fitz = None


SECTION_RE   = re.compile(r"^Section\s+([0-9A-Z]+\.[0-9]+)\s+(.+)$")
RULE_RE      = re.compile(r"^(Standard|Support|Guidance|Option)\s*:\s*$")
NUM_ONLY_RE  = re.compile(r"^(\d{1,3})\s*$")
CHAPTER_RE   = re.compile(r"^CHAPTER\s+([0-9A-Z]+)\.", re.IGNORECASE)
PART_RE      = re.compile(r"^PART\s+(\d+)", re.IGNORECASE)
PRINTED_PG   = re.compile(r"^Page\s+\d{1,4}\s*$")
SECT_RANGE   = re.compile(r"^Sect\.\s+")
FOOTER_LINES = {"December 2023", "MUTCD 11th Edition"}

# Outline titles are not always clean: "Section 3A.03Colors" (no space) and
# "Rev. 1Section 2F.08 ..." (revision mark glued on). SECTION_RE misses those,
# which silently dropped 5 whole sections (2F.08, 2F.09, 3A.03, 4K.02, 9D.01).
OUTLINE_SECTION_RE = re.compile(r"^(?:Rev\.\s*1\s*)?Section\s*([0-9][A-Z]\.[0-9]{2})\s*(.*)$")
# Body Part headings in the outline have no space: "PART 1GENERAL".
OUTLINE_PART_RE    = re.compile(r"^PART\s*(\d+)\s*(.*)$", re.IGNORECASE)
REV_MARK_RE        = re.compile(r"^Rev\.\s*1$")
BLANK_PAGE_RE      = re.compile(r"^\(This page intentionally left blank\)$", re.IGNORECASE)

# Cross-reference / sign-code patterns (used by KG builder, exported for reuse).
SECREF_RE  = re.compile(r"\bSection\s+([0-9A-Z]+\.[0-9]+)\b", re.IGNORECASE)
FIGREF_RE  = re.compile(r"\bFigure\s+([0-9A-Z]+-[0-9]+(?:\([A-Za-z0-9]+\))?[A-Za-z]?)\b", re.IGNORECASE)
TABREF_RE  = re.compile(r"\bTable\s+([0-9A-Z]+-[0-9]+(?:\([A-Za-z0-9]+\))?[A-Za-z]?)\b", re.IGNORECASE)

# Modal-verb detection: "shall" => Standard provision tone, "should" => Guidance,
# "may" => Option. We never override the outline-supplied content_type, but we
# expose modal verbs for downstream scoring & display.
MODAL_VERBS = {"shall", "should", "may", "must"}
MODAL_RE = re.compile(r"\b(shall|should|may|must)\b", re.IGNORECASE)


@dataclass
class Chunk:
    chunk_id:       str
    part:           Optional[str]
    chapter:        Optional[str]
    section_id:     str
    section_title:  str
    content_type:   str               # Standard | Guidance | Option | Support
    ordinal:        int
    page_pdf:       int
    page_printed:   str
    text:           str
    figure_refs:    List[str]
    table_refs:     List[str]
    section_refs:   List[str]
    sign_codes:     List[str]
    modal_verbs:    List[str]
    # Added with list splitting / note chunks. Defaults keep old files readable.
    source:         str = "paragraph"          # paragraph | list_item | figure_note | table_note | appendix
    parent_id:      Optional[str] = None       # list_item: id of the paragraph it came from
    item:           Optional[str] = None       # list_item: its marker, e.g. "C" or "12"
    authority_inferred: bool = False           # True when content_type was not printed in the manual


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #

def parse_chunks(pdf_path: Path, sign_code_re: Optional[re.Pattern] = None,
                 figures=None) -> List[Chunk]:
    """Walk the entire PDF and return every typed paragraph as a Chunk."""
    if fitz is None:
        raise RuntimeError("parse_chunks requires PyMuPDF: pip install pymupdf")
    doc = fitz.open(str(pdf_path))
    toc = doc.get_toc()

    # ---------- 1. Build hierarchy from outline ----------------------------
    sections, hierarchy, headings = _outline_to_sections(toc, doc.page_count)

    # ---------- 2. Parse each section --------------------------------------
    # The Part 6 "Notes for Figure 6P-N" pages sit inside 6P.01's page range
    # but have their own layout, so they are parsed separately and skipped here.
    notes_pages = {pg for lvl, t, pg in toc
                   if lvl == 3 and NOTES_HEADING_RE.match(t.strip())}
    out: List[Chunk] = []
    for sec in sections:
        chunks = _parse_one_section(
            doc,
            sec_id=sec["id"],
            section_title=sec["title"],
            page_start_idx=sec["start"] - 1,   # outline is 1-indexed
            page_end_idx=sec["end"],            # exclusive
            hierarchy=hierarchy.get(sec["id"], {}),
            sign_code_re=sign_code_re,
            headings=headings,
            skip_pages=notes_pages,
        )
        out.extend(chunks)
    out.extend(_parse_figure_notes(doc, toc, hierarchy.get("6P.01", {}), sign_code_re))
    out.extend(_parse_appendices(doc, toc, sign_code_re))
    # Notes printed inside figure/table crops. Needs `figures`, which
    # ingest_v4 extracts before parsing; without it these notes are skipped.
    if figures:
        out.extend(_parse_crop_notes(doc, figures, out, sign_code_re))
    else:
        log.warning("parse_chunks called without figures: figure/table note "
                    "chunks are skipped")
    return out


def write_chunks_jsonl(chunks: List[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def read_chunks_jsonl(path: Path) -> List[Chunk]:
    out: List[Chunk] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            d = json.loads(line)
            out.append(Chunk(**d))
    return out


# --------------------------------------------------------------------------- #
# Internals                                                                   #
# --------------------------------------------------------------------------- #

def _outline_to_sections(toc, page_count: int):
    """Return (sections_list, hierarchy_map, headings).

    `headings` records where every REAL heading is, so the section walker can
    tell a heading from body text that merely starts with "Section 2A.12
    contains ..." or "Part 7 sets forth ...". The old walker stopped at any
    such line: 191 sections were cut short, including 1C.02 Definitions,
    which ended at definition 125 on a wrapped "49 CFR Part 229.129)".
    """
    sections: List[dict] = []
    hierarchy: dict = {}
    headings = {"section": {}, "chapter": {}, "part": {}}
    current_part = current_chapter = None

    for lvl, title, pg in toc:
        t = title.strip()
        m_part = OUTLINE_PART_RE.match(t)
        m_chap = re.match(r"^CHAPTER\s+([0-9A-Z]+)\.\s*(.*)$", t, re.IGNORECASE)
        m_sec  = OUTLINE_SECTION_RE.match(t)

        # Only level-1 PART entries are the body Parts. The front table of
        # contents lists all nine Parts at level 2 before any section, which
        # made every chunk say "Part 9".
        if lvl == 1 and m_part:
            current_part = f"PART {m_part.group(1)} {m_part.group(2).strip()}".title()
            headings["part"][m_part.group(1)] = pg
        elif m_chap:
            current_chapter = m_chap.group(0).title()
            headings["chapter"][m_chap.group(1).upper()] = pg
        elif lvl == 3 and m_sec:
            sec_id = m_sec.group(1)
            sec_title = re.sub(r"\s+", " ", m_sec.group(2)).strip()
            sections.append({"id": sec_id, "title": sec_title, "start": pg})
            hierarchy[sec_id] = {"part": current_part, "chapter": current_chapter}
            headings["section"][sec_id] = (pg, sec_title)

    # The manual ends at the outline's level-1 "Appendices" entry. Without this
    # cap the last section (9F.03) swallowed the Appendix A1 text.
    appendix_pages = [pg for lvl, title, pg in toc
                      if lvl == 1 and title.strip().lower().startswith("appendi")]
    body_end = (min(appendix_pages) - 1) if appendix_pages else page_count

    for i, sec in enumerate(sections):
        sec["end"] = sections[i + 1]["start"] if i + 1 < len(sections) else body_end
        # parse_one_section uses range(start_idx, end_idx): 0-based, end exclusive.
    return sections, hierarchy, headings


def _clean_text(text: str) -> str:
    """Collapse whitespace and normalise the Unicode dashes used on the
    Revision-1 pages ("Table 6B\u20112"), so FIGREF/TABREF resolve."""
    text = re.sub(r"\s+", " ", text).strip()
    return text.translate({0x2010: "-", 0x2011: "-", 0x2012: "-",
                           0x2013: "-", 0x2014: "-"})


def _norm_title(s: str) -> str:
    return re.sub(r"[\s\-\u2010-\u2014]+", " ", s).strip().lower()


def _real_section_heading(text: str, page_no: int, size: float, headings: dict) -> Optional[str]:
    """Section id if `text` is that section's actual heading, else None.

    A heading must (1) name a section in the outline, (2) sit on that
    section's outline page, (3) begin with that section's title, and (4) be
    set in the heading size (Times-Bold 12; body text is 11). All 951 headings
    meet these; body references such as "Section 2G.19 for the incorporation
    of ..." do not.
    """
    m = OUTLINE_SECTION_RE.match(text)
    if not m or size < 11.5:
        return None
    hit = headings["section"].get(m.group(1))
    if not hit or hit[0] != page_no:
        return None
    line_title, outline_title = _norm_title(m.group(2)), _norm_title(hit[1])
    if len(line_title) >= 3 and (outline_title.startswith(line_title) or line_title.startswith(outline_title)):
        return m.group(1)
    return None


def _real_part_or_chapter_heading(text: str, page_no: int, headings: dict) -> bool:
    m_chap = CHAPTER_RE.match(text)
    if m_chap and text.isupper():
        return headings["chapter"].get(m_chap.group(1).upper()) in (page_no, page_no - 1)
    m_part = OUTLINE_PART_RE.match(text)
    if m_part and text.isupper():
        return headings["part"].get(m_part.group(1)) in (page_no, page_no - 1)
    return False


def _body_font(line: dict) -> bool:
    """True if the line is set in the manual's body typeface (Times)."""
    span = max(line["spans"], key=lambda sp: len(sp["text"]))
    return span["font"].startswith("Times")


def _paragraph_number_style(line: dict) -> bool:
    """Paragraph numbers ("01", "02") are set in HelveticaNeueLTPro-MdCn at 7pt
    in the margin. Number-only table cells are HelveticaNeueLTPro-Md at 8pt,
    so the style separates a real paragraph number from a table cell."""
    span = max(line["spans"], key=lambda sp: len(sp["text"]))
    return "MdCn" in span["font"] and 6.0 <= span["size"] <= 8.0


def _is_running_header_or_footer(line: dict, page_height: float) -> bool:
    """Page furniture: the header ("MUTCD 11th Edition – Revision 1",
    "Page 583") is Times-Roman 10 at the top; the footer ("December 2025",
    "Sect. 2E.30") is Times-Roman 8 at the bottom. Matched by position AND
    style, because table notes also sit in the bottom band (in Helvetica)."""
    span = max(line["spans"], key=lambda sp: len(sp["text"]))
    font, size = span["font"], span["size"]
    y0, y1 = line["bbox"][1], line["bbox"][3]
    if y1 < 0.06 * page_height and font.startswith("Times-Roman") and 9.5 <= size <= 10.5:
        return True
    if y0 > 0.935 * page_height and font.startswith("Times-Roman") and 7.5 <= size <= 8.5:
        return True
    return False


def _parse_one_section(
    doc: fitz.Document,
    sec_id: str,
    section_title: str,
    page_start_idx: int,
    page_end_idx: int,
    hierarchy: dict,
    sign_code_re: Optional[re.Pattern],
    headings: dict,
    skip_pages: Optional[set] = None,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    cur_rule: Optional[str] = None
    cur_ord: Optional[int]  = None
    cur_body: List[str]     = []
    seen_cids: dict         = {}
    section_started = False
    non_body_lines: List[tuple] = []     # (page, text) of table/figure text seen in this section
    last_page_pdf   = page_start_idx + 1
    last_page_label = doc.load_page(page_start_idx).get_label() or str(page_start_idx + 1)

    def _clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        # Revision-1 pages use U+2011 non-breaking hyphens in ids
        # ("Table 6B\u20112") — normalise so FIGREF/TABREF resolve.
        return text.translate({0x2010: "-", 0x2011: "-", 0x2012: "-",
                               0x2013: "-", 0x2014: "-"})

    def _emit(cid: str, text: str, page_pdf: int, page_label: str, **extra) -> None:
        figure_refs  = sorted(set(_normalize_id(x) for x in FIGREF_RE.findall(text)))
        table_refs   = sorted(set(_normalize_id(x) for x in TABREF_RE.findall(text)))
        section_refs = sorted({x for x in SECREF_RE.findall(text) if x != sec_id})
        sign_codes   = sorted(set(sign_code_re.findall(text))) if sign_code_re else []
        modal = sorted({m.lower() for m in MODAL_RE.findall(text)})
        chunks.append(Chunk(
            chunk_id=cid, part=hierarchy.get("part"), chapter=hierarchy.get("chapter"),
            section_id=sec_id, section_title=section_title, content_type=cur_rule,
            ordinal=cur_ord, page_pdf=page_pdf, page_printed=page_label, text=text,
            figure_refs=figure_refs, table_refs=table_refs, section_refs=section_refs,
            sign_codes=sign_codes, modal_verbs=modal, **extra,
        ))

    def flush() -> None:
        nonlocal cur_body
        if section_started and cur_rule and cur_ord is not None and cur_body:
            # section+rule+ordinal is NOT unique: a paragraph split across
            # a page break re-fires the ordinal. Suffix only the 2nd+
            # occurrence so existing ids stay stable.
            cid = f"MUTCD11e_{sec_id.replace('.', '')}_{cur_rule}_{cur_ord:02d}"
            if cid in seen_cids:
                seen_cids[cid] += 1
                cid = f"{cid}_{seen_cids[cid]}"
            else:
                seen_cids[cid] = 0
            texts = [t for t, _, _ in cur_body]
            # Page = where the paragraph STARTS. It used to be the page of the
            # line that ended it, i.e. often the next paragraph's page.
            first_page, first_label = cur_body[0][1], cur_body[0][2]
            found = _split_list(texts)
            if not found:
                text = _clean(" ".join(texts))
                if text:
                    _emit(cid, text, first_page, first_label)
            else:
                lead_end, items = found
                lead = _clean(" ".join(texts[:lead_end]))
                for mk, i, j in items:
                    body = _clean(" ".join(texts[i:j]))
                    text = f"{lead} {body}".strip() if lead else body
                    _emit(f"{cid}_item{mk}", text, cur_body[i][1], cur_body[i][2],
                          source="list_item", parent_id=cid, item=mk)
        cur_body = []

    for p_idx in range(page_start_idx, page_end_idx):
        if p_idx >= doc.page_count: break
        if skip_pages and (p_idx + 1) in skip_pages: continue
        page = doc.load_page(p_idx)
        page_no = p_idx + 1
        page_h = page.rect.height
        last_page_pdf = page_no
        last_page_label = page.get_label() or str(page_no)
        # "dict" mode yields exactly the same line strings as the old "blocks"
        # mode (checked on all 1,162 pages) plus each line's font and position,
        # which the header/footer and heading checks need.
        blocks = sorted(
            [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
            key=lambda b: (b["bbox"][1], b["bbox"][0]),
        )
        for block in blocks:
            for line in block["lines"]:
                s = "".join(sp["text"] for sp in line["spans"]).strip()
                if not s: continue
                if _is_running_header_or_footer(line, page_h): continue
                if s in FOOTER_LINES: continue
                if PRINTED_PG.match(s): continue
                if SECT_RANGE.match(s): continue
                if REV_MARK_RE.match(s): continue      # "Rev. 1" margin mark
                if BLANK_PAGE_RE.match(s): continue    # blank-page filler

                size = max(line["spans"], key=lambda sp: len(sp["text"]))["size"]
                heading_id = _real_section_heading(s, page_no, size, headings)
                if heading_id:
                    if heading_id == sec_id:
                        section_started = True
                        cur_rule = None
                        cur_ord = None
                    elif section_started:
                        flush()
                        return chunks
                    continue  # skip other sections' headings

                # Only REAL part/chapter headings end a section. Body lines
                # such as "Part 7 sets forth ..." are ordinary text.
                if _real_part_or_chapter_heading(s, page_no, headings):
                    if section_started:
                        flush()
                        return chunks
                    continue

                if not section_started:
                    continue

                m_rule = RULE_RE.match(s)
                if m_rule:
                    flush()
                    cur_rule = m_rule.group(1)
                    cur_ord = None
                    continue

                m_num = NUM_ONLY_RE.match(s) if _paragraph_number_style(line) else None
                if m_num:
                    flush()
                    cur_ord = int(m_num.group(1))
                    continue

                if cur_rule and cur_ord is not None:
                    # Provisions are set in Times. Table cells and table notes
                    # are Helvetica Neue LT Pro; figure labels, callouts and
                    # figure notes are Helvetica. Letting those in turned table
                    # cells such as "10" into fake paragraph numbers and mixed
                    # "22.5 x 18" into provision text. Non-Times lines are kept
                    # aside so table and figure notes can become their own chunks.
                    if _body_font(line):
                        cur_body.append((s, page_no, last_page_label))
                    else:
                        non_body_lines.append((page_no, s))
    flush()
    return chunks


NOTES_HEADING_RE = re.compile(r"^Notes for Figure\s+([0-9A-Z]+-[0-9]+)")
NOTE_ITEM_RE     = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
# Indents measured on all 54 notes pages: labels x=36 (202/202), item starts
# x=54 (469/469), wraps x=72 or 90. Nothing else appears at these positions
# except the four "Flagging/Signalized Method" sub-headings on page 927.
_NOTES_LABEL_X, _NOTES_ITEM_X = 44.0, 63.0


def _parse_figure_notes(doc, toc, hierarchy: dict, sign_code_re) -> List[Chunk]:
    """Chunk the Part 6 "Notes for Figure 6P-N" pages.

    These 54 pages carry real Standard/Guidance/Option/Support labels and
    ~469 numbered provisions (147 uses of "shall"), but the section walker
    dropped ~94% of them: the notes use the item number ("4.") as their
    paragraph number instead of the margin number the walker looks for.

    Each numbered item becomes one chunk. Numbering runs across labels, so
    the label in force sets content_type and the item number sets ordinal.
    The notes title and any sub-heading ("Flagging Method") are kept as a
    lead-in: an item under one method must not be read as applying to both.
    """
    out: List[Chunk] = []
    entries = [(m.group(1), pg, t.strip()) for lvl, t, pg in toc
               for m in [NOTES_HEADING_RE.match(t.strip())] if m and lvl == 3]
    for fig_id, page_no, _outline_title in entries:
        page = doc.load_page(page_no - 1)
        page_h = page.rect.height
        page_label = page.get_label() or str(page_no)
        title_lines: List[str] = []
        cur_rule: Optional[str] = None
        subhead: Optional[str] = None
        items: List[dict] = []          # {n, rule, subhead, lines}
        blocks = sorted([b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
                        key=lambda b: (b["bbox"][1], b["bbox"][0]))
        for block in blocks:
            for line in block["lines"]:
                txt = "".join(sp["text"] for sp in line["spans"]).strip()
                if not txt: continue
                if _is_running_header_or_footer(line, page_h): continue
                if txt in FOOTER_LINES or PRINTED_PG.match(txt) or SECT_RANGE.match(txt): continue
                if REV_MARK_RE.match(txt): continue
                span = max(line["spans"], key=lambda sp: len(sp["text"]))
                x0 = line["bbox"][0]
                if span["size"] > 11.5 and span["font"].startswith("Times-Bold"):
                    title_lines.append(txt)          # heading + subtitle
                    continue
                if x0 < _NOTES_LABEL_X and RULE_RE.match(txt):
                    cur_rule = RULE_RE.match(txt).group(1)
                    subhead = None                   # a new label ends the sub-heading
                    continue
                m_item = NOTE_ITEM_RE.match(txt)
                if x0 < _NOTES_ITEM_X and m_item:
                    items.append({"n": int(m_item.group(1)), "rule": cur_rule,
                                  "subhead": subhead, "lines": [m_item.group(2)]})
                    continue
                if x0 < _NOTES_ITEM_X:
                    subhead = txt                    # e.g. "Flagging Method"
                    continue
                if items:
                    items[-1]["lines"].append(txt)   # wrapped line
        title = _clean_text(" ".join(title_lines))
        for it in items:
            if it["rule"] is None:
                log.warning("notes %s item %s has no Standard/Guidance/Option label; skipped",
                            fig_id, it["n"])
                continue
            lead = f"{title}. {it['subhead']}." if it["subhead"] else f"{title}."
            text = _clean_text(f"{lead} {it['n']}. " + " ".join(it["lines"]))
            cid = (f"MUTCD11e_6P01_TA{fig_id.split('-')[1]}"
                   f"_{it['rule']}_{it['n']:02d}")
            figure_refs = sorted(set(_normalize_id(x) for x in FIGREF_RE.findall(text)))
            out.append(Chunk(
                chunk_id=cid, part=hierarchy.get("part"), chapter=hierarchy.get("chapter"),
                section_id="6P.01", section_title="Typical Applications",
                content_type=it["rule"], ordinal=it["n"],
                page_pdf=page_no, page_printed=page_label, text=text,
                figure_refs=figure_refs,
                table_refs=sorted(set(_normalize_id(x) for x in TABREF_RE.findall(text))),
                section_refs=sorted({x for x in SECREF_RE.findall(text) if x != "6P.01"}),
                sign_codes=sorted(set(sign_code_re.findall(text))) if sign_code_re else [],
                modal_verbs=sorted({m.lower() for m in MODAL_RE.findall(text)}),
                source="figure_note", parent_id=f"Figure {fig_id}", item=str(it["n"]),
                authority_inferred=False,     # labels are printed in the manual
            ))
    return out


APPENDIX_OUTLINE_RE = re.compile(r"^APPENDIX\s+(A\d+)\s*(.*)$", re.IGNORECASE)
STATUTE_SECTION_RE  = re.compile(r"^Section\s+\d+[A-Za-z0-9()]*\s*[.\u2014-]")


def _is_caps_heading(text: str) -> bool:
    """A statute heading such as "PUBLIC LAW 104-59-NOV. 28, 1995 (...)" or
    "DIVISION L, TITLE I": bold, at the margin, and with no lower-case letter
    anywhere. Testing only the first word is not enough, because wrapped
    Standard text can begin with an acronym ("FHWA Standard Alphabet ...")."""
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 4 and not any(ch.islower() for ch in letters)


def _parse_appendices(doc, toc, sign_code_re) -> List[Chunk]:
    """Chunk the Appendices (A1 Congressional Actions, A2 Metric Conversions).

    These pages sit past the last section, so the section walker never reached
    them; their text used to leak into 9F.03 as fake numbered paragraphs and
    was then dropped entirely when the body was capped at "Appendices".

    A1 quotes federal statutes under "PUBLIC LAW ..." headings, split at each
    statutory "Section N". Quoted statute carries no MUTCD heading type, and
    its "shall" binds the Secretary rather than a road agency, so it is filed
    as Support with authority_inferred=True rather than read as a Standard.
    The two printed labels on the last A1 page are used as printed.
    A2 keeps its introductory paragraph; Tables A2-1..A2-4 are table content
    (Helvetica) and are left to the table work.
    """
    entries = [(m.group(1).upper(), pg) for lvl, t, pg in toc
               for m in [APPENDIX_OUTLINE_RE.match(t.strip())] if m and lvl == 2]
    if not entries:
        return []
    out: List[Chunk] = []
    for k, (app_id, start) in enumerate(entries):
        end = entries[k + 1][1] - 1 if k + 1 < len(entries) else doc.page_count
        title_lines: List[str] = []
        cur_rule: Optional[str] = None
        lead: Optional[str] = None
        lead_open = False          # previous line was part of a heading
        body: List[str] = []
        first_page = start
        ordinal = 0

        def flush():
            nonlocal body, ordinal, out, cur_rule
            text = _clean_text(" ".join(body))
            body = []
            if len(text) < 15:
                return
            ordinal += 1
            rule = cur_rule or "Support"
            head = _clean_text(" ".join(title_lines))
            full = _clean_text(f"{head}. {lead}. {text}" if lead else f"{head}. {text}")
            out.append(Chunk(
                chunk_id=f"MUTCD11e_{app_id}_{rule}_{ordinal:02d}",
                part="Appendices", chapter=f"Appendix {app_id}",
                section_id=app_id, section_title=head, content_type=rule,
                ordinal=ordinal, page_pdf=first_page,
                page_printed=doc.load_page(first_page - 1).get_label() or str(first_page),
                text=full,
                figure_refs=sorted(set(_normalize_id(x) for x in FIGREF_RE.findall(full))),
                table_refs=sorted(set(_normalize_id(x) for x in TABREF_RE.findall(full))),
                section_refs=sorted(set(SECREF_RE.findall(full))),
                sign_codes=sorted(set(sign_code_re.findall(full))) if sign_code_re else [],
                modal_verbs=sorted({m.lower() for m in MODAL_RE.findall(full)}),
                source="appendix", parent_id=lead, item=None,
                authority_inferred=(cur_rule is None),
            ))

        for page_no in range(start, end + 1):
            page = doc.load_page(page_no - 1)
            page_h = page.rect.height
            lines = []
            for block in sorted([b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
                                key=lambda b: (b["bbox"][1], b["bbox"][0])):
                for line in block["lines"]:
                    txt = "".join(sp["text"] for sp in line["spans"]).strip()
                    if not txt: continue
                    if _is_running_header_or_footer(line, page_h): continue
                    if txt in FOOTER_LINES or PRINTED_PG.match(txt) or REV_MARK_RE.match(txt): continue
                    lines.append((line, txt))
            if not lines:
                continue
            margin = min(ln["bbox"][0] for ln, _ in lines)
            for line, txt in lines:
                span = max(line["spans"], key=lambda sp: len(sp["text"]))
                at_margin = line["bbox"][0] <= margin + 2
                if not span["font"].startswith("Times"):
                    continue                                   # A2 table content
                if span["size"] > 11.5:
                    flush(); title_lines.append(txt); lead = None
                    lead_open = False; first_page = page_no
                    continue
                if RULE_RE.match(txt):
                    lead_open = False
                if RULE_RE.match(txt):
                    flush(); cur_rule = RULE_RE.match(txt).group(1); first_page = page_no
                    continue
                # A "PUBLIC LAW ..." heading is bold at the margin AND starts
                # with an all-caps word. Standard text is ALSO printed bold, so
                # bold alone would split every Standard block at each wrap.
                if at_margin and span["font"] == "Times-Bold" and _is_caps_heading(txt):
                    if lead_open:
                        lead = _clean_text(f"{lead} {txt}")   # wrapped heading
                    else:
                        flush(); lead = txt; cur_rule = None; first_page = page_no
                    lead_open = True
                    continue
                lead_open = False
                if at_margin and STATUTE_SECTION_RE.match(txt):
                    flush(); first_page = page_no
                if not body:
                    first_page = page_no
                body.append(txt)
        flush()
    return out


CAPTION_RE     = re.compile(r"^(Figure|Table)\s+[0-9A-Z]+-[0-9]+[.\s]", re.IGNORECASE)
# "Note:"/"Notes:"/"Where:" are unambiguous. A bare "*" or footnote number is
# not: table cells such as "2 Lane Road" look the same, so those need prose.
NOTE_WORD_RE   = re.compile(r"^(Notes?|Where)\s*:")
NOTE_MARKER_RE = re.compile(r"^([\*\u2020\u2021\u00a7]+\s*|\d{1,2}\s*[\.\)]?\s+(?=[A-Z(])"
                            r"|[a-z]\s*[\.\)]\s+(?=[A-Z(]))")
# Some figure notes carry no marker at all, e.g. Figure 3C-1's "Minimum
# crosswalk width shall be 8 feet where the posted speed limit is 40 mph or
# greater at a non-intersection crosswalk." Those are accepted only when the
# block reads as a finished sentence, which panel labels ("A - Example of
# signing for ...") and table rows do not.
PANEL_LABEL_RE = re.compile(r"^[A-Z]\s*[-\u2010-\u2014]\s")
SENTENCE_VERB_RE = re.compile(r"\b(shall|should|may|must|is|are|can|will)\b", re.IGNORECASE)
NOTE_ITEM_SPLIT_RE = re.compile(r"(?:^|(?<=[.\s]))(\d{1,2})\.\s+(?=[A-Z(])")


def _is_note_prose(text: str, min_words: int = 6, min_lower: int = 3) -> bool:
    w = text.split()
    return len(w) >= min_words and sum(1 for x in w if x[:1].islower()) >= min_lower


def _is_unmarked_note(text: str) -> bool:
    """A complete sentence printed inside a figure, with no note marker."""
    return (len(text) >= 45 and text.rstrip().endswith((".", ")"))
            and not PANEL_LABEL_RE.match(text)
            and bool(SENTENCE_VERB_RE.search(text))
            and _is_note_prose(text, min_words=8))


def _split_note_items(text: str) -> List[str]:
    """"Notes: 1. A 2. B" -> ["Notes 1. A", "Notes 2. B"].

    Markers must run 1, 2, 3..., so "see Sections 2D.29, 2D.30" is not split.
    """
    hits, expect = [], 1
    for m in NOTE_ITEM_SPLIT_RE.finditer(text):
        if int(m.group(1)) == expect:
            hits.append(m.start()); expect += 1
    if len(hits) < 2:
        return [text]
    lead = text[:hits[0]].strip().rstrip(":")
    parts = [text[a:b].strip() for a, b in zip(hits, hits[1:] + [len(text)])]
    return [f"{lead} {x}".strip() if lead else x for x in parts]


def _authority_from_verb(text: str) -> str:
    """Infer the heading type from the verb, per Section 1C.01: a Standard
    statement uses "shall", Guidance "should", an Option "may", and Support
    none of them. Notes inside figures and tables carry no printed heading,
    so anything derived this way is marked authority_inferred=True.
    """
    low = text.lower()
    if re.search(r"\bshall\b", low):  return "Standard"
    if re.search(r"\bshould\b", low): return "Guidance"
    if re.search(r"\bmay\b", low):    return "Option"
    return "Support"


def _crop_note_texts(doc, crop, allow_unmarked: bool = False) -> List[str]:
    """Notes printed inside one figure/table crop, in reading order.

    A note must be introduced by a printed marker ("Note:", "Where:", "*", or
    a footnote number/letter). Sampling showed unmarked prose blocks inside a
    crop are table rows and figure panel labels, not notes, so they are left
    out. Only non-Times lines are read: body prose is Times, and figure crop
    boxes are loose enough to overlap ordinary paragraphs.
    """
    page = doc.load_page(crop["page_pdf"] - 1)
    page_h = page.rect.height
    x0, y0, x1, y1 = crop["bbox"]
    found: List[dict] = []
    for block in sorted([b for b in page.get_text("dict")["blocks"] if b.get("type") == 0],
                        key=lambda b: b["bbox"][1]):
        bx0, by0, bx1, by1 = block["bbox"]
        if not (x0 <= (bx0 + bx1) / 2 <= x1 and y0 <= (by0 + by1) / 2 <= y1): continue
        if by1 < 0.06 * page_h or by0 > 0.935 * page_h: continue
        lines = []
        for ln in block["lines"]:
            t = "".join(sp["text"] for sp in ln["spans"]).strip()
            span = max(ln["spans"], key=lambda sp: len(sp["text"]))
            if t and not span["font"].startswith("Times"):
                lines.append(t)
        if not lines: continue
        txt = _clean_text(" ".join(lines))
        # A revision mark can share a PDF block with the note it sits beside,
        # so stripping whole "Rev. 1" lines is not enough.
        txt = re.sub(r"\s*\bRev\.\s*1\b\s*", " ", txt).strip()
        if not txt or CAPTION_RE.match(txt): continue
        marked = bool(NOTE_WORD_RE.match(txt) or NOTE_MARKER_RE.match(txt))
        # Continuation first: a wrapped tail carries no marker, and left to the
        # start rules it would open a second note mid-sentence ("shoulder
        # signing. 2. The red-colored pavement is optional.").
        if (found and not marked and _is_note_prose(txt, min_words=3, min_lower=1)
                and bx0 >= found[-1]["x0"] - 3 and by0 - found[-1]["y1"] < 30):
            found[-1]["text"] = _clean_text(found[-1]["text"] + " " + txt)
            found[-1]["y1"] = by1
        elif ((NOTE_WORD_RE.match(txt) and _is_note_prose(txt, min_words=4, min_lower=1))
              or (NOTE_MARKER_RE.match(txt) and _is_note_prose(txt))
              or (allow_unmarked and _is_unmarked_note(txt))):
            found.append({"x0": bx0, "y1": by1, "text": txt})
    out: List[str] = []
    for n in found:
        out.extend(_split_note_items(n["text"]))
    return out


def _parse_crop_notes(doc, figures, chunks: List[Chunk], sign_code_re) -> List[Chunk]:
    """One chunk per note printed inside a figure or table.

    These notes carry the conditions attached to the numbers: Table 6B-4's
    variable key, Table 4C-7's definition of a high-occupancy bus, Table
    3G-1's "spacing ... should not exceed 300 feet". They used to be pulled
    into whatever provision paragraph was being read, or dropped entirely.
    """
    if not figures:
        return []
    def get(f, k, default=None):
        return f.get(k, default) if isinstance(f, dict) else getattr(f, k, default)

    # Anchor section = the section the crop SITS IN (last section heading at or
    # before the crop's page). Anchoring to the first citing section instead put
    # Table 6B-4 under 6P.01 and Figure 8D-3 under 4F.18, because a table can be
    # cited from anywhere. Citations are already carried by figure_refs/
    # table_refs on the citing chunks, so nothing is lost. A citing section in
    # the figure's own chapter is used when the crop page has no owner.
    page_owner: List[tuple] = sorted(
        (c.page_pdf, c.section_id, c.section_title, c.part, c.chapter) for c in chunks
        if c.source in ("paragraph", "list_item"))
    citing: dict = {}
    for c in chunks:
        for ref in list(c.figure_refs) + list(c.table_refs):
            citing.setdefault(ref, []).append((c.section_id, c.section_title))

    # part/chapter come from the anchor section too. Leaving them unset filed
    # all 583 note chunks under "Part ?"/"Chapter ?" in the graph and broke the
    # Part-match score bonus in retrieval.
    sec_meta = {sid: (title, part, chap) for _, sid, title, part, chap in page_owner}

    def anchor_for(canon: str, page: int):
        best = None
        for pg, sid, title, part, chap in page_owner:
            if pg <= page: best = (sid, title, part, chap)
            else: break
        if best:
            return best
        chapter = canon.split("-")[0].upper()
        for sid, title in citing.get(canon, []):
            if sid.split(".")[0].upper() == chapter:
                t, part, chap = sec_meta.get(sid, (title, None, None))
                return (sid, t, part, chap)
        sid, title = citing.get(canon, [("", "")])[0]
        t, part, chap = sec_meta.get(sid, (title, None, None))
        return (sid, t, part, chap)

    counter: dict = collections.Counter()
    out: List[Chunk] = []
    for f in sorted(figures, key=lambda f: (get(f, "figure_id", ""), get(f, "page_pdf", 0))):
        crop = {"page_pdf": get(f, "page_pdf"), "bbox": list(get(f, "bbox") or [])}
        if not crop["bbox"]: continue
        fig_id = get(f, "figure_id", "")
        canon = _normalize_id(get(f, "canonical_id", "") or fig_id.split(" ", 1)[-1])
        kind = (get(f, "kind", "Figure") or "Figure").lower()
        sec_id, sec_title, sec_part, sec_chap = anchor_for(canon, crop["page_pdf"])
        # Unmarked sentences are accepted inside figures only. Inside tables
        # they would sweep in prose-heavy cells (Tables 2L-3, 2L-4, 5A-1).
        for text in _crop_note_texts(doc, crop, allow_unmarked=(kind != "table")):
            counter[fig_id] += 1
            n = counter[fig_id]
            full = _clean_text(f"{fig_id}. {text}")
            rule = _authority_from_verb(text)
            tag = "TBLNOTE" if kind == "table" else "FIGNOTE"
            out.append(Chunk(
                chunk_id=f"MUTCD11e_{tag}_{canon}_{n:02d}",
                part=sec_part, chapter=sec_chap,
                section_id=sec_id, section_title=sec_title,
                content_type=rule, ordinal=n,
                page_pdf=crop["page_pdf"], page_printed=str(get(f, "page_printed", "") or crop["page_pdf"]),
                text=full,
                figure_refs=sorted(set(_normalize_id(x) for x in FIGREF_RE.findall(full))),
                table_refs=sorted(set(_normalize_id(x) for x in TABREF_RE.findall(full))),
                section_refs=sorted({x for x in SECREF_RE.findall(full) if x != sec_id}),
                sign_codes=sorted(set(sign_code_re.findall(full))) if sign_code_re else [],
                modal_verbs=sorted({m.lower() for m in MODAL_RE.findall(full)}),
                source=("table_note" if kind == "table" else "figure_note"),
                parent_id=fig_id, item=str(n),
                authority_inferred=True,      # no heading is printed inside a crop
            ))
    return out


LIST_ITEM_RE = re.compile(r"^([A-Z]|\d{1,3})\.(?:\s+(\S.*))?$")


def _next_marker(m: str) -> str:
    return chr(ord(m) + 1) if m.isalpha() else str(int(m) + 1)


def _split_list(lines: List[str]):
    """Find a top-level list inside one paragraph.

    In the manual every list item starts a new printed line with "A." or
    "12." (definitions put the number alone on its line). Items must run in
    sequence from A or 1; markers of any other value are nested content and
    stay inside the current item. Returns (lead_in_end, [(marker, start, end)])
    or None when there is no list of at least two items.
    """
    starts, expected = [], None
    for i, t in enumerate(lines):
        m = LIST_ITEM_RE.match(t)
        if not m:
            continue
        mk = m.group(1)
        if (expected is None and mk in ("A", "1")) or mk == expected:
            starts.append((mk, i))
            expected = _next_marker(mk)
    if len(starts) < 2:
        return None
    items = []
    for k, (mk, i) in enumerate(starts):
        end = starts[k + 1][1] if k + 1 < len(starts) else len(lines)
        items.append((mk, i, end))
    return starts[0][1], items


def _normalize_id(s: str) -> str:
    """Normalise a figure/table id (e.g. 'figure 2b-1' -> '2B-1')."""
    s = s.strip().upper()
    s = re.sub(r"\s+", "", s)
    return s
