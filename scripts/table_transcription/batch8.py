"""The calculator-critical tables: work-zone geometry and delineator spacing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V

SRC = "vlm transcription from a PDF render, unverified"
T = []

def ft(text):
    return V(text=text, number=float(text.replace(" feet", "").replace(",", "")), unit="ft")

def mph(text):
    return V(text=text, number=float(text.replace(" mph", "")), unit="mph")

T.append(Table(
    table_id="Table 6B-1", page_pdf=814, page_printed="814",
    title="Recommended Advance Warning Sign Minimum Spacing",
    crop_file="table_6B-1_p0814.png", kind="numeric",
    # the ** is printed on the "Distance between Signs" heading, so it is
    # carried in the labels and scoped to those columns
    column_labels=["Road Type", "Distance between Signs** — A",
                   "Distance between Signs** — B", "Distance between Signs** — C"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_6B-1_01", "MUTCD11e_TBLNOTE_6B-1_02"],
    rows=[[V(text=a, footnotes=f)] + [ft(x) for x in rest]
          for a, f, *rest in [
        ("Urban (low speed)", ["*"], "100 feet", "100 feet", "100 feet"),
        ("Urban (high speed)", ["*"], "350 feet", "350 feet", "350 feet"),
        ("Rural", [], "500 feet", "500 feet", "500 feet"),
        ("Expressway / Freeway", [], "1,000 feet", "1,500 feet", "2,640 feet"),
    ]],
    footnotes=[
        Footnote(marker="*", text="Speed category to be determined by the highway agency or "
                                  "owner of site roadways open to public travel."),
        Footnote(marker="**", text="The column headings A, B, and C are the dimensions shown in "
            "Figures 6P-1 through 6P-54. The A dimension is the distance from the transition or "
            "point of restriction to the first sign. The B dimension is the distance between the "
            "first and second signs. The C dimension is the distance between the second and third "
            "signs. (The \u201cfirst sign\u201d is the sign in a three-sign series that is closest "
            "to the TTC zone. The \u201cthird sign\u201d is the sign that is furthest upstream "
            "from the TTC zone.)", applies_to="column:1,column:2,column:3"),
    ],
))

T.append(Table(
    table_id="Table 6B-2", page_pdf=816, page_printed="816",
    title="Stopping Sight Distance as a Function of Speed",
    crop_file="table_6B-2_p0816.png", kind="numeric",
    column_labels=["Speed*", "Distance"], row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_6B-2_01"],
    rows=[[mph(s), ft(d)] for s, d in [
        ("20 mph","115 feet"),("25 mph","155 feet"),("30 mph","200 feet"),
        ("35 mph","250 feet"),("40 mph","305 feet"),("45 mph","360 feet"),
        ("50 mph","425 feet"),("55 mph","495 feet"),("60 mph","570 feet"),
        ("65 mph","645 feet"),("70 mph","730 feet"),("75 mph","820 feet"),
    ]],
    footnotes=[Footnote(marker="*", text="Posted speed, off-peak 85th-percentile speed prior to "
                                         "work starting, or the anticipated operating speed",
                        applies_to="column:0")],
))

# 6B-3 gives taper lengths as EXPRESSIONS over L, which Table 6B-4 computes.
# A calculator has to evaluate 6B-4 first, then apply the multiplier here --
# so the cells are formulas, not numbers, and the pointer to 6B-4 is a note.
T.append(Table(
    table_id="Table 6B-3", page_pdf=816, page_printed="816",
    title="Taper Length Criteria for Temporary Traffic Control Zones",
    crop_file="table_6B-3_p0816.png", kind="formula",
    column_labels=["Type of Taper", "Taper Length"], row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_6B-3_01"],
    rows=[
        [V(text="Merging Taper"), V(text="at least L", formula="L", minimum=None)],
        [V(text="Shifting Taper"), V(text="at least 0.5 L", formula="0.5*L")],
        [V(text="Shoulder Taper"), V(text="at least 0.33 L", formula="0.33*L")],
        [V(text="One-Lane, Two-Way Traffic Taper"),
         V(text="50 feet minimum, 100 feet maximum", minimum=50, maximum=100, unit="ft")],
        [V(text="Downstream Taper"),
         V(text="50 feet minimum, 100 feet maximum", minimum=50, maximum=100, unit="ft")],
    ],
    variables={"L": "taper length computed from Table 6B-4"},
    footnotes=[Footnote(marker="Note", text="Use Table 6B-4 to calculate L")],
))

T.append(Table(
    table_id="Table 3G-1", page_pdf=662, page_printed="662",
    title="Approximate Spacing for Delineators on Horizontal Curves",
    crop_file="table_3G-1_p0662.png", kind="numeric",
    column_labels=["Radius (R) of Curve", "Approximate Spacing (S) on Curve"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_3G-1_01","MUTCD11e_TBLNOTE_3G-1_02",
                    "MUTCD11e_TBLNOTE_3G-1_03","MUTCD11e_TBLNOTE_3G-1_04",
                    "MUTCD11e_TBLNOTE_3G-1_05","MUTCD11e_TBLNOTE_3G-1_06"],
    rows=[[ft(r), ft(s)] for r, s in [
        ("50 feet","20 feet"),("115 feet","25 feet"),("180 feet","35 feet"),
        ("250 feet","40 feet"),("300 feet","50 feet"),("400 feet","55 feet"),
        ("500 feet","65 feet"),("600 feet","70 feet"),("700 feet","75 feet"),
        ("800 feet","80 feet"),("900 feet","85 feet"),("1,000 feet","90 feet"),
    ]],
    variables={"R": "radius of curve in feet", "S": "delineator spacing in feet"},
    footnotes=[
        # Notes 1, 2, 3 and 5 are what make this table usable: the printed rows
        # are a sampled, rounded curve, not an exhaustive lookup, and there is
        # a floor, a ceiling and the exact formula behind them.
        Footnote(marker="Note 1", text="Spacing for specific radii may be interpolated from table."),
        Footnote(marker="Note 2", text="The minimum spacing should be 20 feet."),
        Footnote(marker="Note 3", text="The spacing on curves should not exceed 300 feet."),
        Footnote(marker="Note 4", text="In advance of or beyond a curve, and proceeding away "
            "from the end of the curve, the spacing of the first delineator is 2S, the second "
            "3S, and the third 6S, but not to exceed 300 feet."),
        Footnote(marker="Note 5", text="S refers to the delineator spacing for specific radii "
            "computed from the formula S=3*sqrt(R-50)."),
        Footnote(marker="Note 6", text="The distances for S shown in the table above were "
            "rounded to the nearest 5 feet."),
    ],
))

# ---- Table 6B-4 ----------------------------------------------------------
T.append(Table(
    table_id="Table 6B-4", page_pdf=816, page_printed="816",
    title="Formulas for Determining Taper Length",
    crop_file="table_6B-4_p0816.png", kind="formula",
    column_labels=["Speed (S)", "Taper Length (L) in feet"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_6B-4_01"],
    rows=[
        [V(text="40 mph or less", maximum=40, unit="mph"),
         V(text="L = WS\u00b2/60", formula="W*S**2/60")],
        [V(text="45 mph or more", minimum=45, unit="mph"),
         V(text="L = WS", formula="W*S")],
    ],
    variables={"L": "taper length in feet", "W": "width of offset in feet",
               "S": "posted speed limit, or off-peak 85th-percentile speed prior to "
                    "work starting, or the anticipated operating speed in mph"},
    footnotes=[Footnote(marker="where",
                        text="L = taper length in feet; W = width of offset in feet; "
                             "S = posted speed limit, or off-peak 85th-percentile speed prior "
                             "to work starting, or the anticipated operating speed in mph",
                        chunk_id="MUTCD11e_TBLNOTE_6B-4_01")],
))

# ---- Warrant 9 adjustment factors (4C-6, 4C-7, 4C-8) --------------------
# Every row key is a BAND, and the last row of each is open-ended, so a
# measured value above the printed range still resolves.
def _pct(text):
    t = text.replace("%", "")
    if "or more" in text:
        return V(text=text, minimum=float(t.replace(" or more", "")), unit="%")
    if "More than" in text:
        return V(text=text, minimum=float(t.replace("More than ", "")),
                 min_inclusive=False, unit="%")
    if " to " in text:
        lo, hi = [float(x) for x in t.split(" to ")]
        return V(text=text, minimum=lo, maximum=hi, unit="%")
    return V(text=text, number=float(t), unit="%")

T.append(Table(
    table_id="Table 4C-6", page_pdf=706, page_printed="706",
    title="Warrant 9, Adjustment Factor for Daily Frequency of Rail Traffic",
    crop_file="table_4C-6_p0706.png", kind="numeric",
    column_labels=["Rail traffic per day", "Adjustment factor"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="1", number=1, unit="trains/day"), V(text="0.67", number=0.67)],
        [V(text="2", number=2, unit="trains/day"), V(text="0.91", number=0.91)],
        [V(text="3 to 5", minimum=3, maximum=5, unit="trains/day"), V(text="1.00", number=1.00)],
        [V(text="6 to 8", minimum=6, maximum=8, unit="trains/day"), V(text="1.18", number=1.18)],
        [V(text="9 to 11", minimum=9, maximum=11, unit="trains/day"), V(text="1.25", number=1.25)],
        [V(text="12 or more", minimum=12, unit="trains/day"), V(text="1.33", number=1.33)],
    ],
))

T.append(Table(
    table_id="Table 4C-7", page_pdf=706, page_printed="706",
    title="Warrant 9, Adjustment Factor for Percentage of High-Occupancy Buses",
    crop_file="table_4C-7_p0706.png", kind="numeric",
    column_labels=["% of high-occupancy buses on minor-street approach", "Adjustment factor"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_4C-7_01"],
    rows=[[_pct(a), V(text=b, number=float(b))] for a, b in [
        ("0%", "1.00"), ("2%", "1.09"), ("4%", "1.19"), ("6% or more", "1.32"),
    ]],
    footnotes=[Footnote(marker="*", text="A high-occupancy bus is defined as a bus occupied by "
                                         "at least 20 people.", applies_to="column:0",
                        chunk_id="MUTCD11e_TBLNOTE_4C-7_01")],
))
for _r in T[-1].rows:
    _r[0].footnotes = ["*"]

T.append(Table(
    table_id="Table 4C-8", page_pdf=706, page_printed="706",
    title="Warrant 9, Adjustment Factor for Percentage of Tractor-Trailer Trucks",
    crop_file="table_4C-8_p0706.png", kind="numeric",
    column_labels=["% of tractor-trailer trucks on minor-street approach",
                   "Adjustment factor — D less than 70 feet",
                   "Adjustment factor — D of 70 feet or more"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[_pct(a), V(text=b, number=float(b)), V(text=c, number=float(c))]
          for a, b, c in [
        ("0% to 2.5%", "0.50", "0.50"), ("2.6% to 7.5%", "0.75", "0.75"),
        ("7.6% to 12.5%", "1.00", "1.00"), ("12.6% to 17.5%", "2.30", "1.15"),
        ("17.6% to 22.5%", "2.70", "1.35"), ("22.6% to 27.5%", "3.28", "1.64"),
        ("More than 27.5%", "4.18", "2.09"),
    ]],
))

T.append(Table(
    table_id="Table 4C-2", page_pdf=702, page_printed="702",
    title="Minimum Number of Reported Crashes in a One-Year Period",
    crop_file="table_4C-2_p0702.png", kind="numeric",
    column_labels=["Number of through lanes on each approach — Major Street",
                   "Number of through lanes on each approach — Minor Street",
                   "Total of angle and pedestrian crashes (all severities)ᵃ — Four Legs",
                   "Total of angle and pedestrian crashes (all severities)ᵃ — Three Legs",
                   "Total of fatal-and-injury angle and pedestrian crashesᵃ — Four Legs",
                   "Total of fatal-and-injury angle and pedestrian crashesᵃ — Three Legs"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a, number=1, unit="lanes") if a == "1"
           else V(text=a, minimum=2, unit="lanes"),
           V(text=b, number=1, unit="lanes") if b == "1"
           else V(text=b, minimum=2, unit="lanes")]
          + [V(text=x, number=float(x), unit="crashes") for x in rest]
          for a, b, *rest in [
        ("1", "1", "5", "4", "3", "3"),
        ("2 or more", "1", "5", "4", "3", "3"),
        ("2 or more", "2 or more", "5", "4", "3", "3"),
        ("1", "2 or more", "5", "4", "3", "3"),
    ]],
    footnotes=[Footnote(marker="a", text="Angle crashes include all crashes that occur at an "
        "angle and involve one or more vehicles on the major street and one or more vehicles "
        "on the minor street", applies_to="column:2,column:3,column:4,column:5")],
))
