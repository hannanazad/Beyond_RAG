"""Reviewing a compiled network against the manual's own words.

WHY THIS EXISTS
---------------
`NetworkSpec.problems()` and `Network.validate()` check that a network is
WELL FORMED: no dangling references, no cycles, no merge with one input, a
reachable terminal. A network can pass all of that and still say something the
manual does not.

Measured over eight runs of one question, two models:

  * a provision that says "may be COMBINED WITH the Cross Road sign" was put
    into an exception merge four times, as though combining the signs excused
    posting the Curve sign;
  * "devices may be omitted" was made an alternative SIGN rather than a reason
    to post none, so the network could not distinguish "no sign" from "a
    different sign";
  * the base of the omission merge was Chart A in one run out of four and
    Chart B in the rest.

None of those is catchable structurally. All of them are catchable from the
source text, because the manual marks its own exceptions:

    "instead of", "may be omitted", "except as provided"   -> relaxes
    "may be combined with", "in addition to", "supplement"  -> modifies
    "except as provided in Paragraphs 3, 5 and 6"           -> names WHICH
                                                               paragraphs
                                                               relax THIS one

WARNINGS, NOT REJECTIONS
------------------------
These are returned for a human to read, not used to reject a spec. Two
reasons. The wording rules are good but not perfect -- "may instead be mailed"
relaxes and does not contain "instead of". And paragraph numbering is not
fully trustworthy: 2C.06 paragraph 1 excepts to "Paragraphs 3, 5, and 6", but
in this corpus paragraph 6 is a Support note about pavement markings and the
20 mph omission sits at paragraph 4. Rejecting on a rule that rests on that
numbering would block correct networks.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from .compile import NetworkSpec
from .network import MergeType

__all__ = ["review_spec", "classify_provision", "RELAXES", "MODIFIES"]


RELAXES = re.compile(
    r"\b(instead of|in lieu of|may instead|may be omitted|shall not apply|"
    r"do(?:es)? not apply|is not required|are not required|need not|"
    r"except as provided|except where|rather than)\b", re.I)

MODIFIES = re.compile(
    r"\b(may be combined with|combined with|in addition to|may be used to "
    r"supplement|to supplement|together with|in conjunction with|"
    r"may be supplemented)\b", re.I)

# "except as provided in Paragraphs 3, 5, and 6 of this Section" -- the manual
# naming which of its own paragraphs relax this one.
_EXCEPTS_TO = re.compile(
    r"except as provided in paragraphs?\s+([\d,\s]+?(?:and\s+\d+)?)\s+of this section",
    re.I)


def classify_provision(text: str) -> str:
    """relaxes | modifies | neither, from the manual's own wording."""
    if MODIFIES.search(text or ""):
        return "modifies"
    if RELAXES.search(text or ""):
        return "relaxes"
    return "neither"


def _excepted_paragraphs(text: str) -> List[int]:
    m = _EXCEPTS_TO.search(text or "")
    return [int(n) for n in re.findall(r"\d+", m.group(1))] if m else []


def review_spec(spec: NetworkSpec,
                chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Read the compiled spec back against the provisions it came from.

    Every obligation carries `source_chunk`, a pointer into Kq, so the text
    the model was working from is recoverable. That is what makes this
    deterministic: the check is the manual, not another model.
    """
    by_id = {str(c.get("chunk_id")): c for c in chunks if c.get("chunk_id")}
    src = {o.id: by_id.get(o.source_chunk) for o in spec.obligations}
    claim = {o.id: o.claim for o in spec.obligations}
    for m in spec.merges:
        claim[m.id] = m.claim

    out: List[Dict[str, str]] = []

    def warn(kind: str, where: str, detail: str) -> None:
        out.append({"kind": kind, "where": where, "detail": detail})

    # which paragraph does the manual say each provision relaxes?
    relaxes_para: Dict[str, List[tuple]] = {}
    for chunk in chunks:
        for n in _excepted_paragraphs(chunk.get("text") or ""):
            relaxes_para.setdefault(
                f"{chunk.get('section_id')}:{n}", []).append(
                    (str(chunk.get("section_id")), int(chunk.get("ordinal", 0))))

    for merge in spec.merges:
        if merge.kind != MergeType.EXCEPTION.value or len(merge.inputs) < 2:
            continue
        base, *relaxers = merge.inputs
        base_chunk = src.get(base)

        for rid in relaxers:
            chunk = src.get(rid)
            if chunk is None:
                warn("unverifiable", f"{merge.id} <- {rid}",
                     "no source chunk, so the manual's wording cannot be checked")
                continue
            kind = classify_provision(chunk.get("text") or "")
            if kind == "modifies":
                warn("modifier-as-exception", f"{merge.id} <- {rid}",
                     f"the source says this may be COMBINED WITH or ADDED TO "
                     f"the base, not used instead of it: "
                     f"\"{(chunk.get('text') or '')[:90]}\"")
            elif kind == "neither":
                warn("no-relaxing-language", f"{merge.id} <- {rid}",
                     f"the source carries no word the manual uses to relax a "
                     f"rule: \"{(chunk.get('text') or '')[:90]}\"")

            # does the manual say WHICH provision this one excepts from?
            key = f"{chunk.get('section_id')}:{int(chunk.get('ordinal', 0))}"
            named = relaxes_para.get(key)
            if named and base_chunk is not None:
                pair = (str(base_chunk.get("section_id")),
                        int(base_chunk.get("ordinal", 0)))
                if pair not in named:
                    warn("wrong-base", f"{merge.id} <- {rid}",
                         f"the manual names this an exception to "
                         f"{', '.join(f'{s} para {o}' for s, o in named)}, but "
                         f"the merge relaxes {pair[0]} para {pair[1]} "
                         f"({claim.get(base, '')[:60]})")

    return out
