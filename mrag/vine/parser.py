"""The semantic parser — the first half of Compile, S3.1.

WHERE THIS SITS
---------------
S3.1: "an LLM-based semantic parser extracts atomic verification obligations
and their logical relations into a constrained intermediate representation,
which is then deterministically compiled into a query-specific, Petri-net-
inspired verification network".

    provisions --(THIS FILE: a model)--> NetworkSpec --(compile.py)--> Nq

`compile.py` already holds the deterministic half and everything that checks
it. This file only produces the spec. Nothing it emits reaches the executor
without passing `NetworkSpec.problems()`, `instantiate()` and
`Network.validate()` first.

WHAT THE MODEL DECIDES, AND WHAT IT DOES NOT
--------------------------------------------
Decides: the terminal proposition, how a provision breaks into atomic
obligations, which obligation depends on which, which branches are guarded,
and how results merge. S3.1 step four also says each obligation is assigned a
verifier -- but the assignment is a RULE over the obligation's type and
evidence hints, and `assign_verifier` applies it. A model naming its own
verifier could route a table lookup to itself, so any verifier it proposes is
discarded. It says what KIND of check this is; the rule says which tool runs.

Does not decide: the normative authority beyond reading the printed heading,
the merge semantics (typed, in the executor), whether a guard's code is safe
(guards are a closed vocabulary turned into functions in `compile.py`), or
anything at execution time.

THE REPAIR LOOP IS THE PAPER'S, NOT AN ADDITION
-----------------------------------------------
S3.1: "Networks containing unresolved references, missing producers for
mandatory states, invalid dependencies, or unreachable terminal states are
rejected or returned to the compiler for repair."

So a rejected spec goes back with the specific rules it broke -- not with a
request to try again. `repair_request` already phrases problems in the ids the
model itself wrote.

WHY THERE IS A FALLBACK
-----------------------
If every attempt fails, `compile_section` produces a spec from the printed
structure alone. A model that cannot be made to emit valid JSON should not
take the whole pipeline down with it, and a worse network that runs is more
useful than no network at all. The report says which was used, always.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .compile import (CompileError, NetworkSpec, compile_section, instantiate,
                      repair_request)
from .network import MergeType, ObligationType

log = logging.getLogger("mrag.vine.parser")

__all__ = ["ParseReport", "make_semantic_parser", "build_parser_prompt",
           "read_spec", "PARSER_CONTRACT"]


# --------------------------------------------------------------------------- #
# 1. The contract
# --------------------------------------------------------------------------- #
_TYPES = ", ".join(t.value for t in ObligationType)
_MERGES = ", ".join(k.value for k in MergeType)

PARSER_CONTRACT = f"""Reply with one JSON object and nothing else. No preamble,
no explanation outside the JSON, no markdown fence.

{{
  "terminal": "<id of the obligation or merge that answers the question>",
  "obligations": [
    {{"id": "o1",
      "claim": "<one thing that can be checked on its own>",
      "type": "<{_TYPES}>",
      "authority": "STANDARD | GUIDANCE | OPTION",
      "requires": ["<ids that must be established first>"],
      "guard": <null, or a guard object>,
      "evidence_hint": [{{"type": "table|figure|section", "id": "..."}}],
      "source_chunk": "<the id of the chunk this came from>"}}
  ],
  "merges": [
    {{"id": "m1",
      "claim": "<what the merge establishes>",
      "kind": "<{_MERGES}>",
      "inputs": ["<ids being combined>"]}}
  ]
}}

ATOMIC OBLIGATIONS
One obligation is ONE thing that can be checked by itself. A paragraph that
states two conditions becomes two obligations, not one. "The sign shall be
36 inches and shall have a red border" is two checks. Splitting them is the
point of this step: a check that mixes a measurement with a judgement cannot
be given to a calculator.

TYPE
  applicability     does this provision apply to the situation at all
  classification    what category is this thing
  numerical         a quantity compared against a threshold or a table
  visual            something that must be read off a figure
  definitional      what a defined term means
  cross_reference   what another section or figure says
  exception         a provision that RELAXES another one

AUTHORITY
Copy the printed heading of the paragraph the obligation came from: Standard,
Guidance or Option. Do not infer it from the verb and do not upgrade it.
Support material is never an obligation.

DEPENDENCIES
`requires` lists obligations that must be established BEFORE this one can be
checked. Use it for real prerequisites only. Two checks that could be done in
either order must NOT depend on each other -- independence is what lets them
run in parallel, and inventing an order destroys that.

GUARDS
A guard says when a branch is relevant at all. It is one of:
  {{"state": "<obligation id>", "status": "TRUE|FALSE|UNKNOWN|RESOLVED"}}
  {{"all": [<guard>, <guard>, ...]}}
  {{"any": [<guard>, <guard>, ...]}}
  {{"not": <guard>}}
Nothing else is accepted. Do not write a guard as a sentence.

MERGES
  conjunction   every input must hold
  alternative   any one input satisfies it
  exception     inputs[0] is the BASE RULE; the rest relax it
  threshold     a numeric comparison over the inputs
The first input of an exception merge is the rule being excepted FROM, never
the exception itself.

TERMINAL
The id of whatever answers the question. If several requirements must all
hold, that is a conjunction merge, and the merge is the terminal.

RULES
- Every id in `requires`, `inputs` and a guard must be an id declared here.
- A merge needs at least two inputs.
- No cycles.
- Use only the chunk ids supplied as `source_chunk`; do not invent one.
- Do not name a verifier. The type and the evidence hints decide that."""


# --------------------------------------------------------------------------- #
# 2. The prompt
# --------------------------------------------------------------------------- #
def build_parser_prompt(query: str, chunks: Sequence[Dict[str, Any]],
                        section_id: str = "",
                        repair: Optional[Dict[str, Any]] = None) -> str:
    """The provisions, the question, and the contract.

    Support chunks are shown but marked: S3.1 decomposes "the retrieved
    provisions" into obligations, and Support is explanatory rather than
    normative. It is included because it often carries the definition that
    makes a Standard readable, and excluded from becoming an obligation.
    """
    lines: List[str] = []
    for c in chunks:
        cid = str(c.get("chunk_id") or "")
        if not cid:
            continue
        kind = str(c.get("content_type") or "")
        note = "  (Support: context only, never an obligation)" if kind == "Support" else ""
        if c.get("authority_inferred"):
            note += "  (type inferred from the verb, not a printed heading)"
        lead = (c.get("lead_in") or "").strip()
        text = (c.get("text") or "").strip()
        body = f"{lead} {text}".strip() if lead else text
        refs = []
        for key, label in (("table_refs", "tables"), ("figure_refs", "figures"),
                           ("section_refs", "sections")):
            if c.get(key):
                refs.append(f"{label}: {', '.join(str(x) for x in c[key])}")
        tail = ("\n  cites " + "; ".join(refs)) if refs else ""
        lines.append(f"[{cid}] {kind} paragraph {c.get('ordinal', '')}"
                     f"{note}\n{body}{tail}")

    parts = [
        "Compile the provisions below into a verification network.",
        "",
        f"QUESTION\n{query}",
    ]
    if section_id:
        parts += ["", f"SECTION\n{section_id}"]
    parts += ["", "PROVISIONS\n" + ("\n\n".join(lines) or "(none)"),
              "", PARSER_CONTRACT]

    if repair:
        parts += [
            "",
            "YOUR PREVIOUS ATTEMPT WAS REJECTED.",
            "Problems:\n" + "\n".join(f"- {p}" for p in repair["problems"]),
            "Rules broken:\n" + "\n".join(f"- {r}" for r in repair["rules"]),
            "Fix only what is listed. Return the whole corrected object.",
            "Your previous attempt:\n" + json.dumps(repair["spec"], indent=2)[:4000],
        ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# 3. Reading the reply
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)
_OBJECT = re.compile(r"\{.*\}", re.S)


def read_spec(raw: str, query: str, allowed_chunks: Sequence[str] = (),
              ) -> Tuple[Optional[NetworkSpec], List[str]]:
    """Turn the reply into a NetworkSpec, or say why it cannot be.

    Two things are stripped rather than trusted:

    * any `verifier` the model named. S3.1 assigns a verifier by rule over the
      obligation's type and hints; letting the model choose would let it route
      a table lookup to itself.
    * any `source_chunk` that was not supplied. It is provenance back into Kq,
      and a provenance pointer that resolves to nothing is worse than none.
    """
    text = _FENCE.sub("", raw or "").strip()
    match = _OBJECT.search(text)
    if not match:
        return None, ["the reply contained no JSON object"]
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return None, [f"malformed JSON: {e}"]
    if not isinstance(data, dict):
        return None, ["the JSON was not an object"]

    permitted = set(allowed_chunks)
    notes: List[str] = []
    for ob in (data.get("obligations") or []):
        if not isinstance(ob, dict):
            continue
        if ob.pop("verifier", None) is not None:
            notes.append("a proposed verifier was discarded; the rule assigns it")
        src = ob.get("source_chunk")
        if src and permitted and str(src) not in permitted:
            notes.append(f"source_chunk {src!r} was not supplied and was dropped")
            ob["source_chunk"] = ""

    data.setdefault("query", query)
    data["source"] = "semantic_parser"
    try:
        spec = NetworkSpec.from_dict(data)
    except CompileError as e:
        return None, [str(e)]
    return spec, notes


# --------------------------------------------------------------------------- #
# 4. The parser
# --------------------------------------------------------------------------- #
@dataclass
class ParseReport:
    """What happened, in enough detail to audit a bad network afterwards."""
    source: str = ""                      # semantic_parser | baseline | failed
    attempts: int = 0
    problems: List[List[str]] = field(default_factory=list)   # per attempt
    notes: List[str] = field(default_factory=list)
    raw: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "attempts": self.attempts,
                "problems": self.problems, "notes": self.notes}


def make_semantic_parser(ask: Callable[[str, List[str]], str],
                         max_attempts: int = 3,
                         fall_back_to_baseline: bool = True):
    """Build the parser. `ask(prompt, images) -> str`, the same contract the
    verifiers use, so one model call site serves the whole pipeline.

    Returns `parse(query, chunks, section_id="") -> (NetworkSpec, ParseReport)`.
    """
    def parse(query: str, chunks: Sequence[Dict[str, Any]],
              section_id: str = "") -> Tuple[Optional[NetworkSpec], ParseReport]:
        report = ParseReport()
        allowed = [str(c.get("chunk_id")) for c in chunks if c.get("chunk_id")]
        repair: Optional[Dict[str, Any]] = None
        spec: Optional[NetworkSpec] = None

        for attempt in range(1, max_attempts + 1):
            report.attempts = attempt
            prompt = build_parser_prompt(query, chunks, section_id, repair)
            try:
                raw = ask(prompt, [])
            except Exception as e:                            # noqa: BLE001
                report.problems.append([f"the model call failed: {e!r}"])
                break
            report.raw.append((raw or "")[:4000])

            spec, notes = read_spec(raw, query, allowed)
            report.notes.extend(notes)
            if spec is None:
                report.problems.append(notes or ["the reply could not be read"])
                # a reply that is not JSON cannot be repaired field by field;
                # the contract is restated instead
                repair = None
                continue

            # the SAME checks the executor will apply, applied here so a
            # rejected spec is repaired rather than discovered at run time
            _net, problems = instantiate(spec)
            if not problems:
                report.source = "semantic_parser"
                return spec, report
            report.problems.append(list(problems))
            repair = repair_request(spec, problems)
            spec = None

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
