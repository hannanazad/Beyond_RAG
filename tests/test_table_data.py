"""Table schema: lookup, conditions, and what the validator catches."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine.table_data import Footnote, Table, Value, load, save, validate

# Table 6B-4 as it is printed: two formula rows plus the variable key, which
# sits in a footnote rather than in the grid.
t6b4 = Table(
    table_id="Table 6B-4", page_pdf=816, page_printed="816",
    title="Formulas for Determining Taper Length",
    crop_file="table_6B-4_p0816.png", kind="formula",
    column_labels=["Speed (S)", "Taper Length (L) in feet"],
    row_key_columns=[0],
    rows=[
        [Value(text="40 mph or less", maximum=40, unit="mph"),
         Value(text="L = WS\u00b2/60", formula="L = W*S**2/60")],
        [Value(text="45 mph or more", minimum=45, unit="mph"),
         Value(text="L = WS", formula="L = W*S")],
    ],
    footnotes=[Footnote(marker="where",
                        text="L = taper length in feet; W = width of offset in feet; "
                             "S = posted speed limit, or off-peak 85th-percentile speed "
                             "prior to work starting, or the anticipated operating speed in mph",
                        chunk_id="MUTCD11e_TBLNOTE_6B-4_01")],
    variables={"L": "taper length in feet", "W": "width of offset in feet",
               "S": "posted speed limit, off-peak 85th-percentile speed, or "
                    "anticipated operating speed, in mph"},
    note_chunk_ids=["MUTCD11e_TBLNOTE_6B-4_01"],
    source="manual transcription",
)

# Table 2C-3 in miniature: N/A and em-dash mean DIFFERENT things, and a
# footnote hangs off the N/A cells.
t2c3 = Table(
    table_id="Table 2C-3", page_pdf=193, page_printed="152",
    title="Guidelines for Advance Placement of Warning Signs",
    kind="numeric",
    column_labels=["Posted or 85th-Percentile Speed",
                   "Condition A: Speed reduction and lane changing in heavy traffic",
                   "Condition B \u2014 advisory speed 0 mph",
                   "Condition B \u2014 advisory speed 10 mph"],
    rows=[
        [Value(text="20 mph", number=20, unit="mph"),
         Value(text="225 ft", number=225, unit="ft"),
         Value(text="115 ft", number=115, unit="ft"),
         Value(text="N/A", missing="not_applicable", footnotes=["5"])],
        [Value(text="25 mph", number=25, unit="mph"),
         Value(text="325 ft", number=325, unit="ft"),
         Value(text="155 ft", number=155, unit="ft"),
         Value(text="\u2014", missing="none")],
    ],
    footnotes=[Footnote(marker="5", text="No suggested distances are provided for these "
                                         "speeds, as the placement location is dependent "
                                         "on site conditions and other signing.",
                        applies_to="cell")],
    source="manual transcription",
)

print("1. validation of two well-formed tables")
problems = validate([t6b4, t2c3])
assert problems == [], problems
print("   problems:", problems)

print("\n2. range lookup — the calculator's entry point")
v = t6b4.lookup(35, column=1)
print("   35 mph ->", v.text, "| formula:", v.formula)
assert v.formula == "L = W*S**2/60"
v = t6b4.lookup(55, column=1)
print("   55 mph ->", v.text, "| formula:", v.formula)
assert v.formula == "L = W*S"
assert t6b4.lookup(42, column=1) is None, "42 mph falls in neither band"
print("   42 mph -> None (falls in neither printed band)")

print("\n3. the conditions travel with the value")
conds = t6b4.conditions_on(t6b4.lookup(55, column=1))
assert conds and conds[0].chunk_id == "MUTCD11e_TBLNOTE_6B-4_01"
print("   ", conds[0].text[:80], "...")
print("    linked chunk:", conds[0].chunk_id)

print("\n4. N/A and em-dash are different facts")
na = t2c3.rows[0][3]; dash = t2c3.rows[1][3]
assert na.missing == "not_applicable" and dash.missing == "none"
assert t2c3.conditions_on(na)[0].marker == "5"
print("   N/A carries footnote 5; em-dash carries none")

print("\n5. column lookup by label fragment")
assert t2c3.column("Condition A") == 1
assert t6b4.column("Taper Length") == 1
print("   'Condition A' -> col 1, 'Taper Length' -> col 1")

print("\n6. round trip through a file")
p = Path("/tmp/tables_test.jsonl")
save([t6b4, t2c3], p)
back = load(p)
assert back[0].as_dict() == t6b4.as_dict() and back[1].as_dict() == t2c3.as_dict()
assert back[0].lookup(55, 1).formula == "L = W*S"
print("   saved, reloaded, lookup still works")

print("\n7. what the validator catches")
def problems_of(mutate):
    import copy
    t = Table.from_dict(copy.deepcopy(t2c3.as_dict()))
    mutate(t)
    return validate([t])

def ragged(t): t.rows[0] = t.rows[0][:2]
def bad_ref(t): t.rows[0][3].footnotes = ["9"]
def numeric_text(t): t.rows[0][1] = Value(text="225")
def mixed_units(t): t.rows[1][1].unit = "m"
def bad_range(t): t.rows[0][0] = Value(text="x", minimum=90, maximum=10)
def bad_missing(t): t.rows[0][3].missing = "dunno"
for name, fn in (("ragged row", ragged), ("undefined footnote", bad_ref),
                 ("number left as text", numeric_text), ("mixed units", mixed_units),
                 ("inverted range", bad_range), ("bad missing kind", bad_missing)):
    ps = problems_of(fn)
    assert ps, f"{name} not caught"
    print(f"   {name:<22} -> {ps[0]}")

# a formula whose variables are undeclared
t = Table.from_dict(json.loads(json.dumps(t6b4.as_dict())))
t.variables = {"L": "taper length in feet"}
ps = validate([t])
assert any("variables" in p for p in ps), ps
print(f"   {'undeclared variables':<22} -> {[p for p in ps if 'variables' in p][0]}")

# a table that is not in figures.jsonl
crops = [{"kind": "Table", "figure_id": "Table 6B-4", "sheet": None}]
ps = validate([t2c3], crops=crops)
assert any("not a table in figures.jsonl" in p for p in ps)
print(f"   {'unknown table id':<22} -> {ps[0]}")

print("\nTABLE SCHEMA TESTS PASSED")
