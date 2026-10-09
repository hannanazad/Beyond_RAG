"""The LLM and VLM verifiers — S3.3, Eq 3 and Eq 5.

WHY THESE TAKE A CALLABLE RATHER THAN A MODEL
---------------------------------------------
S3.3: "different language models, vision-language models, retrieval systems,
or deterministic tools can be substituted without changing the representation
or execution semantics of Nq."

So the verifier holds the contract -- what is asked, what shape the reply must
take, what happens when it does not -- and the model is a function passed in:

    ask(prompt: str, images: list[str]) -> str

Swapping provider means passing a different function, not editing this file
and not editing `vlm.py`. `vlm.py` stays what it is: the generator for the
answer step, Eq 6, where prose is the right output.

WHY THE REPLY IS JSON AND NOT PROSE
-----------------------------------
Appendix A: "The certificate is not intended as unrestricted natural-language
memory. Its fields are constrained so that readiness guards and downstream
operations can inspect the result programmatically."

And S3.2: "A downstream operation cannot run merely because an upstream model
has produced an intermediate statement; its prerequisite states must carry
acceptable certificates."

Recovering a status by pattern-matching prose would rebuild the very thing
S4.6 ablates away as "textual intermediate summaries". Measured on the
compiled networks, that configuration scores 56.6% terminal accuracy at an
18.7% unsupported certification rate. It is the ablation, not the system.

THE THREE RULES THAT MAKE A MODEL'S ANSWER USABLE
-------------------------------------------------
1. UNKNOWN is always available and is the default. A reply that will not
   parse, a missing field, a crash -- all UNKNOWN. Never FALSE. A model that
   failed to answer has refuted nothing.
2. Cited evidence must be evidence that was supplied. A model naming a
   section it was never shown is fabricating provenance, and S3.4 requires
   the trace to be auditable. Unsupplied ids are dropped and recorded; if
   NOTHING it cited was supplied, the certificate is UNKNOWN.
3. Authority is never the model's to set. It comes from the operation, which
   got it from the printed heading. The executor enforces this too; this file
   simply does not ask. One exception, in one direction only: Eq 3 has r_i
   record the normative authority of R_i, the evidence. When the checker
   answers FALSE and names as its `basis` a supplied provision whose PRINTED
   heading is stronger than the operation's (a Standard, for a check the
   parser labelled Guidance), the certificate takes that heading. The heading
   is read from the provision's record, never from the reply, and it is never
   lowered. Without this, a check labelled Guidance that the checker found to
   break a "shall" was filed as a mere non-conformance, and the decision
   came out the wrong way (DEV, 8 October 2026).

WHAT THE CHECKER SEES
---------------------
The claim, the facts the question states (Γ0q, listed by the parser and put
in the initial store by `instantiate`), what earlier checks established, and
the manual text found for this claim. Never the question itself: S3.3 says
"All verification remains grounded in the persistent knowledge graph", and
Eq 5 uses q only to retrieve the evidence.

HOW IT READS AND LOOKS FURTHER (9 October 2026)
-----------------------------------------------
1. Reading rules. The prompt says how a claim is judged (the case, not the
   rule in general; "applies" means the case falls under the provision; a
   statement about the case is compared with the facts) and quotes the
   manual's own rules for reading it: 1C.01 (the headings, and that Option
   statements may modify a Standard or Guidance), 1A.04 Paragraphs 5 and 6
   (tables and figures; numerals on figures are examples), 1B.03 Paragraph 9
   (not prohibited is not allowed).
2. Labels. Every piece of evidence is shown with its section number and
   title, paragraph, printed heading, and the links it carries in the graph:
   the exceptions it names, what it refers to, the Option paragraphs of its
   section, the defined terms it uses (`lookup.ManualView`). The paragraphs a
   pointed provision names as its exceptions are added to the evidence.
3. Lookups. When the model function offers `converse` (the Anthropic client
   does), the checker can open sections, paragraphs, tables and figures,
   definitions, and search the manual, read-only and capped
   (`lookup.Lookups`). S3.3: "Nq in turn issues obligation-specific requests
   back to the graph as execution proceeds."
   After a TRUE or FALSE, if a provision the answer rests on names an
   exception the checker has not read, that exception is handed to it and it
   answers again, once. If such a provision says "except as otherwise provided
   in this Manual", it is asked to look for the specific provision first.
Everything looked up is logged in the certificate's provenance, and the ids
it cites that were not in the evidence it started with are recorded as
`found_by_checker`.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .certificate import (Authority, Certificate, CertificateStore, Evidence, Status,
                          stronger)
from .lookup import DEFAULT_MAX_LOOKUPS, Lookups, ManualView
from .network import Operation

log = logging.getLogger("mrag.vine.model_verifiers")

__all__ = ["Ask", "make_llm_verifier", "make_vlm_verifier",
           "certificates_for_retrieval", "parse_model_reply", "build_prompt",
           "READING_RULES", "LOOKUP_RULES"]

# prompt, image paths -> raw reply text
Ask = Callable[[str, List[str]], str]


# --------------------------------------------------------------------------- #
# 1. Handing the store back to retrieval — Eq 5
# --------------------------------------------------------------------------- #
def certificates_for_retrieval(store: CertificateStore) -> List[Dict[str, Any]]:
    """Γ_t as the Appendix A mappings `retrieve_for_obligation` expects.

    Eq 5 is R_i = Retrieve(q, φ_i, Γ_t, K): what is already established
    conditions what is fetched next. `anchors_from_certificates` drops
    UNKNOWN ones itself, so everything is passed and the filtering stays in
    one place.
    """
    out: List[Dict[str, Any]] = []
    for cert in store.all():
        out.append({
            "claim": cert.claim,
            "status": cert.status.value,
            "evidence": [e.as_dict() for e in cert.evidence],
        })
    return out


# --------------------------------------------------------------------------- #
# 2. The prompt
# --------------------------------------------------------------------------- #
_CONTRACT = """Reply with one JSON object and nothing else. No preamble, no
explanation outside the JSON, no markdown fence.

{"status": "TRUE" | "FALSE" | "UNKNOWN",
 "evidence": ["<id>", ...],
 "basis": "<id>",
 "confidence": <number between 0 and 1>,
 "reason": "<one or two sentences>"}

status
  TRUE     the manual text you have read establishes the claim
  FALSE    it refutes the claim
  UNKNOWN  it does not settle the claim

Choose UNKNOWN whenever the evidence is absent, partial, or about a
different situation. UNKNOWN is a correct answer and is preferred to a guess.
Do not reason from general knowledge of traffic engineering; decide only from
the manual text {WHERE}.

Facts about the case come only from GIVEN IN THE QUESTION and ALREADY
ESTABLISHED. What the manual requires, recommends or allows comes only from
the manual text.

evidence
  the ids of the items you actually used, copied exactly: a piece of the
  manual {WHERE}, or a fact from GIVEN IN THE QUESTION (f1, f2, ...). Do not
  name anything else.

basis
  the one id from the manual your answer rests on most, also listed under
  evidence. For FALSE, the provision the claim fails against.

A TRUE or FALSE needs at least one piece of the manual: the facts of the case
alone never settle what the manual requires."""

_WHERE_STATIC = "shown under EVIDENCE"
_WHERE_LOOKUPS = "shown under EVIDENCE or returned by a lookup"

READING_RULES = """HOW TO READ THE CLAIM
- The claim is about the case described in GIVEN IN THE QUESTION and ALREADY
  ESTABLISHED. Judge that case, not the rule in general.
- "The manual requires / recommends / allows / prohibits X" (for this case):
  TRUE when a provision says so for a case like this one. FALSE when the
  manual says otherwise for this case: a different value, a prohibition, or an
  exception, condition or Option that covers this case. A general rule that is
  changed for this case cannot support TRUE.
- "Provision P applies" (or "is applicable", "governs"): TRUE when this case
  falls under P, that is, P's subject and P's conditions fit the facts. FALSE
  when a fact or another provision puts this case outside P. It does not ask
  whether the case obeys P.
- "The case meets / complies with P": TRUE when the facts satisfy what P
  requires; FALSE when a fact breaks it; UNKNOWN when a fact it needs is not
  given.
- A statement about the case itself (a size, a place, a count, the kind of
  road or device): compare it with the facts. FALSE when a fact contradicts
  it; UNKNOWN when the facts do not say. Never replace a fact with what is
  typical.

HOW THE MANUAL SAYS IT IS TO BE READ (its own words)
- Section 1C.01: a Standard is "a statement of required, mandatory, or
  specifically prohibitive practice"; "Standard statements are sometimes
  modified by Option statements." Guidance is "a statement of recommended
  practice in typical situations, with deviations allowed if engineering
  judgment or engineering study ... indicates the deviation to be
  appropriate." An Option is "a statement of practice that is a permissive
  condition and carries no requirement or recommendation. Option statements
  sometimes contain allowable modifications to a Standard or Guidance
  statement." Support is "an informational statement that does not convey any
  degree of mandate, recommendation, authorization, prohibition, or
  enforceable condition."
  So before deciding on a Standard or Guidance, read the Option paragraphs of
  its section (listed in its links): one of them may change it for this case.
- A provision that says "Except as provided in Section X" or "... in
  Paragraph N" names its exception. The exception is part of the rule: read
  it before deciding.
- A provision that says "except as otherwise provided in this Manual" (or
  "unless otherwise provided") says that exceptions exist elsewhere without
  naming them. Before relying on it, look for the provision about the
  specific device or situation in this case.
- Section 1A.04, Paragraph 5: "Figures and tables, including the notes
  contained therein, supplement the text and might constitute a Standard,
  Guidance, Option, or Support. The user needs to refer to the appropriate
  text to classify the nature of the figure, table, or note contained
  therein." Read a value from a table together with the table's notes.
- Section 1A.04, Paragraph 6: "Except when a specific numeral is required or
  recommended by the text of a Section of this Manual, numerals displayed on
  the images of devices in the figures that specify quantities such as times,
  distances, speed limits, and weights should be regarded as examples only."
- Section 1B.03, Paragraph 9: "The absence of a provision in this Manual that
  explicitly prohibits a particular practice ... does not, in itself,
  constitute acceptability or permission to use the device in a manner not
  provided for in this Manual." Not prohibited does not mean allowed. But
  what you have not read is not absent from the manual: if nothing you have
  read settles the claim, look further or answer UNKNOWN.
- A FIGURE DESCRIPTION was written by a reader, not the manual, and may
  contain mistakes: never rest an answer on it alone."""

LOOKUP_RULES = """LOOKING FURTHER
You can read more of the manual with the lookup tools: open_section,
open_paragraph, open_table_or_figure, define_term{SEARCH}. At most {N}
lookups for this claim. Everything they return may be cited by its id.
- Before you answer, open what could change the answer and is not shown yet:
  an exception that a provision you rely on names, the Option paragraphs of
  its section, the notes of a table you read a value from, the definition of
  a term the claim turns on, and the provision for the specific device or
  situation when a rule says "except as otherwise provided in this Manual".
- Do not open what cannot change the answer.
- When you have what you need, reply with the JSON object only."""


def _contract(lookups: bool) -> str:
    return _CONTRACT.replace("{WHERE}", _WHERE_LOOKUPS if lookups else _WHERE_STATIC)


def _evidence_block(chunks: Sequence[Dict[str, Any]],
                    figures: Sequence[Dict[str, Any]],
                    view: Optional[ManualView] = None) -> Tuple[str, List[str]]:
    """The numbered evidence, and the ids a reply is allowed to cite. With a
    `view` (the VINE graph), each piece carries its label and links."""
    lines: List[str] = []
    allowed: List[str] = []
    for c in chunks:
        cid = str(c.get("chunk_id") or "")
        if not cid:
            continue
        allowed.append(cid)
        if view is not None:
            try:
                lines.append(view.label(c))
                continue
            except Exception:                                 # noqa: BLE001
                pass                       # fall back to the plain form below
        head = f"{c.get('section_id', '')} {c.get('content_type', '')}".strip()
        lead = (c.get("lead_in") or "").strip()
        text = (c.get("text") or "").strip()
        body = f"{lead} {text}".strip() if lead else text
        inferred = ("  [type inferred from the verb, not a printed heading]"
                    if c.get("authority_inferred") else "")
        lines.append(f"[{cid}] ({head}){inferred}\n{body}")
    for f in figures:
        fid = str(f.get("figure_id") or "")
        if not fid:
            continue
        allowed.append(fid)
        total = int(f.get("n_sheets") or f.get("sheet_of") or 1)
        shown = int(f.get("_sheets_shown") or total)
        partial = (f"  [only {shown} of {total} sheets are shown]"
                   if total > 1 and shown < total else "")
        lines.append(f"[{fid}] {f.get('caption', '')}{partial}")
    return ("\n\n".join(lines) or "(no evidence was retrieved)"), allowed


def build_prompt(op: Operation, chunks: Sequence[Dict[str, Any]],
                 figures: Sequence[Dict[str, Any]],
                 established: Sequence[Certificate] = (),
                 given: Sequence[Certificate] = (),
                 view: Optional[ManualView] = None,
                 lookups: int = 0, search: bool = True) -> Tuple[str, List[str]]:
    """The prompt for ONE obligation, and the ids it may cite.

    The claim is the obligation, not the user's question. S3.3 is explicit
    that evidence is retrieved for "the obligation currently being verified",
    and asking the model the original question here would invite it to answer
    that instead -- which is the single-shot RAG this architecture replaces.

    `given` are the facts of the case from Γ0q (verifier "given"). They are
    listed apart from what earlier checks established, so the checker can
    tell a fact of the case from a result, and they may be cited by id.
    """
    evidence, allowed = _evidence_block(chunks, figures, view)
    facts = [c for c in given if c.obligation_id]
    given_block = "\n".join(f"[{c.obligation_id}] {c.claim}" for c in facts) or "(none)"
    allowed = allowed + [c.obligation_id for c in facts]
    # A check found not to apply is shown as such, in words: the checker can
    # only answer TRUE, FALSE or UNKNOWN, and should not read a fourth status
    # word as an answer it may give.
    known = "\n".join(
        f"- {c.claim} => "
        + ("DOES NOT APPLY HERE" if c.status is Status.NOT_APPLICABLE
           else c.status.value)
        for c in established
        if c.status is not Status.UNKNOWN) or "(nothing yet)"
    parts = [
        "You are checking ONE claim against the manual (the MUTCD), as an engineer "
        "who signs for it would.",
        "",
        f"CLAIM\n{op.claim}",
        "",
        "GIVEN IN THE QUESTION (facts of the case, copied from the question; "
        "they say nothing about what the manual requires)\n" + given_block,
        "",
        f"ALREADY ESTABLISHED\n{known}",
        "",
        READING_RULES,
        "",
    ]
    if lookups:
        parts += [LOOKUP_RULES.replace("{N}", str(int(lookups)))
                  .replace("{SEARCH}", " and search_manual" if search else ""), ""]
    parts += [
        f"EVIDENCE\n{evidence}",
        "",
        _contract(bool(lookups)),
        "",
        f"THE CLAIM AGAIN\n{op.claim}",
    ]
    return "\n".join(parts), allowed


# --------------------------------------------------------------------------- #
# 3. Reading the reply
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)
_OBJECT = re.compile(r"\{.*\}", re.S)
_STATUSES = {"TRUE": Status.TRUE, "FALSE": Status.FALSE,
             "UNKNOWN": Status.UNKNOWN}


@dataclass
class Reply:
    status: Status
    evidence: List[str]
    confidence: float
    reason: str
    dropped: List[str]           # ids cited that were never supplied
    problem: str = ""
    basis: str = ""              # the supplied id the answer rests on most


def parse_model_reply(raw: str, allowed: Sequence[str]) -> Reply:
    """Read the reply strictly, and fall to UNKNOWN rather than to FALSE.

    Every failure here -- no JSON, an unknown status word, a confidence that
    is not a number -- means the model did not answer, and a model that did
    not answer has refuted nothing. Rule 1 of this module.
    """
    text = _FENCE.sub("", raw or "").strip()
    match = _OBJECT.search(text)
    if not match:
        return Reply(Status.UNKNOWN, [], 0.0, "", [],
                     "the reply contained no JSON object")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return Reply(Status.UNKNOWN, [], 0.0, "", [], f"malformed JSON: {e}")
    if not isinstance(data, dict):
        return Reply(Status.UNKNOWN, [], 0.0, "", [], "the JSON was not an object")

    word = str(data.get("status", "")).strip().upper()
    status = _STATUSES.get(word)
    if status is None:
        return Reply(Status.UNKNOWN, [], 0.0, str(data.get("reason", "")), [],
                     f"status {word!r} is not TRUE, FALSE or UNKNOWN")

    cited = [str(x).strip() for x in (data.get("evidence") or [])
             if str(x).strip()]
    permitted = set(allowed)
    kept = [c for c in cited if c in permitted]
    dropped = [c for c in cited if c not in permitted]

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(max(confidence, 0.0), 1.0)

    basis = str(data.get("basis") or "").strip()
    if basis not in permitted:
        basis = ""
    return Reply(status, kept, confidence, str(data.get("reason", "")).strip(),
                 dropped, basis=basis)


# --------------------------------------------------------------------------- #
# 4. The verifiers
# --------------------------------------------------------------------------- #
def _evidence_objects(ids: Sequence[str],
                      chunks: Sequence[Dict[str, Any]],
                      figures: Sequence[Dict[str, Any]],
                      given_ids: Sequence[str] = ()) -> List[Evidence]:
    chunk_ids = {str(c.get("chunk_id")) for c in chunks}
    given = set(given_ids)
    out: List[Evidence] = []
    inferred = {str(c.get("chunk_id")): bool(c.get("authority_inferred"))
                for c in chunks}
    for ident in ids:
        if ident in given:
            out.append(Evidence("given", ident))
        elif ident in chunk_ids:
            out.append(Evidence("chunk", ident, inferred.get(ident, False)))
        elif ident.lower().startswith("table"):
            out.append(Evidence("table", ident))
        else:
            out.append(Evidence("figure", ident))
    return out


_HEADINGS = {"Standard": Authority.STANDARD, "Guidance": Authority.GUIDANCE,
             "Option": Authority.OPTION}


def _printed_heading(chunk_id: str, chunks: Sequence[Dict[str, Any]]
                     ) -> Optional[Authority]:
    """The Standard / Guidance / Option heading the manual PRINTS over this
    provision, or None (Support, a table row, a figure description, or a
    heading this project inferred from the verb)."""
    for c in chunks:
        if str(c.get("chunk_id")) == chunk_id:
            if c.get("authority_inferred"):
                return None
            return _HEADINGS.get(str(c.get("content_type") or ""))
    return None


def _merge_by_id(first: Sequence[Dict[str, Any]], then: Sequence[Dict[str, Any]],
                 key: str) -> List[Dict[str, Any]]:
    out, seen = [], set()
    for item in list(first) + list(then):
        k = item.get(key)
        if k and k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out


_GATE_MOST = 16          # exception pieces handed over after an answer, at most


def _exception_gate(view: ManualView, looks: Lookups, allowed_now: Callable[[], List[str]],
                    given_ids: Sequence[str], record: Dict[str, Any]):
    """`after_answer` for the conversation: once, after a TRUE or FALSE, hand
    over the exceptions that the provisions the answer rests on name and the
    checker has not read; name the long sections they name whole; and, if such
    a provision says an exception exists "otherwise" without naming where, ask
    the checker to look for the specific provision.

    The manual names a rule's exceptions in the rule; reading the rule without
    them is reading half of it (1C.01, and every "Except as provided in ...")."""
    def gate(text: str) -> Optional[str]:
        if record.get("gate_used"):
            return None
        reply = parse_model_reply(text, allowed_now())
        if reply.status not in (Status.TRUE, Status.FALSE):
            return None
        relied = [x for x in dict.fromkeys([reply.basis] + list(reply.evidence))
                  if x and x not in set(given_ids) and x in looks.shown]
        items = [looks.shown[x] for x in relied]
        missing = [x for x in view.named_exception_ids(items) if x not in looks.shown]
        opened = {e.get("section") for e in looks.log
                  if e.get("tool") == "open_section" and not e.get("error")}
        long_secs = [sec for it in items for sec in view.links(it).long_exception_sections
                     if sec not in opened]
        long_secs = list(dict.fromkeys(long_secs))
        open_ended = [(str(it.get("chunk_id")), view.links(it).open_exception) for it in items
                      if view.links(it).open_exception]
        can_look = looks.used < looks.max_lookups
        if not missing and not (long_secs and can_look) and not (open_ended and can_look):
            return None
        record["gate_used"] = True
        record["first_answer"] = reply.status.value
        parts = []
        if missing:
            payloads = view.payloads(missing[:_GATE_MOST])
            record["handed_over_exceptions"] = [str(p.get("chunk_id")) for p in payloads]
            parts.append(looks.render(
                payloads,
                "Before this answer stands: the provisions it rests on name these "
                "exceptions, which you had not read. They are part of those rules. If "
                "one of them covers this case, the answer must follow it."))
            if len(missing) > _GATE_MOST:
                record["exceptions_not_handed_over"] = missing[_GATE_MOST:]
                parts.append("Also named as exceptions and not shown here: "
                             + ", ".join(f"[{x}]" for x in missing[_GATE_MOST:]) + ".")
        if long_secs and can_look:
            record["asked_to_open_sections"] = long_secs
            parts.append("The provisions it rests on also name these whole sections as "
                         "exceptions, and you have not opened them: "
                         + ", ".join(f"Section {x}" for x in long_secs)
                         + ". Open the parts that could cover this case.")
        if open_ended and can_look:
            record["asked_to_look_for_specific_provision"] = [c for c, _p in open_ended]
            how = "search_manual or open_section" if looks.view.search is not None else "open_section"
            parts.append("Before this answer stands: "
                         + "; ".join(f'[{c}] says "{p}"' for c, p in open_ended)
                         + ". Look for the provision about the specific device or situation "
                         f"in this case ({how}) if you have not already.")
        parts.append("Then reply again with the JSON object only.")
        return "\n\n".join(parts)
    return gate


def _make(kind: str, ask: Ask, retriever=None, query: str = "",
          top_k: Optional[int] = None, with_images: bool = False,
          use_pointers: bool = True, max_pointed_chunks: int = 8,
          max_images: int = 4, labels: bool = True,
          use_lookups: bool = True, max_lookups: int = DEFAULT_MAX_LOOKUPS,
          named_exceptions: bool = True, max_named_exceptions: int = 6):
    view: Optional[ManualView] = None
    if retriever is not None and labels:
        try:
            view = ManualView.from_retriever(retriever, cache_dir=getattr(ask, "cache_dir", None))
        except Exception as e:                                # noqa: BLE001
            log.warning("labels and lookups are off: %r", e)
            view = None
    converse = getattr(ask, "converse", None)

    def verify(op: Operation, store: CertificateStore) -> Certificate:
        chunks: List[Dict[str, Any]] = []
        figures: List[Dict[str, Any]] = []
        debug: Dict[str, Any] = {}
        pointed: Dict[str, Any] = {"chunks": [], "figures": []}

        # ---- what the plan points to for this obligation, by id ----------
        if (retriever is not None and use_pointers
                and (getattr(op, "source_chunk", "") or op.evidence_hint)):
            try:
                from .pointers import pointed_evidence
                pointed = pointed_evidence(retriever, getattr(op, "source_chunk", ""),
                                           op.evidence_hint,
                                           max_chunks=max_pointed_chunks)
                debug["pointed"] = pointed.get("debug", {})
            except Exception as e:                            # noqa: BLE001
                debug["pointer_error"] = repr(e)

        # ---- the exceptions those provisions name (the manual's own pointers)
        excepted: List[Dict[str, Any]] = []
        if view is not None and named_exceptions and pointed["chunks"]:
            try:
                have = {c.get("chunk_id") for c in pointed["chunks"]}
                ids = [x for x in view.named_exception_ids(pointed["chunks"])
                       if x not in have][:max_named_exceptions]
                excepted = [{**p, "source": "named_exception"} for p in view.payloads(ids)]
                if excepted:
                    debug["named_exceptions"] = [p.get("chunk_id") for p in excepted]
            except Exception as e:                            # noqa: BLE001
                debug["named_exception_error"] = repr(e)

        # ---- Eq 5: evidence for THIS obligation, given what is known ----
        if retriever is not None:
            try:
                got = retriever.retrieve_for_obligation(
                    query or op.claim, op.claim,
                    certificates=certificates_for_retrieval(store),
                    top_k=top_k)
                chunks, figures = list(got.chunks), list(got.figures)
                debug.update({k: got.debug.get(k) for k in
                              ("established_sections", "established_figures",
                               "established_tables", "established_notes")
                              if got.debug.get(k)})
            except Exception as e:                            # noqa: BLE001
                # Retrieval failing is missing evidence, not a refutation.
                if not pointed["chunks"] and not pointed["figures"]:
                    return _abstain(op, kind, f"retrieval failed: {e!r}")
                debug["retrieval_error"] = repr(e)

        # the pointed evidence first, its named exceptions, then what the search added
        chunks = _merge_by_id(list(pointed["chunks"]) + excepted, chunks, "chunk_id")
        figures = _merge_by_id(pointed["figures"], figures, "figure_id")

        if not chunks and not figures:
            return _abstain(op, kind, "no evidence was retrieved for this "
                                      "obligation")

        given = [c for c in store.all()
                 if c.verifier == "given" and c.status is Status.TRUE]
        established = [c for c in store.all()
                       if c.status is not Status.UNKNOWN and c.verifier != "given"]
        given_ids = [c.obligation_id for c in given if c.obligation_id]
        tools_on = bool(view is not None and use_lookups and callable(converse)
                        and int(max_lookups) > 0)
        looks: Optional[Lookups] = Lookups(view, max_lookups) if tools_on else None
        prompt, allowed = build_prompt(
            op, chunks, figures, established, given, view=view,
            lookups=int(max_lookups) if tools_on else 0,
            search=bool(looks is not None and looks.view.search is not None))
        started_with = list(allowed)

        images: List[str] = []
        images_left_out: List[str] = []
        images_missing: List[str] = []
        if with_images:
            for f in figures:
                for path in (f.get("image_paths") or [f.get("image_path")]):
                    if not path:
                        continue
                    if not os.path.exists(str(path)):
                        images_missing.append(str(path))
                        continue
                    if len(images) < max_images:
                        images.append(str(path))
                    else:
                        images_left_out.append(str(path))

        transcript: Dict[str, Any] = {}
        gate_record: Dict[str, Any] = {}
        try:
            if looks is not None:
                looks.show(chunks)

                def allowed_now() -> List[str]:
                    return list(dict.fromkeys(list(allowed) + list(looks.shown)))

                raw, transcript = converse(
                    prompt, images, looks.specs(), looks.run, max_lookups=int(max_lookups),
                    after_answer=_exception_gate(view, looks, allowed_now, given_ids,
                                                 gate_record))
                allowed = allowed_now()
                seen_chunks = list(looks.shown.values())
                chunks = _merge_by_id(chunks, seen_chunks, "chunk_id")
            else:
                raw = ask(prompt, images)
        except Exception as e:                                # noqa: BLE001
            # S3.2: a crashed tool has established nothing.
            return _abstain(op, kind, f"the model call failed: {e!r}")

        reply = parse_model_reply(raw, allowed)
        provenance: Dict[str, Any] = {
            "verifier": kind,
            "reason": reply.reason,
            "evidence_offered": started_with,
            "images_shown": len(images),
            "raw_reply": (raw or "")[:2000],   # S3.4: the trace is auditable
            "pointed_evidence": [c.get("chunk_id") for c in pointed["chunks"]]
                                + [f.get("figure_id") for f in pointed["figures"]],
        }
        if looks is not None:
            provenance["lookups"] = looks.log
            provenance["lookups_used"] = looks.used
            provenance["lookup_limit"] = int(max_lookups)
            provenance["conversation"] = {k: transcript.get(k) for k in
                                          ("turns", "lookups", "refused_lookups",
                                           "follow_ups", "nudged", "stopped")}
            provenance["conversation"]["cache_keys"] = [
                str(k)[:16] for k in (transcript.get("cache_keys") or [])]
            provenance.update({k: v for k, v in gate_record.items() if k != "gate_used"})
            if transcript.get("stopped"):
                provenance["conversation_stopped"] = transcript["stopped"]
        if images_left_out:
            provenance["images_left_out"] = images_left_out
        if images_missing:
            provenance["images_missing"] = images_missing
        provenance.update(debug)
        if reply.problem:
            provenance["problem"] = reply.problem
        if reply.dropped:
            # Rule 2. Naming evidence that was never supplied is fabricated
            # provenance, so it is recorded and removed rather than trusted.
            provenance["fabricated_evidence_ids"] = reply.dropped
        if reply.basis:
            provenance["basis"] = reply.basis
        if given_ids:
            provenance["given_facts_shown"] = given_ids
        handed = set(gate_record.get("handed_over_exceptions") or [])
        found = [x for x in reply.evidence
                 if x not in set(started_with) and x not in set(given_ids) and x not in handed]
        if found:
            # What the checker found in the manual itself, beyond what retrieval
            # and the plan gave it: a record of what they missed.
            provenance["found_by_checker"] = found
        cited_handed = [x for x in reply.evidence if x in handed]
        if cited_handed:
            provenance["cited_handed_over_exceptions"] = cited_handed

        status = reply.status
        manual_cited = [e for e in reply.evidence if e not in set(given_ids)]
        if status is not Status.UNKNOWN and not reply.evidence:
            # A definitive answer resting on nothing that was shown is not a
            # verification result. S3.2 keeps it unresolved instead.
            provenance["downgraded"] = ("a definitive answer cited no evidence "
                                        "that was actually supplied")
            status = Status.UNKNOWN
        elif status is not Status.UNKNOWN and not manual_cited:
            # The facts of the case say what the case is, never what the
            # manual makes of it. S3.3: "All verification remains grounded in
            # the persistent knowledge graph." An answer citing only facts
            # from the question is not grounded there.
            provenance["downgraded"] = ("a definitive answer cited only facts from "
                                        "the question and no manual text")
            status = Status.UNKNOWN

        confidence = reply.confidence if status is not Status.UNKNOWN else 0.0
        partial = [f for f in figures
                   if int(f.get("_sheets_shown") or 0)
                   and int(f.get("_sheets_shown")) < int(f.get("n_sheets")
                                                         or f.get("sheet_of") or 1)]
        if (partial or images_left_out or images_missing) and status is not Status.UNKNOWN:
            # Seeing part of a figure is weaker evidence than seeing it whole,
            # and the certificate should say so rather than carry the model's
            # own confidence unchanged.
            provenance["partial_figures"] = [f.get("figure_id") for f in partial]
            confidence = min(confidence, 0.5)

        # Rule 3: authority comes from a printed heading. Normally the
        # operation's; for a FALSE that rests on a provision printed under a
        # stronger heading, that provision's (Eq 3). Never lowered.
        authority = op.normative_authority
        cited = list(reply.evidence)
        # the basis must be something the checker says it USED, not merely
        # something it was shown
        if status is Status.FALSE and reply.basis and reply.basis in cited:
            heading = _printed_heading(reply.basis, chunks)
            if heading is not None and stronger(heading, authority):
                provenance["authority_from"] = {
                    "basis": reply.basis, "printed_heading": heading.value,
                    "declared": authority.value}
                authority = heading

        return Certificate(
            claim=op.claim, status=status,
            evidence=_evidence_objects(cited, chunks, figures, given_ids),
            normative_authority=authority,
            confidence=confidence, verifier=kind, obligation_id=op.id,
            dependencies=list(op.requires), provenance=provenance)

    return verify


def _abstain(op: Operation, kind: str, reason: str) -> Certificate:
    return Certificate(claim=op.claim, status=Status.UNKNOWN,
                       normative_authority=op.normative_authority,
                       confidence=0.0, verifier=kind, obligation_id=op.id,
                       dependencies=list(op.requires),
                       provenance={"verifier": kind, "reason": reason})


def make_llm_verifier(ask: Ask, retriever=None, query: str = "",
                      top_k: Optional[int] = None, **options):
    """Textual and definitional obligations. Plugs in as verifiers["llm"].

    options: use_pointers (default True), max_pointed_chunks (8), labels
    (True), use_lookups (True; needs `ask.converse`), max_lookups (12),
    named_exceptions (True), max_named_exceptions (6)."""
    options.pop("max_images", None)
    return _make("llm", ask, retriever, query, top_k, with_images=False, **options)


def make_vlm_verifier(ask: Ask, retriever=None, query: str = "",
                      top_k: Optional[int] = None, **options):
    """Obligations that need the figure looked at. verifiers["vlm"].

    The only difference from the LLM verifier is that the crops are passed to
    the model and a partial figure caps the confidence. Both use the same
    contract, because a visual certificate and a textual one are the same
    object with the same fields -- which is what Eq 3 says.

    options: use_pointers (default True), max_pointed_chunks (8), max_images
    (4; images beyond it are left out, recorded, and cap the confidence), and
    the same labels / lookups options as the text checker.
    """
    return _make("vlm", ask, retriever, query, top_k, with_images=True, **options)
