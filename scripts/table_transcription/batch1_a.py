import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "vlm transcription from crop, unverified"

T = []

T.append(Table(
    table_id="Table 1B-1", page_pdf=46, page_printed="46",
    title="Target Compliance Dates Established by the FHWA",
    crop_file="table_1B-1_p0046.png", kind="text",
    column_labels=["MUTCD Section(s)", "Subject Area", "Specific Provision",
                   "Compliance Date"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="2B.64"), V(text="Weight Limit Signs"),
         V(text="Paragraph 14 - requirement for additional Weight Limit sign with the advisory "
                "distance or directional legend in advance of applicable section of highway or structure"),
         V(text="January 18, 2029")],
        [V(text="2C.25"), V(text="Low Clearance Signs (W12-2)"),
         V(text="Paragraph 1 - Required posting of the Low Clearance Advance (W12-2) sign in "
                "advance of the structure"),
         V(text="January 18, 2029")],
        [V(text="2C.25"), V(text="Low Clearance Signs (W12-2a, W12-2b)"),
         V(text="Paragraph 8 - Recommended posting of Low Clearance Overhead (W12-2a or 12-2b) "
                "signs on an arch or other structure under which the clearance varies greatly"),
         V(text="January 18, 2029")],
        [V(text="3A.05"), V(text="Maintaining Minimum Retroreflectivity"),
         V(text="Implementation and continued use of a method that is designed to maintain "
                "retroreflectivity of longitudinal pavement markings (see Paragraph 1 of Section 3A.05)"),
         V(text="September 6, 2026")],
        [V(text="8B.16"), V(text="High-Profile Grade Crossings"),
         V(text="Paragraphs 3 and 7 - Recommended installation of Low Ground Clearance and/or "
                "Vehicle Exclusion signs and detour signs for vehicles with low ground clearances "
                "that might hang up on high-profile grade crossings at locations with a known history"),
         V(text="January 18, 2029")],
        [V(text="8D.09 through 8D.12"), V(text="Highway Traffic Signals at or Near Grade Crossings"),
         V(text="Assessment and determination of appropriate treatment to achieve compliance "
                "(preemption, movement prohibition, pre-signals, queue cutter signals)"),
         V(text="January 18, 2034")],
    ],
))

T.append(Table(
    table_id="Table 1D-3", page_pdf=78, page_printed="78",
    title="Unacceptable Abbreviations",
    crop_file="table_1D-3_p0078.png", kind="text",
    column_labels=["Abbreviation", "Intended Word", "Common Misinterpretation"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a), V(text=b), V(text=c)] for a, b, c in [
        ("ACC", "Accident", "Access (Road)"),
        ("CLRS", "Clears", "Colors"),
        ("DLY", "Delay", "Daily"),
        ("FDR", "Feeder", "Federal"),
        ("L", "Left", "Lane (Merge)"),
        ("LT", "Light (Traffic)", "Left"),
        ("PARK", "Parking", "Park"),
        ("POLL", "Pollution (Index)", "Poll"),
        ("RED", "Reduce", "Red"),
        ("STAD", "Stadium", "Standard"),
        ("WRNG", "Warning", "Wrong"),
    ]],
))

T.append(Table(
    table_id="Table 2A-1", page_pdf=83, page_printed="83",
    title="Use of Sign Shapes",
    crop_file="table_2A-1_p0083.png", kind="text",
    column_labels=["Shape", "Signs"], row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2A-1_01", "MUTCD11e_TBLNOTE_2A-1_02",
                    "MUTCD11e_TBLNOTE_2A-1_03", "MUTCD11e_TBLNOTE_2A-1_04"],
    rows=[
        [V(text="Octagon", footnotes=["*"]), V(text="Stop (R1-1)", footnotes=["**"])],
        [V(text="Equilateral Triangle (downward-pointing)", footnotes=["*"]),
         V(text="Yield (R1-2)", footnotes=["**"])],
        [V(text="Circle", footnotes=["*"]),
         V(text="Grade Crossing Advance Warning (W10-1)", footnotes=["**"])],
        [V(text="Pennant (Isosceles Triangle with longer axis horizontal, pointed right)",
           footnotes=["*"]),
         V(text="No Passing Zone (W14-3)", footnotes=["**"])],
        [V(text="Pentagon (upward-pointing)", footnotes=["*"]),
         V(text="School (S1-1) (squared bottom corners); County Route (M1-6) "
                "(tapered lower sides)", footnotes=["**"])],
        [V(text="Crossbuck (two rectangles in a perpendicular \"X\" configuration)",
           footnotes=["*"]),
         V(text="Grade Crossing (R15-1)", footnotes=["**"])],
        [V(text="Diamond"), V(text="Warning Series")],
        [V(text="Rectangle (including square)"),
         V(text="Regulatory Series; Guide Series; Warning Series", footnotes=["***"])],
        [V(text="Trapezoid", footnotes=["*"]),
         V(text="Recreational and Cultural Interest Area Guide Series (isosceles or "
                "right-angled); National Forest Route Sign (M1-1) (isosceles)",
           footnotes=["**"])],
    ],
    footnotes=[
        Footnote(marker="*", text="This shape shall be limited exclusively to the sign(s) indicated."),
        Footnote(marker="**", text="This sign shall be exclusively the shape shown."),
        Footnote(marker="***", text="Guide series includes general service, specific service, "
                                    "tourist-oriented directional, general information, recreational "
                                    "and cultural interest area, and emergency management signs."),
        Footnote(marker="Note", text="Signs with standardized designs shall not be modified to "
                                     "accommodate a different shape except as provided in this Manual."),
    ],
))

T.append(Table(
    table_id="Table 2A-3", page_pdf=103, page_printed="103",
    title="Illumination of Sign Elements",
    crop_file="table_2A-3_p0103.png", kind="text",
    column_labels=["Means of Illumination", "Sign Element to be Illuminated"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="Light behind the sign face"),
         V(text="Symbol or word message; Background; Symbol, word message, and background "
                "(through a translucent material)")],
        [V(text="Attached or independently-mounted light source designed to direct essentially "
                "uniform illumination onto the sign face"),
         V(text="Entire sign face")],
        [V(text="Light-emitting diodes (LEDs)"),
         V(text="Symbol or word message; Entire sign border")],
        [V(text="Other devices or treatments that highlight the sign shape, color, or message: "
                "Luminous tubing; Fiber optics; Incandescent light bulbs; Luminescent panels"),
         V(text="Symbol or word message; Entire sign face")],
    ],
))

T.append(Table(
    table_id="Table 2A-4", page_pdf=103, page_printed="103",
    title="Retroreflection of Sign Elements",
    crop_file="table_2A-4_p0103.png", kind="text",
    column_labels=["Means of Retroreflection", "Sign Element"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="Prismatic reflector \"buttons\" or similar units"),
         V(text="Symbol; Word message; Border")],
        [V(text="A material that has a smooth, sealed outer surface over a microstructure "
                "that reflects light"),
         V(text="Symbol; Word message; Border; Background")],
    ],
))

from mrag.vine.table_data import Quantity as Q

def _cell(text, qs, star_on=None, note=None):
    v = V(text=text,
          quantities=[Q(name=n, value=val, unit="cd/lx/m2", comparator=">=")
                      for n, val in qs])
    v.footnotes = ([ "*" ] if star_on else []) + ([note] if note else [])
    return v

# Beaded-sheeting cells read "W*; G >= 7": the asterisk sits on the WHITE
# legend, and the number is the BACKGROUND threshold. Reading it as "W >= 7"
# put the value on the wrong variable -- a calculator would then check white
# retroreflectivity against the green limit and pass a sign that should fail.
def _beaded(bg_name, bg_val):
    return _cell(f"W*; {bg_name} >= {bg_val}", [(bg_name, bg_val)], star_on=True)

def _both(a_name, a_val, b_name, b_val, note=None):
    return _cell(f"{a_name} >= {a_val}; {b_name} >= {b_val}",
                 [(a_name, a_val), (b_name, b_val)], note=note)

T.append(Table(
    table_id="Table 2A-5", page_pdf=104, page_printed="104",
    # the caption itself carries "1", which defines the units for every
    # value in the table
    title="Minimum Maintained Retroreflectivity Levels¹",
    crop_file="table_2A-5_p0104.png", kind="numeric",
    column_labels=["Sign Color", "Beaded Sheeting Type (ASTM D4956) I",
                   "Beaded Sheeting Type (ASTM D4956) II",
                   "Beaded Sheeting Type (ASTM D4956) III",
                   "Prismatic Sheeting", "Additional Criteria"],
    row_key_columns=[0, 5], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2A-5_01"],
    rows=[
        [V(text="White on Green"), _beaded("G", 7), _beaded("G", 15), _beaded("G", 25),
         _both("W", 250, "G", 25), V(text="Overhead")],
        [V(text="White on Green"), _beaded("G", 7),
         _both("W", 120, "G", 15), _both("W", 120, "G", 15), _both("W", 120, "G", 15),
         V(text="Post-mounted")],
        [V(text="White on Blue"), _beaded("B", 3), _beaded("B", 5), _beaded("B", 12),
         _both("W", 250, "B", 12), V(text="Overhead")],
        [V(text="White on Blue"), _beaded("B", 3),
         _both("W", 120, "B", 7), _both("W", 120, "B", 7), _both("W", 120, "B", 7),
         V(text="Post-mounted")],
        [V(text="White on Brown"), _beaded("Br", 1), _beaded("Br", 5), _beaded("Br", 10),
         _both("W", 350, "Br", 10), V(text="Overhead")],
        [V(text="White on Brown"), _beaded("Br", 1),
         _both("W", 150, "Br", 5), _both("W", 150, "Br", 5), _both("W", 150, "Br", 5),
         V(text="Post-mounted")],
        [V(text="Black on Yellow or Black on Orange"),
         V(text="Y*; O*", footnotes=["*"]),
         _both("Y", 50, "O", 50), _both("Y", 50, "O", 50), _both("Y", 50, "O", 50, note="2"),
         V(text="", missing="blank", footnotes=["2"])],
        [V(text="Black on Yellow or Black on Orange"),
         V(text="Y*; O*", footnotes=["*"]),
         _both("Y", 75, "O", 75), _both("Y", 75, "O", 75), _both("Y", 75, "O", 75, note="3"),
         V(text="", missing="blank", footnotes=["3"])],
        [V(text="White on Red"),
         _both("W", 35, "R", 7), _both("W", 35, "R", 7), _both("W", 35, "R", 7),
         _both("W", 35, "R", 7, note="4"),
         V(text="", missing="blank", footnotes=["4"])],
        [V(text="Black on White"),
         _cell("W >= 50", [("W", 50)]), _cell("W >= 50", [("W", 50)]),
         _cell("W >= 50", [("W", 50)]), _cell("W >= 50", [("W", 50)]),
         V(text="", missing="blank")],
    ],
    variables={"W": "white legend retroreflectivity", "G": "green background",
               "B": "blue background", "Br": "brown background",
               "Y": "yellow background", "O": "orange background",
               "R": "red background"},
    footnotes=[
        Footnote(marker="1", text="The minimum maintained retroreflectivity levels shown in this "
                                  "table are in units of cd/lx/m2 measured at an observation angle "
                                  "of 0.2 degrees and an entrance angle of -4.0 degrees."),
        Footnote(marker="2", text="For overhead and fine symbol signs measuring at least 48 inches "
                                  "and for all sizes of bold symbol signs"),
        Footnote(marker="3", text="For word legend and fine symbol signs measuring less than 48 inches"),
        Footnote(marker="4", text="Minimum sign contrast ratio >= 3:1 (white retroreflectivity / "
                                  "red retroreflectivity)"),
        Footnote(marker="*", text="This sheeting type shall not be used for this color for this "
                                  "application."),
    ],
))
