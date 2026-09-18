"""Worked examples for one-shot / few-shot prompting of the answer VLM.

Each example mirrors the structure of a real `ask()` call:
  - question     : the user's question
  - chunks       : list of evidence-chunk dicts (same shape produced by retrieval)
  - figures      : list of figure dicts (may be empty)
  - answer       : the desired model output, formatted per the spec in vlm.py

The chunks and answers below are drawn from real MUTCD 11th-Edition text so
the model learns accurate citation patterns, accurate verbatim quoting, and
correct use of the Standard / Guidance / Option / Support taxonomy. Do NOT
add fake section numbers, fake figure IDs, or paraphrased "standard"
provisions here — examples that lie teach the model to lie.

To add more examples, append to FEWSHOT_EXAMPLES. The first example in the
list is used for one-shot prompting; all examples are used for few-shot.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Examples — keep diverse: cover different MUTCD normative categories,
# different sections, and edge cases like "evidence spans many categories".
# ---------------------------------------------------------------------------

FEWSHOT_EXAMPLES: List[Dict[str, Any]] = [
    # -----------------------------------------------------------------------
    # Example 1 — Multi-category answer (Guidance + Standard + Option + Support).
    # Best single example: shows the model how to handle answers that span all
    # four MUTCD rule types, and how to carry a Standard whose scope is stated
    # as an exception. Used as the one-shot example.
    #
    # The section is deliberately ADMINISTRATIVE. An example drawn from a
    # design provision teaches the shape of an answer and, at the same time,
    # hands the model a substantive rule it may then recite for any question
    # touching that provision. The previous version of this example was drawn
    # from 2B.04 and stated the ALL-WAY plaque requirement in full; measured
    # against the MUTCD-150 gold answers it covered 83% of one and 80% of
    # another, and five benchmark questions cited the sections it quoted.
    # Nothing in 1B.08 is an engineering rule, so the format is all it can
    # teach — which is all an example should teach.
    # -----------------------------------------------------------------------
    {
        "question": (
            "How is a request for an official interpretation or permission to "
            "experiment submitted to FHWA?"
        ),
        "chunks": [
            {
                "section_id": "1B.08",
                "section_title": (
                    "Requesting Official Interpretations, Experiments, Changes "
                    "to the MUTCD, or Interim Approvals"
                ),
                "content_type": "Guidance",
                "ordinal": "01",
                "page_printed": "12",
                "text": (
                    "A local jurisdiction, toll facility operator, or owner of a "
                    "site roadway open to public travel that is requesting "
                    "permission to experiment or permission to use a device or "
                    "application under an existing interim approval should first "
                    "check for any State laws, regulations, and/or directives "
                    "covering the application of the MUTCD provisions that might "
                    "apply."
                ),
            },
            {
                "section_id": "1B.08",
                "section_title": (
                    "Requesting Official Interpretations, Experiments, Changes "
                    "to the MUTCD, or Interim Approvals"
                ),
                "content_type": "Standard",
                "ordinal": "02",
                "page_printed": "12",
                "text": (
                    "Except as provided in Paragraph 3 of this Section, requests "
                    "for an interpretation, permission to experiment, a change to "
                    "the MUTCD, granting of an interim approval, or permission to "
                    "use an existing interim approval shall be submitted "
                    "electronically to the Federal Highway Administration (FHWA), "
                    "Office of Transportation Operations, MUTCD team, at the "
                    "following e-mail address: MUTCDofficialrequest@dot.gov."
                ),
            },
            {
                "section_id": "1B.08",
                "section_title": (
                    "Requesting Official Interpretations, Experiments, Changes "
                    "to the MUTCD, or Interim Approvals"
                ),
                "content_type": "Option",
                "ordinal": "03",
                "page_printed": "12",
                "text": (
                    "If electronic submittal is not possible, requests for an "
                    "interpretation, permission to experiment, a change to the "
                    "MUTCD, granting of an interim approval, or permission to use "
                    "an existing interim approval may instead be mailed to the "
                    "Office of Transportation Operations, HOTO-1, Federal Highway "
                    "Administration, 1200 New Jersey Avenue, SE, Washington, DC "
                    "20590."
                ),
            },
            {
                "section_id": "1B.08",
                "section_title": (
                    "Requesting Official Interpretations, Experiments, Changes "
                    "to the MUTCD, or Interim Approvals"
                ),
                "content_type": "Support",
                "ordinal": "05",
                "page_printed": "12",
                "text": (
                    "For additional information concerning interpretations, "
                    "experimentation, changes, or interim approvals, visit the "
                    "MUTCD Web site at http://mutcd.fhwa.dot.gov."
                ),
            },
        ],
        "figures": [],
        "answer": (
            "Direct Answer: Requests shall be submitted electronically to the "
            "FHWA Office of Transportation Operations, MUTCD team, except as "
            "provided in Paragraph 3 of Section 1B.08. Where electronic "
            "submittal is not possible, the request may be mailed instead. A "
            "requester should first check for any applicable State laws, "
            "regulations, or directives.\n"
            "\n"
            "Standards (mandatory):\n"
            "- Except as provided in Paragraph 3 of Section 1B.08, requests for "
            "an interpretation, permission to experiment, a change to the MUTCD, "
            "granting of an interim approval, or permission to use an existing "
            "interim approval shall be submitted electronically to the Federal "
            "Highway Administration, Office of Transportation Operations, MUTCD "
            "team.\n"
            "\n"
            "Guidance (recommended):\n"
            "- A local jurisdiction, toll facility operator, or owner of a site "
            "roadway open to public travel that is requesting permission to "
            "experiment, or permission to use a device under an existing interim "
            "approval, should first check for any State laws, regulations, or "
            "directives that might apply.\n"
            "\n"
            "Options (permitted):\n"
            "- If electronic submittal is not possible, the request may instead "
            "be mailed to the Office of Transportation Operations, HOTO-1, "
            "Federal Highway Administration, Washington, DC.\n"
            "\n"
            "Support (explanatory, not enforceable):\n"
            "- Further information on interpretations, experimentation, changes "
            "and interim approvals is available on the MUTCD Web site.\n"
            "\n"
            "Citations:\n"
            "- Section 1B.08 Guidance §01 (p.12)\n"
            "- Section 1B.08 Standard §02 (p.12)\n"
            "- Section 1B.08 Option §03 (p.12)\n"
            "- Section 1B.08 Support §05 (p.12)"
        ),
    },

    # -----------------------------------------------------------------------
    # Example 2 — Pure Standard answer with explicit exceptions list.
    # Shows the model how to quote mandatory provisions verbatim and how
    # to handle "shall not... except in the following cases" patterns.
    # -----------------------------------------------------------------------
    {
        "question": "Can STOP signs or YIELD signs be used with traffic signals?",
        "chunks": [
            {
                "section_id": "2B.06",
                "section_title": "General Considerations",
                "content_type": "Standard",
                "ordinal": "08",
                "page_printed": "75",
                "text": (
                    "Because the potential for conflicting commands could create driver "
                    "confusion, YIELD or STOP signs shall not be used in conjunction with "
                    "any traffic control signal operation, except in the following cases:\n"
                    "A. If the signal indication for an approach is a flashing red at all times;\n"
                    "B. If a minor street or driveway is located within or adjacent to the area "
                    "controlled by the traffic control signal, but does not require separate "
                    "traffic signal control because an extremely low potential for conflict exists; or\n"
                    "C. If a channelized turn lane is separated from the adjacent travel lanes "
                    "by an island and the channelized turn lane is not controlled by a traffic "
                    "control signal."
                ),
            },
        ],
        "figures": [],
        "answer": (
            "Direct Answer: As a general rule, STOP and YIELD signs may not be used with a "
            "traffic control signal because conflicting commands could confuse drivers. The "
            "MUTCD permits only three specific exceptions.\n"
            "\n"
            "Standards (mandatory):\n"
            "- YIELD or STOP signs shall not be used in conjunction with any traffic control "
            "signal operation, except in the following cases: (A) if the signal indication for "
            "an approach is a flashing red at all times; (B) if a minor street or driveway is "
            "located within or adjacent to the signal-controlled area but does not require "
            "separate signal control because an extremely low potential for conflict exists; or "
            "(C) if a channelized turn lane is separated from adjacent travel lanes by an island "
            "and is not itself signal-controlled.\n"
            "\n"
            "Citations:\n"
            "- Section 2B.06 Standard §08 (p.75)"
        ),
    },

    # -----------------------------------------------------------------------
    # Example 3 — Standard + Guidance, no Option. Shows the model what to do
    # when only some categories are present (omit empty sections).
    # -----------------------------------------------------------------------
    {
        "question": "How are non-statutory speed limits established?",
        "chunks": [
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Standard",
                "ordinal": "06",
                "page_printed": "84",
                "text": (
                    "Speed zones (other than statutory speed limits) shall only be established "
                    "on the basis of an engineering study that has been performed in accordance "
                    "with traffic engineering practices. The engineering study shall consider "
                    "the roadway context."
                ),
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "A. Roadway environment (such as roadside development, number and "
                    "frequency of driveways and access points, and land use), functional "
                    "classification, public transit volume and location or frequency of "
                    "stops, parking practices, and pedestrian and bicycle facilities and "
                    "activity;"
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "A",
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "B. Roadway characteristics (such as lane widths, shoulder condition, "
                    "grade, alignment, median type, and sight distance);"
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "B",
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "C. Geographic context (such as an urban district, rural town center, "
                    "non-urbanized rural area, or suburban area), and multi-modal trip "
                    "generation;"
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "C",
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "D. Reported crash experience for at least a 12-month period;"
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "D",
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "E. Speed distribution of free-flowing vehicles including the pace, "
                    "median (50th-percentile), and 85th-percentile speeds; and"
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "E",
            },
            {
                "section_id": "2B.21",
                "section_title": "Speed Limit Sign (R2-1)",
                "content_type": "Guidance",
                "ordinal": "07",
                "page_printed": "84",
                "text": (
                    "F. A review of past speed studies to identify any trends in "
                    "operating speeds."
                ),
                "lead_in": (
                    "Among the factors that should be considered when conducting "
                    "an engineering study for establishing or reevaluating speed "
                    "limits within speed zones are the following:"
                ),
                "source": "list_item",
                "item": "F",
            },
        ],
        "figures": [],
        "answer": (
            "Direct Answer: Non-statutory speed limits must be set on the basis of an engineering "
            "study performed in accordance with traffic engineering practices. The study is "
            "required to consider roadway context, and should weigh a wide range of factors "
            "including roadway characteristics, crash history, and observed speed distribution.\n"
            "\n"
            "Standards (mandatory):\n"
            "- Speed zones (other than statutory speed limits) shall only be established on the "
            "basis of an engineering study performed in accordance with traffic engineering "
            "practices, and the study shall consider the roadway context.\n"
            "\n"
            "Guidance (recommended):\n"
            "- Among the factors that should be considered when conducting the "
            "engineering study are: roadway environment and functional "
            "classification (item A); roadway characteristics such as lane widths, "
            "shoulder condition, grade, alignment, median type and sight distance "
            "(item B); geographic context and multi-modal trip generation (item C); "
            "reported crash experience for at least a 12-month period (item D); the "
            "speed distribution of free-flowing vehicles, including the pace, median "
            "and 85th-percentile speeds (item E); and a review of past speed studies "
            "to identify trends in operating speeds (item F).\n"
            "\n"
            "Citations:\n"
            "- Section 2B.21 Standard §06 (p.84)\n"
            "- Section 2B.21 Guidance \u00a707 items A-F (p.84)"
        ),
    },
]


def _render_example_evidence_block(ex: Dict[str, Any], max_chars: int = 1400) -> str:
    """Render an example's chunks in the same `=== {category} provisions ===`
    format that vlm.py's _build_prompt_and_images uses for real evidence.

    Mirroring the real format exactly is what makes few-shot examples useful:
    the model sees the example evidence laid out identically to the real
    evidence it will receive at inference time.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {
        "Standard": [], "Guidance": [], "Option": [], "Support": [],
    }
    for c in ex["chunks"]:
        ct = c.get("content_type", "Support")
        groups.setdefault(ct, []).append(c)

    blocks: List[str] = []
    for ct in ("Standard", "Guidance", "Option", "Support"):
        cs = groups.get(ct, [])
        if not cs:
            continue
        blocks.append(f"=== {ct} provisions ===")
        for c in cs:
            blocks.append(
                f"[Section {c.get('section_id')} §{c.get('ordinal')} — "
                f"{c.get('section_title','')} (p.{c.get('page_printed','?')})]\n"
                f"{(c.get('text','') or '')[:max_chars]}"
            )
        blocks.append("")
    return "\n".join(blocks)


def _render_example_allowed_cites(ex: Dict[str, Any]) -> str:
    """Same citation-list format the real prompt uses."""
    lines: List[str] = []
    for c in ex["chunks"]:
        lines.append(
            f"  - Section {c.get('section_id')} {c.get('content_type')} "
            f"§{c.get('ordinal')} (p.{c.get('page_printed','?')})"
        )
    for f in ex.get("figures") or []:
        lines.append(
            f"  - {f.get('figure_id','?')} (p.{f.get('page_printed','?')})"
        )
    return "\n".join(lines) if lines else "  (none)"


def _render_example_visual_lines(ex: Dict[str, Any]) -> str:
    figs = ex.get("figures") or []
    if not figs:
        return "(none)"
    lines: List[str] = []
    for i, f in enumerate(figs, 1):
        lines.append(
            f"[Image {i}] {f.get('figure_id','?')} (p.{f.get('page_printed','?')}): "
            f"{(f.get('caption','') or '')[:160]}"
        )
    return "\n".join(lines)


def format_example(ex: Dict[str, Any], n: int, max_chars: int = 1400) -> str:
    """Render one example as a fully-delimited block ready to splice into a prompt.

    Layout:
        --- Example {n} ---
        Question: ...
        Visual evidence (N images):
        ...
        Text evidence:
        === Standard provisions ===
        [Section 2B.04 §04 — ... (p.74)]
        ...
        Allowed citations (use ONLY these strings verbatim):
          - ...
        Answer:
        Direct Answer: ...
        ...
        --- End example {n} ---
    """
    visual = _render_example_visual_lines(ex)
    evidence = _render_example_evidence_block(ex, max_chars=max_chars)
    cites = _render_example_allowed_cites(ex)
    n_figs = len(ex.get("figures") or [])
    return (
        f"--- Example {n} ---\n"
        f"Question: {ex['question']}\n\n"
        f"Visual evidence ({n_figs} images):\n{visual}\n\n"
        f"Text evidence:\n{evidence}\n"
        f"Allowed citations (use ONLY these strings verbatim):\n{cites}\n\n"
        f"Answer:\n{ex['answer']}\n"
        f"--- End example {n} ---\n"
    )
