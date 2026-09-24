"""Splitting a normative provision into its condition and its consequence.

A provision in this manual routinely states both in one sentence:

    "A Turn (W1-1) sign should be used instead of a Curve (W1-2) sign in
     advance of a horizontal curve that has an advisory speed of 30 mph or
     less."

That is two checks. The advisory speed is arithmetic; the sign choice follows
from it. Left joined, the pair has to go to a language model, which then
decides the arithmetic too -- and every routing failure seen so far came from
obligations fused this way.

The manual is regular about how it writes them:

  * the CONDITION is introduced by if / where / when / unless / because /
    that has / with an, and may come first or second;
  * the CONSEQUENCE is the clause carrying the modal -- shall, should, may,
    must -- which is also what Section 1C.01 uses to assign normative
    authority.

So the split is mechanical. This module does it and reports how confident it
is, so the cases it cannot read can be handed to a model rather than guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

__all__ = ["Split", "split_provision", "needs_split", "MODAL"]

MODAL = re.compile(r"\b(shall|should|may|must)\b", re.I)

# A list marker before the condition. The manual numbers and letters its
# items, and the enumerator is part of the chunk text: "11. If a STAY IN LANE
# sign is used, then solid white lane lines should be used." A rule anchored
# on the start of the string never sees the "If".
_ENUMERATOR = re.compile(r"^\s*(?:\*+|[A-Z]\.|\d+\.|[a-z]\)|\([a-z0-9]+\)|"
                         r"Notes?\s*\d*\.?)\s+", re.I)

# The condition opens the sentence: "If X, then Y shall ..."
_LEAD = re.compile(r"^\s*(if|where|when|whenever|unless|except where|"
                   r"except as otherwise provided|in situations where|"
                   r"at locations where|on roadways (?:where|having)|"
                   r"for purposes of|on approaches)\b", re.I)

# A prepositional phrase that carries the condition and is closed by a comma:
# "For a major street where the 85th-percentile speed exceeds 35 mph, the need
# for a pedestrian hybrid beacon should be considered." The phrase only counts
# as a condition when it contains a qualifier -- where, that, with, having,
# involving -- otherwise "At intersections, signs shall be placed" would make
# a location into a test.
_PREPOSITIONAL = re.compile(
    r"^\s*(for|at|in|on|under|during|along|near|within|throughout)\s", re.I)
_QUALIFIER = re.compile(r"\b(where|that|which|with|having|involving|when)\b", re.I)

# The condition set off by commas inside the sentence: "Temporary traffic
# barriers, IF USED, shall comply with ...". The consequence is what remains
# once the aside is lifted out.
_PARENTHETICAL = re.compile(
    r",\s*((?:if|when|where|unless)\s+[^,]{2,60}?),\s*", re.I)

# The condition follows the consequence: "Y shall ... where X"
# NOTE: "with a" / "with an" are NOT markers. "Temporary lane separators
# shall consist of a longitudinal base component with a maximum height of 4
# inches" states a dimension, not a test, and treating it as a condition made
# the specification the condition and the subject the rule.
_MID = re.compile(
    r"\s+(?:(where|when|whenever|if|unless|because|provided that|"
    r"that has|that have|that are|having|on urban|"
    r"in advance of a|at locations where|under conditions where))\s", re.I)

# Fragments that look like a condition but introduce an example, not a test.
_NOT_A_CONDITION = re.compile(r"^\s*(such as|for example|including|e\.g\.)", re.I)

# A relative clause describes a noun; it only states a TEST when it carries
# something measurable. "a horizontal curve that has an advisory speed of 30
# mph or less" is a condition; "warning devices that are effective under
# varying conditions" is a description of the devices. Without this, six of
# twenty sampled splits made a description the condition and the rule the
# consequence of it.
_RELATIVE = re.compile(r"^\s*(that has|that have|that are|that is|having)\b", re.I)
_MEASURABLE = re.compile(
    r"\d|\b(more than|less than|greater|fewer|exceeds?|at least|no less|"
    r"minimum|maximum|or less|or more|or higher|or lower)\b", re.I)


@dataclass
class Split:
    condition: str
    consequence: str
    how: str                 # lead | trailing
    confidence: float        # 1.0 clean, lower where the cut was ambiguous

    def as_tuple(self):
        return self.condition, self.consequence


def _balanced(text: str) -> bool:
    """Brackets open and close within the clause.

    A clause that starts mid-parenthesis was cut in the wrong place: the
    trailing marker matched "if used)" inside "(the sponsor name, if used),
    telephone numbers ...", making a fragment the condition.
    """
    depth = 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def needs_split(text: str) -> bool:
    """A provision needs splitting when it states BOTH a test and a rule.

    No modal means it is not a normative provision at all. No conditional
    marker means the rule is unconditional, and splitting it would invent a
    condition that is not there.
    """
    t = _ENUMERATOR.sub("", (text or "").strip(), count=1)
    return bool(MODAL.search(t)
                and (_LEAD.match(t) or _MID.search(t) or _PARENTHETICAL.search(t)))


_SENTENCE = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")

# A sign code, route marker or figure id: W11-6, R10-11b, 2C-16.
_ITEM_CODE = re.compile(r"^(?:and\s+|or\s+)?[A-Z]?\d*[A-Z]\d*-\d+[a-z]?\b")


def _cut_points(text: str):
    """Commas that could end a clause.

    A comma inside brackets, or inside a list of item codes, is not a clause
    boundary. Cutting at one produced "a No Turn on Red (R10-11a" as the
    condition and "or R10-11b) sign shall be installed" as the rule -- three
    of twenty sampled splits failed this way, and all three were the same
    mistake.
    """
    depth = 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            m = re.match(r",\s+", text[i:])
            if not m:
                continue
            after = text[i + m.end():]
            if _ITEM_CODE.match(after):
                continue                    # inside "W11-2, W11-6, and W11-9"
            yield i, i + m.end()


def split_provision(text: str) -> Optional[Split]:
    """Separate the condition from the consequence, or return None.

    None means the sentence does not carry both, or is written in a way these
    rules cannot read. It is not a failure to be papered over: the caller
    should hand those to a model rather than guess.
    """
    # A chunk can hold several sentences, and a provision's condition never
    # spans a full stop. Splitting the chunk as one string cut 2E.43 on the
    # SECOND sentence's "If" and dragged that whole sentence into the
    # condition. Each sentence is read on its own and the first that carries
    # both a test and a rule is the one returned.
    whole = (text or "").strip()
    sentences = [x for x in _SENTENCE.split(whole) if x.strip()]
    if len(sentences) > 1:
        for sentence in sentences:
            got = split_provision(sentence)
            if got is not None:
                return got
        return None

    t = whole
    # strip any list marker so the condition, if it leads, is visible
    stripped = _ENUMERATOR.sub("", t, count=1)
    while _ENUMERATOR.match(stripped):
        stripped = _ENUMERATOR.sub("", stripped, count=1)
    t = stripped.strip()
    if not MODAL.search(t):
        return None

    # a condition set off by commas, lifted out of the middle
    m = _PARENTHETICAL.search(t)
    if m and MODAL.search(t[m.end():]):
        condition = m.group(1).strip()
        consequence = (t[:m.start()] + " " + t[m.end():]).strip()
        if condition and consequence and not MODAL.search(condition):
            return Split(condition, consequence, "parenthetical", 1.0)

    if _LEAD.match(t):
        return _split_leading(t)
    if _PREPOSITIONAL.match(t):
        got = _split_leading(t)
        if got is not None and _QUALIFIER.search(got.condition):
            return got
    m = _MID.search(t)
    if m:
        condition = t[m.start():].strip()
        consequence = t[:m.start()].strip()
        if _NOT_A_CONDITION.match(condition) or not consequence:
            return None
        if _RELATIVE.match(condition) and not _MEASURABLE.search(condition):
            return None
        if not _balanced(condition) or not _balanced(consequence):
            return None
        # the consequence must be the half that carries the modal; if the
        # modal ended up in the condition the cut was in the wrong place
        confidence = 1.0 if MODAL.search(consequence) else 0.4
        if not MODAL.search(consequence):
            return None
        return Split(condition, consequence, "trailing", confidence)
    return None


def _split_leading(t: str) -> Optional[Split]:
    """"If <condition>, <consequence>" -- cut at the right comma.

    The first comma is often inside a list: "If Table 2C-4 indicates that a
    sign is required, recommended, or allowed, the sign shall be ...". Cutting
    there leaves "recommended, or allowed, the sign shall be ..." as the
    consequence. The consequence is the clause carrying the modal, so the cut
    is the LAST comma before the first modal.
    """
    # The first modal can sit INSIDE the condition -- "If highway traffic
    # signals MUST be located within close proximity, the signals MAY be
    # mounted on the same structure." Cutting before the first modal leaves no
    # comma to cut at. Each modal is tried in turn, and the first one that
    # leaves a comma behind it is the boundary.
    points = list(_cut_points(t))
    cut = None
    for modal in MODAL.finditer(t):
        candidate = None
        for start, end in points:
            if end <= modal.start():
                candidate = (start, end)
        if candidate is not None:
            cut = candidate
            break
    if cut is None:
        return None
    condition = t[:cut[0]].strip()
    consequence = t[cut[1]:].strip()
    if not condition or not consequence:
        return None
    if not _balanced(condition) or not _balanced(consequence):
        return None
    if MODAL.search(condition):
        # both halves carry a modal: two rules in one sentence, not a
        # condition and its consequence
        return Split(condition, consequence, "lead", 0.5)
    return Split(condition, consequence, "lead", 1.0)
