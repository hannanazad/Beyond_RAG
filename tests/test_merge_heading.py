"""A merge answers its own claim at its own heading (execute._non_blocking, 12 Oct 2026).

Inside a conjunction (and for the base rule of an exception), a FALSE input
counts as "does not refute" only when its heading is WEAKER than the merge's:

    merge STANDARD, input GUIDANCE FALSE -> does not refute (non-conformance)
    merge STANDARD or GUIDANCE, input OPTION FALSE -> does not refute
    input at the merge's own heading, or stronger, FALSE -> refutes

Before the change every non-Standard FALSE counted as TRUE whatever the merge,
so "this Guidance is followed" held although a Guidance item was not followed,
and "this Option may be used here" held although one of its conditions was not
met. Merges at Standard heading behave exactly as before.

Every network here is a made-up example in the shape the parser writes (an
Option with conditions, a Guidance with several items, an exception). None
comes from a sample question, a gold answer or the MUTCD.

Run: python3 tests/test_merge_heading.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine import (Authority, Certificate, MergeType, NetworkSpec, Status, compose, execute,
                       instantiate, merge_statuses)
from mrag.vine.experiments import Scenario, reference_terminal

T, F, U, NA = Status.TRUE, Status.FALSE, Status.UNKNOWN, Status.NOT_APPLICABLE
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")
S, G, O = "STANDARD", "GUIDANCE", "OPTION"


def ob(i, claim, auth, typ="applicability", requires=()):
    return {"id": i, "claim": claim, "type": typ, "authority": auth, "requires": list(requires),
            "evidence_hint": [], "source_chunk": "made_up"}


def merge(i, claim, kind, inputs, auth):
    return {"id": i, "claim": claim, "kind": kind, "inputs": inputs, "authority": auth}


def run(obligations, merges, terminal, table):
    spec = NetworkSpec.from_dict({"query": "made-up test", "terminal": terminal,
                                  "obligations": obligations, "merges": merges})
    net, problems = instantiate(spec)
    assert problems == [], problems

    def verify(op, store):
        return Certificate(claim=op.claim, status=table[op.id], normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id, confidence=0.9)
    trace = execute(net, {v: verify for v in ALL})
    return net, trace


def status_of(trace, net, op_id):
    return trace.store.latest(net.op(op_id).produces)


checks = 0


def check(cond, what):
    global checks
    assert cond, what
    checks += 1
    print(f"  ok  {what}")


# --------------------------------------------------------------------------- #
print("1. An Option with conditions: 'item X may be used here' (OPTION merge)")
# made-up Option: "Item X may be used where the area is a zone of kind K and the road is two-lane."
opt = [ob("o1", "The area is a zone of kind K.", O), ob("o2", "The road is a two-lane road.", O)]
m = [merge("m1", "Item X may be used here.", "conjunction", ["o1", "o2"], O)]
net, tr = run(opt, m, "m1", {"o1": T, "o2": F})
check(tr.terminal.status is F, "one condition not met -> the Option does not apply here (FALSE; it was TRUE)")
check(status_of(tr, net, "m1").provenance["blocking_adjusted"]["s_o2"] == "FALSE",
      "the failed condition is recorded as blocking, not adjusted to TRUE")
net, tr = run(opt, m, "m1", {"o1": T, "o2": T})
check(tr.terminal.status is T, "both conditions met -> the Option applies (TRUE)")
net, tr = run(opt, m, "m1", {"o1": T, "o2": U})
check(tr.terminal.status is U, "a condition unknown -> UNKNOWN, as before")

# --------------------------------------------------------------------------- #
print("2. A Guidance with two items, inside a Standard-level decision")
g = [ob("s1", "The sign is the required shape.", S, "classification"),
     ob("g1", "The sign is placed at the recommended distance.", G, "numerical"),
     ob("g2", "The sign is on the recommended side.", G, "classification")]
ms = [merge("mg", "The placement Guidance is followed.", "conjunction", ["g1", "g2"], G),
      merge("m_final", "The signing meets the manual.", "conjunction", ["s1", "mg"], S)]
net, tr = run(g, ms, "m_final", {"s1": T, "g1": F, "g2": T})
mg = status_of(tr, net, "mg")
check(mg.status is F and mg.normative_authority is Authority.GUIDANCE,
      "'the Guidance is followed' is FALSE when one Guidance item is not followed (it was TRUE)")
check(mg.non_conformance(), "... and it is recorded as a non-conformance with Guidance")
check(tr.terminal.status is T, "the Standard-level decision still holds: a Guidance departure does not refute it")
ans = compose("made-up test", net, tr)
check("non-conformance with Guidance" in ans.text and "placed at the recommended distance" in ans.text,
      "the answer says the decision holds and names the Guidance item not followed")
net, tr = run(g, ms, "m_final", {"s1": F, "g1": T, "g2": T})
check(tr.terminal.status is F, "a failed Standard still refutes the decision")

# --------------------------------------------------------------------------- #
print("3. Standard-level merges behave exactly as before")
for inp_auth, want in ((G, T), (O, T), (S, F)):
    net, tr = run([ob("a", "A holds.", S), ob("b", "B holds.", inp_auth)],
                  [merge("m", "A and B.", "conjunction", ["a", "b"], S)], "m", {"a": T, "b": F})
    check(tr.terminal.status is want, f"STANDARD conjunction, {inp_auth} input FALSE -> {want.value}")

# --------------------------------------------------------------------------- #
print("4. Inputs weaker than the merge still do not refute it")
net, tr = run([ob("g1", "G1 is followed.", G), ob("p1", "Optional item P is used.", O)],
              [merge("m", "The Guidance is followed.", "conjunction", ["g1", "p1"], G)], "m", {"g1": T, "p1": F})
check(tr.terminal.status is T, "GUIDANCE merge, OPTION input FALSE -> TRUE (an option not taken)")
net, tr = run([ob("g1", "G1 is followed.", G), ob("s1", "S1 is met.", S)],
              [merge("m", "The Guidance is followed.", "conjunction", ["g1", "s1"], G)], "m", {"g1": T, "s1": F})
check(tr.terminal.status is F and tr.terminal.normative_authority is Authority.STANDARD,
      "GUIDANCE merge, STANDARD input FALSE -> FALSE, and the merge carries STANDARD (it rests on a Standard)")

# --------------------------------------------------------------------------- #
print("5. One Guidance item, or a merge of Guidance items, as the decision: the same answer")
net, tr = run([ob("g1", "Spacing Q does not exceed its advised maximum.", G, "numerical")], [], "g1", {"g1": F})
single = tr.terminal.status
net, tr = run([ob("g1", "Spacing Q does not exceed its advised maximum.", G, "numerical"),
               ob("g2", "The lines are the recommended width.", G, "numerical")],
              [merge("m", "The marking follows the Guidance.", "conjunction", ["g1", "g2"], G)], "m",
              {"g1": F, "g2": T})
check(single is F and tr.terminal.status is F,
      "a failed Guidance item gives FALSE alone and inside a Guidance merge (before: FALSE and TRUE)")

# --------------------------------------------------------------------------- #
print("6. Exception merges")
base_exc = [ob("b", "The item meets the recommended height.", G, "numerical"),
            ob("e", "The low-clearance exception covers this item.", O, "exception")]
net, tr = run(base_exc, [merge("x", "The height Guidance is met, or excepted.", "exception", ["b", "e"], G)],
              "x", {"b": F, "e": T})
check(tr.terminal.status is T, "GUIDANCE exception merge: base not met, exception applies -> TRUE")
net, tr = run(base_exc, [merge("x", "The height Guidance is met, or excepted.", "exception", ["b", "e"], G)],
              "x", {"b": F, "e": F})
check(tr.terminal.status is F, "GUIDANCE exception merge: base not met, no exception -> FALSE (it was TRUE)")
net, tr = run(base_exc, [merge("x", "The item meets the manual.", "exception", ["b", "e"], S)],
              "x", {"b": F, "e": F})
check(tr.terminal.status is T, "STANDARD exception merge, GUIDANCE base FALSE -> TRUE, as before")

# --------------------------------------------------------------------------- #
print("7. merge_statuses without a heading reads the merge as Standard, as before")
cert = lambda st, a: Certificate(claim="c", status=st, normative_authority=a)
check(merge_statuses(MergeType.CONJUNCTION, [cert(T, Authority.GUIDANCE), cert(F, Authority.GUIDANCE)]) is T,
      "default (Standard) merge: GUIDANCE FALSE does not refute")
check(merge_statuses(MergeType.CONJUNCTION, [cert(T, Authority.GUIDANCE), cert(F, Authority.GUIDANCE)],
                     authority=Authority.GUIDANCE) is F,
      "GUIDANCE merge: GUIDANCE FALSE refutes")
check(merge_statuses(MergeType.ALTERNATIVE, [cert(F, Authority.OPTION), cert(F, Authority.OPTION)],
                     authority=Authority.OPTION) is F,
      "alternatives are untouched: no input holds -> FALSE")

# --------------------------------------------------------------------------- #
print("8. The executor and the independent reference agree on every combination")
shapes = [
    (opt, m, "m1"),
    (g, ms, "m_final"),
    (base_exc, [merge("x", "The height Guidance is met, or excepted.", "exception", ["b", "e"], G)], "x"),
]
n = 0
from itertools import product
for obligations, merges_, terminal in shapes:
    ids = [o["id"] for o in obligations]
    for combo in product((T, F, U), repeat=len(ids)):
        table = dict(zip(ids, combo))
        net, tr = run(obligations, merges_, terminal, table)
        ref = reference_terminal(net, Scenario(statuses=table))
        assert tr.terminal.status is ref, (terminal, table, tr.terminal.status, ref)
        n += 1
check(n > 0, f"{n} combinations: executor == reference")

print(f"\nALL MERGE-HEADING TESTS PASSED ({checks} checks)")
