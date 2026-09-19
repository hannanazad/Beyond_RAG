"""Tests for the compiler — Kq -> Nq.

Part 1 is the intermediate representation, the deterministic instantiator and
the repair path, all built in code.
Part 2 compiles real sections out of `chunks.jsonl`, sweeps the whole manual,
and runs one compiled network on the real deterministic verifiers.

No models, no GPU, no Qdrant.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import (Authority, Certificate, CertificateStore, Status,
                       execute, make_calculator, make_rule_evaluator)
from mrag.vine.compile import (CompileError, GuardSpec, MergeSpec, NetworkSpec,
                               Obligation, assign_verifier, compile_section,
                               instantiate, repair_request)
from mrag.vine.table_data import load as load_tables


def spec_of(obligations, merges=(), terminal="o1", query="q"):
    return NetworkSpec(query=query, terminal=terminal,
                       obligations=[Obligation.from_dict(o) for o in obligations],
                       merges=[MergeSpec.from_dict(m) for m in merges])


OK = {"id": "o1", "claim": "the provision applies", "type": "applicability"}


# ===========================================================================
# Part 1 — built in code
# ===========================================================================

# ---- 1. the IR catches its own errors, in the parser's vocabulary ---------
assert spec_of([OK]).problems() == []

bad = spec_of([OK, {"id": "o1", "claim": "again"}])
assert any("duplicate ids" in p for p in bad.problems())

bad = spec_of([{**OK, "requires": ["o9"]}])
assert any("requires 'o9'" in p for p in bad.problems())

bad = spec_of([{**OK, "authority": "SUPPORT"}])
assert any("SUPPORT" in p for p in bad.problems())

bad = spec_of([OK], [{"id": "m1", "kind": "conjunction", "inputs": ["o1"]}],
              terminal="m1")
assert any("at least two inputs" in p for p in bad.problems())

bad = spec_of([OK], terminal="nowhere")
assert any("terminal 'nowhere'" in p for p in bad.problems())
print("1. the IR rejects duplicates, dangling refs, SUPPORT, thin merges, "
      "bad terminals")

# ---- 2. an exception merge's first input is the base, not the exception ----
bad = spec_of([{"id": "o1", "claim": "except where...", "type": "exception"},
               {"id": "o2", "claim": "the rule", "type": "applicability"}],
              [{"id": "m1", "kind": "exception", "inputs": ["o1", "o2"]}],
              terminal="m1")
assert any("is itself an exception" in p for p in bad.problems())
good = spec_of([{"id": "o1", "claim": "the rule", "type": "applicability"},
                {"id": "o2", "claim": "except where...", "type": "exception"}],
               [{"id": "m1", "kind": "exception", "inputs": ["o1", "o2"]}],
               terminal="m1")
assert good.problems() == []
print("2. an exception merge must put the base rule first")

# ---- 3. guards are data, and only data ------------------------------------
g = GuardSpec.from_dict({"all": [{"state": "o1", "status": "TRUE"},
                                 {"not": {"state": "o2", "status": "FALSE"}}]})
assert g.states() == ["o1", "o2"]
assert g.describe() == "(o1 is TRUE and not (o2 is FALSE))"
for junk, why in [({"state": "o1", "status": "MAYBE"}, "invented status"),
                  ({"python": "os.system('x')"}, "code"),
                  ("o1 is TRUE", "prose"),
                  ({"all": [{"state": "o1"}]}, "one-part all")]:
    try:
        GuardSpec.from_dict(junk)
        raise AssertionError(f"{why} was accepted as a guard")
    except CompileError:
        pass
print("3. guards use a closed vocabulary; prose and code are rejected")

# ---- 4. a guard becomes a real gate at run time ----------------------------
spec = spec_of([{"id": "o1", "claim": "classification", "type": "classification"},
                {"id": "o2", "claim": "only if classified", "type": "applicability",
                 "requires": ["o1"],
                 "guard": {"state": "o1", "status": "TRUE"}}],
               terminal="o2")
net, problems = instantiate(spec)
assert problems == [], problems
op2 = net.op("o2")
assert op2.guard is not None and op2.guard_desc == "o1 is TRUE"

store = CertificateStore()
store.add("s_o1", Certificate(claim="c", status=Status.FALSE))
assert op2.guard(store) is False
store.add("s_o1", Certificate(claim="c", status=Status.TRUE))
assert op2.guard(store) is True
print("4. a guard in the spec becomes the function Eq 4 needs")

# ---- 5. a spec problem stops instantiation before a network is built -------
net, problems = instantiate(spec_of([{**OK, "requires": ["ghost"]}]))
assert problems and not net.operations
print("5. a spec naming a missing obligation is never half-built")

# ---- 6. verifier assignment by rule ---------------------------------------
def v(**kw):
    return assign_verifier(Obligation.from_dict({**OK, **kw}))

assert v(type="cross_reference") == "cross_reference_resolver"
assert v(type="visual") == "vlm"
# the TYPE decides the tool; a hint only says where the evidence is
assert v(type="numerical",
         evidence_hint=[{"type": "table", "id": "Table 6B-4"}]) == "calculator"
assert v(type="numerical") == "symbolic"
assert v(evidence_hint=[{"type": "figure", "id": "Figure 2C-1"}]) == "vlm"
# A classification that cites a table is still a classification. Sending it to
# the calculator, as an earlier rule did, guaranteed an abstention: a lookup
# cannot decide "the sign installed in advance of the curve is a Curve sign".
assert v(type="classification",
         evidence_hint=[{"type": "figure", "id": "Figure 2C-1"},
                        {"type": "table", "id": "Table 2C-4"}]) == "llm"
# bare ids are normalised to what the verifiers actually look up
from mrag.vine.compile import Obligation as _Ob
_o = _Ob.from_dict({**OK, "evidence_hint": [{"type": "table", "id": "2C-4"},
                                            {"type": "figure", "id": "2C-1"}]})
assert [h["id"] for h in _o.evidence_hint] == ["Table 2C-4", "Figure 2C-1"]
assert v(claim="the major-street speed exceeds 40 mph") == "symbolic"
assert v(claim="the design is appropriate for the site") == "llm"
# a whole paragraph that CONTAINS a comparison is not the comparison
para = ("A Turn (W1-1) sign should be used instead of a Curve (W1-2) sign in "
        "advance of a horizontal curve that has an advisory speed of 30 mph "
        "or less.")
assert v(claim=para) == "llm"
assert v(claim=para, verifier="calculator") == "calculator"   # parser may override
print("6. verifier by rule: table beats figure, and a paragraph is not a "
      "comparison")

# ---- 7. repair speaks the parser's language -------------------------------
broken = spec_of([{"id": "o1", "claim": "a", "requires": ["o2"]},
                  {"id": "o2", "claim": "b", "requires": ["o1"]}], terminal="o1")
net, problems = instantiate(broken)
req = repair_request(broken, problems)
assert req["status"] == "rejected"
assert all("s_o" not in p for p in req["problems"]), req["problems"]
assert req["obligation_ids"] == ["o1", "o2"]
assert "spec" in req and req["rules"]
print("7. repair returns ids the parser used, not internal state names")

# ---- 8. a cycle is caught -------------------------------------------------
cyc = spec_of([{"id": "o1", "claim": "a", "requires": ["o2"]},
               {"id": "o2", "claim": "b", "requires": ["o1"]}], terminal="o1")
_net, problems = instantiate(cyc)
assert any("cycle" in p for p in problems), problems
print("8. a dependency cycle is rejected, not executed")

# ---- 9. the IR round-trips through JSON -----------------------------------
original = spec_of([{"id": "o1", "claim": "a", "type": "classification"},
                    {"id": "o2", "claim": "b", "requires": ["o1"],
                     "guard": {"any": [{"state": "o1", "status": "TRUE"},
                                       {"state": "o1", "status": "RESOLVED"}]}}],
                   [{"id": "m1", "kind": "conjunction", "inputs": ["o1", "o2"]}],
                   terminal="m1")
again = NetworkSpec.from_json(original.to_json())
assert again.as_dict() == original.as_dict()
assert again.problems() == []
print("9. the IR survives a JSON round trip unchanged")

# ---- 10. junk from a parser is an error, not a crash ----------------------
for junk in ['{"obligations": [{"claim": "no id"}]}', "not json at all",
             '{"obligations": [{"id": "o1"}]}']:
    try:
        NetworkSpec.from_json(junk)
        raise AssertionError(f"accepted {junk[:30]!r}")
    except CompileError:
        pass
print("10. malformed parser output raises CompileError, never a traceback")


# ===========================================================================
# Part 2 — real sections
# ===========================================================================
def _find(name):
    if os.environ.get(name.upper().replace(".", "_")):
        return Path(os.environ[name.upper().replace(".", "_")])
    for p in (Path("/mnt/user-data/uploads") / name,
              Path(__file__).resolve().parents[1] / name):
        if p.exists():
            return p
    return None


CHUNKS = _find("chunks.jsonl")
if CHUNKS is None:
    print("\nchunks.jsonl not found; skipped the live checks")
else:
    chunks = [json.loads(line) for line in CHUNKS.read_text().splitlines() if line.strip()]

    # ---- L1. a section with a gate and a wide fork ------------------------
    spec = compile_section("2C.07", chunks)
    net, problems = instantiate(spec)
    assert problems == [], problems
    assert spec.obligations[0].id == "o1"
    # the gate is the opening Standard, which is answered by a table lookup
    assert net.op("o1").verifier == "calculator"
    assert all(net.op(o.id).requires == ["s_o1"]
               for o in spec.obligations if o.id != "o1")

    stub = (lambda op, st: Certificate(claim=op.claim, status=Status.TRUE,
                                       confidence=0.5,
                                       normative_authority=op.normative_authority))
    verifiers = {k: stub for k in ("llm", "vlm", "calculator", "symbolic",
                                   "cross_reference_resolver")}
    trace = execute(net, verifiers)
    assert trace.waves[0] == ["o1"]
    assert len(trace.waves[1]) == 7, trace.waves
    assert trace.synchronization_depth == 3 and trace.operations_run == 9
    print(f"\nL1. 2C.07 -> 9 operations in depth {trace.synchronization_depth}; "
          f"the 7 branches after the gate run together")

    # ---- L2. a section with real exception branches -----------------------
    spec = compile_section("2N.02", chunks)
    net, problems = instantiate(spec)
    assert problems == []
    dec = net.op("m_decision")
    assert dec.merge.value == "exception"
    # the base comes first; the relaxing branches follow
    assert dec.merge_inputs[0] == "s_m_base" and len(dec.merge_inputs) == 3
    base = net.op("m_base")
    assert all(Authority(net.op(i[2:]).normative_authority).value in
               ("STANDARD", "GUIDANCE") for i in base.merge_inputs)
    print("L2. 2N.02 -> a base of 5 with 2 exception branches, base first")

    # ---- L3. every section in the manual ----------------------------------
    sections = sorted({c["section_id"] for c in chunks})
    built = rejected = empty = 0
    for s in sections:
        try:
            sp = compile_section(s, chunks)
        except CompileError:
            empty += 1
            continue
        _n, probs = instantiate(sp)
        if probs:
            rejected += 1
            print("   REJECTED", s, probs)
        else:
            built += 1
    assert rejected == 0, f"{rejected} sections produced invalid networks"
    print(f"L3. swept {len(sections)} sections: {built} compiled and validated, "
          f"{rejected} rejected, {empty} with no normative material")

    # ---- L4. a compiled network on the REAL deterministic verifiers -------
    TABLES = _find("mutcd_tables.jsonl")
    if TABLES is None:
        print("L5. mutcd_tables.jsonl not found; skipped the live-verifier run")
    else:
        tables = load_tables(TABLES)
        spec = compile_section("2C.07", chunks)
        net, _ = instantiate(spec)
        live = {"calculator": make_calculator(tables),
                "symbolic": make_rule_evaluator(tables),
                "cross_reference_resolver": stub, "llm": stub, "vlm": stub}
        trace = execute(net, live)
        assert trace.problems == []
        assert trace.terminal is not None
        # the calculator cannot answer 2C.07's gate from the text alone, and
        # says so rather than inventing a value
        gate = trace.store.latest("s_o1")
        assert gate.verifier == "calculator" and gate.status is Status.UNKNOWN
        assert "reason" in gate.provenance
        # and one UNKNOWN in a conjunction leaves the terminal unresolved,
        # not refuted
        assert trace.terminal.status is Status.UNKNOWN
        assert not trace.unsupported_certification()
        print("L4. the same network on the real calculator: the gate abstains, "
              "the terminal stays UNKNOWN, and UCR is False")

print("\nALL COMPILER TESTS PASSED")
