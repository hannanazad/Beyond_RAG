"""Tests for the experiment harness — Tables 3 and 5.

Part 1 builds one small network by hand and checks each configuration fails
in the specific way it is supposed to.
Part 2 runs both tables over networks compiled from the real manual.

No models, no GPU, no Qdrant.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import Authority, MergeType, Network, Operation, Status
from mrag.vine.compile import CompileError, compile_section, instantiate
from mrag.vine.experiments import (ABLATIONS, Scenario, format_table,
                                   make_scenario, reference_terminal,
                                   run_ablation, run_sequential, run_vine,
                                   table3, table5)


def gated_network():
    """gate -> two independent branches -> conjunction.

    The smallest shape that can tell these configurations apart: one branch
    resolves, the other does not, and the question is what the machinery does
    about the one that did not.
    """
    net = Network(query="does the section hold?", terminal="s_m")
    net.states = {"s_gate", "s_a", "s_b", "s_m"}
    net.operations = [
        Operation("gate", "the provision applies", "s_gate", [], "llm"),
        Operation("a", "condition A holds", "s_a", ["s_gate"], "calculator"),
        Operation("b", "condition B holds", "s_b", ["s_gate"], "symbolic"),
        Operation("m", "the requirements are met", "s_m", ["s_a", "s_b"],
                  "merge", merge=MergeType.CONJUNCTION,
                  merge_inputs=["s_a", "s_b"]),
    ]
    return net


NET = gated_network()
assert NET.validate() == [], NET.validate()

# gate resolves, A holds, B does not resolve
PARTIAL = Scenario({"gate": Status.TRUE, "a": Status.TRUE, "b": Status.UNKNOWN})
ALL_TRUE = Scenario({"gate": Status.TRUE, "a": Status.TRUE, "b": Status.TRUE})
A_FAILS = Scenario({"gate": Status.TRUE, "a": Status.FALSE, "b": Status.TRUE})


# ===========================================================================
# Part 1 — built in code
# ===========================================================================

# ---- 1. the reference is the network's own logic ---------------------------
assert reference_terminal(NET, ALL_TRUE) is Status.TRUE
assert reference_terminal(NET, A_FAILS) is Status.FALSE
assert reference_terminal(NET, PARTIAL) is Status.UNKNOWN
print("1. the reference folds the scenario through the declared merge types")

# ---- 2. a scenario is reproducible ----------------------------------------
assert make_scenario(NET, 3).statuses == make_scenario(NET, 3).statuses
# a three-operation network has few distinct scenarios, so compare across a
# range rather than asserting two adjacent seeds must differ
assert len({tuple(sorted((k, v.value) for k, v in make_scenario(NET, i).statuses.items()))
            for i in range(30)}) > 1
print("2. a seed fixes the scenario; different seeds differ")

# ---- 3. VINE agrees with the reference ------------------------------------
for scenario in (ALL_TRUE, A_FAILS, PARTIAL):
    r = run_vine(NET, scenario)
    assert r.correct, (r.terminal, r.reference)
    assert not r.unsupported
for seed in range(40):
    assert run_vine(NET, make_scenario(NET, seed)).correct
print("3. VINE matches the reference on every scenario, and never certifies "
      "past an unresolved branch")

# ---- 4. the same work, a shorter critical path ----------------------------
v = run_vine(NET, ALL_TRUE)
s = run_sequential(NET, ALL_TRUE)
assert v.calls == s.calls == 4          # same obligations, same verifiers
assert v.latency == 3 and s.latency == 4
assert v.latency < s.latency
print(f"4. identical call count ({v.calls}); latency {s.latency} sequential "
      f"vs {v.latency} on the critical path")

# ---- 5. each ablation fails in its own way --------------------------------
# B never resolved, so the honest answer is UNKNOWN.
expected = {
    "VINE": (Status.UNKNOWN, False),
    # a textual summary carries no status to gate on
    "w/o certificates": (Status.TRUE, True),
    # a model asked the question answers it instead of abstaining
    "w/o typed verifiers": (Status.TRUE, True),
    # the unresolved branch is quietly dropped from the composition
    "w/o completeness check": (Status.TRUE, True),
    # a free-form composition sees one TRUE and concludes
    "w/o typed merge": (Status.TRUE, True),
}
for name, (status, unsupported) in expected.items():
    r = run_ablation(name, NET, PARTIAL)
    assert r.terminal is status, (name, r.terminal)
    assert r.unsupported is unsupported, (name, r.unsupported)
print("5. every removed mechanism turns the same unresolved branch into a "
      "definitive answer")

# ---- 6. removing retrieval loses answers but does not invent them ---------
r = run_ablation("w/o obligation retrieval", NET, ALL_TRUE)
assert r.terminal is Status.UNKNOWN and r.reference is Status.TRUE
assert not r.unsupported      # it abstained; that is a miss, not a fabrication
print("6. w/o obligation retrieval abstains rather than fabricating")

# ---- 7. an ablation with nothing to remove is not reported ----------------
r = run_ablation("w/o guards", NET, PARTIAL)
assert r.applicable is False
guarded = gated_network()
guarded.op("a").guard = lambda store: True
assert run_ablation("w/o guards", guarded, PARTIAL).applicable is True
print("7. the guards row is marked n/a unless a network actually has guards")

# ---- 8. abstention is not counted as a failure ----------------------------
r = run_vine(NET, PARTIAL)
assert r.terminal is Status.UNKNOWN and r.correct and not r.unsupported
print("8. abstaining when the evidence is incomplete counts as correct")

# ---- 9. the tables assemble ------------------------------------------------
t3 = table3([NET], range(5))
assert {row["configuration"] for row in t3} >= {"VINE", "Sequential-Verify"}
vine_row = next(r for r in t3 if r["configuration"] == "VINE")
assert vine_row["terminal_accuracy"] == 100.0
assert vine_row["latency"] < next(r for r in t3
                                  if r["configuration"] == "Sequential-Verify")["latency"]

t5 = table5([NET], range(5))
assert [r["configuration"] for r in t5] == ABLATIONS
assert next(r for r in t5 if r["configuration"] == "w/o guards")["UCR"] is None
assert "n/a" in format_table(t5, ["UCR"])
print("9. both tables assemble, and n/a survives formatting")


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
        if not problems and len(net.operations) >= 3:
            nets.append(net)
        if len(nets) >= 100:
            break

    rows = table3(nets, range(10))
    vine = next(r for r in rows if r["configuration"] == "VINE")
    seq = next(r for r in rows if r["configuration"] == "Sequential-Verify")
    assert vine["terminal_accuracy"] == 100.0
    assert abs(vine["calls"] - seq["calls"]) < 1.0      # the controlled part
    assert vine["latency"] < seq["latency"] / 2
    print(f"\nL1. Table 3 over {len(nets)} compiled networks: VINE "
          f"{vine['terminal_accuracy']:.0f}% at latency {vine['latency']:.1f}, "
          f"sequential {seq['terminal_accuracy']:.1f}% at {seq['latency']:.1f}")

    rows = table5(nets, range(10))
    vine = next(r for r in rows if r["configuration"] == "VINE")
    assert vine["terminal_accuracy"] == 100.0 and vine["UCR"] == 0.0
    weakened = [r for r in rows
                if r["configuration"] not in ("VINE", "w/o guards")]
    assert all(r["terminal_accuracy"] < 100.0 for r in weakened), rows
    assert any(r["UCR"] > 10.0 for r in weakened)
    print(f"L2. Table 5: VINE 100% at UCR 0; every measurable ablation loses "
          f"accuracy, and {sum(1 for r in weakened if r['UCR'] > 0)} of "
          f"{len(weakened)} start certifying unsupported conclusions")

print("\nALL EXPERIMENT TESTS PASSED")
