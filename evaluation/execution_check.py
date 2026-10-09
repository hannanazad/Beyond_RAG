"""What execution did, measured without gold answers.

For each executed plan:

  certificates   every check's result (TRUE / FALSE / UNKNOWN / NOT_APPLICABLE),
                 which checker decided it, the evidence it cited and its reason
  hand-overs     calculator or rule checks that could not decide and went to
                 the text checker
  pointers       how much of the evidence the plan pointed to reached the checker
  terminal       the decision, whether it is certified, and unsupported
                 certification (a definite answer while a required check never
                 resolved)
  model calls    how many, from the cache or not, how they finished

No test question's gold answer is read or stored here. Whether a decision is
RIGHT is scored outside the pipeline.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

__all__ = ["make_exec_record", "summarize_execution", "print_execution",
           "print_exec_summary"]


def _short(text: Any, n: int = 160) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 3] + "..."


def make_exec_record(case_id: str, question: str, spec, net, trace, answer,
                     calls: Sequence[Dict[str, Any]], seconds: float,
                     plan_from_cache: Optional[bool] = None) -> Dict[str, Any]:
    """One executed plan as plain JSON."""
    ops = {o.id: o for o in (net.operations if net is not None else [])}
    certs = []
    for c in (trace.store.all() if trace is not None else []):
        op = ops.get(c.obligation_id)
        prov = c.provenance or {}
        kind = ("given" if c.verifier == "given" else
                "merge" if (op is not None and op.merge is not None) else "check")
        certs.append({
            "id": c.obligation_id,
            "kind": kind,
            "type": (op.obligation_type.value if op is not None and op.obligation_type else
                     (op.merge.value if op is not None and op.merge else "")),
            "assigned": op.verifier if op is not None else "",
            "decided_by": c.verifier,
            "status": c.status.value,
            "authority": c.normative_authority.value,
            "confidence": round(float(c.confidence or 0.0), 3),
            "evidence": [e.id for e in c.evidence],
            "pointed": prov.get("pointed_evidence") or [],
            "reason": prov.get("reason") or prov.get("error") or "",
            "handed_over_from": prov.get("handed_over_from"),
            "basis": prov.get("basis") or "",
            "authority_from": prov.get("authority_from"),
            "applicability_unknown": c.applicability_unknown(),
            "claim": c.claim,
            "provenance": prov,
        })
    terminal = trace.terminal if trace is not None else None
    return {
        "case_id": case_id, "question": question,
        "spec": spec.as_dict() if spec is not None else None,
        "plan_from_cache": plan_from_cache,
        "certificates": certs,
        "waves": trace.waves if trace is not None else [],
        "not_applicable": dict(trace.not_applicable) if trace is not None else {},
        "undecided": dict(trace.undecided) if trace is not None else {},
        "skipped": dict(trace.skipped) if trace is not None else {},
        "problems": list(trace.problems) if trace is not None else [],
        "terminal": terminal.status.value if terminal is not None else None,
        "terminal_claim": terminal.claim if terminal is not None else None,
        "unsupported_certification": (trace.unsupported_certification()
                                      if trace is not None else None),
        "answer": answer.as_dict() if answer is not None else None,
        "calls": list(calls), "seconds": round(seconds, 1),
    }


def summarize_execution(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    checks = [c for r in records for c in r["certificates"] if c["kind"] == "check"]
    by_checker = Counter((c["decided_by"], c["status"]) for c in checks)
    hand = [c for c in checks if c["handed_over_from"]]
    given = [c for r in records for c in r["certificates"] if c["kind"] == "given"]
    raised = [c for r in records for c in r["certificates"] if c.get("authority_from")]
    reasons = Counter(_short(c["reason"], 90) for c in checks
                      if c["status"] == "UNKNOWN" and c["reason"])
    calls = [x for r in records for x in r["calls"]]
    pointed = [c for c in checks if c["pointed"]]
    used_pointed = [c for c in pointed if set(c["pointed"]) & set(c["evidence"])]
    return {
        "plans": len(records),
        "terminal": dict(Counter(r["terminal"] for r in records)),
        "unsupported_certification": sum(bool(r["unsupported_certification"]) for r in records),
        "checks": len(checks),
        "check_status": dict(Counter(c["status"] for c in checks)),
        "by_checker": {f"{k[0]}:{k[1]}": v for k, v in sorted(by_checker.items())},
        "handed_over": len(hand),
        "handed_over_status": dict(Counter(f"{c['handed_over_from']['verifier']} -> {c['status']}"
                                           for c in hand)),
        "given_facts": len(given),
        "plans_with_given_facts": sum(1 for r in records
                                      if any(c["kind"] == "given" for c in r["certificates"])),
        "authority_raised": len(raised),
        "not_applicable": sum(len(r["not_applicable"]) for r in records),
        "undecided": sum(len(r["undecided"]) for r in records),
        "never_settled": sum(len(r["skipped"]) for r in records),
        "checks_given_pointed_evidence": len(pointed),
        "of_which_cited_it": len(used_pointed),
        "unknown_reasons": reasons.most_common(8),
        "model_calls": len(calls),
        "from_cache": sum(1 for x in calls if x.get("cached")),
        "finish_reasons": dict(Counter(str(x.get("finish_reason")) for x in calls)),
        "completion_tokens": sum(int((x.get("usage") or {}).get("completion_tokens") or 0)
                                 for x in calls if not x.get("cached")),
        "seconds": round(sum(r["seconds"] for r in records), 1),
    }


def print_exec_summary(s: Dict[str, Any]) -> None:
    print(f"plans executed        : {s['plans']}")
    print(f"decisions             : {s['terminal']}")
    print(f"unsupported certif.   : {s['unsupported_certification']} "
          f"(a definite decision while a required check never resolved)")
    print(f"checks                : {s['checks']}  {s['check_status']}")
    print(f"  not applicable      : {s['not_applicable']}   whether it applies unknown: "
          f"{s['undecided']}   never settled: {s['never_settled']}")
    print(f"  by checker          : {s['by_checker']}")
    print(f"  passed to text check: {s['handed_over']} checks went from an exact tool to the "
          f"text checker -> {s['handed_over_status']}")
    print(f"  authority raised    : {s.get('authority_raised', 0)} results took a stronger printed "
          f"heading from the evidence they rest on")
    print(f"  pointed evidence    : {s['checks_given_pointed_evidence']} checks were given it; "
          f"{s['of_which_cited_it']} cited some of it")
    print(f"given facts           : {s.get('given_facts', 0)} in "
          f"{s.get('plans_with_given_facts', 0)} of {s['plans']} plans (from the question, via the parser)")
    if s["unknown_reasons"]:
        print("  why UNKNOWN (most common):")
        for reason, n in s["unknown_reasons"]:
            print(f"    {n:3d}  {reason}")
    print(f"model calls           : {s['model_calls']} ({s['from_cache']} from the cache), "
          f"finish {s['finish_reasons']}, {s['completion_tokens']:,} new tokens")
    print(f"time                  : {s['seconds']:.0f}s")


def print_execution(rec: Dict[str, Any], width: int = 110) -> None:
    """One executed plan, check by check, for reading by hand."""
    print("=" * width)
    print(f"{rec['case_id']}: {_short(rec['question'], width - len(rec['case_id']) - 2)}")
    if rec.get("plan_from_cache") is not None:
        print(f"plan from the parser cache: {rec['plan_from_cache']}")
    print("-" * width)
    given = [c for c in rec["certificates"] if c["kind"] == "given"]
    for c in given:
        print(f"[given         ] {c['id']:6s} {_short(c['claim'], width - 24)}")
    if given:
        print("-" * width)
    order = [x for wave in rec["waves"] for x in wave]
    seen = set(order) | {c["id"] for c in given}
    order += [c["id"] for c in rec["certificates"] if c["id"] not in seen]
    by_id = {c["id"]: c for c in rec["certificates"] if c["kind"] != "given"}
    for oid in order:
        c = by_id.get(oid)
        if c is None:
            continue
        who = c["decided_by"]
        if c["handed_over_from"]:
            who = f"{c['handed_over_from']['verifier']} -> {who}"
        flag = "  (applicability unknown)" if c["applicability_unknown"] else ""
        print(f"[{c['status']:14s}] {oid:6s} {c['kind']:5s} {c['type']:15s} {c['authority']:8s} "
              f"by {who}{flag}")
        print(f"     claim   : {_short(c['claim'], width - 15)}")
        if c["evidence"]:
            print(f"     cited   : {', '.join(c['evidence'][:6])}"
                  + (" ..." if len(c["evidence"]) > 6 else ""))
        if c["pointed"]:
            print(f"     pointed : {', '.join(c['pointed'][:6])}"
                  + (" ..." if len(c["pointed"]) > 6 else ""))
        if c["kind"] == "merge":
            ins = (c["provenance"] or {}).get("inputs") or {}
            if ins:
                print(f"     inputs  : {ins}")
        if c["reason"]:
            print(f"     reason  : {_short(c['reason'], width - 15)}")
        if c["handed_over_from"] and c["handed_over_from"].get("reason"):
            h = c["handed_over_from"]
            print(f"     first   : {h['verifier']} said {h.get('status', 'UNKNOWN')}: "
                  f"{_short(h['reason'], width - 40)}")
        if c.get("authority_from"):
            a = c["authority_from"]
            why = (f"rests on {a['basis']}" if a.get("basis")
                   else f"failed inputs {a.get('failed_inputs')}")
            print(f"     raised  : {a.get('declared')} -> {c['authority']} ({why})")
    print("-" * width)
    print(f"decision : {rec['terminal']}   unsupported certification: "
          f"{rec['unsupported_certification']}")
    if rec.get("answer"):
        print(f"answer   : {_short(rec['answer']['text'], 600)}")
    calls = rec["calls"]
    if calls:
        print(f"model    : {len(calls)} calls, {sum(1 for x in calls if x.get('cached'))} cached, "
              f"finish {dict(Counter(str(x.get('finish_reason')) for x in calls))}, "
              f"{rec['seconds']:.0f}s")
