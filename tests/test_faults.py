"""Tests for fault injection — Table 4.

Part 1 builds one network by hand and checks each perturbation does what it
claims, and that the two metrics measure different things.
Part 2 runs the table over networks compiled from the manual.

No models, no GPU, no Qdrant.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import MergeType, Network, Operation, Status
from mrag.vine.compile import CompileError, compile_section, instantiate
from mrag.vine.experiments import Scenario, format_table
from mrag.vine.faults import (CONFIGURATIONS, Fault, FaultKind,
                              _faulted_verifier, candidate_faults, contained,
                              containment_rate, preserved, run_faulted, table4)
from mrag.vine.certificate import CertificateStore


def net_with_branches():
    """gate -> a (calculator), b (vlm), c (llm, feeds nothing) -> conjunction."""
    net = Network(query="does it hold?", terminal="s_m")
    net.states = {"s_gate", "s_a", "s_b", "s_c", "s_m"}
    net.operations = [
        Operation("gate", "the provision applies", "s_gate", [], "llm"),
        Operation("a", "the threshold is met", "s_a", ["s_gate"], "calculator"),
        Operation("b", "the layout matches the figure", "s_b", ["s_gate"], "vlm"),
        Operation("c", "an option may be used", "s_c", ["s_gate"], "llm"),
        Operation("m", "the requirements are met", "s_m", ["s_a", "s_b"],
                  "merge", merge=MergeType.CONJUNCTION,
                  merge_inputs=["s_a", "s_b"]),
    ]
    return net


NET = net_with_branches()
assert NET.validate() == [], NET.validate()
ALL_TRUE = Scenario({"gate": Status.TRUE, "a": Status.TRUE,
                     "b": Status.TRUE, "c": Status.TRUE})


# ===========================================================================
# Part 1 — built in code
# ===========================================================================

# ---- 1. only branches the answer rests on are worth corrupting ------------
targets = {f.target for f in candidate_faults(NET)}
assert targets == {"gate", "a", "b"}, targets
assert "c" not in targets      # nothing consumes s_c
assert "m" not in targets      # a merge has no evidence of its own
print("1. faults target only the branches the terminal rests on")

# ---- 2. each verifier gets faults that make sense for it ------------------
kinds = {f.target: {f.kind for f in candidate_faults(NET) if f.target == f.target}
         for f in candidate_faults(NET)}
by_target = {}
for f in candidate_faults(NET):
    by_target.setdefault(f.target, set()).add(f.kind)
assert FaultKind.FIGURE_WITHHELD in by_target["b"]        # the vlm branch
assert FaultKind.FIGURE_WITHHELD not in by_target["a"]    # not the table lookup
assert FaultKind.NUMERIC_CHANGED in by_target["a"]
print("2. a figure is only withheld from a branch that reads a figure")

# ---- 3. removing evidence leaves an unresolvable branch -------------------
op_a = NET.op("a")
store = CertificateStore()
store.add("s_gate", _faulted_verifier(ALL_TRUE, Fault(FaultKind.PROVISION_REMOVED,
                                                      "zzz"))(NET.op("gate"), store))
cert = _faulted_verifier(ALL_TRUE, Fault(FaultKind.PROVISION_REMOVED, "a"))(op_a, store)
assert cert.status is Status.UNKNOWN and cert.evidence == []
assert cert.confidence == 0.0
print("3. a removed provision leaves no evidence and no status")

# ---- 4. the other faults look exactly like healthy branches ---------------
for kind in (FaultKind.NUMERIC_CHANGED, FaultKind.DECISION_REVERSED,
             FaultKind.DISTRACTOR_INSERTED):
    cert = _faulted_verifier(ALL_TRUE, Fault(kind, "a"))(op_a, store)
    assert cert.status is not Status.UNKNOWN
    assert cert.confidence == 1.0 and cert.evidence
assert _faulted_verifier(ALL_TRUE, Fault(FaultKind.DECISION_REVERSED, "a"))(
    op_a, store).status is Status.FALSE
print("4. a changed number or a reversed decision reports itself as clean and "
      "confident")

# ---- 5. missing evidence is always contained ------------------------------
for kind in (FaultKind.PROVISION_REMOVED, FaultKind.FIGURE_WITHHELD):
    for target in ("gate", "a", "b"):
        got, clean = run_faulted("VINE", NET, ALL_TRUE, Fault(kind, target))
        assert contained(got, clean), (kind, target, got, clean)
        assert got is Status.UNKNOWN
print("5. VINE abstains on every missing-evidence fault, on every branch")

# ---- 6. containment and answer-preserved measure different things --------
# the fault reverses branch A, so the honest terminal changes from TRUE
got, clean = run_faulted("VINE", NET, ALL_TRUE,
                         Fault(FaultKind.DECISION_REVERSED, "a"))
assert clean is Status.TRUE
assert contained(got, clean) is (got is Status.UNKNOWN or got is clean)

# a configuration that abstains on everything scores perfect containment
assert contained(Status.UNKNOWN, Status.TRUE) is True
assert preserved(Status.UNKNOWN, Status.TRUE) is False
# and one that answers correctly scores on both
assert contained(Status.TRUE, Status.TRUE) and preserved(Status.TRUE, Status.TRUE)
# an abstention is never "preserved", so always-abstain cannot win the table
assert preserved(Status.UNKNOWN, Status.UNKNOWN) is False
print("6. containment alone rewards abstaining; the second column does not")

# ---- 7. an unconstrained composition propagates ---------------------------
losses = 0
for target in ("a", "b"):
    got, clean = run_faulted("Unconstrained chain", NET, ALL_TRUE,
                             Fault(FaultKind.DECISION_REVERSED, target))
    losses += not contained(got, clean)
_r, _k, n = containment_rate("Unconstrained chain", [NET], range(6))
_r2, _k2, _n2 = containment_rate("VINE", [NET], range(6))
assert _r2 > _r, (_r2, _r)
print(f"7. VINE contains {_r2:.0f}% against {_r:.0f}% for an unconstrained "
      f"composition of the same branches")

# ---- 8. the model-driven baselines are named, not invented ----------------
rows = table4([NET], range(3))
names = [r["configuration"] for r in rows]
assert "CoT" in names and "Self-Verify" in names
for r in rows:
    if r["configuration"] in ("CoT", "Self-Verify"):
        assert all(r[c] is None for c in ("text", "numeric", "visual"))
        assert r["note"] == "needs models"
assert names[-1] == "VINE"
print("8. CoT and Self-Verify appear as n/a rather than as numbers nobody ran")


# ===========================================================================
# Part 2 — on networks compiled from the manual
# ===========================================================================
def _find(name):
    env = os.environ.get(name.upper().replace(".", "_"))
    if env:
        return Path(env)
    for p in (Path("/mnt/user-data/uploads") / name,
              Path(__file__).resolve().parents[1] / name):
        if p.exists():
            return p
    return None


CHUNKS = _find("chunks.jsonl")
if CHUNKS is None:
    print("\nchunks.jsonl not found; skipped the live checks")
else:
    chunks = [json.loads(line) for line in CHUNKS.read_text().splitlines()
              if line.strip()]
    nets = []
    for s in sorted({c["section_id"] for c in chunks}):
        try:
            spec = compile_section(s, chunks)
        except CompileError:
            continue
        net, problems = instantiate(spec)
        if not problems and len(net.operations) >= 4:
            nets.append(net)
        if len(nets) >= 60:
            break

    rows = table4(nets, range(6))
    by = {r["configuration"]: r for r in rows}
    vine, chain = by["VINE"], by["Unconstrained chain"]
    seq = by["Sequential-Verify"]
    permuted = by["Sequential-Verify (permuted)"]

    # missing evidence is contained completely, whatever the modality
    assert vine["visual"] == 100.0
    # an unconstrained composition of the same branches contains far less,
    # in every modality
    for column in ("text", "numeric", "visual"):
        assert vine[column] - chain[column] > 14.0, (column, vine, chain)
    # and the reason to report both columns: the permuted chain contains at
    # least as much as VINE while preserving LESS, because it abstains more
    assert permuted["numeric"] >= vine["numeric"]
    assert permuted["answer preserved"] < vine["answer preserved"]
    print(f"\nL1. over {len(nets)} compiled networks, VINE contains "
          f"{vine['text']:.0f}% of text faults against {chain['text']:.0f}% "
          f"for an unconstrained composition")
    print(f"L2. the permuted chain contains {permuted['numeric']:.0f}% of "
          f"numeric faults to VINE's {vine['numeric']:.0f}%, but preserves "
          f"{permuted['answer preserved']:.0f}% of answers to VINE's "
          f"{vine['answer preserved']:.0f}% -- containment alone would have "
          f"ranked it above VINE")
    # Sequential-Verify in document order matches VINE here, because the
    # compiled networks come out already in dependency order. That is a
    # property of this compiler, not a general result, and it is asserted as
    # such rather than papered over.
    assert seq["answer preserved"] <= vine["answer preserved"]

print("\nALL FAULT INJECTION TESTS PASSED")
