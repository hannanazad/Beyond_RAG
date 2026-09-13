"""Tests for the VINE executor. Builds the paper's Appendix B network and
checks Eq 4 gating, typed merges, Unknown propagation and the S3.1 rejections."""
import sys
sys.path.insert(0, "/home/claude/w")
from mrag.vine import (Authority, Certificate, CertificateStore, Evidence,
                       MergeType, Network, Operation, Status, enabled, execute,
                       merge_statuses)

def cert(claim, status, auth=Authority.STANDARD, ev=(), conf=0.9):
    return Certificate(claim=claim, status=status, normative_authority=auth,
                       evidence=[Evidence("section", e) for e in ev], confidence=conf)

def fixed(status, auth=Authority.STANDARD, ev=()):
    return lambda op, store: cert(op.claim, status, auth, ev)

def appendix_b(class_=Status.TRUE, volume=Status.TRUE, geometry=Status.TRUE,
               exception=Status.FALSE, exc_auth=Authority.OPTION):
    """Appendix B: applicable rule -> {class, volume, geometry} -> base warrant,
    plus a separate exception branch into the decision."""
    net = Network(query="is the treatment warranted?", terminal="s_decision")
    net.states = {"s_applicable", "s_class", "s_volume", "s_geometry",
                  "s_base", "s_exception", "s_decision"}
    net.operations = [
        Operation("O1", "the provision applies", "s_applicable", [], "llm"),
        Operation("O2", "roadway class", "s_class", ["s_applicable"], "llm"),
        Operation("O3", "traffic volume meets the minimum", "s_volume",
                  ["s_applicable"], "calculator"),
        Operation("O4", "geometry conforms to the figure", "s_geometry",
                  ["s_applicable"], "vlm"),
        Operation("M1", "base warrant", "s_base",
                  ["s_class", "s_volume", "s_geometry"], "merge",
                  merge=MergeType.CONJUNCTION,
                  merge_inputs=["s_class", "s_volume", "s_geometry"]),
        Operation("O5", "the engineering-judgement exception applies", "s_exception",
                  ["s_applicable"], "llm", normative_authority=exc_auth),
        Operation("M2", "decision", "s_decision", ["s_base", "s_exception"], "merge",
                  merge=MergeType.EXCEPTION, merge_inputs=["s_base", "s_exception"]),
    ]
    vs = {
        "llm": lambda op, st: cert(op.claim,
                                   {"O1": Status.TRUE, "O2": class_,
                                    "O5": exception}[op.id],
                                   op.normative_authority, ["4C.05"]),
        "calculator": fixed(volume, ev=["Table 4C-1"]),
        "vlm": fixed(geometry, ev=["Figure 4C-3"]),
    }
    return net, vs

# ---- 1. the network the paper describes is well formed --------------------
net, vs = appendix_b()
assert net.validate() == [], net.validate()
print("1. Appendix B validates:", net.validate() == [])

# ---- 2. fork-join: O2/O3/O4 run together, not one after another -----------
t = execute(net, vs)
print("2. waves:", t.waves)
assert t.waves[0] == ["O1"]
assert set(t.waves[1]) == {"O2", "O3", "O4", "O5"}, t.waves[1]
assert t.waves[2] == ["M1"] and t.waves[3] == ["M2"]
assert t.synchronization_depth == 4 and t.operations_run == 7
assert t.terminal.status is Status.TRUE
print("   depth", t.synchronization_depth, "for", t.operations_run,
      "operations; terminal", t.terminal.status.value)

# ---- 3. Eq 4: an operation cannot run before its prerequisites ------------
store = CertificateStore()
assert [o.id for o in enabled(net, store, set())] == ["O1"], "only O1 has no Pre"
store.add("s_applicable", cert("x", Status.TRUE))
assert {o.id for o in enabled(net, store, {"O1"})} == {"O2", "O3", "O4", "O5"}
print("3. gating respects Pre(o)")

# ---- 4. a STANDARD FALSE refutes; conjunction is determined despite UNKNOWN
net, vs = appendix_b(volume=Status.FALSE, geometry=Status.UNKNOWN)
t = execute(net, vs)
assert t.store.latest("s_base").status is Status.FALSE, "FALSE beats UNKNOWN"
assert t.terminal.status is Status.FALSE
print("4. STANDARD FALSE + UNKNOWN -> base FALSE, decision FALSE")

# ---- 5. UNKNOWN propagates rather than becoming a verdict -----------------
net, vs = appendix_b(geometry=Status.UNKNOWN)
t = execute(net, vs)
assert t.store.latest("s_base").status is Status.UNKNOWN
assert t.terminal.status is Status.UNKNOWN
print("5. one UNKNOWN branch -> UNKNOWN decision, not False")

# ---- 6. the exception branch rescues a failed base ------------------------
net, vs = appendix_b(volume=Status.FALSE, exception=Status.TRUE)
t = execute(net, vs)
assert t.store.latest("s_base").status is Status.FALSE
assert t.terminal.status is Status.TRUE, "exception should relax the rule"
print("6. base FALSE + exception TRUE -> decision TRUE")

# an UNKNOWN exception cannot rescue a failed base
net, vs = appendix_b(volume=Status.FALSE, exception=Status.UNKNOWN)
assert execute(net, vs).terminal.status is Status.UNKNOWN
print("   base FALSE + exception UNKNOWN -> UNKNOWN")

# ---- 7. authority decides what FALSE means --------------------------------
assert merge_statuses(MergeType.CONJUNCTION,
                      [cert("a", Status.TRUE), cert("b", Status.FALSE, Authority.GUIDANCE)]
                      ) is Status.TRUE
assert merge_statuses(MergeType.CONJUNCTION,
                      [cert("a", Status.TRUE), cert("b", Status.FALSE, Authority.STANDARD)]
                      ) is Status.FALSE
net, vs = appendix_b(geometry=Status.FALSE)
net.op("O4").normative_authority = Authority.GUIDANCE
t = execute(net, vs)
assert t.terminal.status is Status.TRUE
assert t.store.latest("s_base").provenance["non_conformance"] == ["s_geometry"]
print("7. FALSE Guidance records non-conformance without refuting")

# ---- 8. evidence accumulates through merges -------------------------------
net, vs = appendix_b()
t = execute(net, vs)
ids = [e.id for e in t.terminal.evidence]
assert {"4C.05", "Table 4C-1", "Figure 4C-3"} <= set(ids), ids
print("8. terminal evidence:", ids)

# ---- 9. a missing or crashing verifier yields UNKNOWN, never FALSE --------
net, vs = appendix_b()
del vs["vlm"]
t = execute(net, vs)
assert t.store.latest("s_geometry").status is Status.UNKNOWN
assert "no verifier" in t.store.latest("s_geometry").provenance["error"]
net, vs = appendix_b()
def boom(op, st): raise RuntimeError("model timed out")
vs["calculator"] = boom
t = execute(net, vs)
assert t.store.latest("s_volume").status is Status.UNKNOWN
print("9. absent verifier and crashed verifier both -> UNKNOWN")

# ---- 10. guards close branches (Eq 4, second conjunct) --------------------
net, vs = appendix_b()
net.op("O5").guard = lambda st: st.latest("s_class") is not None and \
                                st.latest("s_class").status is Status.FALSE
net.op("M2").mandatory = False
t = execute(net, vs)
assert "O5" in t.skipped and "O5" not in [o for w in t.waves for o in w]
print("10. guard closed O5; skipped:", list(t.skipped))

# ---- 11. S3.1 rejections ---------------------------------------------------
bad = Network(query="q", terminal="s_end")
bad.states = {"s_a", "s_end"}
bad.operations = [Operation("A", "a", "s_a", ["s_missing"], "llm")]
probs = bad.validate()
assert any("undeclared state" in p for p in probs) and any("unreachable" in p for p in probs)

cyc = Network(query="q", terminal="s_b")
cyc.states = {"s_a", "s_b"}
cyc.operations = [Operation("A", "a", "s_a", ["s_b"], "llm"),
                  Operation("B", "b", "s_b", ["s_a"], "llm")]
assert any("cycle" in p for p in cyc.validate()), cyc.validate()

sup = Network(query="q", terminal="s_a")
sup.states = {"s_a"}
sup.operations = [Operation("A", "a", "s_a", [], "llm",
                            normative_authority=Authority.SUPPORT)]
assert any("SUPPORT" in p for p in sup.validate())

bm = Network(query="q", terminal="s_m")
bm.states = {"s_x", "s_m"}
bm.operations = [Operation("X", "x", "s_x", [], "llm"),
                 Operation("M", "m", "s_m", ["s_x"], "merge",
                           merge=MergeType.CONJUNCTION, merge_inputs=["s_x"])]
assert any("needs at least 2" in p for p in bm.validate())
print("11. rejects undeclared refs, cycles, SUPPORT obligations, 1-input merges")

# a rejected network does not execute
t = execute(bad, {})
assert t.waves == [] and t.problems
print("    rejected network does not execute")

# ---- 12. unsupported certification is detectable --------------------------
net, vs = appendix_b()
net.op("O4").guard = lambda st: False          # geometry never checked
t = execute(net, vs)
assert t.terminal.status is Status.UNKNOWN
assert t.terminal.verifier == "executor"
assert set(t.terminal.provenance["unresolved_operations"]) == {"O4", "M1", "M2"}
assert not t.unsupported_certification(), "UNKNOWN terminal is honest abstention"
print("12. terminal never reached ->", t.terminal.status.value,
      "| unresolved:", t.terminal.provenance["unresolved_operations"],
      "| UCR:", t.unsupported_certification())

# ---- 13. UCR fires only on a DEFINITIVE decision with work left undone ----
net, vs = appendix_b()
net.op("O5").guard = lambda st: False       # optional exception never runs
net.op("O5").mandatory = False
net.op("M2").merge_inputs = ["s_base"]      # decision now rests on the base alone
net.op("M2").requires = ["s_base"]
net.op("M2").merge = MergeType.CONJUNCTION
probs = net.validate()
assert any("needs at least 2" in p for p in probs)
print("13. a merge stripped to one input is rejected:", [p for p in probs if "at least 2" in p])

# an honest True with nothing skipped is not unsupported certification
net, vs = appendix_b()
t = execute(net, vs)
assert t.terminal.status is Status.TRUE and not t.skipped
assert not t.unsupported_certification()
print("    clean TRUE run: UCR", t.unsupported_certification(),
      "| unknowns", t.unknown_certificates(), "| non-conformances", t.non_conformances())

print("\nALL VINE EXECUTOR TESTS PASSED")
