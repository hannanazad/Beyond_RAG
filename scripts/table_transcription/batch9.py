"""Warrant 1 volumes and the crash-count warrant tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

def lanes(text):
    return (V(text=text, number=1, unit="lanes") if text == "1"
            else V(text=text, minimum=2, unit="lanes"))

# The a/b/c/d columns are not alternatives a designer may pick freely: each
# has a condition on when it may be used at all (major-street speed above
# 40 mph, isolated community under 10,000, after trial of other remedies).
# Those live in the footnotes, so the percentage columns carry the marker.
# applies_to="cell", NOT the default "table": footnote b governs only the 80%
# columns and d only the 56% columns. Left table-wide, a lookup of the 100%
# volume came back carrying all four conditions, including two that do not
# apply to it -- which would let a verifier justify a value by a condition
# attached to a different column.
_4C1_NOTES = [
    Footnote(marker="a", text="Basic minimum hourly volume", applies_to="cell"),
    Footnote(marker="b", text="Used for combination of Conditions A and B after adequate trial "
                              "of other remedial measures", applies_to="cell"),
    Footnote(marker="c", text="May be used when the major-street speed exceeds 40 mph or in an "
                              "isolated community with a population of less than 10,000",
             applies_to="cell"),
    Footnote(marker="d", text="May be used for combination of Conditions A and B after adequate "
                              "trial of other remedial measures when the major-street speed "
                              "exceeds 40 mph or in an isolated community with a population of "
                              "less than 10,000", applies_to="cell"),
]
_4C1_COLS = ["Number of lanes for moving traffic on each approach — Major Street",
             "Number of lanes for moving traffic on each approach — Minor Street"] + \
            [f"Vehicles per hour on major street (total of both approaches) — {p}{m}"
             for p, m in zip(("100%", "80%", "70%", "56%"), ("ᵃ", "ᵇ", "ᶜ", "ᵈ"))] + \
            [f"Vehicles per hour on more critical minor-street approach (one direction only) — {p}{m}"
             for p, m in zip(("100%", "80%", "70%", "56%"), ("ᵃ", "ᵇ", "ᶜ", "ᵈ"))]
_MARK = ["a", "b", "c", "d", "a", "b", "c", "d"]

def _4c1(part, page, rows):
    return Table(
        table_id="Table 4C-1", part=part, page_pdf=page, page_printed=str(page),
        title=f"Warrant 1, Eight-Hour Vehicular Volume — {part}",
        crop_file="table_4C-1_p0694.png", kind="numeric",
        column_labels=_4C1_COLS, row_key_columns=[0, 1], source=SRC,
        note_chunk_ids=[],
        rows=[[lanes(r[0]), lanes(r[1])]
              + [V(text=x, number=float(x), unit="veh/h", footnotes=[_MARK[i]])
                 for i, x in enumerate(r[2:])] for r in rows],
        footnotes=list(_4C1_NOTES),
    )

T.append(_4c1("Condition A - Minimum Vehicular Volume", 694, [
    ("1","1","500","400","350","280","150","120","105","84"),
    ("2 or more","1","600","480","420","336","150","120","105","84"),
    ("2 or more","2 or more","600","480","420","336","200","160","140","112"),
    ("1","2 or more","500","400","350","280","200","160","140","112"),
]))
T.append(_4c1("Condition B - Interruption of Continuous Traffic", 694, [
    ("1","1","750","600","525","420","75","60","53","42"),
    ("2 or more","1","900","720","630","504","75","60","53","42"),
    ("2 or more","2 or more","900","720","630","504","100","80","70","56"),
    ("1","2 or more","750","600","525","420","100","80","70","56"),
]))

# 4C-2..4C-5 share a shape. 4C-4 and 4C-5 apply ONLY to a community under
# 10,000 or a major street above 40 mph -- printed as a banner over the grid,
# so it is carried as a condition on every row rather than dropped.
_CRASH_COLS = ["Number of through lanes on each approach — Major Street",
               "Number of through lanes on each approach — Minor Street",
               "Total of angle and pedestrian crashes (all severities)ᵃ — Four Legs",
               "Total of angle and pedestrian crashes (all severities)ᵃ — Three Legs",
               "Total of fatal-and-injury angle and pedestrian crashesᵃ — Four Legs",
               "Total of fatal-and-injury angle and pedestrian crashesᵃ — Three Legs"]
_ANGLE = Footnote(marker="a", text="Angle crashes include all crashes that occur at an angle "
                                   "and involve one or more vehicles on the major street and "
                                   "one or more vehicles on the minor street",
                  applies_to="column:2,column:3,column:4,column:5")
# Printed as a banner ACROSS the whole grid of 4C-4 and 4C-5, so it is a
# condition on the table, not on a cell: these counts apply only in a small
# community or on a fast major street.
_SCOPE = Footnote(marker="scope", text="Community less than 10,000 population or above 40 mph "
                                       "on major street", applies_to="table")

def _crash(tid, page, title, rows, scoped):
    return Table(
        table_id=tid, page_pdf=page, page_printed=str(page), title=title,
        crop_file=f"table_{tid.replace('Table ','')}_p{page:04d}.png", kind="numeric",
        column_labels=_CRASH_COLS, row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[lanes(r[0]), lanes(r[1])]
              + [V(text=x, number=float(x), unit="crashes",
                   footnotes=["a"] + (["scope"] if scoped else [])) for x in r[2:]]
              for r in rows],
        footnotes=[_ANGLE] + ([_SCOPE] if scoped else []),
    )

T.append(_crash("Table 4C-3", 703, "Minimum Number of Reported Crashes in a Three-Year Period", [
    ("1","1","6","5","4","4"), ("2 or more","1","6","5","4","4"),
    ("2 or more","2 or more","6","5","4","4"), ("1","2 or more","6","5","4","4"),
], scoped=False))
T.append(_crash("Table 4C-4", 703, "Minimum Number of Reported Crashes in a One-Year Period "
                                   "(community less than 10,000 population or above 40 mph on "
                                   "major street)", [
    ("1","1","4","3","3","3"), ("2 or more","1","10","9","6","6"),
    ("2 or more","2 or more","10","9","6","6"), ("1","2 or more","4","3","3","3"),
], scoped=True))
T.append(_crash("Table 4C-5", 703, "Minimum Number of Reported Crashes in a Three-Year Period "
                                   "(community less than 10,000 population or above 40 mph on "
                                   "major street)", [
    ("1","1","6","5","4","4"), ("2 or more","1","16","13","9","9"),
    ("2 or more","2 or more","16","13","9","9"), ("1","2 or more","6","5","4","4"),
], scoped=True))
