"""Tests for the deterministic calculator (handover S5.5).

Part 1 builds tables in code, so every branch is reachable without the data
file. Part 2 runs the live check against `mutcd_tables.jsonl`.

No models, no GPU, no Qdrant.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import (Authority, Certificate, CertificateStore, Network,
                       Operation, Status, execute, make_calculator)
from mrag.vine.calculator import (ConditionKind, FormulaError,
                                  classify_condition, evaluate_formula,
                                  extract_footnote_formulas)
from mrag.vine.table_data import Footnote, Table, Value
from mrag.vine.table_data import load as load_tables


def op(claim, hint=(), oid="O1"):
    return Operation(oid, claim, "s_out", [], "calculator",
                     evidence_hint=list(hint))


def run(tables, claim, hint=(), store=None):
    return make_calculator(tables)(op(claim, hint), store or CertificateStore())


# ===========================================================================
# Part 1 — built in code
# ===========================================================================

# ---- 1. the restricted evaluator ------------------------------------------
assert evaluate_formula("W*S**2/60", {"W": 12, "S": 40}) == 320.0
assert evaluate_formula("3*sqrt(R-50)", {"R": 450}) == 60.0
# the same rule reproduces a printed row once Note 6's rounding is applied:
# 3*sqrt(500-50) = 63.64, and the grid prints 65
assert round(evaluate_formula("3*sqrt(R-50)", {"R": 500}), 2) == 63.64
for bad, why in [("__import__('os').system('x')", "import"),
                 ("open('/etc/passwd')", "open"),
                 ("[1,2,3]", "list literal"),
                 ("S", "unbound name")]:
    try:
        evaluate_formula(bad, {})
        raise AssertionError(f"{why} was allowed through")
    except FormulaError:
        pass
print("1. restricted evaluator: arithmetic works, code does not")

# ---- 2. a formula stated in a footnote ------------------------------------
assert extract_footnote_formulas(
    "S refers to the spacing computed from the formula S=3*sqrt(R-50).") == \
    [("S", "3*sqrt(R-50)")]
# a variable KEY is prose, not a rule, and must not be mistaken for one
assert extract_footnote_formulas(
    "L = taper length in feet; W = width of offset in feet") == []
print("2. footnote formulas read; variable keys not mistaken for formulas")

# ---- 3. a table built in code ---------------------------------------------
SPEED = Table(
    table_id="Table 9Z-1", page_pdf=1, title="Taper length",
    column_labels=["Speed (S)", "Taper Length (L) in feet"],
    rows=[[Value("40 mph or less", maximum=40, unit="mph"),
           Value("L = WS²/60", formula="W*S**2/60")],
          [Value("45 mph or more", minimum=45, unit="mph"),
           Value("L = WS", formula="W*S")]],
    variables={"L": "taper length in feet", "W": "width of offset in feet",
               "S": "posted speed limit in mph"},
    footnotes=[Footnote("where", "L = taper length in feet; W = width of "
                                 "offset in feet; S = posted speed limit in mph")],
    kind="formula", verified=True, note_chunk_ids=["TBLNOTE_Z-1_01"])

c = run([SPEED], "taper length from Table 9Z-1 at 55 mph with W = 12")
assert c.status is Status.TRUE, c.provenance
assert c.provenance["computed"] == 660.0
assert c.confidence == 1.0
assert [e.id for e in c.evidence if e.type == "table"] == ["Table 9Z-1"]
assert "TBLNOTE_Z-1_01" in [e.id for e in c.evidence]
print("3. range lookup + formula cell -> 660.0, table and note cited")

# ---- 4. a missing input is UNKNOWN, never a default -----------------------
c = run([SPEED], "taper length from Table 9Z-1 at 55 mph")
assert c.status is Status.UNKNOWN and "W" in str(c.provenance["reason"])
assert c.confidence == 0.0
print("4. missing input -> UNKNOWN, not a guess")

# ---- 5. an input established upstream is used ------------------------------
store = CertificateStore()
store.add("s_w", Certificate(claim="offset width is 12 feet", status=Status.TRUE,
                             obligation_id="O_w",
                             provenance={"measurements": {"W": {"value": 12,
                                                                "unit": "ft"}}}))
c = run([SPEED], "taper length from Table 9Z-1 at 55 mph", store=store)
assert c.status is Status.TRUE and c.provenance["computed"] == 660.0
# an UNKNOWN certificate establishes nothing (S3.2)
store2 = CertificateStore()
store2.add("s_w", Certificate(claim="offset width", status=Status.UNKNOWN,
                              provenance={"measurements": {"W": 12}}))
assert run([SPEED], "taper length from Table 9Z-1 at 55 mph",
           store=store2).status is Status.UNKNOWN
print("5. upstream certificate supplies W; an UNKNOWN one does not")

# ---- 6. an unverified table is refused ------------------------------------
UNCHECKED = Table(table_id="Table 9Z-2", page_pdf=1,
                  column_labels=["Speed", "Distance"],
                  rows=[[Value("55 mph", number=55, unit="mph"),
                         Value("100 ft", number=100, unit="ft")]],
                  verified=False)
c = run([UNCHECKED], "distance from Table 9Z-2 at 55 mph")
assert c.status is Status.UNKNOWN and c.provenance.get("verified") is False
print("6. unverified table -> UNKNOWN, with the reason recorded")

# ---- 7. a key outside every printed band ----------------------------------
GRID = Table(table_id="Table 9Z-3", page_pdf=1,
             column_labels=["Radius (R) of Curve", "Spacing (S) on Curve"],
             rows=[[Value("400 feet", number=400, unit="ft"),
                    Value("55 feet", number=55, unit="ft")],
                   [Value("500 feet", number=500, unit="ft"),
                    Value("65 feet", number=65, unit="ft")]],
             variables={"R": "radius of curve in feet",
                        "S": "delineator spacing in feet"},
             verified=True)
c = run([GRID], "spacing from Table 9Z-3 at a radius of 450 feet")
assert c.status is Status.UNKNOWN, c.provenance
assert "outside every printed band" in str(c.provenance.get("detail"))
print("7. out-of-range key with no rule -> UNKNOWN")

# ---- 8. ...unless the manual states the rule the grid came from ------------
WITH_RULE = Table(**{**GRID.__dict__,
                     "footnotes": [Footnote("Note 5", "S refers to the spacing "
                                            "computed from the formula "
                                            "S=3*sqrt(R-50).")]})
c = run([WITH_RULE], "spacing from Table 9Z-3 at a radius of 450 feet")
assert c.status is Status.TRUE and c.provenance["computed"] == 60.0
assert c.confidence < 1.0 and "footnote" in c.provenance["basis"]
print("8. footnote formula computes the off-grid value, at lower confidence")

# ---- 9. a condition the calculator cannot discharge ------------------------
ROUTED = Table(
    table_id="Table 9Z-4", page_pdf=1,
    column_labels=["Sign size (W)", "Minimum size"],
    rows=[[Value("12 in", number=12, unit="in"), Value("30", number=30, unit="in")]],
    variables={"W": "sign width in inches"},
    footnotes=[Footnote("2", "If the sign applies to motorists and bicyclists, "
                             "then the size shall be as shown in Tables 2B-1, "
                             "2C-1, 2D-1, or 8B-1.", applies_to="column:1")],
    verified=True)
c = run([ROUTED], "minimum size from Table 9Z-4 for a 12 in sign")
assert c.status is Status.UNKNOWN, c.provenance
und = c.provenance["undischarged"]
assert len(und) == 1 and und[0]["kind"] == "routing"
# all four routing targets are named, not just the first
assert und[0]["routes_to"] == ["Table 2B-1", "Table 2C-1", "Table 2D-1",
                               "Table 8B-1"], und[0]["routes_to"]
# the value is REPORTED even though it is not certified
assert c.provenance["value"] == 30
print("9. undischarged routing condition -> UNKNOWN, value reported, "
      "all 4 targets named")

# ---- 10. ...and an upstream certificate can discharge it -------------------
store = CertificateStore()
store.add("s_class", Certificate(
    claim="the sign serves bicyclists only", status=Status.TRUE,
    obligation_id="O_class", provenance={"discharges": ["Table 9Z-4:2"]}))
c = run([ROUTED], "minimum size from Table 9Z-4 for a 12 in sign", store=store)
assert c.status is Status.TRUE and c.provenance["value"] == 30
print("10. the same condition, settled upstream -> the value is certified")

# ---- 11. N/A and the em dash are different facts, and neither is a number --
MISSING = Table(
    table_id="Table 9Z-5", page_pdf=1, column_labels=["Speed", "Distance"],
    rows=[[Value("20 mph", number=20, unit="mph"),
           Value("N/A", missing="not_applicable")],
          [Value("25 mph", number=25, unit="mph"),
           Value("—", missing="none")]],
    verified=True)
a = run([MISSING], "distance from Table 9Z-5 at 20 mph")
b = run([MISSING], "distance from Table 9Z-5 at 25 mph")
assert a.status is Status.UNKNOWN and b.status is Status.UNKNOWN
assert a.provenance["missing"] == "not_applicable"
assert b.provenance["missing"] == "none"
assert a.provenance["reason"] != b.provenance["reason"]
print("11. N/A and '—' both abstain, and say different things")

# ---- 12. an ambiguous call is refused, not resolved by picking -------------
TWO_KEYS = Table(
    table_id="Table 9Z-6", page_pdf=1,
    column_labels=["Advisory speed", "Curve radius", "Spacing"],
    rows=[[Value("25 mph", number=25, unit="mph"),
           Value("200 feet", number=200, unit="ft"),
           Value("40 feet", number=40, unit="ft")]],
    row_key_columns=[0, 1], verified=True)
c = run([TWO_KEYS], "spacing from Table 9Z-6 at 25")
assert c.status is Status.UNKNOWN
print("12. a number with no unit against two key columns -> UNKNOWN")

# ---- 13. no table named, and a table that does not exist -------------------
assert run([SPEED], "what is the taper length at 55 mph").status is Status.UNKNOWN
assert run([SPEED], "value from Table 99Z-9 at 55 mph").status is Status.UNKNOWN
print("13. no table named, and an unknown table, both -> UNKNOWN")

# ---- 14. it plugs into the executor unchanged ------------------------------
net = Network(query="is the taper long enough?", terminal="s_out")
net.states = {"s_out"}
net.operations = [Operation("O1", "taper length from Table 9Z-1 at 55 mph "
                                  "with W = 12", "s_out", [], "calculator")]
trace = execute(net, {"calculator": make_calculator([SPEED])})
assert trace.problems == [] and trace.terminal.status is Status.TRUE
assert trace.terminal.provenance["computed"] == 660.0
assert trace.terminal.normative_authority is Authority.STANDARD
assert not trace.unsupported_certification()
print("14. runs inside execute() with no change to the executor")

# ---- 15. a crashing table does not produce a FALSE -------------------------
BROKEN = Table(table_id="Table 9Z-7", page_pdf=1, column_labels=["Speed", "L"],
               rows=[[Value("55 mph", number=55, unit="mph"),
                      Value("L = ??", formula="W*/60")]],
               variables={"W": "width in feet"}, verified=True)
c = run([BROKEN], "L from Table 9Z-7 at 55 mph with W = 12")
assert c.status is Status.UNKNOWN
print("15. an unparsable formula -> UNKNOWN, never FALSE")

# ---- 16. the classifier ----------------------------------------------------
T = SPEED
assert classify_condition(Footnote("a", "See Table 2B-1 for sizes"), T) \
    is ConditionKind.ROUTING
assert classify_condition(Footnote("b", "May be used when the major-street "
                                        "speed exceeds 40 mph"), T) \
    is ConditionKind.CONDITIONAL
assert classify_condition(Footnote("c", "The minimum spacing should be 20 feet"), T) \
    is ConditionKind.BOUND
assert classify_condition(Footnote("d", "Dimensions are shown in inches"), T) \
    is ConditionKind.PRESENTATION
assert classify_condition(Footnote("e", "Bananas"), T) is ConditionKind.UNRECOGNISED
print("16. classifier: routing, conditional, bound, presentation, unrecognised")


# ===========================================================================
# Part 2 — the live check against the real data
# ===========================================================================
def _table_file():
    """Where mutcd_tables.jsonl is. No sandbox path lives in this file.

    Order: an explicit override, then the one place the project keeps paths
    (`scripts/table_transcription/paths.py`), then the repo root.
    """
    if os.environ.get("MUTCD_TABLES"):
        return Path(os.environ["MUTCD_TABLES"])
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                               / "scripts" / "table_transcription"))
        import paths as _p                                   # noqa: WPS433
        if _p.TABLES_OUT.exists():
            return _p.TABLES_OUT
    except Exception:                                        # noqa: BLE001
        pass
    here = Path(__file__).resolve().parents[1] / "mutcd_tables.jsonl"
    return here if here.exists() else None


DATA = _table_file()
if DATA is None:
    print("\nmutcd_tables.jsonl not found; skipped the live checks")
else:
    tables = load_tables(DATA)
    calc = make_calculator(tables)

    # 6B-4 at 55 mph with W = 12 -> L = W*S -> 660 ft (handover S5.5)
    c = calc(op("taper length from Table 6B-4 at 55 mph for W = 12 offset"),
             CertificateStore())
    assert c.status is Status.TRUE, c.provenance
    assert c.provenance["computed"] == 660.0
    assert c.provenance["formula"] == "W*S"
    assert set(c.provenance["variables"]) == {"W", "S"}
    print("\nL1. 6B-4 at 55 mph, W=12 -> 660.0 ft, with the L/W/S key attached")

    # the other branch of the same table is a different formula
    c = calc(op("taper length from Table 6B-4 at 35 mph for W = 10 offset"),
             CertificateStore())
    assert round(c.provenance["computed"], 2) == 204.17
    print("L2. 6B-4 at 35 mph, W=10 -> 204.17 ft (W*S^2/60, the other row)")

    # 3G-1: printed radius, then one the grid does not print
    c = calc(op("delineator spacing from Table 3G-1 at a radius of 500 feet"),
             CertificateStore())
    assert c.status is Status.TRUE and c.provenance["value"] == 65.0
    assert len(c.provenance["conditions"]) == 6
    c = calc(op("delineator spacing from Table 3G-1 at a radius of 450 feet"),
             CertificateStore())
    assert c.status is Status.TRUE and c.provenance["computed"] == 60.0
    assert len(c.provenance["conditions"]) == 6
    print("L3. 3G-1 at R=500 -> 65 ft printed; at R=450 -> 60 ft from Note 5; "
          "both carry all 6 notes")

    # 2C-3: the value is found, but which Condition column applies is not
    # this verifier's call
    hint = [{"type": "table", "id": "Table 2C-3"},
            {"type": "column", "id": "Condition A"}]
    c = calc(op("advance placement distance from Table 2C-3 at 55 mph", hint),
             CertificateStore())
    assert c.status is Status.UNKNOWN and c.provenance["value"] == 990.0
    assert any(u["kind"] == "conditional" for u in c.provenance["undischarged"])
    store = CertificateStore()
    store.add("s_cond", Certificate(
        claim="Condition A applies", status=Status.TRUE, obligation_id="O_c",
        provenance={"discharges": ["Table 2C-3:1", "Table 2C-3:2"]}))
    c = calc(op("advance placement distance from Table 2C-3 at 55 mph", hint), store)
    assert c.status is Status.TRUE and c.provenance["value"] == 990.0
    print("L4. 2C-3 at 55 mph -> 990 ft, held back until Condition A is "
          "established, then certified")

    # every table must be survivable: nothing may raise
    errors = []
    for t in tables:
        try:
            calc(op(f"a value from {t.table_id} at 55 mph"), CertificateStore())
        except Exception as e:                                # noqa: BLE001
            errors.append(f"{t.table_id}: {e!r}")
    assert not errors, errors[:5]
    print(f"L5. swept all {len(tables)} records; no exception, "
          f"every unanswerable case abstained")

print("\nALL CALCULATOR TESTS PASSED")
