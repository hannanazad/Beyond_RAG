"""Chapter 2B-2C tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V
from batch2 import sz

SRC = "vlm transcription from a PDF render, unverified"
T = []

T.append(Table(
    table_id="Table 2B-2", page_pdf=136, page_printed="136",
    title="Meanings of Symbols and Legends on Reversible Lane Control Signs",
    crop_file="table_2B-2_p0136.png", kind="text",
    column_labels=["Symbol / Word Message", "Meaning"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a), V(text=b)] for a, b in [
        ("Red X on white background", "Lane closed"),
        ("Upward-pointing black arrow on white background (if left turns are permitted, "
         "the arrow shall be modified to show left / through arrow)",
         "Lane open for through travel and any turns not otherwise prohibited"),
        ("Black two-way left-turn arrows on white background and legend ONLY",
         "Lane may be used only for left turns in either direction (i.e., as a two-way "
         "left-turn lane)"),
        ("Black single left-turn arrow on white background and legend ONLY",
         "Lane may be used only for left turns in one direction (without opposing left "
         "turns in the same lane)"),
    ]],
))

# 2C-2: the row key is the WARNING SIGN size, and two sign sizes share one set
# of plaque sizes. Each printed sign size gets its own row so a lookup on
# "36 x 36" resolves without having to know it was grouped with 48 x 48.
T.append(Table(
    table_id="Table 2C-2", page_pdf=192, page_printed="192",
    title="Minimum Size of Supplemental Warning Plaques",
    crop_file="table_2C-2_p0192.png", kind="numeric",
    column_labels=["Size of Warning Sign",
                   "Size of Supplemental Plaque — Rectangular — 1 Line",
                   "Size of Supplemental Plaque — Rectangular — 2 Lines",
                   "Size of Supplemental Plaque — Rectangular — Arrow",
                   "Size of Supplemental Plaque — Square"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2C-2_01"],
    rows=[[sz(a), sz(b), sz(c), sz(d), sz(e)] for a, b, c, d, e in [
        ("24 x 24", "24 x 12", "24 x 18", "21 x 15", "18 x 18"),
        ("30 x 30", "24 x 12", "24 x 18", "21 x 15", "18 x 18"),
        ("36 x 36", "30 x 18", "30 x 24", "30 x 21", "24 x 24"),
        ("48 x 48", "30 x 18", "30 x 24", "30 x 21", "24 x 24"),
    ]],
    footnotes=[
        Footnote(marker="Note 1", text="Larger supplemental plaques may be used when appropriate"),
        Footnote(marker="Note 2", text="Dimensions are shown as width x height, in inches"),
    ],
))

# ---- Table 2C-3 ----------------------------------------------------------
# The workhorse for a calculator: "advance placement distance at 55 mph under
# Condition B with a 40 mph advisory" is a two-key lookup. N/A and the em-dash
# are DIFFERENT: N/A carries footnote 5 ("no suggested distances are provided
# ... an alignment warning sign may be placed anywhere from the point of
# curvature up to 100 feet in advance"), while the em-dash means the advisory
# speed is at or above the posted speed, so the combination does not arise.
def ft(text):
    if text == "—":
        return V(text="—", missing="none")
    if text.startswith("N/A"):
        return V(text="N/A", missing="not_applicable", footnotes=["5"])
    note = ["6"] if text.endswith("6") else []
    body = text.rstrip("6").replace(" ft", "").replace(",", "").strip()
    return V(text=text.rstrip("6"), number=float(body), unit="ft", footnotes=note)

_2C3 = [
 ("20 mph", "225 ft", "115 ft", "N/A5", "—", "—", "—", "—", "—", "—", "—"),
 ("25 mph", "325 ft", "155 ft", "N/A5", "N/A5", "—", "—", "—", "—", "—", "—"),
 ("30 mph", "460 ft", "200 ft", "N/A5", "N/A5", "—", "—", "—", "—", "—", "—"),
 ("35 mph", "565 ft", "250 ft", "N/A5", "N/A5", "N/A5", "—", "—", "—", "—", "—"),
 ("40 mph", "670 ft", "305 ft", "100 ft6", "100 ft6", "N/A5", "—", "—", "—", "—", "—"),
 ("45 mph", "775 ft", "360 ft", "125 ft", "100 ft6", "100 ft6", "N/A5", "—", "—", "—", "—"),
 ("50 mph", "885 ft", "425 ft", "200 ft", "175 ft", "125 ft", "100 ft6", "—", "—", "—", "—"),
 ("55 mph", "990 ft", "495 ft", "275 ft", "225 ft", "200 ft", "125 ft", "N/A5", "—", "—", "—"),
 ("60 mph", "1,100 ft", "570 ft", "350 ft", "325 ft", "275 ft", "200 ft", "100 ft6", "—", "—", "—"),
 ("65 mph", "1,200 ft", "645 ft", "450 ft", "400 ft", "350 ft", "275 ft", "200 ft", "100 ft6", "—", "—"),
 ("70 mph", "1,250 ft", "730 ft", "525 ft", "500 ft", "450 ft", "375 ft", "275 ft", "150 ft", "—", "—"),
 ("75 mph", "1,350 ft", "820 ft", "625 ft", "600 ft", "550 ft", "475 ft", "375 ft", "250 ft", "100 ft6", "—"),
 ("80 mph", "1,475 ft", "910 ft", "725 ft", "700 ft", "625 ft", "550 ft", "450 ft", "350 ft", "200 ft", "—"),
 ("85 mph", "1,600 ft", "1,010 ft", "825 ft", "800 ft", "750 ft", "675 ft", "575 ft", "450 ft", "300 ft", "150 ft"),
]

T.append(Table(
    table_id="Table 2C-3", page_pdf=193, page_printed="152",
    title="Guidelines for Advance Placement of Warning Signs",
    crop_file="table_2C-3_p0193.png", kind="numeric",
    column_labels=["Posted or 85th-Percentile Speed",
                   "Advance Placement Distance¹ — Condition A²: Speed reduction and lane "
                   "changing in heavy traffic"]
                  + [f"Advance Placement Distance¹ — Condition B: Deceleration to the listed "
                     f"advisory speed (mph) for the condition — {s}"
                     + ("³" if s == "0" else "⁴")
                     for s in ("0", "10", "20", "30", "40", "50", "60", "70", "80")],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2C-3_01", "MUTCD11e_TBLNOTE_2C-3_02",
                    "MUTCD11e_TBLNOTE_2C-3_03", "MUTCD11e_TBLNOTE_2C-3_04",
                    "MUTCD11e_TBLNOTE_2C-3_05", "MUTCD11e_TBLNOTE_2C-3_06",
                    "MUTCD11e_TBLNOTE_2C-3_07"],
    rows=[[V(text=r[0], number=float(r[0].split()[0]), unit="mph",
             footnotes=[])] + [ft(x) for x in r[1:]] for r in _2C3],
    footnotes=[
        Footnote(marker="1", text="The distances are adjusted for a sign legibility distance of "
            "180 feet for Condition A. The distances for Condition B (with the exception of the "
            "potential stop condition) have been adjusted for a sign legibility distance of 250 "
            "feet, which is appropriate for an alignment warning symbol sign. For Conditions A "
            "and B, warning signs with less than 6-inch legend or more than four words, a minimum "
            "of 100 feet should be added to the advance placement distance to provide adequate "
            "legibility of the warning sign.", applies_to="table"),
        Footnote(marker="2", text="Typical conditions are locations where the road user must use "
            "extra time to adjust speed and change lanes in heavy traffic because of a complex "
            "driving situation. Typical signs are Merge and Lane Ends. The distances are "
            "determined by providing the driver a PRT of 14.0 to 14.5 seconds for vehicle "
            "maneuvers (2018 AASHTO Policy, Table 3-3, Decision Sight Distance, Avoidance "
            "Maneuver E) and adjusted for a legibility distance of 180 feet for the appropriate "
            "sign.", applies_to="column:1"),
        Footnote(marker="3", text="Typical condition is the warning of a potential stop situation. "
            "Typical signs are Stop Ahead, Yield Ahead, Signal Ahead, and Intersection Warning "
            "signs. The distances are based on the 2018 AASHTO Policy, Table 3-1, Stopping Sight "
            "Distance, providing a PRT of 2.5 seconds, a deceleration rate of 11.2 feet/second2.",
            applies_to="column:2"),
        Footnote(marker="4", text="Typical conditions are locations where the road user must "
            "decrease speed to maneuver through the warned condition. Typical signs are Turn, "
            "Curve, Reverse Turn, or Reverse Curve. The distance is determined by providing a 2.5 "
            "second PRT, a vehicle deceleration rate of 10 feet/second2, and adjusted for a sign "
            "legibility distance of 250 feet.",
            applies_to=",".join(f"column:{i}" for i in range(3, 11))),
        Footnote(marker="5", text="No suggested distances are provided for these speeds, as the "
            "placement location is dependent on site conditions and other signing. An alignment "
            "warning sign may be placed anywhere from the point of curvature up to 100 feet in "
            "advance of the curve. However, the alignment warning sign should be installed in "
            "advance of the curve and at least 100 feet from any other signs.", applies_to="cell"),
        Footnote(marker="6", text="The minimum advance placement distance is listed as 100 feet "
            "to provide adequate spacing between signs.", applies_to="cell"),
        Footnote(marker="Note", text="Warning signs that advise road users about conditions that "
            "are not related to a specific location, such as Deer Crossing or SOFT SHOULDER, can "
            "be installed in an appropriate location, based on engineering judgment."),
    ],
))

# ---- Table 2C-4: two lettered sub-tables under one caption ---------------
T.append(Table(
    table_id="Table 2C-4", part="A", page_pdf=196, page_printed="196",
    title="Application of Traffic Control Devices for Changes in Horizontal "
          "Alignment — A: Determination of the Need for Devices¹",
    crop_file="table_2C-4_p0196.png", kind="text",
    column_labels=["Roadway Type", "AADT — Less than 1,000", "AADT — 1,000-2,999",
                   "AADT — 3,000-3,999", "AADT — Greater than 3,999"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2C-4_01", "MUTCD11e_TBLNOTE_2C-4_02"],
    rows=[[V(text=a, footnotes=f), V(text=b), V(text=c), V(text=d), V(text=e)]
          for a, f, b, c, d, e in [
        ("Freeways and Expressways", [], "Required", "Required", "Required", "Required"),
        ("Arterial or Collector without Pavement Markings", [], "Optional",
         "Recommended", "Required", "Required"),
        ("Arterial or Collector with Pavement Markings", ["2"], "Optional",
         "Recommended", "Recommended", "Required"),
        ("All other roadways", [], "Optional", "Optional", "Optional", "Optional"),
    ]],
    footnotes=[
        Footnote(marker="1", text="If devices are determined to be needed, the selection of the "
                                  "device(s) is based on Chart B below."),
        Footnote(marker="2", text="An arterial or collector is considered to have pavement "
                                  "markings when either a center line, edge lines, or both are "
                                  "present.", applies_to="cell"),
    ],
))

# Speed differential is a row KEY that is a threshold, not a point value:
# "20 mph or more" must match a measured 25 mph.
T.append(Table(
    table_id="Table 2C-4", part="B", page_pdf=196, page_printed="196",
    title="Application of Traffic Control Devices for Changes in Horizontal "
          "Alignment — B: Selection of Devices",
    crop_file="table_2C-4_p0196.png", kind="mixed",
    # both headings carry markers: 3 points at Section 2C.06 and back to
    # chart A, 6 at the Advisory Speed Plaque section
    column_labels=["Speed Differential³",
                   "Devices for Change in Horizontal Alignment³‧⁶"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="5 mph", number=5, unit="mph"),
         V(text="Pavement markings or advance horizontal alignment warning sign on paved "
                "roadways. Advance horizontal alignment warning sign on unpaved roadways.",
           footnotes=["4"])],
        [V(text="10 mph", number=10, unit="mph"),
         V(text="Advance horizontal alignment warning sign")],
        [V(text="15 mph", number=15, unit="mph"),
         V(text="Delineators and advance horizontal alignment warning sign", footnotes=["5"])],
        [V(text="20 mph or more", minimum=20, unit="mph"),
         V(text="Chevrons and advance horizontal alignment warning sign", footnotes=["5"])],
    ],
    footnotes=[
        Footnote(marker="3", text="The provisions for the use of Horizontal Alignment warning "
                                  "signs and devices are contained in Section 2C.06. The need for "
                                  "devices is determined by Chart A above.",
                 applies_to="column:0,column:1"),
        Footnote(marker="4", text="A roadway is considered to have pavement markings when either "
                                  "a center line, edge lines, or both are present.", applies_to="cell"),
        Footnote(marker="5", text="Section 2C.10 contains information about the use of a "
                                  "One-Direction Large Arrow (W1-6) sign in place of or to "
                                  "supplement delineators and chevrons.", applies_to="cell"),
        Footnote(marker="6", text="See Section 2C.59 for the use of the Advisory Speed Plaque.",
                 applies_to="column:1"),
    ],
))

# ---- Table 2C-5 ----------------------------------------------------------
# Every column is a RANGE: a calculator asked for the spacing at a 500-foot
# radius must match "401 to 700 feet", not look for an exact row.
T.append(Table(
    table_id="Table 2C-5", page_pdf=199, page_printed="199",
    title="Typical Spacing of Chevron Alignment Signs on Horizontal Curves",
    crop_file="table_2C-5_p0199.png", kind="numeric",
    column_labels=["Advisory Speed", "Curve Radius", "Sign Spacing"],
    row_key_columns=[0, 1], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2C-5_01"],
    rows=[
        [V(text="15 mph or less", maximum=15, unit="mph"),
         V(text="Less than 200 feet", maximum=200, max_inclusive=False, unit="ft"),
         V(text="40 feet", number=40, unit="ft")],
        [V(text="20 to 30 mph", minimum=20, maximum=30, unit="mph"),
         V(text="200 to 400 feet", minimum=200, maximum=400, unit="ft"),
         V(text="80 feet", number=80, unit="ft")],
        [V(text="35 to 45 mph", minimum=35, maximum=45, unit="mph"),
         V(text="401 to 700 feet", minimum=401, maximum=700, unit="ft"),
         V(text="120 feet", number=120, unit="ft")],
        [V(text="50 to 60 mph", minimum=50, maximum=60, unit="mph"),
         V(text="701 to 1,250 feet", minimum=701, maximum=1250, unit="ft"),
         V(text="160 feet", number=160, unit="ft")],
        [V(text="More than 60 mph", minimum=60, min_inclusive=False, unit="mph"),
         V(text="More than 1,250 feet", minimum=1250, min_inclusive=False, unit="ft"),
         V(text="200 feet", number=200, unit="ft")],
    ],
    footnotes=[
        Footnote(marker="Note", text="The relationship between the curve radius and the advisory "
                                     "speed shown in this table should not be used to determine "
                                     "the advisory speed."),
    ],
))
