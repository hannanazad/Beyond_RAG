"""Branches that do not apply: dead-path elimination in the VINE executor.

Every network here is a made-up example, written for this test. None comes
from a sample question, a gold answer or the MUTCD.

The example rule:
    "A work-zone sign must be orange. If the work is at night, the sign must
     also be lit."

    A  the sign is orange                  (always checked)
    B  the work is at night                (the gate)
    C  the sign is lit                     guard: B is TRUE
    M  the sign meets the rule             conjunction of A and C
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine import (Authority, Certificate, CertificateStore, Evidence, Gate,
                       MergeType, Network, NetworkSpec, Operation, Status,
                       compose, execute, instantiate, merge_statuses)
from mrag.vine.experiments import make_scenario, make_scenario_verifier, reference_terminal
from mrag.vine.model_verifiers import build_prompt

T, F, U, NA = Status.TRUE, Status.FALSE, Status.UNKNOWN, Status.NOT_APPLICABLE
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")


def network(obligations, merges, terminal):
    spec = NetworkSpec.from_dict({"query": "made-up test", "terminal": terminal,
                                  "obligations": obligations, "merges": merges})
    net, problems = instantiate(spec)
    assert problems == [], problems
    return net


def answers(table, authority=None):
    """A verifier that returns a fixed status per obligation id."""
    def verify(op, store):
        return Certificate(claim=op.claim, status=table[op.id],
                           normative_authority=op.normative_authority,
                           evidence=[Evidence("section", f"ev-{op.id}")],
                           confidence=0.9, verifier=op.verifier)
    return {name: verify for name in ALL}


def ob(id_, claim, requires=(), guard=None, authority="STANDARD", type_="applicability"):
    return {"id": id_, "claim": claim, "type": type_, "authority": authority,
            "requires": list(requires), "guard": guard}


def sign_rule(merge_kind="conjunction"):
    return network(
        [ob("A", "the sign is orange"),
         ob("B", "the work is at night"),
         ob("C", "the sign is lit", requires=["B"],
            guard={"state": "B", "status": "TRUE"})],
        [{"id": "M", "claim": "the sign meets the rule", "kind": merge_kind,
          "inputs": ["A", "C"]}],
        terminal="M")


# ---- 1. night work: the branch applies and runs ------------------------------
t = execute(sign_rule(), answers({"A": T, "B": T, "C": T}))
assert t.terminal.status is T and not t.not_applicable and not t.skipped
t = execute(sign_rule(), answers({"A": T, "B": T, "C": F}))
assert t.terminal.status is F
print("1. night work: the lighting check runs and decides with A")

# ---- 2. day work: the branch does not apply, and M decides on A alone --------
t = execute(sign_rule(), answers({"A": T, "B": F, "C": F}))
c = t.store.latest("s_C")
assert c.status is NA and c.verifier == "executor", c
assert c.provenance["decided_by"] == {"s_B": "FALSE"}
assert [e.id for e in c.evidence] == ["ev-B"], "the gate's evidence explains why"
assert t.terminal.status is T, t.terminal
assert t.terminal.provenance["not_applicable"] == ["s_C"]
assert "C" in t.not_applicable and "C" not in t.skipped
assert not t.unsupported_certification(), "a check that does not apply is resolved"
assert "C" not in [o for w in t.waves for o in w], "the verifier was never called"
print("2. day work: C is NOT_APPLICABLE, M = A = TRUE; before this fix it was UNKNOWN")

t = execute(sign_rule(), answers({"A": F, "B": F, "C": T}))
assert t.terminal.status is F, "a failed STANDARD still fails the rule"
print("   day work with a sign that is not orange: FALSE")

# ---- 3. an UNKNOWN gate never switches a rule off (S3.2) ----------------------
t = execute(sign_rule(), answers({"A": T, "B": U, "C": T}))
assert t.store.latest("s_C").status is U and "C" in t.undecided
assert t.terminal.status is U, "unknown whether lighting applies: no decision"
t = execute(sign_rule(), answers({"A": F, "B": U, "C": T}))
assert t.terminal.status is F, "FALSE beats UNKNOWN in a conjunction, as before"
print("3. gate UNKNOWN: C is UNKNOWN (not skipped), M UNKNOWN unless A already fails")

# ---- 4. settled results add no wave ------------------------------------------
day = execute(sign_rule(), answers({"A": T, "B": F, "C": T}))
night = execute(sign_rule(), answers({"A": T, "B": T, "C": T}))
assert day.synchronization_depth == night.synchronization_depth - 1
assert day.operations_run == night.operations_run - 1
print("4. depth", night.synchronization_depth, "-> ", day.synchronization_depth,
      "when C does not apply; operations", night.operations_run, "->", day.operations_run)

# ---- 5. dead paths: the whole branch below the gate goes with it -------------
chain = network(
    [ob("A", "the sign is orange"),
     ob("B", "the work is at night"),
     ob("C", "the sign is lit", requires=["B"], guard={"state": "B", "status": "TRUE"}),
     ob("D", "the light is bright enough", requires=["C"])],
    [{"id": "M", "claim": "the sign meets the rule", "kind": "conjunction",
      "inputs": ["A", "D"]}],
    terminal="M")
t = execute(chain, answers({"A": T, "B": F, "C": T, "D": F}))
assert t.store.latest("s_D").status is NA and "D" in t.not_applicable
assert t.terminal.status is T, "D would have failed, but it does not apply in daytime"
print("5. D needs only C, C does not apply, so D does not apply: M = TRUE")

# one live prerequisite keeps a step alive; its checker sees the dead one
seen = {}
def watch(op, store):
    seen[op.id] = {s: (store.latest(s).status if store.latest(s) else None)
                   for s in op.requires}
    return Certificate(claim=op.claim, status=T, evidence=[Evidence("section", "x")],
                       confidence=0.9)
mixed = network(
    [ob("B", "the work is at night"),
     ob("C", "the sign is lit", requires=["B"], guard={"state": "B", "status": "TRUE"}),
     ob("E", "the sign is reflective"),
     ob("S", "the sign is visible", requires=["C", "E"])],
    [], terminal="S")
t = execute(mixed, {"llm": lambda op, st: watch(op, st) if op.id == "S" else
                    Certificate(claim=op.claim, status={"B": F, "E": T}[op.id],
                                evidence=[Evidence("section", "x")], confidence=0.9)})
assert t.terminal.status is T and seen["S"] == {"s_C": NA, "s_E": T}
print("   S needs C and E; only C is dead, so S runs and sees C =", seen["S"]["s_C"].value)

# ---- 6. typed merges ----------------------------------------------------------
def cert(status, auth=Authority.STANDARD):
    return Certificate(claim="x", status=status, normative_authority=auth)

assert merge_statuses(MergeType.CONJUNCTION, [cert(NA), cert(T)]) is T
assert merge_statuses(MergeType.CONJUNCTION, [cert(NA), cert(F)]) is F
assert merge_statuses(MergeType.CONJUNCTION, [cert(NA), cert(NA)]) is NA
assert merge_statuses(MergeType.ALTERNATIVE, [cert(NA), cert(F)]) is F, \
    "a branch that does not apply does not satisfy an alternative"
assert merge_statuses(MergeType.ALTERNATIVE, [cert(NA), cert(T)]) is T
assert merge_statuses(MergeType.ALTERNATIVE, [cert(NA), cert(NA)]) is NA
# exception: inputs[0] is the base rule
assert merge_statuses(MergeType.EXCEPTION, [cert(F), cert(NA)]) is F, \
    "the exception does not apply, so the base rule decides"
assert merge_statuses(MergeType.EXCEPTION, [cert(T), cert(NA)]) is T
assert merge_statuses(MergeType.EXCEPTION, [cert(F), cert(NA), cert(T)]) is T
assert merge_statuses(MergeType.EXCEPTION, [cert(NA), cert(T)]) is NA, \
    "no rule to relax"
assert merge_statuses(MergeType.EXCEPTION, [cert(F), cert(U)]) is U, "unchanged"
print("6. merges leave out what does not apply; all out -> NOT_APPLICABLE")

exc = network(
    [ob("R", "the sign is at least the minimum size"),
     ob("L", "the road is low-speed"),
     ob("X", "a smaller sign is allowed on this road", type_="exception",
        authority="OPTION", requires=["L"], guard={"state": "L", "status": "TRUE"})],
    [{"id": "M", "claim": "the sign size is acceptable", "kind": "exception",
      "inputs": ["R", "X"]}],
    terminal="M")
assert execute(exc, answers({"R": F, "L": F, "X": T})).terminal.status is F
assert execute(exc, answers({"R": F, "L": T, "X": T})).terminal.status is T
print("   exception guarded on a low-speed road: high-speed -> base decides (FALSE)")

# ---- 7. a merge with nothing that applies, up to the answer -------------------
both = network(
    [ob("B", "the work is at night"),
     ob("C", "the sign is lit", requires=["B"], guard={"state": "B", "status": "TRUE"}),
     ob("D", "the light is steady", requires=["B"], guard={"state": "B", "status": "TRUE"})],
    [{"id": "M", "claim": "the lighting meets the rule", "kind": "conjunction",
      "inputs": ["C", "D"]}],
    terminal="M")
t = execute(both, answers({"B": F, "C": T, "D": T}))
assert t.terminal.status is NA and "M" in t.not_applicable
assert not t.unsupported_certification()
a = compose("made-up", both, t)
assert a.status is NA and "does not apply" in a.text and "the work is at night (FALSE)" in a.text, a.text
assert not a.abstained
print("7. nothing applies -> terminal NOT_APPLICABLE; answer:", a.text)

t = execute(sign_rule(), answers({"A": T, "B": F, "C": T}))
a = compose("made-up", sign_rule(), t)
assert a.status is T and "Not applicable here: the sign is lit" in a.text, a.text
print("   a TRUE answer names what did not apply:", a.text)

# ---- 8. guard forms -----------------------------------------------------------
def gate_of(guard, statuses):
    net = network([ob("P", "p"), ob("Q", "q"),
                   ob("G", "g", requires=["P", "Q"], guard=guard)], [], terminal="G")
    store = CertificateStore()
    for k, v in statuses.items():
        store.add(f"s_{k}", Certificate(claim=k, status=v))
    return net.op("G").guard_eval(store)

P_T = {"state": "P", "status": "TRUE"}
Q_T = {"state": "Q", "status": "TRUE"}
P_U = {"state": "P", "status": "UNKNOWN"}
P_R = {"state": "P", "status": "RESOLVED"}
cases = [
    # guard,                        results,              gate
    (P_T,                           {},                   Gate.PENDING),
    (P_T,                           {"P": T},             Gate.OPEN),
    (P_T,                           {"P": F},             Gate.CLOSED),
    (P_T,                           {"P": U},             Gate.UNDECIDED),
    (P_T,                           {"P": NA},            Gate.CLOSED),
    ({"not": P_T},                  {"P": F},             Gate.OPEN),
    # an unknown fact cannot switch a rule ON either
    ({"not": P_T},                  {"P": U},             Gate.UNDECIDED),
    ({"not": P_T},                  {"P": NA},            Gate.OPEN),
    ({"all": [P_T, Q_T]},           {"P": F, "Q": U},     Gate.CLOSED),
    ({"all": [P_T, Q_T]},           {"P": T, "Q": U},     Gate.UNDECIDED),
    ({"all": [P_T, Q_T]},           {"P": NA, "Q": T},    Gate.CLOSED),
    ({"any": [P_T, Q_T]},           {"P": NA, "Q": T},    Gate.OPEN),
    ({"any": [P_T, Q_T]},           {"P": F, "Q": U},     Gate.UNDECIDED),
    ({"any": [P_T, Q_T]},           {"P": NA, "Q": NA},   Gate.CLOSED),
    ({"any": [P_T, Q_T]},           {"P": T},             Gate.OPEN),     # no need to wait for Q
    ({"all": [P_T, Q_T]},           {"P": F},             Gate.PENDING),  # a closure waits for Q
    (P_U,                           {"P": U},             Gate.UNDECIDED),
    (P_U,                           {"P": T},             Gate.CLOSED),
    (P_R,                           {"P": F},             Gate.OPEN),
    (P_R,                           {"P": U},             Gate.UNDECIDED),
    # the same condition as RESOLVED, written another way: same answer
    ({"not": P_U},                  {"P": U},             Gate.UNDECIDED),
    ({"not": P_U},                  {"P": T},             Gate.OPEN),
    # not over all, with one part UNKNOWN and one part not applicable: open
    # however P turns out, so the item runs
    ({"not": {"all": [P_T, Q_T]}},  {"P": U, "Q": NA},    Gate.OPEN),
    # De Morgan holds: two ways of writing one condition agree
    ({"not": {"any": [P_T, Q_T]}},  {"P": F, "Q": NA},    Gate.OPEN),
    ({"all": [{"not": P_T}, {"not": Q_T}]}, {"P": F, "Q": NA}, Gate.OPEN),
]
for guard, statuses, want in cases:
    got = gate_of(guard, statuses)
    assert got is want, (guard, statuses, got, want)
# Eq 4's open/closed predicate agrees with the gate
for guard, statuses, _want in cases:
    net = network([ob("P", "p"), ob("Q", "q"),
                   ob("G", "g", requires=["P", "Q"], guard=guard)], [], terminal="G")
    st = CertificateStore()
    for k, v in statuses.items():
        st.add(f"s_{k}", Certificate(claim=k, status=v))
    assert net.op("G").guard(st) is (net.op("G").guard_eval(st) is Gate.OPEN)
print(f"8. {len(cases)} guard cases: a guard decides only what holds however "
      f"its UNKNOWN results turn out")

# The safety rule, checked by brute force over guards of depth <= 2 on two
# results and every combination of their statuses: whenever the gate says
# CLOSED or OPEN, replacing each UNKNOWN result by TRUE or by FALSE must give
# the same gate.
import itertools
leaves = [{"state": x, "status": w} for x in ("P", "Q")
          for w in ("TRUE", "FALSE", "UNKNOWN", "RESOLVED")]
def grow(level):
    out = list(level)
    for g in level:
        out.append({"not": g})
    for a, b in itertools.combinations(level, 2):
        out += [{"all": [a, b]}, {"any": [a, b]}]
    return out
guards = grow(grow(leaves))
checked = closed = 0
for guard in guards[::7]:                      # a fixed sample keeps this quick
    for sp, sq in itertools.product((T, F, U, NA), repeat=2):
        g = gate_of(guard, {"P": sp, "Q": sq})
        checked += 1
        if g not in (Gate.CLOSED, Gate.OPEN):
            continue
        closed += 1
        for rp in ((T, F) if sp is U else (sp,)):
            for rq in ((T, F) if sq is U else (sq,)):
                assert gate_of(guard, {"P": rp, "Q": rq}) is g, \
                    ("an UNKNOWN result decided a guard", guard, sp, sq, rp, rq, g)
print(f"   safety: {checked:,} guard/status cases, {closed:,} decided; none would "
      f"change if an UNKNOWN result were known")

# the same two conditions inside a running network
c = network([ob("A", "the sign is orange"), ob("B", "the work is at night"),
             ob("C", "the sign is lit", requires=["B"],
                guard={"not": {"state": "B", "status": "UNKNOWN"}})],
            [{"id": "M", "claim": "m", "kind": "conjunction", "inputs": ["A", "C"]}], "M")
t = execute(c, answers({"A": T, "B": U, "C": T}))
assert t.store.latest("s_C").status is U and t.terminal.status is U, \
    "not(B is UNKNOWN) with B UNKNOWN must not switch C off"

# ---- 9. only the executor may say "does not apply" ----------------------------
claims_na = {name: (lambda op, st: Certificate(claim=op.claim, status=NA,
                                                evidence=[Evidence("section", "x")],
                                                confidence=0.9)) for name in ALL}
t = execute(sign_rule(), claims_na)
a_cert = t.store.latest("s_A")
assert a_cert.status is U and a_cert.provenance["verifier_claimed_status"] == "NOT_APPLICABLE"
print("9. a checker that returns NOT_APPLICABLE is read as UNKNOWN")

prompt, _ = build_prompt(sign_rule().op("A"), [{"chunk_id": "c1", "text": "x"}], [],
                         [Certificate(claim="the sign is lit", status=NA)])
assert "the sign is lit => DOES NOT APPLY HERE" in prompt and "NOT_APPLICABLE" not in prompt
print("   the checker's prompt shows it in words: 'DOES NOT APPLY HERE'")

# ---- 10. a bare predicate guard keeps the old meaning -------------------------
legacy = sign_rule()
legacy.op("C").guard_eval = None
legacy.op("C").guard = lambda st: False
t = execute(legacy, answers({"A": T, "B": F, "C": T}))
assert "C" in t.skipped and "C" not in t.not_applicable and t.terminal.status is U
print("10. a hand-written predicate never switches a branch off: UNKNOWN as before")

# ---- 11. the independent reference agrees with the executor -------------------
nets = [sign_rule(), sign_rule("alternative"), chain, exc, both, mixed]
agree = runs = 0
for n in nets:
    for seed in range(200):
        scenario = make_scenario(n, seed, weights=(0.45, 0.35, 0.20))
        verifier = make_scenario_verifier(scenario)
        got = execute(n, {k: verifier for k in ALL}).terminal.status
        ref = reference_terminal(n, scenario)
        assert got is ref, (n.terminal, seed, scenario.statuses, got, ref)
        runs += 1
print(f"11. executor == independent reference on {runs} random runs over {len(nets)} networks")

# ---- 12. an item that feeds nothing is still settled, not "never resolved" ----
side = network(
    [ob("A", "a"), ob("B", "b"), ob("X", "x", requires=["A"]),
     ob("D", "d", requires=["X"], guard={"state": "X", "status": "TRUE"})],
    [{"id": "M", "claim": "m", "kind": "conjunction", "inputs": ["A", "B"]}], "M")
t = execute(side, answers({"A": T, "B": T, "X": F, "D": T}))
assert t.terminal.status is T and "D" in t.not_applicable and not t.skipped
assert not t.unsupported_certification()
print("12. a side item that does not apply is settled; no false UCR")

# ---- 13. 'decided by' names only established results ---------------------------
two = network(
    [ob("P", "the road is rural"), ob("Q", "the road is wide"),
     ob("C", "the sign is large", requires=["P", "Q"],
        guard={"all": [{"state": "P", "status": "TRUE"}, {"state": "Q", "status": "TRUE"}]})],
    [], "C")
t = execute(two, answers({"P": F, "Q": U, "C": T}))
assert t.terminal.status is NA, "P FALSE closes all(...) whatever Q turns out to be"
a = compose("made-up", two, t)
assert "the road is rural (FALSE)" in a.text and "wide" not in a.text, a.text
assert [e.id for e in t.terminal.evidence] == ["ev-P"], "no evidence from an UNKNOWN result"
print("13. decided by:", a.text.split("Decided by: ")[1])


# ---- 14. end to end: a definite answer never rests on an unknown fact --------
# Random made-up networks (guards of every form, every merge kind, mixed
# authorities). For each run whose terminal is definite (TRUE, FALSE or
# NOT_APPLICABLE), every check that came out UNKNOWN is given each other
# outcome in turn (TRUE, FALSE, or left UNKNOWN), in every combination; the
# terminal must not change. This is S3.2's rule, tested on whole networks.
import random
from mrag.vine.experiments import Scenario

def random_network(rng):
    n = rng.randint(3, 6)
    obs = []
    for i in range(n):
        earlier = [o["id"] for o in obs]
        req = sorted(rng.sample(earlier, rng.randint(0, min(2, len(earlier))))) if earlier else []
        guard = None
        if req and rng.random() < 0.6:
            leaf = lambda: {"state": rng.choice(req),
                            "status": rng.choice(["TRUE", "TRUE", "FALSE", "RESOLVED", "UNKNOWN"])}
            form = rng.random()
            guard = (leaf() if form < 0.55 else {"not": leaf()} if form < 0.7 else
                     {rng.choice(["all", "any"]): [leaf(), leaf()]})
        obs.append(ob(f"o{i}", f"made-up check {i}", requires=req, guard=guard,
                      authority=rng.choice(["STANDARD", "STANDARD", "GUIDANCE", "OPTION"]),
                      type_="exception" if i and rng.random() < 0.15 else "applicability"))
    ids = [o["id"] for o in obs]
    merges = []
    for j in range(rng.randint(1, 2)):
        pool = ids + [m["id"] for m in merges]
        k = rng.choice(["conjunction", "alternative", "exception"])
        ins = rng.sample(pool, min(len(pool), rng.randint(2, 3)))
        if k == "exception":
            base = [x for x in ins if not (x in ids and obs[ids.index(x)]["type"] == "exception")]
            if not base:
                k = "conjunction"
            else:
                ins = [base[0]] + [x for x in ins if x != base[0]]
        merges.append({"id": f"m{j}", "claim": f"made-up merge {j}", "kind": k, "inputs": ins})
    return network(obs, merges, merges[-1]["id"])

def run_with(net, statuses):
    v = make_scenario_verifier(Scenario(statuses))
    return execute(net, {k: v for k in ALL}).terminal.status

rng = random.Random(7)
nets = definite = worlds = 0
while nets < 400:
    try:
        net = random_network(rng)
    except AssertionError:
        continue
    nets += 1
    for seed in range(6):
        sc = make_scenario(net, seed, weights=(0.4, 0.3, 0.3))
        base = run_with(net, dict(sc.statuses))
        assert base is reference_terminal(net, sc), "executor and reference disagree"
        if base is U:
            continue
        definite += 1
        unknown_ops = [k for k, v in sc.statuses.items() if v is U]
        for combo in itertools.product((T, F, U), repeat=len(unknown_ops)):
            trial = dict(sc.statuses); trial.update(zip(unknown_ops, combo))
            worlds += 1
            got = run_with(net, trial)
            assert got is base, ("a definite answer changed when an UNKNOWN check "
                                 "became known", net.terminal, sc.statuses, trial, base, got)
print(f"14. {nets} random networks, {definite} definite answers checked against "
      f"{worlds:,} ways their UNKNOWN checks could have turned out: none changed")

# ---- 15. reviewer's last points ------------------------------------------------
# an exception merge whose base does not apply is N/A, even when an exception's
# applicability is unknown
ex2 = network(
    [ob("B", "the road is rural"), ob("W", "the work is at night"),
     ob("R", "the sign is large", requires=["B"], guard={"state": "B", "status": "TRUE"}),
     ob("X", "a smaller sign is allowed", type_="exception", authority="OPTION",
        requires=["W"], guard={"state": "W", "status": "TRUE"})],
    [{"id": "E", "claim": "the size is acceptable", "kind": "exception", "inputs": ["R", "X"]}],
    "E")
t = execute(ex2, answers({"B": F, "W": U, "R": T, "X": T}))
assert t.terminal.status is NA, t.terminal
# a checker cannot mark its own result "applicability unknown"
def flagging(op, st):
    return Certificate(claim=op.claim, status=U, provenance={"applicability": "unknown"})
t = execute(sign_rule(), {k: flagging for k in ALL})
assert not t.store.latest("s_A").applicability_unknown()
# the reference stays fast on a very wide conjunction
import time
wide = Network(query="wide", terminal="s_M")
wide.states = {f"s_x{i}" for i in range(300)} | {"s_M"}
wide.operations = [Operation(f"x{i}", "c", f"s_x{i}", [], "llm") for i in range(300)]
wide.operations.append(Operation("M", "m", "s_M", [f"s_x{i}" for i in range(300)], "merge",
                                 merge=MergeType.CONJUNCTION,
                                 merge_inputs=[f"s_x{i}" for i in range(300)]))
t0 = time.time()
for seed in range(5):
    reference_terminal(wide, make_scenario(wide, seed))
assert time.time() - t0 < 2.0, "reference too slow on a wide merge"
print("15. dead base -> N/A; checker cannot set the flag; reference fast on 300 inputs")

print("\nALL NOT-APPLICABLE TESTS PASSED")
