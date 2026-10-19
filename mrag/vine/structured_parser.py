"""The structured parser -- the plan made paragraph by paragraph (18 Oct 2026).

WHY
---
`parser.make_semantic_parser` asks the model for the whole plan in one reply:
which provisions matter, what to check, the dependencies, guards, merges and
the terminal. On 16-18 Oct three plan-writers (Qwen3.8-27B, Qwen3.8-Max,
Claude Sonnet 5.5) gave plans of about the same quality, and the plan misses
were of one kind: a paragraph that was shown, and that bore on the question,
was left out, or was put in the wrong place in the structure. A larger model
did not remove them. So this parser gives the model less to decide at once,
and lets code do what code can do:

  1. one call reads the QUESTION only: the facts of the case (Γ0q, as before)
     and the things asked, each marked as asking about the CASE (does it meet
     the manual?) or about the MANUAL (what does the manual require or allow
     for a case like this?), with a statement of what is to be decided;
  2. one call per group of retrieved sections asks, for EVERY Standard,
     Guidance and Option paragraph shown, whether it bears on what is asked,
     and if it does, which checks it gives -- each check marked as being about
     the case or about the manual (`compile.Obligation.about`, which the
     checker is shown: model_verifiers.about_block). No paragraph can be
     passed over in silence: each gets a decision and a reason, on record;
  3. CODE builds the structure (section 3 below) from those decisions, the
     paragraphs' printed headings and the manual's own links: a check's
     authority is its paragraph's heading; a paragraph's checks are merged
     by the paragraph; an exception the manual names (the graph's EXCEPTS
     links and "except as provided in ..." clauses, `exceptions_from_graph`)
     or that the model says a paragraph is goes into an exception merge with
     the rule first; the parts are merged per thing asked; the terminal
     merges the things asked. A merge's heading follows the merge rule the
     parser was always given ("STANDARD unless the merge combines only
     GUIDANCE or only OPTION items"), and the executor is unchanged.

Nothing here is shaped by a test question. The wording of the fields comes
from `parser.PARSER_CONTRACT` (itself from S3.1 and the manual's Section
1C.01); the structure rules are the executor's (execute.py); the paragraphs
the graph adds are the manual's own links: the exceptions a provision names,
and the Option paragraphs of a Standard's or Guidance's section (1C.01:
"Standard statements are sometimes modified by Option statements";
"Option statements sometimes contain allowable modifications to a Standard
or Guidance statement").

WHAT IS CHECKED
---------------
The facts as before (`parser.fact_problems`). Each section reply: every
paragraph decided once, every check answering a thing asked, a check that
answers an ask about the case being about the case (a statement of what the
manual says would be TRUE however the case is built), the check types, the
references to the manual (`parser.grounding_problems`), and the labelled
cases (rule A). Problems go back for one repair; what is left is dropped and
recorded (`report.open_problems`). The built plan goes through `instantiate`
like any other, and rules A, C and D of `parser.coverage_problems`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .compile import (AskedItem, CompileError, GivenFact, MergeSpec, NetworkSpec, Obligation,
                      instantiate)
from .network import ObligationType
from .parser import (HINT_TYPES, NORMATIVE, ParseReport, _sentences, _sort_key, _words,
                     claim_names_case, coverage_problems, fact_problems, format_figures,
                     format_provisions, grounding_problems, named_exceptions_shown,
                     several_cases)

log = logging.getLogger("mrag.vine.structured_parser")

__all__ = ["make_structured_parser", "StructuredReport", "INSTRUCTIONS", "VERSION",
           "FACTS_TASK", "SECTION_TASK", "SECTION_CONTRACT", "graph_hooks",
           "build_facts_prompt", "build_section_prompt", "plan_calls", "assemble"]

VERSION = "structured1"

# Normative paragraphs decided in one call, at most. A section with more is
# split; small sections are put together in one call, in retrieval order.
GROUP_CAP = 16
# Paragraphs the graph adds to what search returned (see `_additions`)
EXCEPTIONS_PER_RULE, EXCEPTIONS_PER_QUESTION = 4, 12
OPTIONS_PER_SECTION, OPTIONS_PER_QUESTION = 3, 10
# Table rows are shown for a table's printed column headings (the calculator
# reads the values from the table data itself), so a few rows of a table are
# enough; a call says how many more were retrieved.
ROWS_PER_TABLE = 3

_TYPES = " | ".join(t.value for t in ObligationType)
_TYPE_VALUES = {t.value for t in ObligationType}


# --------------------------------------------------------------------------- #
# 1. The instructions
# --------------------------------------------------------------------------- #
FACTS_TASK = """You are the first step of the semantic parser of VINE, a system that checks
questions about the Manual on Uniform Traffic Control Devices (MUTCD, 11th
Edition).

This step reads the QUESTION only. It does not answer the question and does
not use the manual. It lists the facts the question states about the case,
and the things the question asks. Later steps read the manual paragraph by
paragraph, and separate checkers decide each check.

THE JSON OBJECT

{
  "facts": [
    {"id": "f1", "fact": "<one fact the question states about the case, in its words>"}
  ],
  "asked": [
    {"id": "a1", "ask": "<one thing the question asks, in its words>",
     "about": "<case | manual>",
     "claim": "<the thing asked, written as one statement>"}
  ]
}

THE FIELDS

facts
  The facts the question states about the case: what is there or planned,
  and its sizes, places, counts and conditions. One fact per item, copied
  from the question's statements in their own words, with every value and
  unit exactly as written there. Only what the question states, never what
  it asks. Nothing else: no conclusion, no requirement, no reference to the
  manual, and no value you worked out. Every checker is shown these facts;
  no checker is shown the question. If the question states no facts about a
  case (it only asks what the manual says), give an empty list. Ids f1, f2,
  ...

asked
  One item per thing the question asks: a question that asks two things
  gives two items. Ids a1, a2, ...
  ask     the thing asked, in the question's words.
  about   "case" when it asks whether something the question describes --
          what is there, built, planned, proposed or done -- meets the
          manual: whether it is allowed, acceptable, correct, compliant or
          enough.
          "manual" when it asks what the manual requires, recommends or
          allows for a case like this one: which device, where, when, who,
          how many, what value; or whether something may or must be done,
          when the question describes no design or action of its own to
          judge. When the question describes one and asks whether it is
          allowed, the ask is about the case.
  claim   one statement, never a question, that the later checks together
          decide. Use the question's own words and values, and do not
          decide the answer.
          For "case": that the case meets the manual on what is asked; TRUE
          means it does ("The mounting height of the sign described meets
          the manual").
          For "manual", when it asks which, where, when, who, how many or
          what: what is to be found in the manual, as a statement ("The
          manual states which border color is required for a sign like
          this one").
          For "manual", when it asks whether something may or must be done:
          that the manual allows it, or requires it, for this case ("The
          manual allows a second sign of this kind on the left side of the
          road here").

RULES (a reply that breaks one is sent back to you)
- A fact is a statement copied from the question, never its question. Every
  number in a fact is in the question's statements. A fact names a section,
  figure or table, or says what is required or allowed, only if the
  question's statements do.
- Every thing the question asks is an item of "asked", with "about" and a
  "claim".
- Every claim is a statement, not a question.

Reply with the JSON object only: no text before or after it, and no markdown
fence."""

SECTION_TASK = """You are a step of the semantic parser of VINE, a system that checks
questions about the Manual on Uniform Traffic Control Devices (MUTCD, 11th
Edition).

An earlier step read the question and listed the facts of the case and the
things it asks; they are below. Search then retrieved provisions of the
manual. Some of them are shown here, and every Standard, Guidance and Option
among them is listed under PARAGRAPHS TO DECIDE. Many will not matter for
this question: search also follows the manual's references, and finds
paragraphs that only share words with the question.

Decide, for EACH paragraph listed, whether it bears on what is asked; for
each one that does, write the checks it gives for this case. You do not
answer the question: separate checkers decide every check from the manual
and the facts. Code then builds the plan from your decisions, the
paragraphs' printed headings and the manual's own links between paragraphs.
The other paragraphs retrieved are decided in other calls like this one."""

SECTION_CONTRACT = f"""HOW TO DECIDE

A paragraph BEARS on the question when it governs something an ask is about
-- the device, place, value, time, action or person the ask concerns -- for
a case of the kind the facts describe, and no fact puts the case outside it.
A paragraph about another device or another situation does not bear, even
when it shares words with the question. A paragraph that would change the
answer for this case bears: a condition or limit on a rule that bears, an
exception to it, or an Option that allows something other than what that
rule says.

Support, a TABLE ROW and a FIGURE DESCRIPTION are shown only to help you read
the paragraphs: they are never decided, and never the source of a check.

THE JSON OBJECT

{{
  "paragraphs": [
    {{"id": "<the paragraph's id, as shown in square brackets>",
      "why": "<one short sentence: what the paragraph governs, and why that does or does not bear on what is asked>",
      "bears": <true | false>,
      "condition": "",
      "relaxes": [],
      "join": "all",
      "checks": [
        {{"claim": "<one checkable statement>",
          "about": "<case | manual>",
          "answers": ["<ids of the asks it helps answer>"],
          "type": "<{_TYPES}>",
          "evidence_hint": []}}
      ]}}
  ]
}}

One item for every paragraph under PARAGRAPHS TO DECIDE, in that order. For
a paragraph that does not bear, give "id", "why" and "bears": false, and an
empty "checks" list.

THE FIELDS

checks
  The checks the paragraph gives for this case: one check per thing that
  can be checked on its own. A paragraph that states two requirements gives
  two checks. Check only what bears on what is asked.

claim
  One statement, never a question. The checker sees the claim, the facts and
  the manual, never the question. Say what the paragraph means for this
  case; do not just repeat its sentence. Do not decide whether the claim is
  true, and do not work out a value that a table, figure or provision holds:
  say where it is, in evidence_hint.
  - About the case ("about": "case"): that the case, as the facts describe
    it, meets what the paragraph requires or recommends, or is within what
    it allows. TRUE means it does; FALSE means a fact shows that it does
    not. Carry the values, units and conditions it is about, as written in
    the facts.
  - About the manual ("about": "manual"): what the paragraph requires,
    recommends or allows for a case like this one, said for this case. TRUE
    means the manual says so.
  - When the facts describe more than one case, design, alternative or item
    of the same kind, each told apart by a label, every claim names the one
    it is about, or says that it holds for each of them.
  - When a claim restates a fact, use the fact's own words. Do not widen or
    narrow it with qualifiers the fact does not have.
  - A claim never states something about the case that the facts do not
    say. A condition the facts are silent on stays a condition ("where ...",
    "if ...").
  - When an ask asks which of several items meet a condition, write one
    claim per item, each saying that item meets it.

about
  "case" or "manual", as above. A check that answers an ask about the case
  is about the case: a statement of what the manual says is TRUE however the
  case is built, so it cannot show whether the case meets it. When there are
  no facts of the case, every check is about the manual.

answers
  The ids of the asks (a1, a2, ...) that the check helps answer. At least
  one.

type: what kind of check it is. The type decides the checker.
  applicability     does a provision apply to the situation at all: is the
                    case of the kind, place or situation the provision
                    covers. Not whether the case obeys the provision.
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
  cross_reference   the paragraph points to another section, figure or table
                    -> resolver, then language model
  exception         a check of a paragraph that relaxes another (see
                    "relaxes"): that the exception covers this case
                    -> language model

evidence_hint
  Where the evidence is, beyond the paragraph itself: the checker is always
  given the paragraph. A list of objects:
  {{"type": "table",   "id": "Table <id as printed>"}}
  {{"type": "column",  "id": "<column heading as printed>"}}   with a table: the column to read
  {{"type": "part",    "id": "<chart letter>"}}                 with a table printed as charts A, B, ...
  {{"type": "sheet",   "id": "<sheet number>"}}                 with a table printed on several sheets
  {{"type": "figure",  "id": "Figure <id as printed>"}}
  {{"type": "section", "id": "<section number as printed>", "paragraph": "<number, optional>"}}
  Name only tables, figures and sections that exist in the manual. A TABLE
  ROW item shows a table's printed column headings. Leave the list empty
  when the paragraph is all the evidence.

condition
  Empty, or a condition of scope that the paragraph states (a kind of road,
  device or place; a speed; a time) AND that the facts say something about,
  written as a statement about the case. Code makes it a check of its own,
  decided first: when it does not hold for the case, this paragraph's checks
  do not apply. When the facts do not say whether such a condition holds, no
  check can settle it: leave "condition" empty and write the condition into
  the claims instead ("where the crossing is at an intersection, the manual
  allows ...").

relaxes
  The ids of paragraphs shown here whose rule this paragraph relaxes,
  modifies or makes an exception to, when it could cover this case: an
  Option that allows something other than what a Standard or Guidance says,
  or a paragraph that says another does not apply, or begins "Except ...".
  The exceptions the manual names are already known: a paragraph shown with
  "exceptions it names" has them, and a paragraph marked "named as an
  exception" is one. For an ask about the case, code checks the rule first,
  and the paragraph that relaxes it only when the rule is not met; so the
  checks of such a paragraph say that it covers this case. For an ask about
  the manual, its checks are statements beside the rule's.

join
  "all" when every check of the paragraph must hold for it to be met (the
  usual case); "any" when the paragraph offers alternatives and any one of
  them is enough.

Each paragraph's heading (Standard, Guidance or Option) is printed above it,
and code gives it to its checks: you do not give one.

RULES (a reply that breaks one is sent back to you)
- One item for every paragraph under PARAGRAPHS TO DECIDE, by its id, and no
  other id.
- A paragraph that bears has at least one check; one that does not bear has
  none.
- Every check answers at least one ask, by its id.
- A check that answers an ask about the case is about the case.
- Every claim is a statement, not a question.
- When the facts describe several labelled cases of one kind, every claim
  names the one it is about, or says that it holds for each.
- An exception check belongs to a paragraph that relaxes another, or that is
  named as an exception.
- Every table, figure and section in evidence_hint exists in the manual.
- Do not name a checker.

Reply with the JSON object only: no text before or after it, and no markdown
fence."""

# The structure rules of section 3 are code; their version is part of what
# names a run folder, so a change to them is a new run even when every model
# reply comes from the cache.
ASSEMBLY = """assembly structured1: check authority = paragraph heading; condition ->
applicability check (about case) guarding the paragraph's checks; for an ask
about the case: a paragraph's checks -> conjunction (join all) or alternative
(join any) at its heading, an exception (graph EXCEPTS / except-clause link, or
the model's relaxes) -> exception merge [rule, exceptions] at the rule's
heading, the exception paragraph used only there, an exception check with no
rule that bears not used, the ask's conjunction at STANDARD unless its inputs
are only GUIDANCE or only OPTION; for an ask about the manual: every check that
answers it is a statement, and the ask is one check of its own claim requiring
them all, pointed to their paragraphs; terminal -> conjunction of the asks at
the weakest heading; an ask nothing bears on -> one check of the ask's own
claim, decided with the checker's lookups; a reply's bad hint dropped, a bad
check dropped; the best reply of a call kept"""

INSTRUCTIONS = "\n\n".join([VERSION, FACTS_TASK, SECTION_TASK, SECTION_CONTRACT, ASSEMBLY])


def code_sha() -> str:
    """sha256 of what makes a plan from the model's replies: these
    instructions, this file and the helpers it uses (parser.py, compile.py,
    and lookup.py, which reads the manual's links). The run folder is named by it, so a plan made by other code
    is never read back as this code's; the model's replies are kept by prompt,
    so the same prompts need no model call again (review of 18 Oct 2026)."""
    from . import compile as _compile, parser as _parser
    h = hashlib.sha256(INSTRUCTIONS.encode())
    from . import lookup as _lookup
    for f in (__file__, _parser.__file__, _compile.__file__, _lookup.__file__):
        h.update(Path(f).read_bytes())
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 2. Reading a reply
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)


def find_object(text: str, key: str) -> Tuple[Optional[Any], str]:
    """The reply's JSON object with `key` (else the first object, or a bare
    list for `key`), and what went wrong if there is none. Thinking that
    leaked into the reply is cut at its last `</think>`."""
    text = text or ""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = _FENCE.sub("", text).strip()
    decoder = json.JSONDecoder()
    first: Optional[Any] = None
    error = ""
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(text, i)
        except json.JSONDecodeError as e:
            error = error or f"malformed JSON: {e}"
            continue
        if isinstance(value, dict) and key in value:
            return value, ""
        if first is None and isinstance(value, dict):
            first = value
        if first is None and isinstance(value, list) and value and isinstance(value[0], dict):
            first = {key: value}
    if first is not None:
        return first, ""
    return None, error or "the reply contained no JSON object"


def _bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "yes"):
        return True
    if isinstance(v, str) and v.strip().lower() in ("false", "no"):
        return False
    return None


def _bare_id(v: Any) -> str:
    s = str(v or "").strip()
    m = re.fullmatch(r"\[\s*([^\[\]]+?)\s*\]", s)
    return m.group(1) if m else s


def _id_list(v: Any) -> List[str]:
    if isinstance(v, str):
        v = [v] if v.strip() else []
    if not isinstance(v, list):
        return []
    return [x for x in dict.fromkeys(_bare_id(i) for i in v) if x]


# --------------------------------------------------------------------------- #
# 3. Step 1: the facts and the things asked
# --------------------------------------------------------------------------- #
def _asks_in(query: str) -> List[str]:
    """The question's sentences that end in a question mark (rule C's count)."""
    return [x for x in _sentences(query or "")
            if x.rstrip("\"'”’)] ").endswith("?") and len(_words(x)) >= 3]


def build_facts_prompt(query: str, repair: Optional[Dict[str, Any]] = None) -> str:
    parts = [FACTS_TASK, "", "QUESTION", (query or "").strip()]
    if repair:
        parts += _repair_lines(repair)
    return "\n".join(parts)


def _repair_lines(repair: Dict[str, Any]) -> List[str]:
    if repair.get("reply") is None:
        return ["", "YOUR PREVIOUS REPLY COULD NOT BE READ.",
                "Problem: " + "; ".join(str(p) for p in repair.get("problems") or []),
                "Reply with the JSON object only, as described above. Keep your reasoning short."]
    return ["", "YOUR PREVIOUS REPLY WAS REJECTED.",
            "Problems:\n" + "\n".join(f"- {p}" for p in repair["problems"]),
            "Fix what is listed and keep the rest. Return the whole corrected JSON object.",
            "Your previous reply:\n" + json.dumps(repair["reply"], indent=1)[:60000]]


def read_facts(raw: str, query: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """({"facts": [GivenFact], "asked": [dict], "reply": dict}, problems).
    None when the reply cannot be read at all. Facts and asks are numbered by
    position (f1, f2, ...; a1, a2, ...): nothing else refers to the ids the
    model wrote, and the later prompts show these. "reply" is the reply with
    those ids, for a repair request."""
    data, error = find_object(raw, "asked")
    if data is None or not isinstance(data, dict):
        return None, [error or "the reply is not a JSON object"]
    problems: List[str] = []
    facts: List[GivenFact] = []
    raw_facts = data.get("facts") or []
    if not isinstance(raw_facts, list):
        problems.append('"facts" must be a list')
        raw_facts = []
    for k, f in enumerate(raw_facts, 1):
        try:
            facts.append(GivenFact.from_any(f, k))
        except CompileError as e:
            problems.append(str(e))
    facts = [GivenFact(f"f{k}", f.text) for k, f in enumerate(facts, 1)]
    problems += fact_problems(NetworkSpec(query=query, terminal="", facts=facts))

    asked: List[Dict[str, str]] = []
    raw_asked = data.get("asked")
    if not isinstance(raw_asked, list) or not raw_asked:
        problems.append('"asked" is missing or empty: list each thing the question asks')
        raw_asked = []
    for a in raw_asked:
        if not isinstance(a, dict):
            problems.append(f"asked item number {len(asked) + 1} is not an object")
            continue
        aid = f"a{len(asked) + 1}"
        item = {"id": aid, "ask": str(a.get("ask") or "").strip(),
                "about": str(a.get("about") or "").strip().lower(),
                "claim": str(a.get("claim") or "").strip()}
        if not item["ask"]:
            problems.append(f"asked {aid!r} has no \"ask\"")
        if item["about"] not in ("case", "manual"):
            problems.append(f"asked {aid!r}: about {item['about']!r} is not \"case\" or \"manual\"")
        if not item["claim"]:
            problems.append(f"asked {aid!r} has no claim")
        elif item["claim"].rstrip().endswith("?"):
            problems.append(f"asked {aid!r}: the claim is a question; write it as a statement")
        asked.append(item)
    n_q = len(_asks_in(query))
    if asked and len(asked) < n_q:
        problems.append(f"\"asked\" has {len(asked)} item(s), but the question has {n_q} "
                        f"questions; give one item per thing it asks")
    reply = {"facts": [{"id": f.id, "fact": f.text} for f in facts], "asked": [dict(a) for a in asked]}
    return {"facts": facts, "asked": asked, "reply": reply}, problems


# --------------------------------------------------------------------------- #
# 4. The graph's additions, and the calls
# --------------------------------------------------------------------------- #
def graph_hooks(kg) -> Dict[str, Optional[Callable]]:
    """What this parser reads from the VINE graph (`mrag.kg_vine.VineKG`):
    exceptions_of(chunk) -> ids (the exceptions it names), options_of(chunk)
    -> ids (the Option paragraphs of its section, for a Standard or Guidance),
    record_of(id) -> the paragraph's record. All None without a graph."""
    none = {"exceptions_of": None, "options_of": None, "record_of": None}
    if kg is None or not hasattr(kg, "_chunk_sentences"):
        return none
    from .lookup import ManualView
    view = ManualView(kg)

    def exceptions_of(chunk: Dict[str, Any]) -> List[str]:
        return list(view.links(chunk).exception_ids)

    def options_of(chunk: Dict[str, Any]) -> List[str]:
        sec = str(chunk.get("section_id") or "")
        out: List[str] = []
        for n in view.links(chunk).options_here:
            out += [x for x in kg.chunks_for_paragraph(sec, n) if x not in out]
        return out

    def record_of(cid: str) -> Optional[Dict[str, Any]]:
        rec = getattr(kg, "_chunk", {}).get(cid)
        return dict(rec) if rec else None

    return {"exceptions_of": exceptions_of, "options_of": options_of, "record_of": record_of}


def _normative(c: Dict[str, Any]) -> bool:
    return str(c.get("content_type") or "") in NORMATIVE


def _ordinal(c: Dict[str, Any]) -> int:
    try:
        return int(c.get("ordinal") or 0)
    except (TypeError, ValueError):
        return 0


def _additions(chunks: Sequence[Dict[str, Any]],
               exceptions_of: Optional[Callable], options_of: Optional[Callable],
               record_of: Optional[Callable]) -> List[Dict[str, Any]]:
    """Normative paragraphs the graph links to the retrieved ones, that search
    did not return: [{"chunk": record, "home": rule id, "why": text}].

    The exceptions a retrieved provision names first (EXCEPTIONS_PER_RULE for
    one rule, EXCEPTIONS_PER_QUESTION in all), then the Option paragraphs of a
    retrieved Standard's or Guidance's section -- the one printed nearest after
    such a rule first (OPTIONS_PER_SECTION, OPTIONS_PER_QUESTION). Only one
    step from what search returned."""
    if record_of is None:
        return []
    shown = {str(c.get("chunk_id")) for c in chunks if c.get("chunk_id")}
    out: List[Dict[str, Any]] = []
    taken: set = set()

    def take(cid: str, home: str, why: str) -> bool:
        if not cid or cid in shown or cid in taken:
            return False
        rec = record_of(cid)
        if not rec or not _normative(rec):
            return False
        rec = {**rec, "chunk_id": cid, "source": rec.get("source") or "graph"}
        taken.add(cid)
        out.append({"chunk": rec, "home": home, "why": why})
        return True

    def paragraphs(ids: Iterable[str]) -> List[List[str]]:
        """The ids grouped by the paragraph they belong to (a list's items are
        one paragraph), in order: the caps below count paragraphs."""
        groups: Dict[Tuple, List[str]] = {}
        for x in ids:
            rec = record_of(x) if x not in shown else None
            if not rec:
                continue
            key = (str(rec.get("section_id") or ""), str(rec.get("parent_id") or ""), _ordinal(rec)) \
                if rec.get("ordinal") not in (None, "") else ("", "", x)
            groups.setdefault(key, []).append(x)
        return list(groups.values())

    rules = [c for c in chunks if _normative(c)]
    n_exc = 0
    if exceptions_of is not None:
        for c in rules:
            try:
                named = list(exceptions_of(c) or [])
            except Exception as e:                                # noqa: BLE001
                log.warning("exceptions of %s could not be read: %r", c.get("chunk_id"), e)
                named = []
            k = 0
            for group in paragraphs(dict.fromkeys(str(n) for n in named)):
                if n_exc >= EXCEPTIONS_PER_QUESTION or k >= EXCEPTIONS_PER_RULE:
                    break
                got = [take(x, str(c["chunk_id"]), f"named as an exception by [{c['chunk_id']}]")
                       for x in group]
                if any(got):
                    k += 1
                    n_exc += 1
    if options_of is not None:
        per_sec: Dict[str, List[Tuple[int, int, str, str]]] = {}
        for c in rules:
            if str(c.get("content_type")) not in ("Standard", "Guidance"):
                continue
            try:
                opts = list(options_of(c) or [])
            except Exception as e:                                # noqa: BLE001
                log.warning("options of %s could not be read: %r", c.get("chunk_id"), e)
                opts = []
            sec = str(c.get("section_id") or "")
            n_rule = _ordinal(c)
            for x in opts:
                rec = record_of(x) if x not in shown else None
                if not rec:
                    continue
                n_opt = _ordinal(rec)
                # printed after the rule: nearest first; before it: after all of those
                key = (0, n_opt - n_rule) if n_opt > n_rule else (1, n_rule - n_opt)
                per_sec.setdefault(sec, []).append((*key, str(x), str(c["chunk_id"])))
        n_opt_all = 0
        for sec in per_sec:
            k = 0
            ranked = sorted(per_sec[sec])
            home_of = {}
            for _a, _b, x, home in ranked:
                home_of.setdefault(x, home)              # the rule it is nearest after
            for group in paragraphs(dict.fromkeys(x for _a, _b, x, _h in ranked)):
                if n_opt_all >= OPTIONS_PER_QUESTION or k >= OPTIONS_PER_SECTION:
                    break
                home = home_of[group[0]]
                got = [take(x, home, f"an Option of the same section as [{home}]") for x in group]
                if any(got):
                    k += 1
                    n_opt_all += 1
    return out


@dataclass
class Call:
    """One section call: what it shows, and the paragraphs it decides."""
    items: List[Dict[str, Any]] = field(default_factory=list)
    decide: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)


def _display_order(items: Sequence[Dict[str, Any]]) -> List[str]:
    """The ids in the order `format_provisions` prints them."""
    order: List[str] = []
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    seen: set = set()
    for c in items:
        cid = str(c.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        sec = str(c.get("section_id") or "")
        if sec not in by_sec:
            order.append(sec)
            by_sec[sec] = []
        by_sec[sec].append(c)
    return [str(c["chunk_id"]) for sec in order for c in sorted(by_sec[sec], key=_sort_key)]


def plan_calls(chunks: Sequence[Dict[str, Any]], added: Sequence[Dict[str, Any]] = (),
               cap: int = GROUP_CAP) -> List[Call]:
    """The section calls, in retrieval order. Each retrieved section goes
    whole into one call with its context (Support, table rows, figure
    descriptions) and the paragraphs the graph added for its rules; small
    sections share a call up to `cap` paragraphs to decide; a larger section
    is split into near-equal parts, each of which shows the whole section and
    decides its own part. A section with nothing to decide goes along with the
    call it falls in, as context."""
    home_of_added: Dict[str, List[Dict[str, Any]]] = {}
    sec_of: Dict[str, str] = {}
    seen: set = set()
    order: List[str] = []
    by_sec: Dict[str, List[Dict[str, Any]]] = {}
    for c in chunks:
        cid = str(c.get("chunk_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        sec = str(c.get("section_id") or "")
        sec_of[cid] = sec
        if sec not in by_sec:
            order.append(sec)
            by_sec[sec] = []
        by_sec[sec].append(c)
    for a in added:
        sec = sec_of.get(a["home"], str(a["chunk"].get("section_id") or ""))
        home_of_added.setdefault(sec, []).append(a["chunk"])
    for sec in home_of_added:
        if sec not in by_sec:
            order.append(sec)
            by_sec[sec] = []

    calls: List[Call] = []
    cur = Call()                        # the call being filled
    waiting = Call()                    # context of sections with nothing to decide, for the next call

    def close() -> None:
        nonlocal cur
        if cur.decide:
            calls.append(cur)
        cur = Call()

    for sec in order:
        items = by_sec[sec] + home_of_added.get(sec, [])
        decide = [str(c["chunk_id"]) for c in items if _normative(c)]
        context = [c for c in items if not _normative(c)]
        if not decide:
            target = cur if cur.decide else waiting
            target.items += context
            target.sections.append(sec)
            continue
        if len(decide) > cap:
            close()
            k = math.ceil(len(decide) / cap)
            size = math.ceil(len(decide) / k)
            ordered = [x for x in _display_order(items) if x in set(decide)]
            by_id = {str(c["chunk_id"]): c for c in items}
            first = len(calls)
            for j in range(k):
                part = ordered[j * size:(j + 1) * size]
                if part:
                    # the whole section is shown, so a paragraph can be read with the
                    # rest of its section and name one decided in the other part
                    calls.append(Call(items=list(items), decide=list(part), sections=[sec]))
            if waiting.items:
                calls[first].items = waiting.items + calls[first].items
                calls[first].sections = waiting.sections + calls[first].sections
                waiting = Call()
            continue
        if cur.decide and len(cur.decide) + len(decide) > cap:
            close()
        if not cur.decide and waiting.items:
            cur.items += waiting.items
            cur.sections += waiting.sections
            waiting = Call()
        cur.items += items
        cur.decide += decide
        cur.sections.append(sec)
    close()
    if waiting.items and calls:
        calls[-1].items += waiting.items
        calls[-1].sections += waiting.sections
    for call in calls:
        keep = set(call.decide)
        call.decide = [x for x in _display_order(call.items) if x in keep]
    return calls


# --------------------------------------------------------------------------- #
# 5. Step 2: one section call
# --------------------------------------------------------------------------- #
def _ref(c: Dict[str, Any]) -> str:
    """How a paragraph is named in a claim: "Section 2B.46, paragraph 6"."""
    sec = str(c.get("section_id") or "")
    parent = str(c.get("parent_id") or "")
    if parent.lower().startswith(("table ", "figure ")):
        return f"note {c.get('item')} to {parent}" if c.get("item") else f"the note to {parent}"
    out = f"Section {sec}"
    if c.get("ordinal") not in (None, ""):
        out += f", paragraph {c.get('ordinal')}"
    if c.get("item"):
        out += f", item {c.get('item')}"
    return out


def _heading(c: Dict[str, Any]) -> str:
    return str(c.get("content_type") or "").upper()


def _table_of(c: Dict[str, Any]) -> str:
    refs = list(c.get("table_refs") or [])
    name = str(refs[0] if refs else c.get("parent_id") or c.get("section_id") or "")
    return name if name.lower().startswith("table") else f"Table {name}"


def shown_items(items: Sequence[Dict[str, Any]], rows: int = ROWS_PER_TABLE
                ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """The items a call prints: every item, except that only the first `rows`
    table rows of each table are kept. Returns (items, {table: rows left out})."""
    kept: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}
    left: Dict[str, int] = {}
    for c in items:
        if str(c.get("content_type") or "") == "TableRow":
            t = _table_of(c)
            seen[t] = seen.get(t, 0) + 1
            if seen[t] > rows:
                left[t] = left.get(t, 0) + 1
                continue
        kept.append(c)
    return kept, left


def build_section_prompt(query: str, facts: Sequence[GivenFact], asked: Sequence[Dict[str, str]],
                         call: Call, exceptions: Dict[str, List[str]],
                         tags: Dict[str, str], figures: Sequence[Dict[str, Any]] = (),
                         repair: Optional[Dict[str, Any]] = None) -> str:
    by_id = {str(c["chunk_id"]): c for c in call.items}
    items, rows_left = shown_items(call.items)
    facts_block = "\n".join(f"[{f.id}] {f.text}" for f in facts) or "(none: the question states no facts about a case)"
    asked_block = "\n".join(
        f"[{a['id']}] about the {a['about']}: {a['ask']}\n     to be decided: {a['claim']}" for a in asked)
    decide_block = "\n".join(
        f"[{x}]  {str(by_id[x].get('content_type'))}, {_ref(by_id[x])}"
        + (f"  -- {tags[x]}" if tags.get(x) else "") for x in call.decide)
    shown_exc = {k: [x for x in v if x in by_id] for k, v in exceptions.items() if k in by_id}
    parts = [SECTION_TASK, "", "QUESTION", (query or "").strip(), "",
             "FACTS OF THE CASE (listed by the earlier step; every checker is shown these)",
             facts_block, "", "WHAT IS ASKED", asked_block, "",
             "PROVISIONS (ids in square brackets)", "",
             format_provisions(items, {k: v for k, v in shown_exc.items() if v})]
    if rows_left:
        parts += ["", "(Also retrieved, not shown here: "
                  + "; ".join(f"{n} more row{'s' if n > 1 else ''} of {t}" for t, n in rows_left.items())
                  + ". The rows above show the table's printed column headings; the checkers read "
                    "the values from the table itself.)"]
    figs = format_figures(figures)
    if figs:
        parts += ["", "FIGURES THE VISION MODEL CAN BE GIVEN", figs]
    parts += ["", f"PARAGRAPHS TO DECIDE ({len(call.decide)})", decide_block]
    elsewhere = [x for x in _display_order(items) if x not in set(call.decide) and _normative(by_id[x])]
    if elsewhere:
        parts += [f"(The other Standard, Guidance and Option paragraphs shown above, "
                  f"{', '.join(f'[{x}]' for x in elsewhere)}, are decided in another call: give them no "
                  f"item. You may name them in \"relaxes\".)"]
    parts += ["", SECTION_CONTRACT]
    if repair:
        parts += _repair_lines(repair)
    return "\n".join(parts)


def _check_problem_label(pid: str, k: int) -> str:
    return f"[{pid}] check {k}"


def read_section(raw: str, call: Call, asked: Sequence[Dict[str, str]],
                 facts: Sequence[GivenFact], query: str,
                 known_exceptions: set,
                 check_ref: Optional[Callable[[str, str], bool]] = None,
                 tables: Optional[Dict[str, List[Any]]] = None,
                 ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]], List[str], List[str]]:
    """Read one section reply: (the reply object, {paragraph id: decision},
    problems, notes). A decision is {"bears", "why", "condition", "relaxes",
    "join", "checks": [{"claim", "about", "answers", "type", "evidence_hint"}],
    "bad_checks": [indexes of checks with a problem]}. None when the reply
    cannot be read."""
    data, error = find_object(raw, "paragraphs")
    if data is None or not isinstance(data, dict):
        return None, {}, [error or "the reply is not a JSON object"], []
    items = data.get("paragraphs")
    if not isinstance(items, list):
        return data, {}, ['"paragraphs" must be a list, one item per paragraph to decide'], []
    by_id = {str(c["chunk_id"]): c for c in call.items}
    ask_about = {a["id"]: a["about"] for a in asked}
    problems: List[str] = []
    notes: List[str] = []
    out: Dict[str, Dict[str, Any]] = {}
    cases = several_cases(NetworkSpec(query=query, terminal="", facts=list(facts)))

    for k, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append(f"paragraph item number {k} is not an object")
            continue
        pid = _bare_id(it.get("id"))
        if pid not in call.decide:
            if pid in by_id and _normative(by_id[pid]):
                notes.append(f"[{pid}] was decided in this call, but another call decides it; left out")
            else:
                problems.append(f"item {k}: {pid!r} is not one of the paragraphs to decide")
            continue
        if pid in out:
            problems.append(f"[{pid}] is listed twice; give one item per paragraph")
            continue
        bears = _bool(it.get("bears"))
        d: Dict[str, Any] = {"bears": bool(bears), "why": str(it.get("why") or "").strip(),
                             "condition": "", "relaxes": [], "join": "all", "checks": [],
                             "bad_checks": []}
        out[pid] = d
        if bears is None:
            problems.append(f"[{pid}]: \"bears\" must be true or false")
            continue
        raw_checks = it.get("checks") or []
        if not isinstance(raw_checks, list):
            problems.append(f"[{pid}]: \"checks\" must be a list")
            raw_checks = []
        if not bears:
            if raw_checks:
                problems.append(f"[{pid}]: it does not bear, but it has checks; give checks only "
                                f"for a paragraph that bears (or say that it bears)")
            continue
        if not raw_checks:
            problems.append(f"[{pid}]: it bears, but it has no check; give the checks it gives "
                            f"for this case (or say that it does not bear)")
        cond = it.get("condition")
        d["condition"] = cond.strip() if isinstance(cond, str) else ""
        if d["condition"].endswith("?"):
            problems.append(f"[{pid}]: the condition is a question; write it as a statement about the case")
        elif d["condition"] and not facts:
            problems.append(f"[{pid}]: it has a condition, but the question states no facts about a case, "
                            f"so no check can settle it; leave \"condition\" empty and write the "
                            f"condition into the claims (\"where ...\")")
            d["condition"] = ""
        rel = _id_list(it.get("relaxes"))
        for r in rel:
            if r == pid or r not in by_id or not _normative(by_id[r]):
                notes.append(f"[{pid}] relaxes {r!r}: not a paragraph shown in its call; left out")
        d["relaxes"] = [r for r in rel if r != pid and r in by_id and _normative(by_id[r])]
        join = str(it.get("join") or "all").strip().lower()
        if join not in ("all", "any"):
            problems.append(f"[{pid}]: join {join!r} is not \"all\" or \"any\"")
            join = "all"
        d["join"] = join

        for j, ch in enumerate(raw_checks, 1):
            label = _check_problem_label(pid, j)
            bad = False
            if not isinstance(ch, dict):
                problems.append(f"{label} is not an object")
                d["checks"].append({})
                d["bad_checks"].append(j - 1)
                continue
            claim = str(ch.get("claim") or "").strip()
            about = str(ch.get("about") or "").strip().lower()
            answers = _id_list(ch.get("answers"))
            typ = str(ch.get("type") or "").strip().lower()
            hints = ch.get("evidence_hint") or []
            if not claim:
                problems.append(f"{label} has no claim")
                bad = True
            if about not in ("case", "manual"):
                problems.append(f"{label}: about {about!r} is not \"case\" or \"manual\"")
                bad = True
            elif about == "case" and not facts:
                problems.append(f"{label} is about the case, but the question states no facts "
                                f"about a case, so nothing can show it; write it about the manual")
                bad = True
            unknown = [a for a in answers if a not in ask_about]
            if not answers:
                problems.append(f"{label} answers no ask; name the asks (a1, ...) it helps answer")
                bad = True
            elif unknown:
                problems.append(f"{label}: answers {unknown}, which are not asks; the asks are "
                                f"{sorted(ask_about)}")
                bad = True
            elif about == "manual" and any(ask_about[a] == "case" for a in answers):
                case_asks = [a for a in answers if ask_about[a] == "case"]
                problems.append(f"{label} answers {case_asks}, which asks whether the case meets "
                                f"the manual, but the claim is about the manual: a statement of what "
                                f"the manual says is TRUE however the case is built. Write it about "
                                f"the case (TRUE when the case meets it), or answer only asks about "
                                f"the manual")
                bad = True
            if typ not in _TYPE_VALUES:
                problems.append(f"{label}: type {typ!r} is not one of {sorted(_TYPE_VALUES)}")
                bad = True
            elif typ == ObligationType.EXCEPTION.value and not d["relaxes"] and pid not in known_exceptions:
                problems.append(f"{label} is an exception check, but [{pid}] relaxes no paragraph "
                                f"shown; list the paragraph it relaxes in \"relaxes\", or give the "
                                f"check another type")
                bad = True
            if not isinstance(hints, list) or not all(isinstance(h, dict) for h in hints):
                problems.append(f"{label}: evidence_hint must be a list of objects")
                hints = []
                bad = True
            for head, labels in cases.items():
                if typ != ObligationType.DEFINITIONAL.value and claim and \
                        not claim_names_case(claim, head, labels):
                    kind = head.capitalize()
                    problems.append(f"{label}: the facts describe several of one kind "
                                    f"({', '.join(f'{kind} {x}' for x in labels)}), and the claim names "
                                    f"none of them; say which one it is about (for example \"for {kind} "
                                    f"{labels[0]}\"), or that it holds for each of them")
                    bad = True
            d["checks"].append({"claim": claim, "about": about, "answers": answers, "type": typ,
                                "evidence_hint": hints})
            if bad:
                d["bad_checks"].append(j - 1)

    missing = [x for x in call.decide if x not in out]
    if missing:
        problems.append(f"no item for {', '.join(f'[{x}]' for x in missing)}; give one item for "
                        f"every paragraph to decide")

    # the references to the manual, and the claims, through the parser's own checks
    temp: List[Obligation] = []
    where: Dict[str, str] = {}
    for pid, d in out.items():
        for j, ch in enumerate(d["checks"]):
            if j in d["bad_checks"] or not ch:
                continue
            tid = f"t{len(temp) + 1}"
            where[tid] = _check_problem_label(pid, j + 1)
            try:
                temp.append(Obligation.from_dict({
                    "id": tid, "claim": ch["claim"], "type": ch["type"],
                    "authority": _heading(by_id[pid]), "evidence_hint": ch["evidence_hint"],
                    "source_chunk": pid}))
            except (CompileError, AttributeError, TypeError) as e:
                problems.append(f"{where[tid]}: {e}")
                d["bad_checks"].append(j)
        if d["condition"] and d["condition"].rstrip().endswith("?"):
            d["condition"] = ""
    if temp:
        spec = NetworkSpec(query=query, terminal=temp[0].id, obligations=temp)
        found: Dict[str, List[str]] = {}
        for p in grounding_problems(spec, call.items, check_ref, tables):
            m = re.match(r"^(t\d+):\s*(.*)$", p, re.S)
            if not m or m.group(1) not in where:
                continue
            label = where[m.group(1)]
            problems.append(f"{label}: {m.group(2)}")
            found.setdefault(label, []).append(m.group(2))
        for label, said in found.items():
            pid, j = re.match(r"^\[(.+)\] check (\d+)$", label).groups()
            j = int(j) - 1
            if all(_HINT_PROBLEM.search(x) for x in said):
                # only its hints are wrong: the check stands, with the hints that are right
                ch = out[pid]["checks"][j]
                ch["evidence_hint"] = [h for h in ch["evidence_hint"]
                                       if _hint_ok(h, ch["evidence_hint"], pid, by_id[pid], call.items,
                                                   check_ref, tables)]
            elif j not in out[pid]["bad_checks"]:
                out[pid]["bad_checks"].append(j)
    return data, out, problems, notes


# what `parser.grounding_problems` says about an evidence hint (not about the claim)
_HINT_PROBLEM = re.compile(r"evidence_hint|hint needs a table hint|is not a column of|"
                           r"is not a chart of|is not a sheet of")


def _hint_ok(h: Dict[str, Any], hints: Sequence[Dict[str, Any]], pid: str, chunk: Dict[str, Any],
             items: Sequence[Dict[str, Any]], check_ref, tables) -> bool:
    """Whether one hint passes the parser's checks on references (a column,
    part or sheet hint together with the table hints beside it)."""
    kind = str(h.get("type", "")).lower()
    test = [h] if kind not in ("column", "part", "sheet") else \
        [x for x in hints if str(x.get("type", "")).lower() == "table"] + [h]
    try:
        ob = Obligation.from_dict({"id": "h1", "claim": "A statement.", "type": "classification",
                                   "authority": _heading(chunk), "evidence_hint": test,
                                   "source_chunk": pid})
    except (CompileError, AttributeError, TypeError):
        return False
    return not grounding_problems(NetworkSpec(query="", terminal="h1", obligations=[ob]),
                                  items, check_ref, tables)


# --------------------------------------------------------------------------- #
# 6. Step 3: code builds the plan
# --------------------------------------------------------------------------- #
def _merge_heading(headings: Iterable[str]) -> str:
    """The parser's rule for a merge: STANDARD unless it combines only
    GUIDANCE or only OPTION items."""
    hs = set(headings)
    if hs == {"GUIDANCE"}:
        return "GUIDANCE"
    if hs == {"OPTION"}:
        return "OPTION"
    return "STANDARD"


def _weakest(headings: Iterable[str]) -> str:
    """The weakest heading among the inputs. A merge at the weakest heading
    lets no input's FALSE count as "does not refute" (execute._non_blocking
    only does that for an input weaker than the merge)."""
    hs = set(headings)
    if "OPTION" in hs:
        return "OPTION"
    if "GUIDANCE" in hs:
        return "GUIDANCE"
    return "STANDARD"


def _joined(claims: Sequence[str], sep: str, fallback: str, most: int = 400) -> str:
    text = sep.join(c.rstrip(". ") for c in claims)
    return text if len(text) <= most else fallback


def assemble(query: str, facts: Sequence[GivenFact], asked: Sequence[Dict[str, str]],
             decisions: Sequence[Tuple[str, Dict[str, Any]]], by_id: Dict[str, Dict[str, Any]],
             graph_exceptions: Dict[str, List[str]]) -> Tuple[Optional[NetworkSpec], List[str], List[str]]:
    """The plan from the decisions: (spec, open problems, notes).

    `decisions` are (paragraph id, decision) in the order the paragraphs were
    shown; a decision's checks listed in its "bad_checks" are not used.
    `graph_exceptions` is {rule id: ids of the exceptions it names}.

    First the structure is worked out from the decisions alone, then only
    what it uses is made: no check, condition or merge is made that the
    terminal does not depend on.

      for every thing asked, for every paragraph that bears and has a check
      for it (in the order shown):
        part      its checks for that ask: one check, or a conjunction ("all")
                  or alternative ("any") of them at the paragraph's heading
        unit      the part; or, when paragraphs that bear relax it (the
                  manual's named exceptions, or the model's "relaxes") and
                  have a check for that ask, an exception merge [part,
                  exception parts...] at the paragraph's heading. A paragraph
                  that relaxes one that bears is used only there.
      per ask     its units; two or more -> a conjunction with the ask's claim
      terminal    the asks; two or more -> a conjunction of them
      condition   a paragraph's condition is an applicability check about the
                  case, decided first; the paragraph's checks require it and
                  are guarded on it being TRUE
    Merge headings: the paragraph's for a part and an exception merge; for an
    ask about the case, the parser's rule (`_merge_heading`: a Guidance not
    followed, or an Option not taken, beside a Standard does not make the case
    fail); for the terminal, the weakest heading among the asks (`_weakest`),
    so that one ask's answer never changes because another ask is in the
    question.

    An ask about the MANUAL is answered by statements of what the manual says
    for this case. Each is TRUE or FALSE, but which way it points for the ask
    is not readable by code: "the manual requires the sign on the right" and
    "the manual allows it on the left here" pull opposite ways, so no merge of
    them is right for "may it go on the left?". So every check that answers
    such an ask (a paragraph that relaxes another included) is a statement,
    and the ask is ONE check of its own claim that requires them all: its
    checker sees them as established, is pointed to their paragraphs, and
    decides the ask (review of 18 Oct 2026)."""
    notes: List[str] = []
    open_: List[str] = []
    about_of = {a["id"]: a["about"] for a in asked}
    bearing: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for pid, d in decisions:
        bad = set(d.get("bad_checks") or [])
        good = [c for j, c in enumerate(d.get("checks") or []) if j not in bad and c]
        if d.get("bears") and good and pid in by_id:
            bearing[pid] = {**d, "checks": good}
            order.append(pid)

    # exceptions: (E, P) when E relaxes P, both bearing
    def exception_edges(both_ways: bool = False) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for p in order:
            for e in graph_exceptions.get(p, []):
                if e in bearing and e != p and (e, p) not in out:
                    out.append((e, p))
        for e in order:
            for p in bearing[e].get("relaxes") or []:
                if p in bearing and p != e and (e, p) not in out:
                    out.append((e, p))
        if both_ways:
            return out
        # two paragraphs said to relax each other: both are taken as rules
        return [x for x in out if (x[1], x[0]) not in out]

    # An exception check says that an exception covers the case. For an ask
    # about the case, without a rule that bears for it to relax, it would stand
    # on its own, where "it does not cover the case" would read as the case
    # failing: it is not used there. (Repeated, since leaving a paragraph out can
    # leave another without a rule.)
    for _round in range(len(order) + 1):
        relaxing = {e for e, _p in exception_edges()}
        changed = False
        for pid in list(order):
            if pid in relaxing:
                continue
            keep = []
            for c in bearing[pid]["checks"]:
                if c["type"] == ObligationType.EXCEPTION.value:
                    left = [x for x in c["answers"] if about_of.get(x) != "case"]
                    if left != c["answers"]:
                        c = {**c, "answers": left}
                    if not left:
                        continue
                keep.append(c)
            if keep == bearing[pid]["checks"]:
                continue
            changed = True
            notes.append(f"[{pid}]: its exception check(s) are not used for an ask about the case: "
                         f"no paragraph it relaxes bears")
            if keep:
                bearing[pid] = {**bearing[pid], "checks": keep}
            else:
                del bearing[pid]
                order.remove(pid)
        if not changed:
            break
    edges = exception_edges()
    raw = exception_edges(both_ways=True)
    mutual = sorted({tuple(sorted(x)) for x in raw if (x[1], x[0]) in raw})
    if mutual:
        notes.append(f"paragraphs said to relax each other were taken as rules of their own: {mutual}")
    rules_of: Dict[str, List[str]] = {}
    excs_of: Dict[str, List[str]] = {}
    for e, p in edges:
        rules_of.setdefault(e, []).append(p)
        excs_of.setdefault(p, []).append(e)
    for p in excs_of:
        excs_of[p].sort(key=order.index)

    # which checks of a paragraph answer which ask
    answers_of: Dict[Tuple[str, str], List[int]] = {}
    for pid in order:
        for j, ch in enumerate(bearing[pid]["checks"]):
            for aid in ch["answers"]:
                answers_of.setdefault((pid, aid), []).append(j)

    def has(pid: str, aid: str) -> bool:
        return bool(answers_of.get((pid, aid)))

    def single_exception_check(pid: str, aid: str) -> bool:
        js = answers_of.get((pid, aid)) or []
        return len(js) == 1 and bearing[pid]["checks"][js[0]]["type"] == ObligationType.EXCEPTION.value

    # pass 1: the structure, by paragraph
    plan: Dict[str, List[Tuple[str, List[str]]]] = {}
    for a in asked:
        aid = a["id"]
        units: List[Tuple[str, List[str]]] = []
        if about_of.get(aid) == "manual":
            # statements of what the manual says: every paragraph's checks for it
            # (they feed one check of the ask's own claim, below)
            plan[aid] = [(pid, []) for pid in order if has(pid, aid)]
            continue
        for pid in order:
            if pid in rules_of:
                if all(p in rules_of for p in rules_of[pid]) and has(pid, aid):
                    notes.append(f"[{pid}] relaxes only paragraphs that themselves relax another "
                                 f"({', '.join(f'[{p}]' for p in rules_of[pid])}); an exception to an "
                                 f"exception is not used, so its checks for {aid} are not used")
                    continue
                if has(pid, aid) and not any(has(p, aid) for p in rules_of[pid]):
                    notes.append(f"[{pid}] relaxes {', '.join(f'[{p}]' for p in rules_of[pid])}, which "
                                 f"has no check for {aid}; its checks for {aid} are not used")
                continue
            if not has(pid, aid):
                continue
            excs = [e for e in excs_of.get(pid, []) if has(e, aid)]
            if excs and single_exception_check(pid, aid):
                notes.append(f"[{pid}]'s check for {aid} is itself typed exception; the paragraphs "
                             f"that relax it ({', '.join(f'[{e}]' for e in excs)}) are not merged with it")
                excs = []
            units.append((pid, excs))
        plan[aid] = units

    used: Dict[str, set] = {}
    for aid, units in plan.items():
        for pid, excs in units:
            for x in [pid] + excs:
                used.setdefault(x, set()).update(answers_of[(x, aid)])

    # pass 2: what the structure uses, in the order shown
    obligations: List[Obligation] = []
    merges: List[MergeSpec] = []
    heading: Dict[str, str] = {}
    claim_of: Dict[str, str] = {}
    check_id: Dict[Tuple[str, int], str] = {}
    n_cond = 0

    def next_check_id() -> str:
        return f"o{sum(1 for o in obligations if o.id.startswith('o')) + 1}"

    for pid in order:
        if pid not in used:
            continue
        d, c = bearing[pid], by_id[pid]
        auth = _heading(c)
        guard, req = None, []
        if d.get("condition"):
            n_cond += 1
            cid = f"c{n_cond}"
            obligations.append(Obligation(
                id=cid, claim=f"The condition under which {_ref(c)} applies holds for this case: "
                              f"{d['condition'].rstrip('. ')}.",
                type=ObligationType.APPLICABILITY.value, authority=auth, source_chunk=pid,
                about="case" if facts else ""))
            guard, req = {"state": cid, "status": "TRUE"}, [cid]
        for j, ch in enumerate(d["checks"]):
            if j not in used[pid]:
                continue
            oid = next_check_id()
            obligations.append(Obligation.from_dict({
                "id": oid, "claim": ch["claim"], "type": ch["type"], "authority": auth,
                "requires": req, "guard": guard, "evidence_hint": ch["evidence_hint"],
                "source_chunk": pid, "about": ch["about"]}))
            heading[oid], claim_of[oid] = auth, ch["claim"]
            check_id[(pid, j)] = oid

    def new_merge(kind: str, inputs: List[str], claim: str, authority: str) -> str:
        mid = f"m{len(merges) + 1}"
        merges.append(MergeSpec(id=mid, claim=claim, kind=kind, inputs=list(inputs),
                                authority=authority))
        heading[mid], claim_of[mid] = authority, claim
        return mid

    parts: Dict[Tuple[str, str], str] = {}

    def part(pid: str, aid: str) -> str:
        key = (pid, aid)
        if key not in parts:
            ids = [check_id[(pid, j)] for j in answers_of[key]]
            ref = _ref(by_id[pid])
            if len(ids) == 1:
                parts[key] = ids[0]
            elif bearing[pid].get("join") == "any":
                parts[key] = new_merge("alternative", ids,
                                       _joined([claim_of[i] for i in ids], " or ",
                                               f"At least one check from {ref} holds"),
                                       _heading(by_id[pid]))
            else:
                parts[key] = new_merge("conjunction", ids,
                                       _joined([claim_of[i] for i in ids], " and ",
                                               f"Every check from {ref} holds"),
                                       _heading(by_id[pid]))
        return parts[key]

    asked_items: List[AskedItem] = []
    nodes: List[str] = []
    ask_claims: List[str] = []
    for a in asked:
        aid = a["id"]
        inputs: List[str] = []
        if about_of.get(aid) == "manual" and plan[aid]:
            # An ask about the MANUAL: its checks are statements of what the manual
            # says for this case, each TRUE or FALSE, and which way each points for
            # the ask (does "the manual requires the right side" answer "may it go
            # on the left?") is not something code can read. So the ask is one check
            # of its own claim, made after them: its checker is shown them as
            # established and is pointed to their paragraphs (review of 18 Oct 2026).
            req = [check_id[(pid, j)] for pid, _e in plan[aid] for j in answers_of[(pid, aid)]]
            plain: List[Dict[str, str]] = []
            lists: List[Dict[str, str]] = []
            for pid, _e in plan[aid]:
                c = by_id[pid]
                if (c.get("ordinal") not in (None, "") and c.get("section_id")
                        and not str(c.get("parent_id") or "").lower().startswith(("table ", "figure "))):
                    h = {"type": "section", "id": str(c["section_id"]), "paragraph": str(c["ordinal"])}
                    # a list paragraph brings all its items, and the checker is given at
                    # most a few pointed pieces: the other paragraphs go first
                    target = lists if c.get("item") else plain
                    if h not in plain and h not in lists:
                        target.append(h)
            oid = next_check_id()
            obligations.append(Obligation.from_dict({
                "id": oid, "claim": a["claim"], "type": ObligationType.CLASSIFICATION.value,
                "authority": "STANDARD", "requires": list(dict.fromkeys(req)), "evidence_hint": plain + lists,
                "source_chunk": "", "about": "manual",
                # a model reads it: never the rule evaluator, even when the claim
                # reads like a comparison ("the manual allows no more than 40 yards")
                "verifier": "llm"}))
            heading[oid], claim_of[oid] = "STANDARD", a["claim"]
            nodes.append(oid)
            ask_claims.append(a["claim"])
            asked_items.append(AskedItem(id=aid, ask=a["ask"], answered_by=[oid]))
            continue
        for pid, excs in plan[aid]:
            base = part(pid, aid)
            if excs:
                refs = ", ".join(_ref(by_id[e]) for e in excs)
                unit = new_merge("exception", [base] + [part(e, aid) for e in excs],
                                 f"{claim_of[base].rstrip('. ')}, or {refs} covers this case",
                                 _heading(by_id[pid]))
            else:
                unit = base
            if unit not in inputs:
                inputs.append(unit)
        if not inputs:
            # nothing shown bears on this ask: it is checked as one claim, by a
            # checker that can look further in the manual itself
            oid = next_check_id()
            obligations.append(Obligation(
                id=oid, claim=a["claim"], type=ObligationType.CLASSIFICATION.value,
                authority="STANDARD", about=a["about"] if facts else "manual", verifier="llm"))
            heading[oid], claim_of[oid] = "STANDARD", a["claim"]
            open_.append(f"asked {aid!r}: no paragraph shown bears on it; it is checked as one claim "
                         f"(\"{a['claim'][:120]}\"), with the checker's own lookups")
            node = oid
        elif len(inputs) == 1:
            node = inputs[0]
        else:
            node = new_merge("conjunction", inputs, a["claim"], _merge_heading(heading[i] for i in inputs))
        nodes.append(node)
        ask_claims.append(a["claim"])
        asked_items.append(AskedItem(id=aid, ask=a["ask"], answered_by=[node]))

    if not nodes:
        return None, ["nothing is asked"], notes
    top = list(dict.fromkeys(nodes))
    if len(top) == 1:
        terminal = top[0]
    else:
        terminal = new_merge("conjunction", top,
                             _joined(ask_claims, "; and ",
                                     "Every thing the question asks is as its checks establish"),
                             _weakest(heading[i] for i in top))
    spec = NetworkSpec(query=query, terminal=terminal, obligations=obligations, merges=merges,
                       source="structured", facts=list(facts), asked=asked_items)
    return spec, open_, notes


# --------------------------------------------------------------------------- #
# 7. The parser
# --------------------------------------------------------------------------- #
@dataclass
class StructuredReport(ParseReport):
    """ParseReport, plus what this parser decided on the way."""
    asked: List[Dict[str, str]] = field(default_factory=list)          # with about and claim
    paragraphs: List[Dict[str, Any]] = field(default_factory=list)     # one per paragraph decided
    added: List[Dict[str, str]] = field(default_factory=list)          # paragraphs the graph added
    steps: Dict[str, int] = field(default_factory=dict)                # calls made, by step

    def as_dict(self) -> Dict[str, Any]:
        return {**super().as_dict(), "asked": self.asked, "paragraphs": self.paragraphs,
                "added": self.added, "steps": self.steps}


def make_structured_parser(ask: Callable[[str, List[str]], str], *,
                           check_ref: Optional[Callable[[str, str], bool]] = None,
                           tables: Optional[Dict[str, List[Any]]] = None,
                           exceptions_of: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
                           options_of: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
                           record_of: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
                           fact_attempts: int = 3, section_attempts: int = 2,
                           cap: int = GROUP_CAP):
    """Build the parser. `ask(prompt, images) -> str`, as for
    `parser.make_semantic_parser`; `ask.last` (when there is one) is kept for
    each call. The graph hooks come from `graph_hooks(kg)`.

    Returns `parse(query, chunks, section_id="", figures=()) ->
    (NetworkSpec | None, StructuredReport)`. The spec's source is
    "structured"; the report's source is "semantic_parser" (a model wrote
    it), or "failed" when there is no plan."""

    def call_model(report: StructuredReport, step: str, prompt: str) -> Optional[str]:
        try:
            raw = ask(prompt, [])
        except Exception as e:                                    # noqa: BLE001
            report.problems.append([f"{step}: the model call failed: {e!r}"])
            return None
        meta = getattr(ask, "last", None)
        if isinstance(meta, dict):
            report.calls.append({"step": step, **{k: v for k, v in meta.items() if k != "prompt"}})
        else:
            report.calls.append({"step": step})
        report.raw.append((raw or "")[:200000])
        report.steps[step.split(" ")[0]] = report.steps.get(step.split(" ")[0], 0) + 1
        return raw or ""

    def parse(query: str, chunks: Sequence[Dict[str, Any]], section_id: str = "",
              figures: Sequence[Dict[str, Any]] = ()) -> Tuple[Optional[NetworkSpec], StructuredReport]:
        report = StructuredReport()
        repaired = False

        # ---- step 1: the facts and the things asked
        got: Optional[Dict[str, Any]] = None
        left: List[str] = []
        best_key: Optional[Tuple] = None
        repair: Optional[Dict[str, Any]] = None
        for attempt in range(1, fact_attempts + 1):
            raw = call_model(report, f"facts {attempt}", build_facts_prompt(query, repair))
            if raw is None:
                if got is None:
                    report.source = "failed"
                    return None, report
                report.open_problems.append("facts: the repair call failed; the best reply before it is used")
                break
            data, problems = read_facts(raw, query)
            if data is not None:
                # the best reply: one with asks before one without, then the fewest
                # problems; on a tie the later
                key = (bool(data["asked"]), -len(problems))
                if best_key is None or key >= best_key:
                    got, left, best_key = data, problems, key
            if data is not None and not problems:
                break
            report.problems.append([f"facts: {p}" for p in problems])
            repaired = True
            repair = {"problems": problems, "reply": data["reply"] if data is not None else None}
        if got is None:
            report.source = "failed"
            report.notes.append("the facts and the things asked could not be read")
            return None, report
        facts: List[GivenFact] = list(got["facts"])
        asked: List[Dict[str, str]] = list(got["asked"])
        if left:
            # what is still wrong after the repairs: a fact with a problem is left
            # out (a fact is believed by every checker); an ask with one is left out
            bad_f = {m.group(1) for p in left for m in [re.match(r"^(f\d+):", p)] if m}
            facts = [f for f in facts if f.id not in bad_f]
            asked = [a for a in asked if a["about"] in ("case", "manual")
                     and a["claim"] and not a["claim"].rstrip().endswith("?") and a["ask"]]
            report.open_problems += [f"facts: {p}" for p in left]
            if bad_f:
                report.notes.append(f"facts left out after the repairs: {sorted(bad_f)}")
        if not facts:
            # nothing about a case is stated, so nothing can show that "the case"
            # meets anything: such an ask is read as asking what the manual says
            for a in asked:
                if a["about"] == "case":
                    a["about"] = "manual"
                    report.notes.append(f"asked {a['id']!r}: about the case, but there are no facts of "
                                        f"the case; read as about the manual")
        if not asked:
            report.source = "failed"
            report.notes.append("no thing asked could be read from the question")
            return None, report
        report.asked = [dict(a) for a in asked]

        # ---- the paragraphs to decide, with the graph's additions
        added = _additions(chunks, exceptions_of, options_of, record_of)
        report.added = [{"id": str(a["chunk"]["chunk_id"]), "why": a["why"]} for a in added]
        items = list(chunks) + [a["chunk"] for a in added]
        by_id = {str(c.get("chunk_id")): c for c in items if c.get("chunk_id")}
        graph_exc = named_exceptions_shown(items, exceptions_of)
        known_exc = {e for v in graph_exc.values() for e in v}
        tags: Dict[str, str] = {a["chunk"]["chunk_id"]: f"added from the manual's links: {a['why']}"
                                for a in added}
        for p, es in graph_exc.items():
            for e in es:
                if e not in tags:
                    tags[e] = f"named as an exception by [{p}]"
        calls = plan_calls(chunks, added, cap)
        if not calls:
            report.source = "failed"
            report.notes.append("no Standard, Guidance or Option paragraph was retrieved")
            return None, report

        # ---- step 2: one call per group of sections
        decisions: List[Tuple[str, Dict[str, Any]]] = []
        for n, call in enumerate(calls, 1):
            best: Optional[Tuple[Tuple, Dict[str, Dict[str, Any]], List[str]]] = None
            repair = None
            for attempt in range(1, section_attempts + 1):
                prompt = build_section_prompt(query, facts, asked, call, graph_exc, tags, figures, repair)
                raw = call_model(report, f"section {n}/{len(calls)} attempt {attempt}", prompt)
                if raw is None:
                    if best is None:
                        report.source = "failed"
                        return None, report
                    report.open_problems.append(f"section {n}: the repair call failed; the reply "
                                                f"before it is used")
                    break
                data, dec, problems, notes = read_section(raw, call, asked, facts, query, known_exc,
                                                          check_ref, tables)
                report.notes += notes
                # the best reply: readable, then the most paragraphs decided, then the
                # fewest problems, then the most checks kept; on a tie the later. A
                # reply cut off by the token limit never replaces a readable one.
                good = sum(len(d["checks"]) - len(set(d["bad_checks"])) for d in dec.values())
                key = (data is not None, len(dec), -len(problems), good)
                if best is None or key >= best[0]:
                    best = (key, dec, problems)
                if not problems:
                    break
                report.problems.append([f"section {n}: {p}" for p in problems])
                repaired = True
                repair = {"problems": problems, "reply": data}
            _k, dec, problems = best
            report.open_problems += [f"section {n}: {p}" for p in problems]
            for pid in call.decide:
                d = dec.get(pid) or {"bears": False, "why": "", "checks": [], "bad_checks": [],
                                     "undecided": True}
                decisions.append((pid, d))
                good = [j for j in range(len(d.get("checks") or [])) if j not in d.get("bad_checks", [])]
                report.paragraphs.append({
                    "id": pid, "call": n, "section": str(by_id[pid].get("section_id") or ""),
                    "heading": str(by_id[pid].get("content_type") or ""),
                    "bears": bool(d.get("bears")), "why": d.get("why", ""),
                    "checks": len(good), "dropped_checks": len(d.get("checks") or []) - len(good),
                    "condition": d.get("condition", ""), "relaxes": d.get("relaxes", []),
                    "added": pid in {a["id"] for a in report.added},
                    **({"undecided": True} if d.get("undecided") else {})})

        # ---- step 3: the plan
        spec, open_, notes = assemble(query, facts, asked, decisions, by_id, graph_exc)
        report.notes += notes
        report.open_problems += open_
        report.attempts = 2 if repaired else 1
        report.used_attempt = report.attempts
        if spec is None:
            report.source = "failed"
            return None, report
        _net, built = instantiate(spec)
        if built:
            report.source = "failed"
            report.problems.append([f"the plan built from the decisions is not valid: {p}" for p in built])
            return None, report
        # rule D (an exception check in a conjunction) is about a conjunction the
        # case must meet. Here code builds the structure: a paragraph's own checks,
        # and the statements answering an ask about the manual, may be merged so.
        about_of = {a["id"]: a["about"] for a in asked}
        case_nodes = {x for a in spec.asked if about_of.get(a.id) == "case" for x in a.answered_by}
        report.open_problems += [
            p for p in coverage_problems(spec, items, None)
            if not (" is an exception obligation, but " in p and p.split(":", 1)[0] not in case_nodes)]
        report.open_problems = list(dict.fromkeys(report.open_problems))
        report.notes = list(dict.fromkeys(report.notes))
        report.source = "semantic_parser"
        return spec, report

    return parse
