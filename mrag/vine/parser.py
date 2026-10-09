"""The semantic parser — the first half of Compile, S3.1.

WHERE THIS SITS
---------------
S3.1: "an LLM-based semantic parser extracts atomic verification obligations
and their logical relations into a constrained intermediate representation,
which is then deterministically compiled into a query-specific, Petri-net-
inspired verification network".

    question + Kq --(THIS FILE: a model)--> NetworkSpec --(compile.py)--> Nq

The model reads the question and the provisions retrieval returned, and writes
the plan. It does not answer the question. Every check in the plan is decided
later, by a verifier, from the manual.

WHERE THE PROMPT COMES FROM (rewritten 7 October 2026)
-----------------------------------------------------
Only from two sources, so that nothing in it is shaped by a test question:

  * the paper's own description of compilation (S3.1): the four steps, the
    seven obligation types, the four structural rules, and its worked example
    ("if a provision applies only to a particular class, requires two
    independent conditions to be satisfied, and contains a separate
    exception ...");
  * the manual's own definitions of Standard, Guidance, Option and Support
    (Section 1C.01), and the interface of the verifiers and the executor in
    this repository (which hint types the calculator reads, how each merge
    is applied).

The earlier prompt had a block listing four "usual" dependency shapes,
including "the controlling value is max(A, B)". It was removed: a shape
listed because questions have it is a shape learned from questions.

WHAT IS CHECKED BEFORE A PLAN IS ACCEPTED
-----------------------------------------
S3.1: "Networks containing unresolved references, missing producers for
mandatory states, invalid dependencies, or unreachable terminal states are
rejected or returned to the compiler for repair."

`instantiate()` and `Network.validate()` check the structure. This file adds
the references a plan makes to the MANUAL, all decided mechanically:

  * every obligation names the provision it comes from (`source_chunk`), and
    that provision was shown;
  * that provision is a Standard, Guidance or Option -- never Support, a table
    row or a figure description;
  * the obligation's authority is that provision's printed heading;
  * every table, figure and section named in a hint exists in the manual, and
    a column, chart or sheet named for a table is one the table has;
  * no `threshold` merge: the executor has no comparator for one, so it could
    only ever come out UNKNOWN;
  * the first input of an exception merge is not an applicability check;
  * every listed fact is the question's own: its numbers are in the
    question, and it cites the manual or says what is required or allowed
    only if the question does (`fact_problems`).

THE FACTS (added 8 October 2026, fix5)
--------------------------------------
The checkers never see the question (S3.3; Eq 5 uses q only for retrieval).
Until fix5 the parser had to copy every fact a claim needed into the claim,
and on the DEV cases it sometimes did not ("the facility described ...",
"in the described signal face ..."), leaving the checker unable to decide or
deciding the rule instead of the case. Now the parser also lists the facts
the question states, once, and `instantiate` puts them in Eq 2's initial
certificate store Γ0q, where every checker sees them as established.

A plan that fails any of these goes back to the model with the problems,
phrased in the ids the model wrote. A model naming its own verifier is
overruled: the rule in `compile.assign_verifier` decides.

WHY THERE IS A FALLBACK
-----------------------
If every attempt fails, `compile_section` produces a spec from the printed
structure alone, so a model failure does not stop the pipeline. When the
PARSER is being measured, the fallback must be off (`fall_back_to_baseline=
False`), or the printed structure's results would be reported as the
parser's. The report always says which was used.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .compile import (CompileError, NetworkSpec, compile_section, instantiate,
                      repair_request)
from .network import MergeType, ObligationType

log = logging.getLogger("mrag.vine.parser")

__all__ = ["ParseReport", "make_semantic_parser", "build_parser_prompt",
           "read_spec", "grounding_problems", "fact_problems", "PARSER_TASK",
           "PARSER_CONTRACT", "HINT_TYPES"]

NORMATIVE = ("Standard", "Guidance", "Option")
HINT_TYPES = ("table", "column", "part", "sheet", "figure", "section")
_NOT_A_PROVISION = {"Support": "Support text (information only)",
                    "TableRow": "a TABLE ROW (printed table content)",
                    "FigureReading": "a FIGURE DESCRIPTION (not the manual's words)"}


# --------------------------------------------------------------------------- #
# 1. The instructions
# --------------------------------------------------------------------------- #
PARSER_TASK = """You are the semantic parser of VINE, a system that checks questions about the
Manual on Uniform Traffic Control Devices (MUTCD, 11th Edition).

Read the provisions and the question below. Then write a verification plan as
one JSON object.

You do not answer the question. The plan says what has to be checked, in what
order, under what conditions, and how the results combine. Separate checkers
then decide each item from the manual:
  calculator       reads a value from a printed table and compares it
  rule evaluator   decides a plain comparison of numbers
  resolver         follows a reference to a section, figure or table
  vision model     looks at a figure
  language model   reads provision text and decides a claim"""

_TYPES = " | ".join(t.value for t in ObligationType)

PARSER_CONTRACT = f"""HOW TO WRITE THE PLAN

Step 1. The terminal proposition. Work out from the question what decision is
asked for: whether a design, action or condition satisfies the provisions that
apply, or what the provisions require, recommend or allow in the situation
described. If the question asks for several things, each is its own requirement,
and a merge combines them. The terminal is what the question asks for and
nothing more: a provision about some other matter gets no obligation.

Step 2. Atomic obligations. Break the provisions that bear on the question
into obligations. One obligation is one thing that can be checked on its own.
A provision that states two conditions gives two obligations. Many of the
provisions shown will not matter for this question: they were retrieved by
search and by following the manual's references. Leave those out.

Step 3. Structure.
  - A mandatory prerequisite is a dependency: list it in "requires".
  - Independent requirements are parallel branches: no "requires" between
    them. Do not invent an order.
  - A provision that applies only under a condition is a guarded branch: give
    it a "guard".
  - A rule that needs several results together is a merge.
For example, if a provision applies only to a particular class, requires two
independent conditions to be satisfied, and contains a separate exception:
the classification is an upstream obligation that the others require; the two
conditions are parallel branches; the exception is a branch of its own; and
their results are merged before the terminal.

Step 4. Evidence. Say where each obligation's evidence is, in
"evidence_hint". Do not choose a checker: the obligation's type and hints
decide which checker runs.

THE JSON OBJECT

{{
  "terminal": "<id of the merge or obligation whose result answers the question>",
  "facts": [
    {{"id": "f1", "fact": "<one fact the question states about the case, in its words>"}}
  ],
  "obligations": [
    {{"id": "o1",
      "claim": "<one checkable statement>",
      "type": "<{_TYPES}>",
      "authority": "<STANDARD | GUIDANCE | OPTION>",
      "requires": ["<ids that must be settled before this one>"],
      "guard": null,
      "evidence_hint": [{{"type": "<table | column | part | sheet | figure | section>", "id": "<id>"}}],
      "source_chunk": "<id of the provision it comes from>"}}
  ],
  "merges": [
    {{"id": "m1",
      "claim": "<what the merge establishes>",
      "kind": "<conjunction | alternative | exception>",
      "inputs": ["<ids being combined>"],
      "authority": "<STANDARD | GUIDANCE | OPTION>",
      "guard": null}}
  ]
}}

THE FIELDS

facts
  The facts the question states about the case: what is there or planned,
  and its sizes, places, counts and conditions. One fact per item, copied
  from the question's statements in their own words, with every value and
  unit exactly as written there. Only what the question states, never what
  it asks. Nothing else: no conclusion, no requirement, no reference to the
  manual, and no value you worked out. Every checker is shown these
  facts; no checker is shown the question. If the question states no facts
  about a case (it only asks what the manual says), give an empty list. A
  fact is not a step: never put its id in "requires", "inputs" or a guard.

claim
  One statement, never a question, about the situation in the question. Write
  it so that TRUE means the situation meets the provision (or, for a
  condition, that the condition holds) and FALSE means it does not. When the
  question asks what the manual requires, recommends or allows, rather than
  whether a described design complies, the claim states what the manual
  requires, recommends or allows in this situation, and TRUE means the manual
  says so. Say what the provision means for this case; do not just repeat the
  provision's sentence. The checker sees the claim, the facts and the manual,
  never the question. So every fact a claim depends on must be in "facts",
  and the claim itself should still carry the values, units and conditions
  it is about, as written in the question. Do not decide
  whether the claim is true. Do not work out a value that a table, figure or
  provision holds; say where it is, in evidence_hint.

type: what kind of check it is. The type decides the checker.
  applicability     does a provision apply to the situation at all
                    -> language model
  classification    which category something falls in
                    -> language model (vision model when only a figure shows it)
  numerical         a quantity compared with a limit
                    -> calculator when a table is named, otherwise rule evaluator.
                    For the calculator: name the table, and the column when the
                    table has more than one value column; put the input value
                    with its unit in the claim.
  visual            something that must be seen in a figure
                    -> vision model; name the figure
  definitional      what a defined term means
                    -> language model
  cross_reference   a provision points to another section, figure or table
                    -> resolver, then language model. The resolver confirms the
                    target exists; the language model checks what the claim
                    says about it against the manual. What the target requires
                    is an obligation of its own.
  exception         a provision that relaxes or overrides another
                    -> language model

authority: copy the printed heading of the source provision. The manual
defines the headings this way:
  Standard   required, mandatory, or specifically prohibitive practice ("shall")
  Guidance   recommended practice in typical situations ("should")
  Option     a permissive condition with no requirement or recommendation ("may")
  Support    information only. Never an obligation.
Do not upgrade or downgrade it. A provision marked "heading inferred" has no
printed heading; use the type it is shown with.

requires: the ids that must be settled before this one can be checked. Empty
when the check can be made on its own.

guard: null, or the condition under which this item is relevant at all. Only
these forms:
  {{"state": "<id>", "status": "TRUE"}}    status is TRUE, FALSE, UNKNOWN, or
                                         RESOLVED (meaning TRUE or FALSE)
  {{"all": [<guard>, <guard>, ...]}}
  {{"any": [<guard>, <guard>, ...]}}
  {{"not": <guard>}}
A guard reads only ids that are also in this item's "requires" (for a merge,
its "inputs"): a result can be read only once it is settled. A guard is never
a sentence.

evidence_hint: where the evidence is. A list of objects:
  {{"type": "table",   "id": "Table <id as printed>"}}
  {{"type": "column",  "id": "<column heading as printed>"}}   with a table: the column to read
  {{"type": "part",    "id": "<chart letter>"}}                 with a table printed as charts A, B, ...
  {{"type": "sheet",   "id": "<sheet number>"}}                 with a table printed on several sheets
  {{"type": "figure",  "id": "Figure <id as printed>"}}
  {{"type": "section", "id": "<section number as printed>", "paragraph": "<number, optional>"}}
Name only tables, figures and sections that exist in the manual. A TABLE ROW
item shows a table's printed column headings.

source_chunk: the id, shown in square brackets, of the Standard, Guidance or
Option provision the obligation comes from. Never a Support item, a TABLE ROW
or a FIGURE DESCRIPTION.

merges: how results combine. Every input of a merge, and the merge itself,
read the same way as a claim: TRUE means met (or holds). A merge's claim says
what its inputs together establish, in the same direction as its inputs. The
executor applies merges exactly like this:
  conjunction   holds when every input holds. A GUIDANCE input that fails is
                recorded as a non-conformance and does not make it fail; an
                OPTION input that is not taken does not make it fail either. A
                failed STANDARD input makes it fail.
  alternative   holds when any one input holds.
  exception     inputs[0] is the base rule, written as a claim that the
                situation MEETS it, so it is FALSE when the rule is broken. The
                other inputs each say that an exception covers this situation.
                It holds when the base rule holds, or when the base rule fails
                and one of the exceptions applies. inputs[0] is never itself an
                exception. A claim that a rule APPLIES is not a base rule: it
                belongs in "requires" or a guard.
A numeric comparison is a numerical obligation, not a merge.
The authority of a merge is the heading of the rule it stands for. Leave it
STANDARD unless the merge combines only GUIDANCE or only OPTION items.

RULES (a plan that breaks one is sent back to you)
- Every id is unique. Every id in "requires", "inputs" and a guard is declared
  in this plan, and is an obligation or a merge, never a fact.
- A fact is a statement copied from the question, never its question. Every
  number in a fact is in the question's statements. A fact names a section,
  figure or table, or says what is required or allowed, only if the
  question's statements do.
- A merge has at least two inputs.
- The first input of an exception merge is the base rule: never an
  applicability or exception obligation.
- No cycles.
- The terminal can be reached: everything it depends on can be produced.
- Every obligation has a source_chunk from the provisions shown, and its
  authority is that provision's heading.
- Every table, figure and section in evidence_hint exists in the manual.
- Every claim is a statement, not a question.
- Do not name a checker.

Reply with the JSON object only: no text before or after it, and no markdown
fence."""

# Rules added to every repair request, beside compile.repair_request's own.
GROUNDING_RULES = [
    "every obligation names a source_chunk from the provisions shown",
    "a source_chunk is a Standard, Guidance or Option provision -- never "
    "Support, a TABLE ROW or a FIGURE DESCRIPTION",
    "an obligation's authority is the printed heading of its source_chunk",
    "every table, figure and section named in evidence_hint exists in the "
    "manual, and a column, part or sheet is one that table has",
    "merge kinds are conjunction, alternative and exception; a numeric "
    "comparison is a numerical obligation",
    "a guard reads only ids that are in the same item's requires (for a merge, "
    "its inputs)",
    "every claim is a statement that is TRUE when the situation meets the "
    "provision, never a question",
    "a fact is a statement copied from the question in its own words, never "
    "its question: every number in it is in the question's statements, and it "
    "names the manual or says what is required or allowed only if they do",
    "the first input of an exception merge is the base rule (a claim that the "
    "situation MEETS a rule), never an applicability or exception obligation",
]


# --------------------------------------------------------------------------- #
# 2. The prompt
# --------------------------------------------------------------------------- #
def _refs_line(c: Dict[str, Any]) -> str:
    refs: List[str] = []
    for key, word in (("table_refs", "Table"), ("figure_refs", "Figure")):
        for x in c.get(key) or []:
            x = str(x)
            refs.append(x if x.lower().startswith(("table", "figure")) else f"{word} {x}")
    for s in c.get("section_refs") or []:
        refs.append(f"Section {s}")
    refs = list(dict.fromkeys(refs))
    return ("\n  cites: " + "; ".join(refs)) if refs else ""


def _first_ref(c: Dict[str, Any], key: str, word: str) -> str:
    for x in c.get(key) or []:
        x = str(x)
        return x if x.lower().startswith(word.lower()) else f"{word} {x}"
    return word.lower()


def _header(c: Dict[str, Any]) -> str:
    """The line above a provision: what it is and where it sits."""
    cid = str(c.get("chunk_id"))
    kind = str(c.get("content_type") or "")
    src = str(c.get("source") or "")
    if kind == "TableRow":
        return (f"[{cid}] TABLE ROW of {_first_ref(c, 'table_refs', 'Table')}"
                f" -- printed table content, not a provision")
    if kind == "FigureReading":
        return (f"[{cid}] FIGURE DESCRIPTION of {_first_ref(c, 'figure_refs', 'Figure')}"
                f" -- written by a reader, not the manual's words; it may contain "
                f"mistakes; not a provision")
    where = ""
    parent = str(c.get("parent_id") or "")
    if parent.lower().startswith(("table ", "figure ")) and c.get("item"):
        where = f", note {c.get('item')} to {parent}"
    elif parent.lower().startswith(("table ", "figure ")):
        where = f", note to {parent}"
    elif str(c.get("section_id") or "")[:1].isalpha() or src == "appendix":
        where = ", appendix"
    else:
        if c.get("ordinal") not in (None, ""):
            where = f", paragraph {c.get('ordinal')}"
        if c.get("item"):
            where += f", item {c.get('item')}"
    head = f"[{cid}] {kind}{where}"
    if kind == "Support":
        head += " (information only; never an obligation)"
    if c.get("authority_inferred"):
        head += " (heading inferred from the verb; no printed heading)"
    return head


def _natural(s: str) -> Tuple:
    """'r10' after 'r2': digits compare as numbers."""
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                 for p in re.split(r"(\d+)", s) if p)


def _sort_key(c: Dict[str, Any]):
    """Paragraphs and list items in the manual's order, then the notes of each
    table or figure in note order, then table rows, then figure descriptions."""
    kind = str(c.get("content_type") or "")
    parent = str(c.get("parent_id") or "")
    is_note = parent.lower().startswith(("table ", "figure "))
    group = (3 if kind == "FigureReading" else 2 if kind == "TableRow"
             else 1 if is_note else 0)
    try:
        ordinal = int(c.get("ordinal") or 0)
    except (TypeError, ValueError):
        ordinal = 0
    return (group, _natural(parent) if group else (), ordinal if group == 0 else 0,
            _natural(str(c.get("item") or "")), _natural(str(c.get("chunk_id"))))


def format_provisions(chunks: Sequence[Dict[str, Any]]) -> str:
    """Kq grouped by section, sections in the order retrieval ranked them,
    each section's items in the manual's own order. A list's lead-in is
    printed once, above its first item, because it carries the list's
    condition and repeating it per item only adds length."""
    order: List[str] = []
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    seen: set = set()
    for c in chunks:
        cid = str(c.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        sec = str(c.get("section_id") or "")
        if sec not in by_sec:
            order.append(sec)
            by_sec[sec] = []
        by_sec[sec].append(c)

    blocks: List[str] = []
    for sec in order:
        rows = sorted(by_sec[sec], key=_sort_key)
        title = next((str(r.get("section_title") or "") for r in rows
                      if r.get("section_title")), "")
        lines = [f"=== Section {sec}  {title}".rstrip()]
        last_lead = None
        for c in rows:
            kind = str(c.get("content_type") or "")
            lead = (c.get("lead_in") or "").strip()
            text = (c.get("text") or "").strip()
            parent = str(c.get("parent_id") or "").lower()
            is_note = parent.startswith(("table ", "figure "))
            is_item = bool(c.get("item")) and not is_note
            entry = [_header(c)]
            if is_note and lead.rstrip(". ").lower() == parent:
                lead = ""                 # "Table 7B-1." says only what the header says
            if lead and kind not in ("TableRow", "FigureReading"):
                if is_item or is_note:
                    if lead != last_lead:
                        entry.insert(0, f"(the list below begins: {lead})" if is_item
                                     else f"({lead})")
                    last_lead = lead
                elif not text.startswith(lead):
                    text = f"{lead} {text}"
            else:
                last_lead = None
            entry.append(text)
            refs = "" if kind in ("TableRow", "FigureReading") else _refs_line(c)
            lines.append("\n".join(entry) + refs)
        blocks.append("\n\n".join(lines))
    return "\n\n".join(blocks) or "(none)"


def format_figures(figures: Sequence[Dict[str, Any]]) -> str:
    out = []
    for f in figures or []:
        fid = str(f.get("figure_id") or "")
        if not fid:
            continue
        cap = str(f.get("caption") or "").strip()
        n = int(f.get("n_sheets") or 1)
        out.append(f"[{fid}] {cap}" + (f" ({n} sheets)" if n > 1 else ""))
    return "\n".join(out)


def build_parser_prompt(query: str, chunks: Sequence[Dict[str, Any]],
                        section_id: str = "",
                        repair: Optional[Dict[str, Any]] = None,
                        figures: Sequence[Dict[str, Any]] = ()) -> str:
    """The task, the provisions, the question, the contract, and -- on a
    second attempt -- what was wrong with the first.

    `section_id` is accepted for the fallback's sake and is not shown: the
    parser reads everything retrieval returned, not one section chosen for it.
    """
    parts = [PARSER_TASK, "",
             "PROVISIONS (retrieved for this question; ids in square brackets)",
             "", format_provisions(chunks)]
    figs = format_figures(figures)
    if figs:
        parts += ["", "FIGURES THE VISION MODEL CAN BE GIVEN", figs]
    parts += ["", "QUESTION", (query or "").strip(), "", PARSER_CONTRACT]

    if repair:
        if repair.get("spec") is None:
            parts += [
                "",
                "YOUR PREVIOUS REPLY COULD NOT BE READ.",
                "Problem: " + "; ".join(str(p) for p in repair.get("problems") or []),
                "Reply with the JSON object only, as described above. Keep your "
                "reasoning short.",
            ]
        else:
            parts += [
                "",
                "YOUR PREVIOUS PLAN WAS REJECTED.",
                "Problems:\n" + "\n".join(f"- {p}" for p in repair["problems"]),
                "Rules:\n" + "\n".join(f"- {r}" for r in repair["rules"]),
                "Fix what is listed and keep the rest. Return the whole corrected "
                "JSON object.",
                "Your previous plan:\n" + json.dumps(repair["spec"], indent=1)[:20000],
            ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# 3. Reading the reply
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)


def _find_object(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """The plan object in the reply, and what went wrong if there is none.

    Thinking that leaked into the reply is cut off at its last `</think>`.
    Then every `{` is tried as the start of a JSON value: the first object
    with an "obligations" key wins, else the first object at all. Matching
    from the first `{` to the last `}` would fail on a valid plan followed by
    a remark that happens to contain a brace.
    """
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = _FENCE.sub("", text).strip()
    decoder = json.JSONDecoder()
    first: Optional[Dict[str, Any]] = None
    error = ""
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text, i)
        except json.JSONDecodeError as e:
            error = error or f"malformed JSON: {e}"
            continue
        if isinstance(value, dict):
            if "obligations" in value:
                return value, ""
            first = first or value
    if first is not None:
        return first, ""
    return None, error or "the reply contained no JSON object"


def read_spec(raw: str, query: str, allowed_chunks: Sequence[str] = (),
              ) -> Tuple[Optional[NetworkSpec], List[str]]:
    """Turn the reply into a NetworkSpec, or say why it cannot be.

    A `verifier` the model named is discarded: S3.1 assigns a verifier by
    rule. A `source_chunk` is kept exactly as written; `grounding_problems`
    decides whether it points at a provision that was shown, so the repair
    request can quote the id the model used. (`allowed_chunks` is accepted
    for older callers and no longer used here.)
    """
    data, error = _find_object(raw or "")
    if data is None:
        return None, [error]

    problems: List[str] = []
    obligations = data.get("obligations")
    if not isinstance(obligations, list) or not obligations:
        return None, ['"obligations" must be a non-empty list']
    merges = data.get("merges")
    if merges is None:
        data["merges"] = merges = []
    if not isinstance(merges, list):
        return None, ['"merges" must be a list']
    for k, ob in enumerate(obligations):
        if not isinstance(ob, dict):
            problems.append(f"obligation number {k + 1} is not an object")
            continue
        if not isinstance(ob.get("claim"), str) or not ob["claim"].strip():
            problems.append(f"obligation {ob.get('id', k + 1)!r} has no claim")
    for k, m in enumerate(merges):
        if not isinstance(m, dict):
            problems.append(f"merge number {k + 1} is not an object")
        elif not isinstance(m.get("claim"), str) or not m["claim"].strip():
            m["claim"] = str(m.get("id", ""))
    if problems:
        return None, problems

    notes: List[str] = []
    for ob in obligations:
        if ob.pop("verifier", None) is not None:
            notes.append("a proposed verifier was discarded; the rule assigns it")
    data["query"] = query
    data["source"] = "semantic_parser"
    try:
        spec = NetworkSpec.from_dict(data)
    except (CompileError, TypeError, ValueError, AttributeError, KeyError) as e:
        return None, [f"the JSON does not have the required shape: {e}"]
    return spec, notes


# --------------------------------------------------------------------------- #
# 4. References to the manual
# --------------------------------------------------------------------------- #
_PREFIX = {"table": "table ", "figure": "figure ", "section": "section "}


def _bare(kind: str, ident: str) -> str:
    s = str(ident).strip()
    p = _PREFIX.get(kind, "")
    return s[len(p):].strip() if p and s.lower().startswith(p) else s


def grounding_problems(spec: NetworkSpec, chunks: Sequence[Dict[str, Any]],
                       check_ref: Optional[Callable[[str, str], bool]] = None,
                       tables: Optional[Dict[str, List[Any]]] = None) -> List[str]:
    """What the plan says about the MANUAL that is not so.

    check_ref(kind, bare_id) -> bool, e.g. `VineKG.is_known_citation`, which
    is asked ("table", "2C-4"), ("figure", "3C-1"), ("section", "2C.07").
    tables: {"Table 2C-4": [Table, ...]} from `table_data.load`, for column,
    part and sheet hints. Either may be None, and that check is skipped.
    """
    out: List[str] = []
    by_id = {str(c.get("chunk_id")): c for c in chunks if c.get("chunk_id")}

    for x in list(spec.obligations) + list(spec.merges):
        if x.claim.strip().endswith("?"):
            out.append(f"{x.id}: the claim is a question; write it as a statement "
                       f"that is TRUE when the situation meets the provision")
    for o in spec.obligations:
        src = (o.source_chunk or "").strip()
        if not src:
            out.append(f"{o.id}: no source_chunk; name the provision this "
                       f"obligation comes from")
        elif src not in by_id:
            out.append(f"{o.id}: source_chunk {src!r} is not one of the "
                       f"provisions shown")
        else:
            kind = str(by_id[src].get("content_type") or "")
            if kind not in NORMATIVE:
                out.append(f"{o.id}: source_chunk {src!r} is "
                           f"{_NOT_A_PROVISION.get(kind, kind or 'unlabelled')}, "
                           f"not a Standard, Guidance or Option provision")
            elif o.authority != kind.upper():
                out.append(f"{o.id}: authority {o.authority}, but {src!r} is "
                           f"printed as {kind}; copy the heading")

        named_tables: List[str] = []
        for h in o.evidence_hint:
            kind = str(h.get("type", "")).lower()
            ident = str(h.get("id", "")).strip()
            if kind not in HINT_TYPES:
                out.append(f"{o.id}: evidence_hint type {kind!r} is not one of "
                           f"{list(HINT_TYPES)}")
                continue
            if not ident:
                out.append(f"{o.id}: an evidence_hint of type {kind!r} has no id")
                continue
            if kind in ("table", "figure", "section"):
                other = {"table": "figure ", "figure": "table "}.get(kind)
                if other and ident.lower().startswith(other):
                    out.append(f"{o.id}: evidence_hint {ident!r} is marked "
                               f"{kind!r}; use type {other.strip()!r}")
                    continue
                if check_ref is not None and not check_ref(kind, _bare(kind, ident)):
                    out.append(f"{o.id}: {kind} {ident!r} in evidence_hint is not "
                               f"in the manual")
                    continue
                if kind == "table":
                    named_tables.append(f"Table {_bare('table', ident)}")
        if tables is not None:
            out.extend(_table_detail_problems(o, named_tables, tables))

    # A guard is evaluated against the store as it stands (Eq 4). Reading a
    # result that is not yet settled makes "not TRUE" hold before the check
    # has even run, so a guard may read only what the item already waits for.
    for o in spec.obligations:
        if o.guard:
            early = [x for x in dict.fromkeys(o.guard.states()) if x not in o.requires]
            if early:
                out.append(f"{o.id}: its guard reads {early}, which must also be in "
                           f"its requires")
    for m in spec.merges:
        if m.guard:
            early = [x for x in dict.fromkeys(m.guard.states()) if x not in m.inputs]
            if early:
                out.append(f"{m.id}: its guard reads {early}, which must also be "
                           f"among its inputs")
        if m.kind == MergeType.THRESHOLD.value:
            out.append(f"{m.id}: a threshold merge has no comparator in this "
                       f"system; write the comparison as a numerical obligation")
        if m.authority not in ("STANDARD", "GUIDANCE", "OPTION"):
            out.append(f"{m.id}: merge authority {m.authority!r} is not "
                       f"STANDARD, GUIDANCE or OPTION")

    # The executor reads inputs[0] of an exception merge as "the situation
    # MEETS the rule": TRUE settles the merge without looking at the
    # exception. A claim that a rule APPLIES is TRUE whether or not the rule
    # is met, so in that place it would pass a case the exception does not
    # cover. The instructions above already say so; this enforces it.
    by_ob = {o.id: o for o in spec.obligations}
    for m in spec.merges:
        if m.kind == MergeType.EXCEPTION.value and m.inputs:
            base = by_ob.get(m.inputs[0])
            if base is not None and base.type == ObligationType.APPLICABILITY.value:
                out.append(f"{m.id}: its first input {base.id!r} is an applicability "
                           f"check, but the first input of an exception merge is the "
                           f"base rule, written as a claim that the situation MEETS "
                           f"it; put {base.id!r} in requires or a guard instead")
    out.extend(fact_problems(spec))
    return out


def _table_detail_problems(o, named_tables: List[str],
                           tables: Dict[str, List[Any]]) -> List[str]:
    out: List[str] = []
    details = [(str(h.get("type", "")).lower(), str(h.get("id", "")).strip())
               for h in o.evidence_hint
               if str(h.get("type", "")).lower() in ("column", "part", "sheet")]
    if not details:
        return out
    records = [t for name in named_tables for t in tables.get(name, [])]
    if not named_tables:
        kinds = sorted({k for k, _ in details})
        return [f"{o.id}: a {'/'.join(kinds)} hint needs a table hint beside it"]
    if not records:
        return out          # the table exists in the manual but has no transcription
    for kind, ident in details:
        if kind == "column":
            if not any(t.column(ident) is not None for t in records):
                labels = list(dict.fromkeys(l for t in records for l in t.column_labels))
                out.append(f"{o.id}: column {ident!r} is not a column of "
                           f"{', '.join(named_tables)}; its columns are {labels[:24]}")
        elif kind == "part":
            parts = sorted({str(t.part) for t in records if t.part})
            if parts and ident not in parts:
                out.append(f"{o.id}: part {ident!r} is not a chart of "
                           f"{', '.join(named_tables)}; its charts are {parts}")
        elif kind == "sheet":
            sheets = sorted({str(t.sheet) for t in records if t.sheet})
            if sheets and ident not in sheets:
                out.append(f"{o.id}: sheet {ident!r} is not a sheet of "
                           f"{', '.join(named_tables)}; its sheets are {sheets}")
    return out


# --------------------------------------------------------------------------- #
# 4b. The facts (Γ0q): copied from the question, nothing added
# --------------------------------------------------------------------------- #
_FACT_NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?")
_FACT_REF = re.compile(r"\b\d{1,2}[A-Z]\.\d{2}\b"
                       r"|\b(?:section|figure|table|paragraph|mutcd|manual)s?\b", re.I)
# Words that say what is required or allowed, or whether something passes.
# A fact may use one only if a statement in the question does.
_FACT_NORMATIVE = re.compile(
    r"\b(?:shall|should|must|may|requir(?:e|es|ed|ement|ements)|mandatory|"
    r"permi(?:t|ts|tted|ssible)|allow(?:s|ed)?|prohibit(?:s|ed)?|forbidden|"
    r"recommend(?:s|ed)?|warrant(?:s|ed)?|compl(?:y|ies|iant|iance)|noncompliant|"
    r"conform(?:s|ing|ance)?|nonconforming|violat(?:e|es|ed|ion|ions)|"
    r"satisf(?:y|ies|ied|actory)|meets|met|(?:un)?acceptable|(?:im)?proper(?:ly)?|"
    r"(?:in)?correct(?:ly)?|(?:il)?legal|(?:in)?valid|(?:in)?adequate|"
    r"(?:in)?sufficient|(?:in)?appropriate|ok|okay|fine|(?:un)?suitable|"
    r"needs?|needed|(?:un)?necessary|appl(?:y|ies|ied|icable)|inapplicable|"
    r"qualif(?:y|ies|ied|ying|ication)|pass(?:es|ed)?|fail(?:s|ed)?|"
    r"(?:in)?consistent|(?:in)?eligible|exempt(?:ed|ion)?)\b", re.I)
_ASKING = re.compile(r"^\s*(?:is|are|was|were|does|do|did|can|could|may|might|must|"
                     r"should|shall|will|would|what|which|where|when|who|whom|whose|"
                     r"why|how)\b", re.I)
_NUMBER_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_NUMBER_WORDS.update({"thirty": "30", "forty": "40", "fifty": "50", "sixty": "60",
                      "seventy": "70", "eighty": "80", "ninety": "90",
                      "hundred": "100", "thousand": "1000"})


def _canon_number(n: str) -> str:
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def _numbers(text: str) -> List[str]:
    """Every number in the text, spelt as digits; section numbers left out."""
    text = _FACT_REF.sub(" ", text)
    out = [_canon_number(n) for n in _FACT_NUMBER.findall(text)]
    out += [_NUMBER_WORDS[w] for w in re.findall(r"[a-z]+", text.lower())
            if w in _NUMBER_WORDS]
    return out


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# a full stop after these is part of a short form, not the end of a sentence
_SHORT_FORM = re.compile(r"(?:\b(?:in|ft|mi|yd|lb|no|nos|st|rd|ave|blvd|hwy|approx|"
                         r"fig|sec|para|vs|etc|min|max|sq|e\.g|i\.e)\.|\b[A-Z]\.)$", re.I)


def _sentences(text: str) -> List[str]:
    parts = [x.strip() for x in re.split(r"(?<=[.?!])[\"'\u201d\u2019)\]]*\s+", text or "")
             if x.strip()]
    out: List[str] = []
    for x in parts:
        if out and _SHORT_FORM.search(out[-1]):
            out[-1] = f"{out[-1]} {x}"
        else:
            out.append(x)
    return out


# "Determine whether ...", "Explain what ...": an ask without a question mark
_ASK_VERB = re.compile(r"^\W*(?:please\s+)?(?:(?:determine|explain|decide|check|identify|"
                       r"tell|list|describe|find|confirm|verify)\b|(?:state|say)\s+"
                       r"(?:whether|what|which|how|if|when|where|who|the|any)\b)", re.I)
# words too common to show that a fact was reworded
_GLUE = set("a an the is are was were be been being it its this that these those of to "
            "in on at by for with and or as from there their they them he she his her "
            "has have had will would which who whom".split())
# a fact may bring in at most this share of content words that no statement
# of the question has (a pronoun resolved, a plural made singular)
_NEW_WORD_SHARE = 0.25


def _stem(w: str) -> str:
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _is_ask(sentence: str) -> bool:
    bare = sentence.rstrip("\"'\u201d\u2019)] ")
    return (bare.endswith("?") or bool(_ASKING.match(sentence.lstrip("\"'\u201c\u2018(["))
            and not bare.endswith("."))
            or bool(_ASK_VERB.match(sentence)) or bool(re.search(r"\bwhether\b", sentence, re.I)))


def _split_question(query: str) -> Tuple[List[str], List[str]]:
    """(statements, asks). A question with no recognisable ask is taken to
    ask in its last sentence, so its last sentence never counts as a fact."""
    sentences = _sentences(query)
    asks = [x for x in sentences if _is_ask(x)]
    if not asks and sentences:
        asks = [sentences[-1]]
    return [x for x in sentences if x not in asks], asks


def fact_problems(spec: NetworkSpec) -> List[str]:
    """What a listed fact adds to the question.

    A fact goes into Γ0q and every checker treats it as established, so it
    must be what the question STATES. Only the question's statements count,
    not what it asks: "Is this allowed?" is not a fact, and its "allowed"
    may not appear in one. A fact's numbers are the statements' numbers
    (written in digits or in words); it names the manual, or says what is
    required, allowed or acceptable, only if a statement does; at most a
    quarter of its content words are new (it is the question's own words, not
    a paraphrase that could carry a conclusion: "the panel is good"); it is
    one sentence, never a question, and does not copy the question's ask (a
    sentence ending in "?", one starting "Determine ..." or holding
    "whether", or, failing those, the question's last sentence). Checked against
    `spec.query`, which `read_spec` sets to the question.
    """
    out: List[str] = []
    stated, asked = _split_question(spec.query or "")
    statements = " ".join(stated)
    asks = [" ".join(_words(x)) for x in asked]
    q_refs = {m.group(0).lower() for m in _FACT_REF.finditer(statements)}
    q_numbers = set(_numbers(statements))
    q_words = set(_words(statements))
    for f in spec.facts:
        text = f.text
        flat = " ".join(_words(text))
        if "?" in text or _is_ask(text):
            out.append(f"{f.id}: is a question; a fact states what the case is")
        elif any(len(a.split()) >= 3 and f" {a} " in f" {flat} " for a in asks):
            out.append(f"{f.id}: copies what the question asks; a fact states only "
                       f"what the question says about the case")
        if len(_sentences(text)) > 1:
            out.append(f"{f.id}: has more than one sentence; give one fact per item")
        refs = [m.group(0) for m in _FACT_REF.finditer(text)
                if m.group(0).lower() not in q_refs]
        if refs:
            out.append(f"{f.id}: names {sorted(set(refs))}, which is not in what "
                       f"the question states; a fact describes the case, not the manual")
        new = [n for n in dict.fromkeys(_numbers(text)) if n not in q_numbers]
        if new:
            out.append(f"{f.id}: the number(s) {new} are not in what the question "
                       f"states; copy its values exactly and work nothing out")
        content = [w for w in _words(text) if w not in _GLUE and not w.isdigit()
                   and w not in _NUMBER_WORDS]
        stems = {_stem(w) for w in q_words}
        added = [w for w in content if _stem(w) not in stems]
        if content and len(added) / len(content) > _NEW_WORD_SHARE:
            out.append(f"{f.id}: uses words not found in the question ({sorted(set(added))[:6]}); "
                       f"copy the question's statements in their own words")
        said = sorted({m.group(0).lower() for m in _FACT_NORMATIVE.finditer(text)}
                      - q_words)
        if said:
            out.append(f"{f.id}: says {said}, which is not in what the question "
                       f"states; a fact states what the case is, not what is "
                       f"required, allowed or acceptable")
    return out


# --------------------------------------------------------------------------- #
# 5. The parser
# --------------------------------------------------------------------------- #
@dataclass
class ParseReport:
    """What happened, in enough detail to audit a bad network afterwards."""
    source: str = ""                      # semantic_parser | baseline | failed
    attempts: int = 0
    problems: List[List[str]] = field(default_factory=list)   # per attempt
    notes: List[str] = field(default_factory=list)
    raw: List[str] = field(default_factory=list)              # every reply, whole
    calls: List[Dict[str, Any]] = field(default_factory=list)  # model-call records

    def as_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "attempts": self.attempts,
                "problems": self.problems, "notes": self.notes,
                "calls": self.calls}


def _dedupe(items: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(items))


def make_semantic_parser(ask: Callable[[str, List[str]], str],
                         max_attempts: int = 3,
                         fall_back_to_baseline: bool = True,
                         check_ref: Optional[Callable[[str, str], bool]] = None,
                         tables: Optional[Dict[str, List[Any]]] = None):
    """Build the parser. `ask(prompt, images) -> str`, the same contract the
    verifiers use, so one model call site serves the whole pipeline. If `ask`
    carries a `last` dict after each call (the vLLM client does), it is kept
    in the report.

    Returns `parse(query, chunks, section_id="", figures=()) ->
    (NetworkSpec | None, ParseReport)`.
    """
    def parse(query: str, chunks: Sequence[Dict[str, Any]],
              section_id: str = "", figures: Sequence[Dict[str, Any]] = (),
              ) -> Tuple[Optional[NetworkSpec], ParseReport]:
        report = ParseReport()
        repair: Optional[Dict[str, Any]] = None

        for attempt in range(1, max_attempts + 1):
            report.attempts = attempt
            prompt = build_parser_prompt(query, chunks, section_id, repair, figures)
            try:
                raw = ask(prompt, [])
            except Exception as e:                            # noqa: BLE001
                report.problems.append([f"the model call failed: {e!r}"])
                break
            meta = getattr(ask, "last", None)
            if isinstance(meta, dict):
                report.calls.append({k: v for k, v in meta.items() if k != "prompt"})
            report.raw.append((raw or "")[:200000])

            spec, notes = read_spec(raw, query)
            report.notes.extend(notes)
            if spec is None:
                report.problems.append(notes or ["the reply could not be read"])
                repair = {"problems": notes or ["the reply could not be read"],
                          "rules": [], "spec": None}
                continue

            problems = grounding_problems(spec, chunks, check_ref, tables)
            try:
                _net, built = instantiate(spec)
            except (CompileError, ValueError, KeyError) as e:
                built = [f"the plan could not be built: {e}"]
            problems = _dedupe(problems + list(built))
            if not problems:
                report.source = "semantic_parser"
                return spec, report
            report.problems.append(problems)
            repair = repair_request(spec, problems)
            repair["rules"] = _dedupe(list(repair["rules"]) + GROUNDING_RULES)

        if fall_back_to_baseline and section_id:
            try:
                base = compile_section(section_id, chunks, query=query)
            except CompileError as e:
                report.source = "failed"
                report.notes.append(f"the baseline could not compile it either: {e}")
                return None, report
            _net, problems = instantiate(base)
            if problems:
                report.source = "failed"
                report.notes.append(f"the baseline spec was itself invalid: {problems}")
                return None, report
            report.source = "baseline"
            report.notes.append("the semantic parser did not produce a valid "
                                "spec; the printed structure was used instead")
            return base, report

        report.source = "failed"
        return None, report

    return parse
