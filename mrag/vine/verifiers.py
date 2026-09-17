"""Deterministic verifiers — the non-generative half of S3.3.

    "An operation may be assigned to an LLM, VLM, deterministic calculator,
     symbolic rule evaluator, retrieval module, or exact cross-reference
     resolver. ... generative models are used where interpretation is
     necessary, while deterministic or specialized operators are preferred
     whenever the obligation admits a more constrained verification
     mechanism."

The point of a deterministic verifier is that it cannot be wrong in the way a
model is wrong. "Section 4K.03 exists and paragraph 6 of it says X" is a fact
about the knowledge graph, so it is answered by looking, not by asking.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .certificate import Authority, Certificate, CertificateStore, Evidence, Status
from .network import Operation

# "Section 4K.03", "Paragraph 6 in Section 4K.03", "Paragraph 4 of 4C.05"
_SECTION = r"([0-9][A-Z]\.[0-9]{2})"
PARA_THEN_SECTION_RE = re.compile(
    rf"\bParagraphs?\s+(\d{{1,3}})\s+(?:in|of|to)\s+(?:Section\s+)?{_SECTION}\b", re.I)
SECTION_THEN_PARA_RE = re.compile(
    rf"\bSection\s+{_SECTION}\s*,?\s*Paragraphs?\s+(\d{{1,3}})\b", re.I)
SECTION_RE = re.compile(rf"\bSection\s+{_SECTION}\b", re.I)
FIGURE_RE = re.compile(r"\b(Figure|Table)\s+([0-9A-Z]+-[0-9]+[A-Za-z]?)\b", re.I)
# The manual routinely names several at once: Table 9A-1 Note 2 sends a sign
# that serves motorists and bicyclists "to ... Tables 2B-1, 2C-1, 2D-1, or
# 8B-1". A pattern anchored on the singular word reads ONE target out of four
# and silently drops the other three, so an obligation about a bicycle sign
# resolves against the wrong table roughly three times in four.
PLURAL_FIGURE_RE = re.compile(
    r"\b(Figures|Tables)\s+((?:[0-9A-Z]+-[0-9]+[A-Za-z]?)"
    r"(?:\s*(?:,|,?\s*or|,?\s*and)\s*[0-9A-Z]+-[0-9]+[A-Za-z]?)+)", re.I)
_ID_RE = re.compile(r"[0-9A-Z]+-[0-9]+[A-Za-z]?", re.I)


def parse_references(text: str) -> List[Tuple[str, str, Optional[int]]]:
    """Pointers in `text` as (kind, id, paragraph|None), in reading order.

    A paragraph pointer is kept whole: "Paragraph 6 in Section 4K.03" is one
    reference to a paragraph, not a reference to a section that happens to
    mention a number.
    """
    found: List[Tuple[int, Tuple[str, str, Optional[int]]]] = []
    claimed: List[Tuple[int, int]] = []

    for m in PARA_THEN_SECTION_RE.finditer(text):
        found.append((m.start(), ("section", m.group(2), int(m.group(1)))))
        claimed.append((m.start(), m.end()))
    for m in SECTION_THEN_PARA_RE.finditer(text):
        found.append((m.start(), ("section", m.group(1), int(m.group(2)))))
        claimed.append((m.start(), m.end()))
    for m in SECTION_RE.finditer(text):
        if any(a <= m.start() < b for a, b in claimed):
            continue                       # already captured with its paragraph
        found.append((m.start(), ("section", m.group(1), None)))
    for m in PLURAL_FIGURE_RE.finditer(text):
        kind = "Figure" if m.group(1).lower().startswith("figure") else "Table"
        for i, ident in enumerate(_ID_RE.findall(m.group(2))):
            found.append((m.start(2) + i, ("figure", f"{kind} {ident}", None)))
        claimed.append((m.start(), m.end()))
    for m in FIGURE_RE.finditer(text):
        if any(a <= m.start() < b for a, b in claimed):
            continue                       # already captured in a plural list
        found.append((m.start(), ("figure", f"{m.group(1).title()} {m.group(2)}", None)))

    out, seen = [], set()
    for _pos, ref in sorted(found):
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def make_cross_reference_resolver(kg) -> Callable[[Operation, CertificateStore], Certificate]:
    """Resolve the pointers an obligation names, exactly, against the graph.

    Status:
      TRUE     every pointer resolves; the targets are the evidence
      FALSE    a pointer names something the manual does not contain. This is
               a real finding, not a tool failure -- 8B.05, 8C.05, 8E.10 and
               9D.10 are cited in the text and absent from the outline.
      UNKNOWN  no pointer could be read out of the obligation. Nothing was
               checked, so nothing is established (S3.2).
    """

    def resolve(op: Operation, store: CertificateStore) -> Certificate:
        hinted = [(str(h.get("type", "section")).lower(), str(h.get("id", "")),
                   int(h["paragraph"]) if str(h.get("paragraph", "")).isdigit() else None)
                  for h in (op.evidence_hint or []) if h.get("id")]
        refs = hinted or parse_references(op.claim)

        if not refs:
            return Certificate(
                claim=op.claim, status=Status.UNKNOWN,
                normative_authority=op.normative_authority,
                verifier="cross_reference_resolver", obligation_id=op.id,
                provenance={"reason": "no section/figure/table reference found "
                                      "in the obligation"})

        evidence: List[Evidence] = []
        resolved: List[str] = []
        dangling: List[str] = []
        for kind, ident, para in refs:
            label = f"{'Section ' if kind == 'section' else ''}{ident}" + \
                    (f" Paragraph {para}" if para else "")
            if not kg.resolves(kind, ident):
                dangling.append(label)
                continue
            if kind == "section" and para is not None:
                cid = kg.chunk_for_paragraph(ident, para)
                if cid is None:
                    # the section exists but has no such paragraph: still a
                    # dangling pointer, and a more precise one to report
                    dangling.append(label)
                    continue
                evidence.append(Evidence("chunk", cid))
            evidence.append(Evidence(kind if kind == "section" else
                                     ("table" if ident.lower().startswith("table") else "figure"),
                                     ident))
            resolved.append(label)

        status = Status.FALSE if dangling else Status.TRUE
        return Certificate(
            claim=op.claim, status=status, evidence=evidence,
            normative_authority=op.normative_authority,
            confidence=1.0 if status is Status.TRUE else 0.0,
            verifier="cross_reference_resolver", obligation_id=op.id,
            provenance={"resolved": resolved, "dangling": dangling,
                        "source": "evidence_hint" if hinted else "parsed_from_claim"},
        )

    return resolve
