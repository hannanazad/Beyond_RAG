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
   simply does not ask.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .certificate import Authority, Certificate, CertificateStore, Evidence, Status
from .network import Operation

log = logging.getLogger("mrag.vine.model_verifiers")

__all__ = ["Ask", "make_llm_verifier", "make_vlm_verifier",
           "certificates_for_retrieval", "parse_model_reply", "build_prompt"]

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
 "confidence": <number between 0 and 1>,
 "reason": "<one or two sentences>"}

status
  TRUE     the evidence shown establishes the claim
  FALSE    the evidence shown refutes it
  UNKNOWN  the evidence shown does not settle it

Choose UNKNOWN whenever the evidence is absent, partial, or about a
different situation. UNKNOWN is a correct answer and is preferred to a guess.
Do not reason from general knowledge of traffic engineering; decide only from
the evidence listed below.

evidence
  the ids of the items you actually used, copied exactly from the list.
  Do not name anything that is not in the list."""


def _evidence_block(chunks: Sequence[Dict[str, Any]],
                    figures: Sequence[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """The numbered evidence, and the ids a reply is allowed to cite."""
    lines: List[str] = []
    allowed: List[str] = []
    for c in chunks:
        cid = str(c.get("chunk_id") or "")
        if not cid:
            continue
        allowed.append(cid)
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
                 established: Sequence[Certificate] = ()) -> Tuple[str, List[str]]:
    """The prompt for ONE obligation, and the ids it may cite.

    The claim is the obligation, not the user's question. S3.3 is explicit
    that evidence is retrieved for "the obligation currently being verified",
    and asking the model the original question here would invite it to answer
    that instead -- which is the single-shot RAG this architecture replaces.
    """
    evidence, allowed = _evidence_block(chunks, figures)
    known = "\n".join(
        f"- {c.claim} => {c.status.value}" for c in established
        if c.status is not Status.UNKNOWN) or "(nothing yet)"
    parts = [
        "You are checking ONE claim against the evidence below.",
        "",
        f"CLAIM\n{op.claim}",
        "",
        f"ALREADY ESTABLISHED\n{known}",
        "",
        f"EVIDENCE\n{evidence}",
        "",
        _CONTRACT,
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

    return Reply(status, kept, confidence, str(data.get("reason", "")).strip(),
                 dropped)


# --------------------------------------------------------------------------- #
# 4. The verifiers
# --------------------------------------------------------------------------- #
def _evidence_objects(ids: Sequence[str],
                      chunks: Sequence[Dict[str, Any]],
                      figures: Sequence[Dict[str, Any]]) -> List[Evidence]:
    chunk_ids = {str(c.get("chunk_id")) for c in chunks}
    out: List[Evidence] = []
    inferred = {str(c.get("chunk_id")): bool(c.get("authority_inferred"))
                for c in chunks}
    for ident in ids:
        if ident in chunk_ids:
            out.append(Evidence("chunk", ident, inferred.get(ident, False)))
        elif ident.lower().startswith("table"):
            out.append(Evidence("table", ident))
        else:
            out.append(Evidence("figure", ident))
    return out


def _make(kind: str, ask: Ask, retriever=None, query: str = "",
          top_k: Optional[int] = None, with_images: bool = False):
    def verify(op: Operation, store: CertificateStore) -> Certificate:
        chunks: List[Dict[str, Any]] = []
        figures: List[Dict[str, Any]] = []
        debug: Dict[str, Any] = {}

        # ---- Eq 5: evidence for THIS obligation, given what is known ----
        if retriever is not None:
            try:
                got = retriever.retrieve_for_obligation(
                    query or op.claim, op.claim,
                    certificates=certificates_for_retrieval(store),
                    top_k=top_k)
                chunks, figures = list(got.chunks), list(got.figures)
                debug = {k: got.debug.get(k) for k in
                         ("established_sections", "established_figures",
                          "established_tables", "established_notes")
                         if got.debug.get(k)}
            except Exception as e:                            # noqa: BLE001
                # Retrieval failing is missing evidence, not a refutation.
                return _abstain(op, kind, f"retrieval failed: {e!r}")

        if not chunks and not figures:
            return _abstain(op, kind, "no evidence was retrieved for this "
                                      "obligation")

        established = [c for c in store.all() if c.status is not Status.UNKNOWN]
        prompt, allowed = build_prompt(op, chunks, figures, established)

        images: List[str] = []
        if with_images:
            for f in figures:
                for path in (f.get("image_paths") or [f.get("image_path")]):
                    if path:
                        images.append(str(path))

        try:
            raw = ask(prompt, images)
        except Exception as e:                                # noqa: BLE001
            # S3.2: a crashed tool has established nothing.
            return _abstain(op, kind, f"the model call failed: {e!r}")

        reply = parse_model_reply(raw, allowed)
        provenance: Dict[str, Any] = {
            "verifier": kind,
            "reason": reply.reason,
            "evidence_offered": allowed,
            "images_shown": len(images),
            "raw_reply": (raw or "")[:2000],   # S3.4: the trace is auditable
        }
        provenance.update(debug)
        if reply.problem:
            provenance["problem"] = reply.problem
        if reply.dropped:
            # Rule 2. Naming evidence that was never supplied is fabricated
            # provenance, so it is recorded and removed rather than trusted.
            provenance["fabricated_evidence_ids"] = reply.dropped

        status = reply.status
        if status is not Status.UNKNOWN and not reply.evidence:
            # A definitive answer resting on nothing that was shown is not a
            # verification result. S3.2 keeps it unresolved instead.
            provenance["downgraded"] = ("a definitive answer cited no evidence "
                                        "that was actually supplied")
            status = Status.UNKNOWN

        confidence = reply.confidence if status is not Status.UNKNOWN else 0.0
        partial = [f for f in figures
                   if int(f.get("_sheets_shown") or 0)
                   and int(f.get("_sheets_shown")) < int(f.get("n_sheets")
                                                         or f.get("sheet_of") or 1)]
        if partial and status is not Status.UNKNOWN:
            # Seeing part of a figure is weaker evidence than seeing it whole,
            # and the certificate should say so rather than carry the model's
            # own confidence unchanged.
            provenance["partial_figures"] = [f.get("figure_id") for f in partial]
            confidence = min(confidence, 0.5)

        return Certificate(
            claim=op.claim, status=status,
            evidence=_evidence_objects(reply.evidence, chunks, figures),
            # Rule 3: authority comes from the printed heading, via the
            # operation. The model is never asked and never consulted.
            normative_authority=op.normative_authority,
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
                      top_k: Optional[int] = None):
    """Textual and definitional obligations. Plugs in as verifiers["llm"]."""
    return _make("llm", ask, retriever, query, top_k, with_images=False)


def make_vlm_verifier(ask: Ask, retriever=None, query: str = "",
                      top_k: Optional[int] = None):
    """Obligations that need the figure looked at. verifiers["vlm"].

    The only difference from the LLM verifier is that the crops are passed to
    the model and a partial figure caps the confidence. Both use the same
    contract, because a visual certificate and a textual one are the same
    object with the same fields -- which is what Eq 3 says.
    """
    return _make("vlm", ask, retriever, query, top_k, with_images=True)
