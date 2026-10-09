"""Checks on the semantic parser's plans that need no gold answers.

Everything here is measured against the MANUAL and the run itself:

  outcome      did the plan pass every check first time, after repair, or not
  shape        how many obligations, dependencies, guards and merges, how deep
  numbers      does every number in a claim come from the question or the
               retrieved manual text, or did the model make it up
  repeat       does the same input give the same plan

and, for the development cases only (written from random MUTCD provisions,
`retrieval_dev/manual_cases_v2.jsonl`), one check against the provision the
case was written from:

  source hit   is there an obligation that comes from that provision

No test question's gold answer, obligation list or count is read or stored
here. The test questions are run once, at the end, and their plans are saved
for scoring outside the pipeline.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEV_FILE = Path(__file__).resolve().parent / "retrieval_dev" / "manual_cases_v2.jsonl"


# --------------------------------------------------------------------------- #
# 1. The development cases -- chosen by a fixed rule, before any parser run
# --------------------------------------------------------------------------- #
def load_dev_cases(path=DEV_FILE) -> List[Dict[str, Any]]:
    """The first scenario case of each Part of the manual, plus the first
    two-section case of each kind. Eleven cases. The rule was fixed before
    any parser output was seen and is not to be changed after."""
    cases = [json.loads(l) for l in open(path) if l.strip()]
    out: List[Dict[str, Any]] = []
    seen_parts = set()
    for c in sorted((c for c in cases if c["style"] == "scenario"),
                    key=lambda c: c["case_id"]):
        if c["part"] not in seen_parts:
            seen_parts.add(c["part"])
            out.append(c)
    for style in ("two_section_linked", "two_section_unlinked"):
        first = sorted((c for c in cases if c["style"] == style),
                       key=lambda c: c["case_id"])
        if first:
            out.append(first[0])
    return out


# --------------------------------------------------------------------------- #
# 2. Shape
# --------------------------------------------------------------------------- #
def _depends(spec) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for o in spec.obligations:
        out[o.id] = list(o.requires) + (o.guard.states() if o.guard else [])
    for m in spec.merges:
        out[m.id] = list(m.inputs) + (m.guard.states() if m.guard else [])
    return out


def _levels(spec) -> Dict[str, int]:
    deps = _depends(spec)
    memo: Dict[str, int] = {}

    def level(n: str, path=()) -> int:
        if n in memo:
            return memo[n]
        if n in path:                      # a cycle never passes the checks
            return 0
        lv = 1 + max((level(d, path + (n,)) for d in deps.get(n, []) if d in deps),
                     default=0)
        memo[n] = lv
        return lv

    for n in deps:
        level(n)
    return memo


def spec_stats(spec, net=None) -> Dict[str, Any]:
    if spec is None:
        return {}
    levels = _levels(spec)
    width = Counter(levels.values())
    out = {
        "facts": len(getattr(spec, "facts", []) or []),
        "obligations": len(spec.obligations),
        "merges": len(spec.merges),
        "dependencies": sum(len(o.requires) for o in spec.obligations),
        "guards": sum(1 for x in list(spec.obligations) + list(spec.merges) if x.guard),
        "depth": max(levels.values(), default=0),
        "widest_level": max(width.values(), default=0),
        "terminal": spec.terminal,
        "terminal_is_merge": any(m.id == spec.terminal for m in spec.merges),
        "types": dict(Counter(o.type for o in spec.obligations)),
        "authority": dict(Counter(o.authority for o in spec.obligations)),
        "merge_kinds": dict(Counter(m.kind for m in spec.merges)),
        # a guarded item used as a merge input: when its guard closes, the
        # executor marks it NOT_APPLICABLE and the merge leaves it out
        # (dead-path elimination; see mrag/vine/execute.py)
        "guarded_merge_inputs": sum(1 for m in spec.merges for i in m.inputs
                                    if any(x.id == i and x.guard for x in
                                           list(spec.obligations) + list(spec.merges))),
        "source_sections": [],
    }
    if net is not None:
        out["verifiers"] = dict(Counter(o.verifier for o in net.operations
                                        if o.merge is None))
    return out


# --------------------------------------------------------------------------- #
# 3. Numbers in claims
# --------------------------------------------------------------------------- #
# Identifiers are not quantities: section, table and figure numbers, sign
# codes, and paragraph / item / note / chart numbers. Only a PLURAL word
# ("Paragraphs 3, 5, and 6") takes a list after it; "Part 2 and 45 mph" keeps
# its 45.
_ID = r"(?:\d+|[A-Z])\b"                             # 6, or a letter A-Z
_IDS = re.compile(
    r"\b\d{1,2}[A-Z]\.\d{2}\b"                       # 2C.07
    r"|\b(?i:table|figure|figures|tables)\s+[\dA-Z]+-\d+[A-Za-z]?\b"
    r"|\b\d{1,2}[A-Z]-\d+[A-Za-z]?\b"                # 2C-4
    r"|\b[A-Z]{1,3}\d{1,2}-\d+[A-Za-z]*\b"           # W1-2, R1-1, M1-7a
    r"|\b(?i:paragraphs|items|notes|charts|sheets|sections|parts|chapters)\s+" + _ID
    + r"(?:\s*(?:,?\s*and|,?\s*or|through|,)\s*" + _ID + r")*"
    r"|\b(?i:paragraph|item|note|chart|sheet|section|part|chapter)\s+" + _ID
    # a paragraph named by its heading and number: "Standard 05", "Option 13"
    + r"|\b(?:Standard|Guidance|Option|Support)\s+\d{1,2}\b")
_NUM = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?")


def _canon(n: str) -> str:
    """One spelling per number: no thousands commas, no trailing zeros."""
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def numbers_in(text: str) -> List[str]:
    return [_canon(n) for n in _NUM.findall(_IDS.sub(" ", text or ""))]


def _number_set(text: str) -> set:
    return set(numbers_in(text))


def numbers_check(spec, question: str, chunks: Sequence[Dict[str, Any]]
                  ) -> Dict[str, Any]:
    """Where each number written in a claim came from."""
    if spec is None:
        return {}
    by_id = {str(c.get("chunk_id")): c for c in chunks}
    in_question = _number_set(question)
    in_kq = set()
    for c in chunks:
        in_kq |= _number_set(f"{c.get('lead_in') or ''} {c.get('text') or ''}")
    counts = Counter()
    unsupported: List[Tuple[str, str]] = []
    for o in spec.obligations:
        src = by_id.get(o.source_chunk) or {}
        in_src = _number_set(f"{src.get('lead_in') or ''} {src.get('text') or ''}")
        for n in numbers_in(o.claim):
            if n in in_question:
                counts["question"] += 1
            elif n in in_src:
                counts["source provision"] += 1
            elif n in in_kq:
                counts["other retrieved text"] += 1
            else:
                counts["nowhere"] += 1
                unsupported.append((o.id, n))
    return {"counts": dict(counts), "nowhere": unsupported}


# --------------------------------------------------------------------------- #
# 4. Development cases only: the provision the case was written from
# --------------------------------------------------------------------------- #
def _same_paragraph(a: str, b: str) -> bool:
    """A list item belongs to its paragraph: X_itemA is part of X."""
    return a == b or a.startswith(b + "_item") or b.startswith(a + "_item")


def target_check(spec, case: Dict[str, Any], chunks: Sequence[Dict[str, Any]]
                 ) -> Dict[str, Any]:
    targets = list(case.get("target_chunk_ids") or [])
    sections = list(case.get("target_sections") or [])
    kq_ids = [str(c.get("chunk_id")) for c in chunks]
    kq_secs = {str(c.get("section_id")) for c in chunks}
    out = {"target_chunks": targets, "target_sections": sections,
           "target_chunk_in_kq": (all(any(_same_paragraph(k, t) for k in kq_ids)
                                      for t in targets) if targets else None),
           "target_sections_in_kq": all(s in kq_secs for s in sections)}
    if spec is None:
        out.update(source_hit=False, sections_hit=False)
        return out
    by_id = {str(c.get("chunk_id")): c for c in chunks}
    srcs = [o.source_chunk for o in spec.obligations if o.source_chunk]
    src_secs = {str((by_id.get(s) or {}).get("section_id")) for s in srcs}
    out["source_hit"] = (all(any(_same_paragraph(s, t) for s in srcs) for t in targets)
                         if targets else None)
    out["sections_hit"] = all(s in src_secs for s in sections)
    return out


# --------------------------------------------------------------------------- #
# 5. One record per question
# --------------------------------------------------------------------------- #
def make_record(case_id: str, question: str, kq: Dict[str, Any], spec, report,
                net=None, seconds: float = 0.0,
                case: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    chunks = kq.get("chunks") or []
    stats = spec_stats(spec, net)
    if spec is not None:
        by_id = {str(c.get("chunk_id")): c for c in chunks}
        stats["source_sections"] = sorted({str((by_id.get(o.source_chunk) or {})
                                                .get("section_id", "?"))
                                           for o in spec.obligations})
    tokens = sum(int((c.get("usage") or {}).get("completion_tokens") or 0)
                 for c in (report.calls if report else []))
    rec = {
        "case_id": case_id,
        "question": question,
        "kq_size": len(chunks),
        "kq_types": dict(Counter(str(c.get("content_type")) for c in chunks)),
        "outcome": _outcome(report),
        "attempts": report.attempts if report else 0,
        "problems": report.problems if report else [],
        "notes": report.notes if report else [],
        "spec": spec.as_dict() if spec is not None else None,
        "stats": stats,
        "numbers": numbers_check(spec, question, chunks),
        "seconds": round(seconds, 1),
        "completion_tokens": tokens,
        "calls": report.calls if report else [],
        "raw_replies": report.raw if report else [],
    }
    if case is not None:
        rec["target"] = target_check(spec, case, chunks)
    return rec


def _outcome(report) -> str:
    if report is None:
        return "not run"
    if report.source != "semantic_parser":
        return report.source or "failed"
    return "valid first time" if report.attempts == 1 else "valid after repair"


def same_spec(a, b) -> bool:
    if a is None or b is None:
        return a is b
    da, db = a.as_dict(), b.as_dict()
    return json.dumps(da, sort_keys=True) == json.dumps(db, sort_keys=True)


# --------------------------------------------------------------------------- #
# 6. Summary
# --------------------------------------------------------------------------- #
def summarize(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    ok = [r for r in records if r["outcome"].startswith("valid")]
    out: Dict[str, Any] = {
        "n": n,
        "outcome": dict(Counter(r["outcome"] for r in records)),
        "mean_attempts": round(sum(r["attempts"] for r in records) / n, 2) if n else 0,
        "mean_seconds": round(sum(r["seconds"] for r in records) / n, 1) if n else 0,
        "mean_completion_tokens": (round(sum(r["completion_tokens"] for r in records) / n)
                                   if n else 0),
    }
    if ok:
        st = [r["stats"] for r in ok]
        out.update({
            "plans_with_facts": sum(1 for s in st if s.get("facts")),
            "mean_facts": round(sum(s.get("facts", 0) for s in st) / len(st), 1),
            "mean_obligations": round(sum(s["obligations"] for s in st) / len(st), 1),
            "plans_with_dependencies": sum(1 for s in st if s["dependencies"]),
            "plans_with_guards": sum(1 for s in st if s["guards"]),
            "plans_with_merges": sum(1 for s in st if s["merges"]),
            "mean_depth": round(sum(s["depth"] for s in st) / len(st), 1),
            "types": dict(sum((Counter(s["types"]) for s in st), Counter())),
            "authority": dict(sum((Counter(s["authority"]) for s in st), Counter())),
            "verifiers": dict(sum((Counter(s.get("verifiers", {})) for s in st), Counter())),
            "merge_kinds": dict(sum((Counter(s["merge_kinds"]) for s in st), Counter())),
            "plans_with_guarded_merge_inputs": sum(1 for s in st if s["guarded_merge_inputs"]),
            "numbers": dict(sum((Counter(r["numbers"].get("counts", {})) for r in ok),
                                Counter())),
        })
    dev = [r for r in records if "target" in r]
    if dev:
        reach = [r for r in dev if r["target"]["target_chunk_in_kq"]]
        out["dev"] = {
            "cases": len(dev),
            "target_provision_reached_parser": len(reach),
            "plan_uses_target_provision": sum(1 for r in reach if r["target"]["source_hit"]),
            "plan_uses_every_target_section": sum(1 for r in dev
                                                  if r["target"]["sections_hit"]),
        }
    return out


def print_summary(s: Dict[str, Any]) -> None:
    print(f"  questions                 : {s['n']}")
    print(f"  outcome                   : {s['outcome']}")
    print(f"  mean attempts             : {s['mean_attempts']}")
    print(f"  mean seconds / tokens     : {s['mean_seconds']} s / {s['mean_completion_tokens']} tokens")
    if "mean_obligations" in s:
        if "plans_with_facts" in s:
            print(f"  plans with given facts    : {s['plans_with_facts']} (mean {s['mean_facts']} facts)")
        print(f"  mean obligations          : {s['mean_obligations']}")
        print(f"  plans with dependencies   : {s['plans_with_dependencies']}")
        print(f"  plans with guards         : {s['plans_with_guards']}")
        print(f"  plans with merges         : {s['plans_with_merges']}")
        print(f"  mean depth                : {s['mean_depth']}")
        print(f"  obligation types          : {s['types']}")
        print(f"  authority                 : {s['authority']}")
        print(f"  checkers assigned         : {s['verifiers']}")
        print(f"  merge kinds               : {s['merge_kinds']}")
        print(f"  plans with a guarded item as a merge input: {s['plans_with_guarded_merge_inputs']}")
        print(f"  numbers in claims, from   : {s['numbers']}")
    if "dev" in s:
        d = s["dev"]
        print(f"  DEV: provision reached parser       : {d['target_provision_reached_parser']}/{d['cases']}")
        print(f"  DEV: plan uses that provision       : {d['plan_uses_target_provision']}"
              f"/{d['target_provision_reached_parser']}")
        print(f"  DEV: plan uses every target section : {d['plan_uses_every_target_section']}/{d['cases']}")


def print_plan(rec: Dict[str, Any], width: int = 100) -> None:
    """One plan, readable: terminal, obligations with their sources, merges."""
    print(f"[{rec['case_id']}] {rec['outcome']} in {rec['attempts']} attempt(s), "
          f"{rec['seconds']} s, Kq {rec['kq_size']}")
    spec = rec.get("spec")
    if not spec:
        for g in rec.get("problems") or []:
            for p in g[:6]:
                print("   problem:", str(p)[:width])
        return
    print(f"   terminal: {spec['terminal']}")
    for f in spec.get("facts") or []:
        print(f"   {f['id']:5s} GIVEN       {f['fact'][:width]}")
    for o in spec["obligations"]:
        req = f" requires {o['requires']}" if o.get("requires") else ""
        grd = f" guard {json.dumps(o['guard'])}" if o.get("guard") else ""
        hint = ", ".join(f"{h.get('type')}:{h.get('id')}" for h in o.get("evidence_hint") or [])
        print(f"   {o['id']:5s} {o['type']:15s} {o['authority']:8s} <- {o.get('source_chunk')}{req}{grd}")
        print(f"         {o['claim'][:width]}" + (f"\n         hints: {hint}" if hint else ""))
    for m in spec["merges"]:
        grd = f" guard {json.dumps(m['guard'])}" if m.get("guard") else ""
        print(f"   {m['id']:5s} {m['kind'].upper():11s} {m.get('authority','')} of {m['inputs']}{grd}"
              f"  -- {m['claim'][:width - 30]}")
    if rec["numbers"].get("nowhere"):
        print(f"   numbers found in no input: {rec['numbers']['nowhere']}")
