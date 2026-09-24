"""Semantic tagging of MUTCD sentences against the frozen structural vocabulary.

The vocabulary (MUTCD_structural_vocabulary.md) has seventeen pieces. Each is
announced in the manual by a phrase. This module finds those phrases, sentence
by sentence, and records what it found.

Two rules govern everything here:

  1. Nothing is inferred. A piece is recorded only when its phrase is present.

  2. A number is bound to the quantity it measures only where the grammar makes
     that unambiguous. Otherwise it is reported UNBOUND. An unbound number is
     visible residue. A wrongly bound one is a confident wrong answer, which is
     the failure this whole system exists to prevent.

The phrase tables are data. They are meant to be read and corrected by the
engineer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .provision import split_provision

__all__ = ["PIECES", "QUANTITY_HEADS", "Quantity", "Tag", "SentenceTags",
           "tag_sentence", "sentences"]

# =========================================================================== #
# 1. Phrase tables -- one list per piece
# =========================================================================== #
PIECES: Dict[str, List[str]] = {
    # core units (RULE is the authority below; CONDITION uses the splitter)
    "DEFINITION": [
        r"\bmeans\b", r"\bis considered to\b", r"\bare considered to\b",
        r"\bis defined as\b", r"\bdenotes\b",
        r"\bshall be the (?:difference|sum|distance|average)\b",
        r"^\s*where:\s", r"\bis taken to be\b",
        r"\bthe term\b.{0,40}\bshall include\b",
        r"\bthe (?:word|term) \W?[\w-]+\W? includes\b", r"\bfor the purposes of this (?:warrant|section|chapter)\b",
        r"\bmeasured (?:vertically|horizontally|laterally|longitudinally|"
        r"along|from|between|at)\b",
    ],
    "POINTER": [
        r"\bsee (?:section|table|figure|chapter|paragraph|item)s?\b",
        r"\bcontains? (?:information|provisions)\b",
        r"\bdescribed in (?:section|chapter)\b",
        r"\bas shown in (?:figure|table)\b",
    ],
    # quantities and values
    "ILLUSTRATIVE": [
        r"\bfor example\b", r"\bfor illustrative purposes\b", r"\be\.g\.", r"\bis shown for illustration\b",
    ],
    "COMPUTED": [
        r"\bis (?:less|greater|more) than the number of\b",
        r"\bshall be the difference between\b", r"\bequals\b",
        r"\bdivided by\b", r"\bmultiplied by\b", r"\bsquared\b",
        r"\b[A-Z]\s*=\s*[A-Z0-9]", r"\btotal of both approaches\b",
        r"\bpercent of the\b",
    ],
    "SITE_VARIABLE": [
        r"\bXX\b", r"\bX{2,}\b", r"\banticipated operating speed\b",
        r"\bwidth of offset\b",
    ],
    # structure
    "LOOKUP": [
        r"\bin accordance with (?:the information shown in )?(?:table|figure|chart)\b",
        r"\bas shown in (?:the )?(?:\w+ )?(?:column|table|chart)\b",
        r"\bshown in table\b", r"\bfall above the applicable curve\b",
        r"\bin chart [ab]\b",
    ],
    "SELECTOR": [
        r"\bmay be used in place of\b", r"\bused for combination of\b",
        r"\bapplies as the lower threshold\b", r"\b\d+ percent columns?\b",
        r"\bcolumn of table\b", r"\bin the \w+ column\b",
    ],
    "ARRANGEMENT": [
        r"\bfor each of any \d+ hours\b", r"\beach of any \d+ hours\b",
        r"\bthe same \d+ hours\b", r"\bconsecutive \d+-minute periods\b",
        r"\bdistance between signs\b", r"\bspacing\b", r"\bupstream\b",
        r"\bdownstream\b", r"\bin advance of\b", r"\bpreced(?:e|es|ing)\b",
        r"\bat intervals\b", r"\bof an average day\b",
    ],
    "EXCEPTION": [
        r"\bexcept as (?:otherwise )?provided\b",
        r"\bexcept (?:for|where|when|that|in)\b",
        r"\bunless otherwise (?:provided|specified|noted|required)\b",
        r"\bmay be omitted\b", r"\bneed not\b",
        r"\bother than (?:for )?(?:a |an |the )?\w",
        r"\badditional or supplemental\b", r"\bnotwithstanding\b",
        r"\bunless otherwise directed\b", r"\bexcept as such \w+ is modified by\b",
        r"\b(?:this|the) (?:limitation|requirement|provision)s? (?:does|do|shall) not apply\b",
    ],
    "SUBSTITUTION": [
        r"\bmay be used in place of\b", r"\binstead of\b", r"\bin lieu of\b",
        r"\bmay be substituted\b", r"\bmay be replaced by\b",
        r"\bmay be used as an alternate\b",
    ],
    "INHERITED_AUTHORITY": [
        r"\bcan generally be regarded as (?:standard|guidance|option|support)\b",
        r"\bclearly classified using headings\b",
    ],
    # limits and silence
    "BLOCKED_INFERENCE": [
        r"\bshall not in itself\b", r"\bdoes not,? in itself\b",
        r"\bshould not be used to determine\b", r"\bis not intended to be\b",
        r"\bnot necessarily\b", r"\bis not conclusive\b",
        r"\bnot a substitute for\b",
        r"\beven if (?:one or more of )?the (?:\w+ )?warrants?\b",
    ],
    "DELEGATED_JUDGMENT": [
        r"\bengineering judgment\b", r"\bengineering study\b",
        r"\b(?:to be )?determined by the (?:highway )?agency\b",
        r"\bat the discretion of\b", r"\bas determined by\b",
        r"\bbased on field conditions\b",
    ],
    "UNDETERMINED": [
        r"\badequate trial\b", r"\bisolated community\b", r"\bbuilt-up area\b",
        r"\bwhere practical\b",
        r"\bas practicable\b", r"\bsufficient(?:ly)?\b", r"\breasonabl[ey]\b",
        r"\bappropriate\b", r"\bas needed\b",
        r"\bunusual cases\b", r"\badequate gaps?\b", r"\bnecessary degree\b",
    ],
}
_COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in PIECES.items()}

AUTHORITY = [("STANDARD", re.compile(r"\bshall\b|\bmust\b", re.I)),
             ("GUIDANCE", re.compile(r"\bshould\b", re.I)),
             ("OPTION",   re.compile(r"\bmay\b", re.I))]

# =========================================================================== #
# 2. Numbers and units
# =========================================================================== #
# No bare "m": this edition is US customary, and "m" matched "Chapter 2M".
UNIT = (r"vehicle-hours|vehicle hours|mph|miles? per hour|feet per second|ft/s|feet|foot|ft|inches|inch|in\.|miles?|mi|"
        r"seconds?|sec|minutes?|hours?|degrees?|percent|%|"
        r"vehicles per (?:day|hour)|vph|vpd|pounds?|lbs?|tons?|"
        r"millimeters?|mm|meters|cd/lx/m2|lanes?|persons|pedestrians|"
        r"crashes|months?|years?|days?|vehicle-hours|vehicle hours|schoolchildren|students|children|people")
_NUM = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?|½|¼|¾|one|two|three|four|five|six|eight|ten"
_QTY = re.compile(rf"(?P<num>{_NUM})\s*(?:-\s*)?(?P<unit>{UNIT})(?:\b|(?<=%))", re.I)
# a count with no unit, introduced by its own quantity noun
_COUNT = re.compile(
    r"\b(?P<head>population|AADT|ADT|volume)\s+of\s+"
    r"(?:less than |more than |at least |fewer than |over |under )?"
    r"(?P<num>\d{1,3}(?:,\d{3})+|\d+)\b(?!\s*(?:" + UNIT + r"))", re.I)
_WXH = re.compile(r"\d+\s*x\s*\d+", re.I)
# a number that is part of a device's NAME, not a measurement
_NAME_AFTER = re.compile(r"^\s*(?:-\s*)?(?:\w+\s+){0,2}"
                         r"(?:loop|sign|plaque|symbol|arrow|marker)\b", re.I)

# =========================================================================== #
# 3. Comparison -- or the kind of statement the number makes instead
# =========================================================================== #
_AFTER = [("<=", re.compile(r"^\s*(?:or less|or lower|or fewer|or below)\b", re.I)),
          (">=", re.compile(r"^\s*(?:or more|or greater|or higher|or above|"
                            r"or longer|or wider)\b", re.I))]
_NEG = r"(?:shall|should|must|may|does|do|will|can)\s+not\s+(?:\w+\s+){0,2}"
_BEFORE = [
    (">=", re.compile(r"(?:equals? or exceeds?|equal to or (?:greater|more|higher) than|equal to or exceeding|"
                      r"(?:is|are|be) (?:equal to )?or (?:greater|more) than)\s*:?\s*$", re.I)),
    ("<=", re.compile(r"(?:equal to or (?:less|lower|fewer) than|as much as)\s*:?\s*$", re.I)),
    ("<=", re.compile(_NEG + r"(?:exceed|(?:be\s+)?(?:more|greater|higher|longer|wider|taller) than)\s*$", re.I)),
    (">=", re.compile(_NEG + r"(?:(?:be\s+)?(?:less|lower|fewer|shorter|narrower) than)\s*$", re.I)),
    ("<=", re.compile(r"(?:not (?:more|greater|higher) than|at most|"
                      r"maximum(?: [\w-]+){0,3} of|maximum|up to|no more than|"
                      r"not to exceed|not exceeding|no higher than|no taller than|"
                      r"no longer than|no wider than|no farther than|within|not over|"
                      r"at or below(?: which)?|at or under|"
                      r"less than or equal to)\s*$", re.I)),
    (">=", re.compile(r"(?:greater than or equal to|not less than|at least|minimum(?: [\w-]+){0,3} of|"
                      r"minimum|no less than|no lower than|no shorter than|"
                      r"no closer than)\s*$", re.I)),
    ("<",  re.compile(r"(?:less than|lower than|below|under|fewer than)\s*$", re.I)),
    (">",  re.compile(r"(?:more than|greater than|exceeds?|exceeding|above|"
                      r"over|higher than)\s*$", re.I)),
    ("==", re.compile(r"(?:\bof|\bis|\bbe|equal to|\bat)\s*$", re.I)),
]


def _operator(text: str, start: int, end: int) -> str:
    """ <= >= < > ==      a comparison
        ~                 approximately
        range             between A and B / A to B
        per               a rate, interval or increment
        for               a duration
        =                 an attribute ("a 6-inch border", "36 x 36 inches")
        ?                 none recognised                                   """
    before = text[max(0, start - 40):start]
    after = text[end:end + 25]
    # "shall be a multiple of 5 mph" -- divisibility, NOT equality
    if re.search(r"\b(?:a |an )?(?:whole |even )?multiples? of\s*$", before, re.I):
        return "multiple_of"
    if re.search(r"(?:approximately|about|roughly|nominally)\s*$", before, re.I):
        return "~"
    # "30 to 45 mph": the upper end of a range
    if re.search(r"\d\s*(?:to|through|-)\s*$", before):
        return "range"
    if re.search(r"\bbetween\s*$|\bfrom\s*$", before, re.I) or \
       re.match(r"\s*(?:to|and|through)\s+(?:\d|½|¼|¾)", after, re.I):
        return "range"
    if re.search(r"\b(?:every|each|per)\s*$", before, re.I) or \
       re.match(r"\s*(?:apart|intervals?|increments?)\b", after, re.I):
        return "per"
    if re.search(r"\bfor\s*$", before, re.I):
        return "for"
    for op, rx in _AFTER:
        if rx.search(after):
            return op
    for op, rx in _BEFORE:
        if rx.search(before):
            return op
    if re.search(r"\d\s*x\s*$", before) or re.match(r"\s*x\s*\d", after):
        return ">=" if re.search(r"\bminimum\b", text, re.I) else "="
    if re.search(r"\b(?:a|an|the)\s*$", before, re.I):
        return "="
    return "?"


# =========================================================================== #
# 4. Referents -- what a number is measured ON
# =========================================================================== #
# Quantity KINDS. Subjects such as "sign", "legend", "edge" are deliberately
# absent: they are the things being measured, not measurements. Including them
# bound half the sample to the wrong quantity.
QUANTITY_HEADS = [
    "speed limit", "advisory speed", "85th-percentile speed",
    "85th percentile speed", "speed differential", "posted speed",
    "operating speed", "statutory speed", "prevailing speed", "speed",
    "aadt", "adt", "average daily traffic", "traffic volume", "volume",
    "vehicles per hour", "distance", "spacing", "height", "mounting height",
    "width", "length", "radius", "offset", "clearance", "sight distance",
    "taper", "buffer", "diameter", "pitch", "size", "dimension",
    "stroke width", "letter height", "border", "grade", "angle",
    "change of direction", "change in horizontal alignment", "population",
    "lanes", "hours", "time", "duration", "interval", "period", "flash rate",
    "retroreflectivity", "delay", "gap", "queue", "crashes", "pedestrians",
    "clear zone", "median width", "reduction", "depth", "setback", "headway",
    "difference",
]
_HEADS = sorted(QUANTITY_HEADS, key=len, reverse=True)
_CLAUSE_START = re.compile(r"(?:^|[;:]|\b(?:if|when|where|unless|except)\b)", re.I)


def _heads_in(text: str):
    low = text.lower()
    for h in _HEADS:
        for m in re.finditer(r"\b" + re.escape(h) + r"s?\b", low):
            # "low-speed", "high-volume", "full-width": an adjective, not a measure
            if m.start() > 0 and low[m.start() - 1] == "-":
                continue
            yield m.start(), m.end(), h


def _referent(text: str, start: int, floor: int = 0) -> Tuple[Optional[str], Optional[str]]:
    """Backward binding. Two grammatical forms only.

    1. HEAD of [comparison]? N    "a width of 4 feet", "a speed limit of 30 mph"
    2. the clause SUBJECT         "the mounting height of a ONE WAY sign should
                                   be at least 4 feet" -- the FIRST head in the
                                   clause, not the nearest.
    """
    starts = [m.end() for m in _CLAUSE_START.finditer(text, 0, start)]
    c0 = max(starts[-1] if starts else 0, floor)
    clause = text[c0:start]

    m = re.search(r"([\w -]{2,45}?)\s+of\s+(?:not (?:less|more) than |at least |"
                  r"at most |less than |more than |up to |approximately |about |"
                  r"no more than |no less than |over |under )?$", clause, re.I)
    if m:
        hits = list(_heads_in(m.group(1)))
        if hits:
            s0, e0, h = max(hits, key=lambda x: (x[1], x[1] - x[0]))
            return m.group(1)[max(0, s0 - 25):].strip(), h

    if re.search(r"\b(?:shall|should|may|must|is|are|be)\b", clause, re.I):
        hits = list(_heads_in(clause))
        if hits:
            first = min(x[0] for x in hits)
            s0, e0, h = max((x for x in hits if x[0] == first),
                            key=lambda x: x[1] - x[0])
            return clause[s0:].strip()[:90], h
    return None, None


_FWD_POS = re.compile(
    r"^\s*(?:-\s*\w+\s*)?(?:or (?:less|more|greater|longer)\s*)?"
    r"(?P<rel>above|below|from|beyond|behind|before|after|past|outside|inside|"
    r"in advance of|downstream of|upstream of|in front of|back from)\s+"
    r"(?P<ref>(?:the |a |an |each |any )?[\w-]+(?: [\w-]+){0,5})", re.I)
_FWD_EVENT = re.compile(r"^\s*(?:of|following|after|from|before)\s+"
                        r"(?P<ref>(?:the )?[\w-]+(?: [\w-]+){0,5})", re.I)


_IN_DIM = re.compile(r"^\s*(?:or (?:more|less)\s+)?in\s+(?P<h>width|height|length|"
                     r"diameter|depth|thickness)\b", re.I)


def _attributive(text: str, m) -> Tuple[Optional[str], Optional[str], bool]:
    """A hyphenated number describes the noun right after it. Returns
    (referent, head, is_attributive)."""
    if "-" not in text[m.start():m.end() + 1]:
        return None, None, False
    nxt = text[m.end():m.end() + 40]
    words = re.findall(r"[A-Za-z][\w-]*", nxt)[:3]
    for n in (3, 2, 1):
        cand = " ".join(words[:n]).lower()
        if cand not in QUANTITY_HEADS and cand.endswith("s") and cand[:-1] in QUANTITY_HEADS:
            cand = cand[:-1]
        if cand in QUANTITY_HEADS:
            return f"{text[m.start():m.end()]} {cand}", cand, True
    return None, None, True


def _forward(text: str, m) -> Tuple[Optional[str], Optional[str]]:
    """The manual also names the reference point AFTER the number:
    "2 inches above the walkway", "within 3 months following completion"."""
    unit = m.group("unit").lower()
    after = text[m.end():m.end() + 80]
    if _WXH.search(text[max(0, m.start() - 8):m.end() + 12]):
        return text[max(0, m.start() - 8):m.end() + 12].strip(), "size"
    if unit.startswith("degree"):
        return text[max(0, m.start() - 40):m.end() + 20].strip(), "angle"
    if re.match(r"(?:hours?|minutes?|seconds?|days?|months?|years?)", unit):
        if re.search(r"\b(?:each of any|any|the same|those same)\s*$", text[max(0, m.start() - 20):m.start()], re.I):
            return text[max(0, m.start() - 15):m.end() + 20].strip(), "time window"
        if re.search(r"\bfor (?:a |an )?(?:(?:minimum|maximum|period) (?:of )?)?(?:at least |up to )?$",
                     text[max(0, m.start() - 30):m.start()], re.I):
            return text[max(0, m.start() - 25):m.end()].strip(), "duration"
        if re.match(r"\s*of an? (?:average )?(?:day|week|year)\b", after, re.I):
            return text[m.start():m.end() + 25].strip(), "time window"
        d = _FWD_EVENT.match(after)
        if d:
            return d.group("ref"), "time from event"
    if re.search(r"\bwithin\s*$", text[max(0, m.start() - 12):m.start()], re.I) and re.match(r"\s*of\s+\w", after):
        return "from " + after.strip()[3:60], "distance"
    d = _IN_DIM.match(after)
    if d:
        return f"in {d.group('h')}", d.group("h").lower()
    p = _FWD_POS.match(after)
    if p:
        return f"{p.group('rel')} {p.group('ref')}", "offset"
    return None, None


# =========================================================================== #
# 5. Records
# =========================================================================== #
@dataclass
class Quantity:
    number: str
    unit: str
    op: str
    referent: Optional[str]
    head: Optional[str]
    span: Tuple[int, int]

    @property
    def bound(self) -> bool:
        return self.head is not None


@dataclass
class Tag:
    piece: str
    phrase: str
    span: Tuple[int, int]


@dataclass
class SentenceTags:
    text: str
    authority: Optional[str]
    tags: List[Tag] = field(default_factory=list)
    quantities: List[Quantity] = field(default_factory=list)

    @property
    def pieces(self):
        return {t.piece for t in self.tags}

    @property
    def unbound(self):
        return [q for q in self.quantities if not q.bound]


# =========================================================================== #
# 6. Entry points
# =========================================================================== #
_SENT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])")
_ABBREV = re.compile(r"\b(?:e\.g|i\.e|etc|No|Sect|Fig|approx|min|max|U\.S)\.$")


_ENUM_ONLY = re.compile(r"^\W*(?:[A-Za-z]|\d{1,2})[.)]\W*$")
_ENUM_TAIL = re.compile(r"(?:(?<=[.;:,])|(?<=\band)|(?<=\bor))\s(\(?(?:\d{1,2}|[A-Z])[.)])$")


def sentences(text: str) -> List[str]:
    """Cut on sentence punctuation -- but an item marker ("C.", "2.") belongs to
    the sentence it introduces, never to the one before it or on its own."""
    parts, buf = [], ""
    carry = ""
    for piece in _SENT.split(text.strip()):
        if carry:
            piece, carry = f"{carry} {piece}", ""
        buf = f"{buf} {piece}".strip() if buf else piece
        if _ABBREV.search(buf) or _ENUM_ONLY.match(buf):
            continue
        m = _ENUM_TAIL.search(buf)
        if m:
            carry, buf = m.group(1), buf[:m.start()].rstrip()
        parts.append(buf)
        buf = ""
    if buf or carry:
        parts.append(f"{buf} {carry}".strip())
    return parts


# The unit limits what a number can measure. A binding the unit rules out is wrong.
_TIME_UNITS = re.compile(r"^(?:seconds?|sec|minutes?|hours?|days?|months?|years?)$", re.I)
_LEN_UNITS = re.compile(r"^(?:feet|foot|ft|inch|inches|in\.|miles?|mi|mm|millimeters?|meters)$", re.I)
_TIME_HEADS = {"time", "duration", "interval", "period", "hours", "time window", "time from event",
               "delay", "headway", "flash rate", "gap"}
_LEN_HEADS = {"distance", "spacing", "height", "mounting height", "width", "length", "radius", "offset",
              "clearance", "sight distance", "taper", "buffer", "diameter", "pitch", "size", "dimension",
              "stroke width", "letter height", "border", "median width", "clear zone", "depth", "setback",
              "extent", "reduction", "lateral", "longitudinal", "angle", "change of direction",
              "change in horizontal alignment", "edge"}


def _unit_consistent(text: str, q) -> None:
    unit = q.unit.lower()
    if q.head is None:
        return
    if _TIME_UNITS.match(unit) and q.head not in _TIME_HEADS:
        before = text[max(0, q.span[0] - 30):q.span[0]].lower()
        q.head = "time window" if re.search(r"\b(?:same|any|each of any|those|these)\s*$", before) else "duration"
    elif _LEN_UNITS.match(unit) and q.head not in _LEN_HEADS:
        q.head = None            # a length bound to a non-length: leave it unbound, visibly


def tag_sentence(text: str) -> SentenceTags:
    out = SentenceTags(text=text,
                       authority=next((a for a, rx in AUTHORITY if rx.search(text)), None))

    # CONDITION -- the splitter reads every form the manual uses, including
    # ones with no if/where/when: "on urban streets with an AADT of ..."
    sp = split_provision(text)
    cond_end = 0
    if sp is not None and sp.condition:
        i = max(text.find(sp.condition.strip()[:40]), 0)
        out.tags.append(Tag("CONDITION", sp.condition.strip(), (i, i + len(sp.condition))))
        if i == 0:                        # condition leads: "Where X, Y ..."
            cond_end = len(sp.condition)

    for piece, rxs in _COMPILED.items():
        for rx in rxs:
            for m in rx.finditer(text):
                out.tags.append(Tag(piece, m.group(0), m.span()))

    seen = set()
    for m in _QTY.finditer(text):
        if m.span() in seen:
            continue
        seen.add(m.span())
        unit = m.group("unit").lower()
        tail = text[m.end():m.end() + 30]

        if _NAME_AFTER.match(tail):                          # "270-degree Loop sign"
            continue
        if re.match(r"[A-Z][a-z]+-[A-Z]", text[m.start():m.end() + 2]) and re.match(r"\s+[A-Z][a-z]", tail):
            continue                                          # "Eight-Hour Vehicular Volume": a warrant's name
        if unit.startswith("lane") and "-" in text[m.start():m.end()]:
            continue                                          # "a two-lane road"
        if re.match(r"\s*columns?\b", tail, re.I):            # selector argument
            out.quantities.append(Quantity(m.group("num"), m.group("unit"), "==",
                                           text[m.start():m.end() + 8].strip(),
                                           "column selector", m.span()))
            continue

        if unit.startswith("lane"):
            out.quantities.append(Quantity(m.group("num"), m.group("unit"), _operator(text, m.start(), m.end()),
                                           text[m.start():m.end()], "lanes", m.span()))
            continue
        ref, head, attrib = _attributive(text, m)
        if not attrib:
            floor = cond_end if m.start() >= cond_end else 0
            ref, head = _referent(text, m.start(), floor)
            if head is None:
                ref, head = _forward(text, m)
        op = _operator(text, m.start(), m.end())
        if op in (">", "<") and re.match(r"\s*No\b", text) and \
           re.search(r"(?:more|greater|higher|less|lower|fewer) than\s*$", text[max(0, m.start() - 25):m.start()]):
            op = "<=" if op == ">" else ">="
        # "shall not be less than 12 inches or greater than 24 inches": the NOT
        # governs both halves, so the second bound is a maximum
        if op in (">", "<"):
            back = text[max(0, m.start() - 90):m.start()]
            if re.search(r"\bnot be (?:less|more|greater|lower) than\b[^.;]*\bor\s+"
                         r"(?:greater|more|less|lower) than\s*$", back, re.I):
                op = "<=" if op == ">" else ">="
        if op in ("==", "=", "?"):
            # "the minimum length for Type 3 Barricades shall be 48 inches":
            # the comparison is set by a word on the quantity, before the noun,
            # provided no other number stands between it and this one
            back = text[max(0, m.start() - 110):m.start()]
            lo = [x for x in re.finditer(r"\b(?:minimum|smallest|shortest|lowest)\b", back, re.I)]
            hi = [x for x in re.finditer(r"\b(?:maximum|largest|greatest|longest|highest)\b", back, re.I)]
            last = max(lo + hi, key=lambda x: x.start(), default=None)
            between = back[last.end():] if last is not None else ""
            if last is not None and not _QTY.search(between) and head and \
               re.search(r"\b" + re.escape(head.split()[-1]) + r"s?\b", between, re.I):
                op = ">=" if last in lo else "<="
        if op in ("=", "?") and re.search(r"\b(?:at least|minimum)\s+(?:a|an|the)?\s*$",
                                          text[max(0, m.start() - 20):m.start()], re.I):
            op = ">="
        out.quantities.append(Quantity(m.group("num"), m.group("unit"), op,
                                       ref, head, m.span()))

    for q in out.quantities:
        _unit_consistent(text, q)
    # "reduced as much as 50 percent": the size of a reduction, not a quantity of that kind
    for q in out.quantities:
        if q.unit.lower() in ("percent", "%"):
            b = text[max(0, q.span[0] - 30):q.span[0]]
            if re.search(r"\breduced (?:by |as much as |up to )?(?:\w+ )?$", b, re.I):
                q.head = "reduction"
            elif re.match(r"\s*(?:percent|%)?\s*of the (?:requirements?|criteri|volumes?|values?)", text[q.span[1]:q.span[1] + 30], re.I):
                q.head = "fraction of a criterion"
            elif q.head in _TIME_HEADS or (q.head and "volume" in q.head):
                q.head = None
    # "100 vehicles per hour for one lane or 150 vehicles per hour for two": the second shares the first's comparison
    for i, q in enumerate(out.quantities):
        if q.op == "?" and i:
            p = out.quantities[i - 1]
            between = text[p.span[1]:q.span[0]]
            if p.unit.lower() == q.unit.lower() and p.op not in ("?", "=") and len(between) < 90 and \
               re.search(r"\bor\b", between) and not re.search(r"[.;]", between):
                q.op = p.op
    if re.search(r"\bfor example\b|\bfor illustrative purposes\b|\be\.g\.", text, re.I):
        for q in out.quantities:
            q.op = "example"
    for m in _COUNT.finditer(text):
        span = m.span("num")
        if any(q.span[0] <= span[0] < q.span[1] for q in out.quantities):
            continue
        out.quantities.append(Quantity(m.group("num"), "count",
                                       _operator(text, span[0], span[1]),
                                       m.group(0), m.group("head").lower(), span))
    return out
