"""Cross-reference resolver: one of the six verifier types in S3.3.
Runs against the real knowledge graph — no models involved."""
import sys, pickle
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.kg import KG
from mrag.vine import (Authority, CertificateStore, Operation, Status,
                       make_cross_reference_resolver, parse_references)

kg = KG(pickle.load(open("/home/claude/analysis/graph_v6.gpickle", "rb")))
resolve = make_cross_reference_resolver(kg)
store = CertificateStore()

def run(claim, hint=None):
    op = Operation("O", claim, "s", [], "cross_reference_resolver",
                   evidence_hint=hint or [])
    return resolve(op, store)

# ---- 1. parsing ---------------------------------------------------------
print("1. parsing")
cases = [
    ("see Paragraph 6 in Section 4K.03",        [("section", "4K.03", 6)]),
    ("Section 4C.05, Paragraph 4 applies",      [("section", "4C.05", 4)]),
    ("as provided in Section 2B.04",            [("section", "2B.04", None)]),
    ("Table 6B-4 gives the formula",            [("figure", "Table 6B-4", None)]),
    ("see Figure 2B-1 and Section 2B.04",       [("figure", "Figure 2B-1", None),
                                                 ("section", "2B.04", None)]),
]
for text, want in cases:
    got = parse_references(text)
    assert sorted(got) == sorted(want), f"{text!r}\n  got {got}\n  want {want}"
    print(f"   {text!r:<44} -> {got}")

# a paragraph pointer must not also produce a bare section reference
assert parse_references("see Paragraph 6 in Section 4K.03") == [("section", "4K.03", 6)]

# ---- 2. a pointer that resolves -----------------------------------------
c = run("the requirement in Paragraph 6 of Section 4K.03 applies")
print(f"\n2. {c.status.value} conf={c.confidence} | resolved={c.provenance['resolved']}")
print("   evidence:", [(e.type, e.id) for e in c.evidence])
assert c.status is Status.TRUE
assert ("chunk", "MUTCD11e_4K03_Guidance_06") in [(e.type, e.id) for e in c.evidence]
assert c.confidence == 1.0

# ---- 3. a pointer the manual does not contain ---------------------------
c = run("as set out in Section 8B.05")
print(f"\n3. {c.status.value} | dangling={c.provenance['dangling']}")
assert c.status is Status.FALSE and c.provenance["dangling"] == ["Section 8B.05"]

# a section that exists but has no such paragraph
c = run("see Paragraph 99 in Section 4K.03")
print(f"   paragraph 99 of 4K.03: {c.status.value} | {c.provenance['dangling']}")
assert c.status is Status.FALSE

# ---- 4. nothing to resolve is UNKNOWN, never FALSE ----------------------
c = run("the sign is conspicuous to approaching drivers")
print(f"\n4. no pointer -> {c.status.value} ({c.provenance['reason']})")
assert c.status is Status.UNKNOWN

# ---- 5. a compiler-supplied hint wins over the claim text ---------------
c = run("follow the cross-reference",
        hint=[{"type": "section", "id": "4K.03", "paragraph": 6}])
print(f"\n5. hint -> {c.status.value} | source={c.provenance['source']} "
      f"| {[(e.type, e.id) for e in c.evidence]}")
assert c.status is Status.TRUE and c.provenance["source"] == "evidence_hint"

# ---- 6. tables and figures resolve too ----------------------------------
c = run("the formula in Table 6B-4 and the shapes in Figure 2B-1")
print(f"\n6. {c.status.value} | {[(e.type, e.id) for e in c.evidence]}")
assert c.status is Status.TRUE
assert {e.type for e in c.evidence} == {"table", "figure"}
c = run("see Table 9Z-9")
assert c.status is Status.FALSE
print("   invented Table 9Z-9 ->", c.status.value)

# ---- 7. mixed: one good, one dangling -> FALSE, with both recorded ------
c = run("see Section 2B.04 and Section 8C.05")
print(f"\n7. {c.status.value} | resolved={c.provenance['resolved']} "
      f"dangling={c.provenance['dangling']}")
assert c.status is Status.FALSE
assert c.provenance["resolved"] == ["Section 2B.04"]

# ---- 8. it is deterministic --------------------------------------------
a = run("see Paragraph 6 in Section 4K.03")
b = run("see Paragraph 6 in Section 4K.03")
assert a.as_dict() == b.as_dict()
print("\n8. identical output on repeat calls: True")

print("\nCROSS-REFERENCE RESOLVER TESTS PASSED")
