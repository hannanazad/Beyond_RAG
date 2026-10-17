"""The symbolic rule evaluator — the last deterministic verifier of S3.3.

WHERE IT SITS
-------------
The calculator refuses, on purpose, to decide conditions that are not
arithmetic. Table 4C-1 note c says a column "may be used when the major-street
speed exceeds 40 mph or in an isolated community with a population of less
than 10,000". The calculator returns the value, attaches the note, and stops
at UNKNOWN. The compiler then raises that note as its own obligation.

This verifier is what answers it, when the answer is a comparison over facts
that are already established. "Speed exceeds 40 mph" is not interpretation; it
is 45 > 40. Handing that to a language model would be spending a fallible
model on a decidable question, which is the opposite of what S3.3 asks for.

WHAT IT IS NOT
--------------
It is not a general reasoner. "Typical conditions are locations where the road
user must use extra time to adjust speed" is a judgement about a site, and no
amount of parsing turns it into a comparison. Anything it cannot reduce to a
comparison over known facts comes back UNKNOWN with the unparsed text
recorded, and an LLM operation takes it instead.

HOW IT CLOSES THE LOOP
----------------------
A TRUE certificate carries `provenance["discharges"]`, listing the conditions
it settled as ``"<table id>:<footnote marker>"``. The calculator reads exactly
that on its next pass and releases the value it was holding. A FALSE
certificate discharges nothing: a permission whose condition failed is a
permission that does not apply, and the held value must stay held.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .certificate import (Authority, Certificate, CertificateStore, Evidence,
                          Status)
from .network import Operation
from .table_data import Footnote, Table

__all__ = ["make_rule_evaluator", "parse_rule", "evaluate_rule", "facts_from_store",
           "Comparison", "Conjunction", "Disjunction", "Negation", "Unparsed"]


# --------------------------------------------------------------------------- #
# 1. The expression types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Comparison:
    """`subject` `comparator` `bound` — the only thing that is ever decided."""
    subject: str                 # normalised fact name, e.g. "speed"
    comparator: str              # > >= < <= == !=
    bound: float
    unit: Optional[str] = None
    source_text: str = ""

    def describe(self) -> str:
        u = f" {self.unit}" if self.unit else ""
        return f"{self.subject} {self.comparator} {self.bound:g}{u}"


@dataclass(frozen=True)
class Unparsed:
    """A clause that could not be reduced to a comparison. Always UNKNOWN.

    Kept as a node rather than dropped, because dropping it would silently
    turn "A or B" into "A" and change the answer.
    """
    text: str

    def describe(self) -> str:
        return f"unparsed({self.text[:60]!r})"


@dataclass(frozen=True)
class Conjunction:
    parts: Tuple["Expr", ...]

    def describe(self) -> str:
        return "(" + " and ".join(p.describe() for p in self.parts) + ")"


@dataclass(frozen=True)
class Disjunction:
    parts: Tuple["Expr", ...]

    def describe(self) -> str:
        return "(" + " or ".join(p.describe() for p in self.parts) + ")"


@dataclass(frozen=True)
class Negation:
    part: "Expr"

    def describe(self) -> str:
        return f"not {self.part.describe()}"


Expr = Union[Comparison, Unparsed, Conjunction, Disjunction, Negation]


# --------------------------------------------------------------------------- #
# 2. Facts
# --------------------------------------------------------------------------- #
@dataclass
class Fact:
    value: float
    unit: Optional[str] = None
    source: str = ""


# Quantity names the manual actually compares against a number, read off the
# conditional footnotes in the table data. A condition naming none of these
# has no fact to test and is left Unparsed rather than guessed at.
_QUANTITIES: List[Tuple[str, re.Pattern]] = [
    ("major_street_speed", re.compile(r"major[- ]street speed|speed on (the )?major street"
                                      r"|on major street", re.I)),
    ("population", re.compile(r"\bpopulation\b|\bcommunity\b", re.I)),
    ("pixel_spacing", re.compile(r"pixel spacing", re.I)),
    ("letter_height", re.compile(r"letter height|upper[- ]case letters?", re.I)),
    ("sign_size", re.compile(r"sign(s)? measuring|\bmeasuring\b|sign size", re.I)),
    ("volume", re.compile(r"\bvolume\b|vehicles per (hour|day)|\baadt\b", re.I)),
    ("radius", re.compile(r"\bradius\b", re.I)),
    ("spacing", re.compile(r"\bspacing\b", re.I)),
    ("width", re.compile(r"\bwidth\b", re.I)),
    ("distance", re.compile(r"\bdistance\b", re.I)),
    # the bare word comes last, so "major-street speed" is never read as "speed"
    ("speed", re.compile(r"\bspeed(s| limits?)?\b|mph", re.I)),
]

_UNIT_RE = re.compile(r"\b(mph|feet|foot|ft|inches|inch|in|mm|millimeters|"
                      r"meters|metres|m|vph|vpd)\b", re.I)
_UNIT_CANON = {"mph": "mph", "feet": "ft", "foot": "ft", "ft": "ft",
               "inches": "in", "inch": "in", "in": "in", "mm": "mm",
               "millimeters": "mm", "meters": "m", "metres": "m", "m": "m",
               "vph": "vph", "vpd": "vpd"}
# Conversions that are exact. Nothing lossy is done silently.
_CONVERT: Dict[Tuple[str, str], float] = {("ft", "in"): 12.0, ("in", "ft"): 1 / 12.0}


def facts_from_store(store: CertificateStore) -> Dict[str, Fact]:
    """Established facts, from `provenance["facts"]` or `["measurements"]`.

    Only a TRUE certificate contributes. S3.2 is explicit that an UNKNOWN
    establishes nothing, and a FALSE claim is not a measurement of anything.
    """
    out: Dict[str, Fact] = {}
    for cert in store.all():
        if cert.status is not Status.TRUE:
            continue
        prov = cert.provenance or {}
        for key in ("facts", "measurements"):
            raw = prov.get(key) or {}
            if not isinstance(raw, dict):
                continue
            for name, val in raw.items():
                try:
                    if isinstance(val, dict):
                        out[_norm(name)] = Fact(
                            float(val["value"]), val.get("unit"),
                            f"certificate:{cert.obligation_id or cert.verifier}")
                    else:
                        out[_norm(name)] = Fact(
                            float(val), None,
                            f"certificate:{cert.obligation_id or cert.verifier}")
                except (TypeError, ValueError, KeyError):
                    continue
    return out


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


# --------------------------------------------------------------------------- #
# 3. Reading a condition
# --------------------------------------------------------------------------- #
# Ordered: the longest phrasing must be tried first, or "40 mph or less" is
# read as a bare "40 mph" and the "or less" is lost, which inverts the test.
_UNIT_ALT = (r"mph|feet|foot|ft|inches|inch|in|mm|millimeters|meters|metres|m|vph|vpd")

# Ordered: the longest phrasing must be tried first, or "40 mph or less" is
# read as a bare "40 mph" and the "or less" is lost, which inverts the test.
# The unit slot in the suffix forms is restricted to REAL units. Leaving it as
# any word let "less than 10,000 population or above 40 mph on major street"
# match as "10,000 <population> or above", producing `speed >= 10000` — a
# number from one clause bolted onto the subject of another.
_COMPARATORS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(rf"(?:of\s+)?([\d,]+\.?\d*)\s*({_UNIT_ALT})?\s+or\s+"
                rf"(?:less|lower|fewer|below)\b(?!\s*\d)", re.I), "<=", "after"),
    (re.compile(rf"(?:of\s+)?([\d,]+\.?\d*)\s*({_UNIT_ALT})?\s+or\s+"
                rf"(?:more|greater|higher|above)\b(?!\s*\d)", re.I), ">=", "after"),
    (re.compile(r"\b(?:exceeds|exceeding|greater than|more than|above|over)\s+"
                r"([\d,]+\.?\d*)\s*([A-Za-z]+)?", re.I), ">", "before"),
    (re.compile(r"\b(?:less than|fewer than|below|under)\s+"
                r"([\d,]+\.?\d*)\s*([A-Za-z]+)?", re.I), "<", "before"),
    (re.compile(r"\b(?:at least|no less than|not less than|a minimum of|minimum of)\s+"
                r"([\d,]+\.?\d*)\s*([A-Za-z]+)?", re.I), ">=", "before"),
    (re.compile(r"\b(?:at most|no more than|not more than|does not exceed|"
                r"not exceed|a maximum of|maximum of)\s+"
                r"([\d,]+\.?\d*)\s*([A-Za-z]+)?", re.I), "<=", "before"),
    (re.compile(r"\b(?:equals|equal to|is)\s+([\d,]+\.?\d*)\s*([A-Za-z]+)?", re.I),
     "==", "before"),
]

# The compiler may also hand over a rule already written as an expression.
_EXPLICIT_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(-?[\d,]+\.?\d*)\s*"
    r"([A-Za-z]+)?\s*$")

_SPLIT_OR = re.compile(r"\s+or\s+", re.I)
_SPLIT_AND = re.compile(r"\s+and\s+", re.I)
_HAS_NUMBER = re.compile(r"\d")
# "a posted, statutory, or 85th-percentile speed" is a list of adjectives, not
# a choice between conditions. The comma before the "or" is what tells them
# apart, and it is the manual's own punctuation, not a guess.
_LIST_OR = re.compile(r",\s*or\s+", re.I)
# "or less" / "or above" belongs to the comparator; "or above 40 mph" starts a
# new clause. The difference is whether a number follows. The lookahead is on
# a DIGIT only: written as [\d,] it also refused a trailing comma, so
# "30 mph or less, so a Turn sign should be used" was split at the "or" and
# came out as `speed == 30` instead of `speed <= 30`. One sentence can
# hold both: "may be used on low-volume roadways or roadways with speeds of
# 25 mph or less" has a real choice AND a comparator suffix. Masking the
# suffix first is what lets the real one be found.
_OR_SUFFIX = re.compile(
    r"\s+or\s+(less|lower|fewer|below|more|greater|higher|above)\b(?!\s*\d)", re.I)
_MASK = "\x00OR\x00"


def _split_or(text: str) -> Optional[List[str]]:
    """Alternatives, keeping one that cannot be decided rather than dropping it.

    "may be used on low-volume roadways or roadways with speeds of 25 mph or
    less" offers two ways to qualify and only the second is arithmetic. Keeping
    the first as an undecidable clause makes the disjunction UNKNOWN when the
    speed test fails, which is right: the manual would still allow it on a
    low-volume road. Dropping it would have returned a confident FALSE and
    denied a use the manual permits.
    """
    if _LIST_OR.search(text):
        return None
    masked = _OR_SUFFIX.sub(lambda m: f"{_MASK}{m.group(1)}", text)
    parts = [p.strip().replace(_MASK, " or ") for p in _SPLIT_OR.split(masked)
             if p.strip()]
    if len(parts) < 2 or not any(_HAS_NUMBER.search(p) for p in parts):
        return None
    return parts


def _split_and(text: str) -> Optional[List[str]]:
    """Requirements that must all hold — but only where each really is one.

    Unlike `or`, an undecidable branch of an `and` drags the whole condition
    to UNKNOWN, so a noun list read as a conjunction costs a decision every
    time. "For word legend and fine symbol signs measuring less than 48
    inches" is one condition about one measurement. Every part must carry a
    number for this to be a genuine conjunction.
    """
    parts = [p.strip() for p in _SPLIT_AND.split(text) if p.strip()]
    if len(parts) < 2 or not all(_HAS_NUMBER.search(p) for p in parts):
        return None
    return parts


def _canon_unit(word: Optional[str]) -> Optional[str]:
    if not word:
        return None
    return _UNIT_CANON.get(word.strip().lower())


def _subject_for(text: str, span: Tuple[int, int], side: str) -> Optional[str]:
    """Which quantity this comparison is about.

    The manual puts the subject on either side: "the major-street speed
    exceeds 40 mph" puts it before, "Community less than 10,000 population"
    puts it after. Both windows are searched, nearest first, against the
    quantity names that actually occur in the data.
    """
    before, after = text[:span[0]], text[span[1]:]
    windows = [before, after] if side == "before" else [after, before]
    for window in windows:
        best: Optional[Tuple[int, str]] = None
        for name, rx in _QUANTITIES:
            m = None
            for m in rx.finditer(window):
                pass                       # keep the LAST hit: nearest the number
            if m is None:
                continue
            distance = (len(window) - m.end()) if window is before else m.start()
            if best is None or distance < best[0]:
                best = (distance, name)
        if best is not None:
            return best[1]
    return None


def _parse_clause(text: str) -> Expr:
    clause = text.strip().rstrip(".")
    if not clause:
        return Unparsed(text)

    m = _EXPLICIT_RE.match(clause)
    if m:
        return Comparison(_norm(m.group(1)), m.group(2),
                          float(m.group(3).replace(",", "")),
                          _canon_unit(m.group(4)), clause)

    for rx, comparator, side in _COMPARATORS:
        m = rx.search(clause)
        if not m:
            continue
        subject = _subject_for(clause, m.span(), side)
        if subject is None:
            continue
        unit = _canon_unit(m.group(2))
        if m.group(2) and unit is None:
            # "10,000 population" -- the trailing word is the subject, not a
            # unit. A number with no unit is fine; a misread unit is not.
            unit = None
        return Comparison(subject, comparator,
                          float(m.group(1).replace(",", "")), unit, clause)
    return Unparsed(clause)


def parse_rule(text: str) -> Expr:
    """Read a condition into an expression tree.

    Splits on `or` and `and` before looking for comparisons, so a compound
    condition keeps its shape. "or less" and "or more" are NOT split on: they
    belong to the comparator, and splitting there would turn "40 mph or less"
    into a disjunction of "40 mph" and "less".
    """
    text = (text or "").strip()
    if not text:
        return Unparsed("")

    negated = False
    stripped = re.sub(r"^\s*(it is not the case that|not)\s+", "", text, flags=re.I)
    if stripped != text:
        negated, text = True, stripped

    parts = _split_or(text)
    if parts:
        node: Expr = Disjunction(tuple(parse_rule(p) for p in parts))
    else:
        parts = _split_and(text)
        node = (Conjunction(tuple(parse_rule(p) for p in parts))
                if parts else _parse_clause(text))
    return Negation(node) if negated else node


# --------------------------------------------------------------------------- #
# 4. Deciding it
# --------------------------------------------------------------------------- #
_OPS: Dict[str, Callable[[float, float], bool]] = {
    ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
}


def _kleene_and(states: Sequence[Status]) -> Status:
    if any(s is Status.FALSE for s in states):
        return Status.FALSE
    return Status.UNKNOWN if any(s is Status.UNKNOWN for s in states) else Status.TRUE


def _kleene_or(states: Sequence[Status]) -> Status:
    if any(s is Status.TRUE for s in states):
        return Status.TRUE
    return Status.UNKNOWN if any(s is Status.UNKNOWN for s in states) else Status.FALSE


def _resolve(subject: str, facts: Dict[str, Fact]) -> Tuple[Optional[Fact], str]:
    """Find the fact a comparison is about.

    Exact name first. Failing that, a fact whose name ENDS with the subject —
    "major_street_speed" answers a rule about "speed" — but only when exactly
    one does. Two candidates mean the condition does not say which, and a
    coin flip here would be a wrong answer wearing a certificate.
    """
    if subject in facts:
        return facts[subject], "exact name"
    ends = [k for k in facts if k.endswith("_" + subject) or subject.endswith("_" + k)]
    if len(ends) == 1:
        return facts[ends[0]], f"matched {ends[0]!r}"
    if len(ends) > 1:
        return None, f"ambiguous: {sorted(ends)} could all answer {subject!r}"
    return None, f"no established fact for {subject!r}"


def evaluate_rule(expr: Expr, facts: Dict[str, Fact],
                  trace: Optional[List[Dict[str, Any]]] = None) -> Status:
    """Kleene three-valued evaluation. A missing fact is UNKNOWN, never False.

    The same logic the executor uses for merges (S3.2): "a or b" is TRUE as
    soon as one side is, even if the other is unresolved, so a condition can
    be settled without every input being known.
    """
    if isinstance(expr, Conjunction):
        return _kleene_and([evaluate_rule(p, facts, trace) for p in expr.parts])
    if isinstance(expr, Disjunction):
        return _kleene_or([evaluate_rule(p, facts, trace) for p in expr.parts])
    if isinstance(expr, Negation):
        inner = evaluate_rule(expr.part, facts, trace)
        return {Status.TRUE: Status.FALSE, Status.FALSE: Status.TRUE,
                Status.UNKNOWN: Status.UNKNOWN}[inner]
    if isinstance(expr, Unparsed):
        if trace is not None:
            trace.append({"clause": expr.text, "status": "UNKNOWN",
                          "why": "not reducible to a comparison"})
        return Status.UNKNOWN

    fact, how = _resolve(expr.subject, facts)
    if fact is None:
        if trace is not None:
            trace.append({"clause": expr.describe(), "status": "UNKNOWN", "why": how})
        return Status.UNKNOWN

    value = fact.value
    note = how
    if expr.unit and fact.unit and expr.unit != fact.unit:
        factor = _CONVERT.get((fact.unit, expr.unit))
        if factor is None:
            if trace is not None:
                trace.append({"clause": expr.describe(), "status": "UNKNOWN",
                              "why": f"the fact is in {fact.unit} and the rule "
                                     f"is in {expr.unit}; no exact conversion"})
            return Status.UNKNOWN
        value = value * factor
        note += f", converted {fact.value:g} {fact.unit} to {value:g} {expr.unit}"
    elif expr.unit and not fact.unit:
        note += f", the fact states no unit; read as {expr.unit}"

    held = _OPS[expr.comparator](value, expr.bound)
    if trace is not None:
        trace.append({"clause": expr.describe(), "status": "TRUE" if held else "FALSE",
                      "value": value, "source": fact.source, "why": note})
    return Status.TRUE if held else Status.FALSE


# --------------------------------------------------------------------------- #
# 4b. A comparison the claim states itself, its value given in the question
# --------------------------------------------------------------------------- #
# "The panel flow of 1,250 units per hour is 1,000 units per hour or more."
# (made up) The claim names the case's value (1,250) and the provision's bound
# (1,000, from the paragraph the obligation was taken from), and asks only how
# they compare. That is arithmetic, and S3.3 prefers a deterministic operator
# "whenever the obligation admits a more constrained verification mechanism"
# ("a threshold should be checked numerically"). Facts given in the question
# are text, not measurements, so nothing above read them and such checks went
# to the language model -- whose correct answer, citing only the question's
# fact, was then set aside as ungrounded (15 and 16 Oct 2026).
#
# Decided only when it is unambiguous: exactly one comparison phrase; exactly
# one other value in the claim that a fact given in the question also states;
# no fraction; no multiplier; no "not", "no" or "n't" outside the phrase; both
# numbers with units of one kind (lengths and times converted, anything else
# only the same unit). Anything else stays UNKNOWN and goes to the
# interpreting verifier, as before.
# a number, not a piece of a code or an id: "R1-1", "2B.21" and "W9-6" hold none
_NUM = r"(?<![A-Za-z\d.,-])(\d[\d,]*(?:\.\d+)?)(?![\d.]*[A-Za-z]\.\d)(?![A-Za-z\d])"
_THE = r"(?:the\s+)?"
_STATED = [   # (pattern, comparator); a longer phrase is listed before its part
    (r"\bis\s+not\s+(?:less|fewer)\s+than\s+" + _THE + _NUM, ">="),
    (r"\bis\s+not\s+(?:more|greater)\s+than\s+" + _THE + _NUM, "<="),
    (r"\b(?:not\s+less\s+than|no\s+less\s+than|not\s+fewer\s+than|no\s+fewer\s+than|at\s+least|"
     r"a\s+minimum\s+of)\s+"
     + _THE + _NUM, ">="),
    (r"\b(?:not\s+more\s+than|no\s+more\s+than|not\s+greater\s+than|no\s+greater\s+than|"
     r"does\s+not\s+exceed|do\s+not\s+exceed|not\s+exceeding|at\s+most|a\s+maximum\s+of)\s+"
     + _THE + _NUM, "<="),
    (_NUM + r"[\s-]*(?:[a-z]+[\s-]+){0,3}?or\s+(?:more|greater|larger|higher|above|longer|wider)\b", ">="),
    (_NUM + r"[\s-]*(?:[a-z]+[\s-]+){0,3}?or\s+(?:less|fewer|lower|below|shorter|narrower)\b", "<="),
    (r"\b(?:more\s+than|greater\s+than|in\s+excess\s+of|exceeds|exceeding|larger\s+than|"
     r"higher\s+than|longer\s+than|wider\s+than)\s+" + _THE + _NUM, ">"),
    (r"\b(?:less\s+than|fewer\s+than|lower\s+than|shorter\s+than|narrower\s+than)\s+" + _THE + _NUM, "<"),
]
# Units read as such. Lengths and times are converted (to inches, to seconds);
# anything else is compared only with the same unit ("12 lanes" with "3 lanes",
# "1,250 units" with "1,000 units"), never with a different one.
_SCALE = {"ft": 12.0, "feet": 12.0, "foot": 12.0, "in": 1.0, "inch": 1.0, "inches": 1.0,
          "mi": 63360.0, "mile": 63360.0, "miles": 63360.0, "yd": 36.0, "yard": 36.0,
          "yards": 36.0, "mm": 1 / 25.4, "millimeter": 1 / 25.4, "millimeters": 1 / 25.4,
          "meter": 1000 / 25.4, "meters": 1000 / 25.4, "km": 1e6 / 25.4,
          "kilometer": 1e6 / 25.4, "kilometers": 1e6 / 25.4,
          "second": 1.0, "seconds": 1.0, "sec": 1.0, "secs": 1.0, "minute": 60.0,
          "minutes": 60.0, "min": 60.0, "mins": 60.0, "hour": 3600.0, "hours": 3600.0,
          "hr": 3600.0, "hrs": 3600.0}
_TIMES = {"second", "seconds", "sec", "secs", "minute", "minutes", "min", "mins", "hour",
          "hours", "hr", "hrs"}
_UNIT_KIND = {u: ("time" if u in _TIMES else "length") for u in _SCALE}
# a "not", "no" or "n't" anywhere outside the comparison phrase turns it round
# ("no higher than", "is not at least"): such a claim is not read here
_NEGATION = re.compile(r"\b(?:not|no|never|neither|nor|none|without|cannot)\b|n't\b", re.I)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _unit_after(text: str, end: int) -> Optional[str]:
    """The word after a number, lower case ("percent" for %), or None."""
    m = re.match(r"[\s-]*([A-Za-z%]+)", text[end:])
    if not m:
        return None
    w = m.group(1).lower()
    return "percent" if w == "%" else w


def _same_word(a: str, b: str) -> bool:
    return a == b or a.rstrip("s") == b.rstrip("s")


def stated_comparison(claim: str, given: Sequence[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
    """Decide a claim that states its own comparison, when the value it names
    is also stated by a fact given in the question. `given` is (fact id, text).
    None when it is not exactly that."""
    text = str(claim or "")
    if re.search(r"\d\s*/\s*\d|[\u00bc-\u00be\u2150-\u215e]", text):
        return None                                  # a fraction: not read here
    found = []
    for pat, cmp_ in _STATED:
        for m in re.finditer(pat, text, re.I):
            found.append((m.start(), m.end(), m.start(1), m.end(1), cmp_))
    found = [f for f in found if not any(g is not f and g[0] <= f[0] and f[1] <= g[1]
                                         and (g[0], g[1]) != (f[0], f[1]) for g in found)]
    spans = {(f[0], f[1]) for f in found}
    if len(spans) != 1:
        return None
    s, e, bs, be, cmp_ = next(f for f in found)
    if _NEGATION.search(text[:s]) or _NEGATION.search(text[e:]):
        return None                                  # "no higher than": not read here
    if re.match(r"\s*(?:times\b|x\b|\u00d7|percent\s+of\b|%\s+of\b)", text[be:], re.I):
        return None                                  # "3 times the width": a multiplier
    bound = _num(text[bs:be])
    b_unit = _unit_after(text, be)
    # The claim's one other number is the case's value. A second one (an arm
    # length beside a sheeting height, a period beside a count) leaves it open
    # which is compared, so nothing is decided.
    others = [m for m in re.finditer(_NUM, text) if not (s <= m.start() < e)]
    if len({_num(m.group(1)) for m in others}) != 1:
        return None
    m = others[0]
    value = _num(m.group(1))
    v_unit = _unit_after(text, m.end(1))
    confirming = [fid for fid, ft in given
                  if any(abs(_num(x) - value) < 1e-9 for x in re.findall(_NUM, str(ft)))]
    if not confirming:
        return None
    values = [(value, v_unit, confirming)]
    # both numbers carry a unit, and the units are of one kind: converted when
    # they are lengths or times, otherwise only the same unit
    if not v_unit or not b_unit:
        return None
    if v_unit in _SCALE and b_unit in _SCALE:
        if _UNIT_KIND[v_unit] != _UNIT_KIND[b_unit]:
            return None
        value, bound = value * _SCALE[v_unit], bound * _SCALE[b_unit]
    elif not _same_word(v_unit, b_unit):
        return None
    held = {">=": value >= bound, "<=": value <= bound, ">": value > bound,
            "<": value < bound}[cmp_]
    return {"status": Status.TRUE if held else Status.FALSE, "value": values[0][0],
            "value_unit": v_unit, "comparator": cmp_, "bound": _num(text[bs:be]),
            "bound_unit": b_unit, "phrase": text[s:e], "facts": confirming}


# --------------------------------------------------------------------------- #
# 5. The verifier
# --------------------------------------------------------------------------- #
def _condition_text(op: Operation, tables_by_id: Dict[str, List[Table]]
                    ) -> Tuple[str, Optional[str], Optional[Footnote]]:
    """The text to decide: a named footnote if the hint points at one, else
    an explicit rule, else the obligation's own claim."""
    table_id = marker = None
    for h in (op.evidence_hint or []):
        kind = str(h.get("type", "")).lower()
        if kind == "rule" and h.get("id"):
            return str(h["id"]), None, None
        if kind == "table" and h.get("id"):
            table_id = str(h["id"])
        if kind == "footnote" and h.get("id") is not None:
            marker = str(h["id"])
    if table_id and marker:
        for t in tables_by_id.get(table_id, []):
            fn = t.footnote(marker)
            if fn is not None:
                return fn.text, f"{table_id}:{marker}", fn
    return op.claim, None, None


def make_rule_evaluator(tables: Sequence[Table] = ()) -> Callable[
        [Operation, CertificateStore], Certificate]:
    """Build the symbolic rule evaluator.

    Plugs into ``execute(net, verifiers={"symbolic": make_rule_evaluator(...)})``.
    `tables` is optional and is only used to look a footnote up by marker when
    the compiler points at one.
    """
    by_id: Dict[str, List[Table]] = {}
    for t in tables:
        by_id.setdefault(t.table_id, []).append(t)

    def evaluate(op: Operation, store: CertificateStore) -> Certificate:
        text, condition_id, footnote = _condition_text(op, by_id)
        expr = parse_rule(text)
        facts = facts_from_store(store)
        trace: List[Dict[str, Any]] = []
        status = evaluate_rule(expr, facts, trace)

        provenance: Dict[str, Any] = {
            "condition": text,
            "parsed": expr.describe(),
            "clauses": trace,
            "facts_available": {k: {"value": v.value, "unit": v.unit,
                                    "source": v.source}
                                for k, v in sorted(facts.items())},
        }
        if condition_id:
            provenance["condition_id"] = condition_id

        evidence: List[Evidence] = []
        if condition_id:
            evidence.append(Evidence("table", condition_id.split(":", 1)[0]))
        if footnote is not None and footnote.chunk_id:
            evidence.append(Evidence("chunk", footnote.chunk_id))

        if status is Status.UNKNOWN and not condition_id:
            given = [(c.obligation_id, c.claim) for c in store.all()
                     if c.verifier == "given" and c.status is Status.TRUE and c.obligation_id]
            stated = stated_comparison(op.claim, given)
            if stated is not None:
                status = stated["status"]
                provenance["stated_comparison"] = {k: v for k, v in stated.items() if k != "status"}
                evidence.extend(Evidence("given", fid) for fid in stated["facts"])
                if op.source_chunk:
                    # the bound is the provision's: the paragraph the obligation came from
                    evidence.append(Evidence("chunk", op.source_chunk))
        if status is Status.UNKNOWN:
            provenance["reason"] = (
                "the condition could not be decided from established facts; "
                "an interpreting verifier must take it")
        elif condition_id:
            # Only a condition that HOLDS releases the value the calculator is
            # holding. "May be used when the speed exceeds 40 mph" evaluated
            # FALSE is a permission that does not apply, so the held value
            # must stay held, and nothing is discharged.
            if status is Status.TRUE:
                provenance["discharges"] = [condition_id]

        return Certificate(
            claim=op.claim, status=status, evidence=evidence,
            normative_authority=op.normative_authority,
            confidence=1.0 if status is not Status.UNKNOWN else 0.0,
            verifier="symbolic", obligation_id=op.id, provenance=provenance)

    return evaluate
