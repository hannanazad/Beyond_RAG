"""A second look at the plan before it is checked (14 Nov 2026).

The parser (Qwen) writes the plan. Two kinds of slip were left that no code
rule can see, because they are about meaning:
  - a provision that bears on the question is marked "not related", so no
    check rests on it and the answer never mentions it;
  - a part of the question is "answered" by checks whose results do not answer
    it as it is asked (for example, "is the substitution permitted?" answered
    only by "this provision does not prohibit it", or never checked against
    the Standard that requires what the case removes).

Here a different model (the checker model, Sonnet) reads the question, the
plan and every Standard, Guidance and Option shown, and names what is
missing. It does not answer the question and decides no check. Each thing it
names becomes one plain check, like the checks the code adds for a provision
left unaccounted (parser.add_checks_for_unaccounted):
  - type "classification", decided by the language-model checker;
  - at the heading of the provision it rests on, which must be one shown;
  - for a provision marked "not related": it joins no merge, so the answer
    reports it among the other checks;
  - for a part of the question: it is also named in that part's
    "answered_by", so the answer gives its result under that part.
The plan's own checks and structure are never changed, and the added checks
are decided after them, on their own (run_added_checks), so no review result
reaches a check of the plan. At most MAX_ADD checks are added, at most one per
provision and at most MAX_NOT_RELATED for provisions marked "not related". If the reply cannot be read, or the plan would not build with the
additions, the plan is used as it was and the record says why.

No question and no answer of a test set is read here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .compile import NetworkSpec, Obligation
from .network import ObligationType

MAX_ADD = 8
MAX_NOT_RELATED = 3            # of them, at most this many for a provision marked "not related"
NORMATIVE = ("Standard", "Guidance", "Option")

REVIEW_TASK = """You review a verification plan that another model wrote for a question about
the Manual on Uniform Traffic Control Devices (MUTCD, 11th Edition). You do not
answer the question and you do not decide any check. You look only for what
the plan has left out.

The plan lists the facts of the case, the parts of the question, and checks.
Each check rests on one provision shown below. Every Standard, Guidance and
Option shown is either checked by the plan or marked "not related" with the
plan's reason.

Look for two things.

1. A provision marked "not related" that does bear on the question: a stated
   fact of the case falls under it, and a traffic engineer answering this
   question would take it into account, because it requires, recommends or
   allows something about the case or about one of the parts asked. A
   provision about another device, place, road or situation than the case is
   not related; leave it. Name only the few that matter most.

2. A part of the question whose checks do not answer it as it is asked:
   - A part that asks whether something is permitted, acceptable or allowed
     is answered only by checks against the provisions that could require or
     forbid something about it, Standards included. A check that a provision
     does not prohibit something does not answer it (Section 1B.03: not
     prohibited does not mean allowed).
   - A part about a case that removes, replaces or changes something a
     provision requires is answered by a check of the changed case against
     that provision.
   - A part that asks whether a chosen display, device, layout or option
     suits the case is answered by a check that what it shows or does fits
     the facts of the case.
   - A part that asks which heading (Standard, Guidance or Option) governs
     something is answered by a check of that heading here.

For each thing missing, give one check to add. A check you add is decided on
its own, after the plan's checks, and reported in the answer; it never
changes, relaxes or excuses another check's result. Add a check only where
the answer would be wrong or incomplete without it."""

REVIEW_CONTRACT = """REPLY

One JSON object and nothing else:
{"add": [
  {"for": "<not_related, or the id of the part of the question, such as a2>",
   "provision": "<the id of a Standard, Guidance or Option shown above, without brackets>",
   "claim": "<the check: one statement>",
   "why": "<one sentence: what the plan left out>"}
]}

The claim:
- is one statement, never a question, about the case in the question,
  measured against that provision: TRUE means the case meets it. When the
  part asks what the manual requires, recommends or allows rather than
  whether the case complies, the claim states what the manual requires,
  recommends or allows in this situation, and TRUE means the manual says so;
- carries the values, units and conditions it is about, as the facts state
  them, because the checker sees the claim, the facts and the manual, never
  the question;
- names the case it is about when the facts describe several labelled cases,
  and is about one case only;
- joins no reason ("because ...") and no conclusion ("..., so ...").

Add a check only where something is missing; do not repeat a check the plan
has, and give at most one check for each provision. At most """ + str(MAX_ADD) + """ checks, of
which at most """ + str(MAX_NOT_RELATED) + """ for provisions marked "not related", the most important
first. If nothing is missing, reply {"add": []}."""

PROMPT_SHA256 = hashlib.sha256((REVIEW_TASK + REVIEW_CONTRACT).encode()).hexdigest()

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)


def _cid(x: Any) -> str:
    return str(x or "").strip().strip("[]").strip()


def _normative(chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for c in chunks:
        cid = _cid(c.get("chunk_id"))
        if cid and cid not in seen and str(c.get("content_type") or "") in NORMATIVE:
            seen.add(cid)
            out.append(c)
    return out


def _paragraph(c: Dict[str, Any]) -> Tuple[str, str]:
    return str(c.get("section_id") or ""), str(c.get("ordinal") or "")


def _text(c: Dict[str, Any], limit: int = 500) -> str:
    lead = str(c.get("lead_in") or "").strip()
    text = " ".join(x for x in (lead, str(c.get("text") or "").strip()) if x)
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


def build_review_prompt(question: str, spec: NetworkSpec, chunks: Sequence[Dict[str, Any]]) -> str:
    """The question, the plan and every Standard, Guidance and Option shown."""
    claims = {o.id: o for o in spec.obligations}
    merges = {m.id: m for m in spec.merges}
    entries = {_cid(p.get("id")): p for p in spec.provisions}

    def line(i: str) -> str:
        if i in claims:
            o = claims[i]
            return f"   - {i} [{o.authority.value if hasattr(o.authority, 'value') else o.authority}] {o.claim}"
        if i in merges:
            m = merges[i]
            how = (f"exception merge: rule {m.inputs[0]}, exceptions {', '.join(m.inputs[1:])}"
                   if m.kind == "exception" and m.inputs else f"{m.kind} of {', '.join(m.inputs)}")
            return f"   - {i} ({how}) {m.claim}"
        return f"   - {i}"

    parts = [REVIEW_TASK, "", "QUESTION", (question or "").strip(), "", "FACTS OF THE CASE (as the plan lists them)"]
    parts += [f"- {f.id}: {f.text}" for f in spec.facts] or ["(none)"]
    parts += ["", "PARTS OF THE QUESTION, AND THE CHECKS THE PLAN SAYS ANSWER EACH"]
    for a in spec.asked:
        parts.append(f"{a.id}. {a.ask}")
        parts += [line(i) for i in a.answered_by] or ["   (no check)"]
    parts += ["", "CHECKS IN THE PLAN (id [heading] claim -- the provision it rests on)"]
    for o in spec.obligations:
        auth = o.authority.value if hasattr(o.authority, "value") else o.authority
        parts.append(f"- {o.id} [{auth}] {o.claim} -- {o.source_chunk}")
    parts += ["", "STANDARDS, GUIDANCE AND OPTIONS SHOWN TO THE PLAN"]
    rest_on: Dict[str, List[str]] = {}
    for o in spec.obligations:
        rest_on.setdefault(_cid(o.source_chunk), []).append(o.id)
    for c in _normative(chunks):
        cid = _cid(c.get("chunk_id"))
        sec, para = _paragraph(c)
        e = entries.get(cid) or {}
        by = list(dict.fromkeys(list(e.get("checked_by") or []) + rest_on.get(cid, [])))
        status = (f"checked by {', '.join(by)}" if by else
                  f"NOT RELATED, the plan says: {str(e.get('not_related') or '').strip()}"
                  if str(e.get("not_related") or "").strip() else "not listed by the plan")
        where = f"Section {sec}" + (f" paragraph {para}" if para else "")
        parts.append(f"[{cid}] {where} ({c.get('content_type')}): {_text(c)}\n   -> {status}")
    parts += ["", REVIEW_CONTRACT]
    return "\n".join(parts)


def _find_object(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = _FENCE.sub("", text or "").strip()
    decoder = json.JSONDecoder()
    first, error = None, ""
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError as e:
            error = error or f"malformed JSON: {e}"
            continue
        if isinstance(value, dict):
            if "add" in value:
                return value, ""
            first = first or value
    if first is not None:
        return None, "the JSON object has no \"add\" list"
    return None, error or "the reply contained no JSON object"


def read_review(text: str, spec: NetworkSpec, chunks: Sequence[Dict[str, Any]]
                ) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The additions the reply asks for that can be made, and why any other
    was refused."""
    obj, err = _find_object(text)
    if obj is None:
        return [], [err]
    items = obj.get("add")
    if not isinstance(items, list):
        return [], ["\"add\" is not a list"]
    shown = {_cid(c.get("chunk_id")): c for c in _normative(chunks)}
    parts = {a.id for a in spec.asked}
    entries = {_cid(p.get("id")): p for p in spec.provisions}
    rest_on = {_cid(o.source_chunk) for o in spec.obligations}
    ok: List[Dict[str, Any]] = []
    refused: List[str] = []
    seen = set()
    used: set = set()
    n_not_related = 0
    for k, it in enumerate(items, 1):
        if not isinstance(it, dict):
            refused.append(f"item {k}: not an object")
            continue
        target = str(it.get("for") or "").strip()
        pid = _cid(it.get("provision"))
        claim = " ".join(str(it.get("claim") or "").split())
        if pid not in shown:
            refused.append(f"item {k}: provision {pid!r} is not a Standard, Guidance or Option shown")
            continue
        if not claim or claim.endswith("?") or len(claim) > 800:
            refused.append(f"item {k}: the claim is empty, a question or too long")
            continue
        if target == "not_related":
            e = entries.get(pid) or {}
            if not str(e.get("not_related") or "").strip() or e.get("checked_by") or pid in rest_on:
                refused.append(f"item {k}: {pid} is not marked not related in the plan")
                continue
        elif target not in parts:
            refused.append(f"item {k}: {target!r} is neither not_related nor a part of the question")
            continue
        key = (target, pid, claim.lower())
        if key in seen:
            refused.append(f"item {k}: the same check twice")
            continue
        if pid in used:
            refused.append(f"item {k}: a second check on {pid}; one check per provision")
            continue
        if target == "not_related":
            if n_not_related >= MAX_NOT_RELATED:
                refused.append(f"item {k}: more than {MAX_NOT_RELATED} checks for provisions marked not related")
                continue
            n_not_related += 1
        seen.add(key)
        used.add(pid)
        ok.append({"for": target, "provision": pid, "claim": claim,
                   "why": " ".join(str(it.get("why") or "").split())[:400]})
    if len(ok) > MAX_ADD:
        refused.append(f"{len(ok) - MAX_ADD} more checks than the {MAX_ADD} allowed were left out")
        ok = ok[:MAX_ADD]
    return ok, refused


def apply_review(spec: NetworkSpec, additions: Sequence[Dict[str, Any]],
                 chunks: Sequence[Dict[str, Any]]) -> Tuple[NetworkSpec, List[str]]:
    """A copy of the plan with one check per addition. Returns (plan, ids added)."""
    new = copy.deepcopy(spec)
    shown = {_cid(c.get("chunk_id")): c for c in _normative(chunks)}
    original = {_cid(p.get("id")): p for p in spec.provisions}
    taken = ({o.id for o in new.obligations} | {m.id for m in new.merges}
             | {f.id for f in new.facts} | {a.id for a in new.asked})
    asked = {a.id: a for a in new.asked}
    added: List[str] = []
    k = 0
    for it in additions:
        c = shown[it["provision"]]
        k += 1
        while f"rev{k}" in taken:
            k += 1
        oid = f"rev{k}"
        taken.add(oid)
        sec, para = _paragraph(c)
        kind = str(c.get("content_type") or "Standard")
        new.obligations.append(Obligation.from_dict({
            "id": oid, "claim": it["claim"], "type": ObligationType.CLASSIFICATION.value,
            "verifier": "llm",            # read by the language-model checker, whatever the wording
            "authority": kind.upper(), "requires": [], "guard": None,
            "evidence_hint": [{"type": "section", "id": sec, "paragraph": para}] if sec and para else [],
            "source_chunk": it["provision"]}))
        pid = it["provision"]
        rest = [p for p in new.provisions if _cid(p.get("id")) != pid]
        old = next((p for p in new.provisions if _cid(p.get("id")) == pid), None)
        entry = {"id": pid, "checked_by": list((old or {}).get("checked_by") or []) + [oid],
                 "added_by_review": True}
        said = original.get(pid)
        if said is not None and str(said.get("not_related") or "").strip():
            entry["parser_said"] = {k2: v for k2, v in said.items() if k2 != "id"}
        new.provisions = rest + [entry]
        if it["for"] in asked:
            asked[it["for"]].answered_by = list(asked[it["for"]].answered_by) + [oid]
        added.append(oid)
    return new, added


def run_added_checks(reviewed: NetworkSpec, added_ids: Sequence[str], verifiers: Dict[str, Callable],
                     execute: Callable, instantiate: Callable) -> List[Tuple[str, Any]]:
    """Decide the checks the review added, on their own: a small network of
    those checks and the facts of the case only, run after the plan's own
    network has finished. So no result of the review reaches the plan's own
    checks (they see only the plan's results as earlier results), and the
    plan's checks are exactly what they would be without the review.
    Returns [(state, certificate)] to add to the plan's store for the answer."""
    ids = [i for i in added_ids if any(o.id == i for o in reviewed.obligations)]
    if not ids:
        return []
    mini = NetworkSpec(query=reviewed.query, terminal=ids[0] if len(ids) == 1 else "review_all",
                       obligations=[copy.deepcopy(o) for o in reviewed.obligations if o.id in ids],
                       facts=copy.deepcopy(reviewed.facts), source="plan_review")
    if len(ids) > 1:
        from .compile import MergeSpec
        mini.merges = [MergeSpec(id="review_all", claim="the checks added by the review", kind="conjunction",
                                 inputs=list(ids), authority="STANDARD")]
    net, problems = instantiate(mini)
    if net is None or problems:
        return []
    trace = execute(net, verifiers)
    producer = {op.id: op.produces for op in net.operations}
    out = []
    for i in ids:
        cert = trace.store.latest(producer[i])
        if cert is not None:
            out.append((producer[i], cert))
    return out


def review_plan(question: str, spec: NetworkSpec, chunks: Sequence[Dict[str, Any]],
                ask: Callable[[str, List[str]], str],
                build: Optional[Callable[[NetworkSpec], Tuple[Any, List[str]]]] = None
                ) -> Tuple[NetworkSpec, Dict[str, Any]]:
    """(the plan to execute, the record). `ask(prompt, images)` is the
    reviewing model; `build` is compile.instantiate, to make sure the plan
    with the additions still builds. On any failure the plan is returned as
    it was."""
    record: Dict[str, Any] = {"prompt_sha256": PROMPT_SHA256, "added": [], "refused": [], "error": ""}
    if spec is None:
        record["error"] = "no plan"
        return spec, record
    prompt = build_review_prompt(question, spec, chunks)
    record["prompt_chars"] = len(prompt)
    try:
        reply = ask(prompt, [])
    except Exception as e:                                   # noqa: BLE001
        record["error"] = f"the review call failed: {e!r}"
        return spec, record
    record["reply"] = reply
    additions, refused = read_review(reply, spec, chunks)
    record["refused"] = refused
    if not additions:
        return spec, record
    new, ids = apply_review(spec, additions, chunks)
    if build is not None:
        try:
            _net, problems = build(new)
        except Exception as e:                               # noqa: BLE001
            problems = [repr(e)]
        if problems:
            record["error"] = "the plan with the added checks would not build: " + "; ".join(map(str, problems))[:600]
            return spec, record
    record["added"] = [{"id": i, **a} for i, a in zip(ids, additions)]
    return new, record
