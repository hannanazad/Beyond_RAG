"""Tables 2C-6 and the 2D series."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "vlm transcription from a PDF render, unverified"
T = []

T.append(Table(
    table_id="Table 2C-6", page_pdf=237, page_printed="237",
    title="Use of Advisory Speed Plaque for Horizontal Alignment Changes",
    crop_file="table_2C-6_p0237.png", kind="mixed",
    # the "1" is printed on the second column heading, not on any cell
    column_labels=["Speed Differential", "Use of Advisory Speed Plaque (W13-1P)¹"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="5 mph", number=5, unit="mph"), V(text="Optional")],
        [V(text="10 mph", number=10, unit="mph"), V(text="Recommended")],
        # "or more" is a threshold: a measured 20 mph differential must match.
        [V(text="15 mph or more", minimum=15, unit="mph"), V(text="Required")],
    ],
    footnotes=[Footnote(marker="1", text="See Section 2C.59", applies_to="column:1")],
))

_2D3 = [("Avenue","Ave"),("Boulevard","Blvd"),("Bypass","Byp"),("Causeway","Cswy"),
        ("Circle","Cir"),("Corner","Cor"),("Court","Ct"),("Crescent","Cres"),
        ("Drive","Dr"),("East","E*"),("Expressway","Expwy"),("Extension","Ext"),
        ("Freeway","Fwy"),("Highway","Hwy"),("Lane","La, Ln"),("Landing","Lndg"),
        ("North","N*"),("Northeast","NE*"),("Northwest","NW*"),("Parkway","Pkwy"),
        ("Place","Pl"),("Plaza","Plz"),("Road","Rd"),("Route","Rte"),("South","S*"),
        ("Southeast","SE*"),("Southwest","SW*"),("Square","Sq"),("Street","St"),
        ("Terrace","Ter"),("Thruway","Thwy"),("Trafficway","Trfwy"),("Trail","Tr"),
        ("Turnpike","Tpk"),("West","W*")]

T.append(Table(
    table_id="Table 2D-3", page_pdf=254, page_printed="254",
    title="Acceptable Abbreviations for Street Name Descriptors",
    crop_file="table_2D-3_p0254.png", kind="text",
    column_labels=["Descriptor", "Standard Abbreviation"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    # printed in two side-by-side columns on the page; one logical list
    rows=[[V(text=a), V(text=b.rstrip("*"), footnotes=["*"] if b.endswith("*") else [])]
          for a, b in _2D3],
    footnotes=[Footnote(marker="*", text="For pre-directional or post-directional designations "
                                         "or cardinal orientations, such as E Main St or 3rd St SW")],
))

_2D4 = ["Alley","Belt","Beltway","Close","Cove","Edge","Gate","Green","Grove","Hill",
        "Loop","Mews","Oval","Pass","Passage","Path","Ridge","Row","Run","Trace",
        "Turn","View","Vista","Walk"]

T.append(Table(
    table_id="Table 2D-4", page_pdf=254, page_printed="254",
    title="Street Name Descriptors Not Acceptable for Abbreviation",
    crop_file="table_2D-4_p0254.png", kind="text",
    column_labels=["Descriptor"], row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=x)] for x in _2D4],
))

T.append(Table(
    table_id="Table 2D-5", page_pdf=277, page_printed="277",
    title="Overhead Arrow-per-Lane Arrow Height Based on Principal Legend Letter Height",
    crop_file="table_2D-5_p0277.png", kind="numeric",
    column_labels=["Principal Legend Letter Height", "Straight Arrow", "Turn Arrow"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2D-5_01"],
    rows=[[V(text=a, number=av, unit="in"), V(text=b, number=bv, unit="in"),
           V(text=c, number=cv, unit="in")]
          for a, av, b, bv, c, cv in [
              ("13.33", 13.33, "32", 32, "25.333", 25.333),
              ("10.67", 10.67, "25.5", 25.5, "20.188", 20.188),
              ("8", 8, "21", 21, "16.625", 16.625),
          ]],
    footnotes=[Footnote(marker="Note", text="Letter and arrow heights are shown in inches.")],
))

T.append(Table(
    table_id="Table 2D-6", page_pdf=289, page_printed="289",
    title="Minimum Letter Heights on Street Name Signs",
    crop_file="table_2D-6_p0289.png", kind="mixed",
    column_labels=["Type of Mounting", "Type of Street or Highway", "Speed Limit",
                   "Recommended Minimum Letter Height — Initial Upper-Case",
                   "Recommended Minimum Letter Height — Lower-Case"],
    row_key_columns=[0, 2], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2D-6_01", "MUTCD11e_TBLNOTE_2D-6_02"],
    rows=[
        [V(text="Overhead"), V(text="All types"), V(text="All speed limits"),
         V(text="12 inches", number=12, unit="in", footnotes=["*"]),
         V(text="9 inches", number=9, unit="in", footnotes=["*"])],
        [V(text="Post-mounted"), V(text="Multi-lane"),
         V(text="More than 40 mph", minimum=40, min_inclusive=False, unit="mph"),
         V(text="8 inches", number=8, unit="in", footnotes=["*"]),
         V(text="6 inches", number=6, unit="in", footnotes=["*"])],
        [V(text="Post-mounted"), V(text="Multi-lane"),
         V(text="40 mph or less", maximum=40, unit="mph"),
         V(text="6 inches", number=6, unit="in", footnotes=["*"]),
         V(text="4.5 inches", number=4.5, unit="in", footnotes=["*"])],
        [V(text="Post-mounted"), V(text="2-lane"), V(text="All speed limits"),
         V(text="6 inches", number=6, unit="in", footnotes=["*", "**"]),
         V(text="4.5 inches", number=4.5, unit="in", footnotes=["*", "**"])],
    ],
    footnotes=[
        Footnote(marker="*", text="Letter heights shown are for the street name. Descriptors or "
                                  "other supplementary legend may be displayed in smaller "
                                  "lettering of at least 3 inches."),
        Footnote(marker="**", text="On two-lane local streets with speed limits of 25 mph or "
                                   "less, 4-inch initial upper-case letters with 3-inch "
                                   "lower-case letters may be used.", applies_to="cell"),
    ],
))

# ---- Table 2D-1 (2 sheets) ----------------------------------------------
from batch2 import sz

_2D1_COLS = ["Sign or Plaque", "Designation", "Section", "Conventional Road",
             "Minimum", "Oversized"]
# This "*" is different again: it marks a size that is only TYPICAL, so a
# calculator must not treat those cells as a fixed requirement.
_2D1_NOTES = [
    Footnote(marker="*", text="The size shown is for a typical sign. The size should be "
                              "determined based on the amount of legend required for the sign."),
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions in inches are shown as width x height"),
]

def _2d1(n, page, rows):
    return Table(
        table_id="Table 2D-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="Conventional Road Guide Sign and Plaque Sizes",
        crop_file=f"table_2D-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=_2D1_COLS, row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [sz(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_2D1_NOTES),
    )

_2D1_S1 = [
 ("Interstate Route (1 or 2 digits)","M1-1,1a","2D.11","24 x 24","—","36 x 36"),
 ("Interstate Route (3 digits)","M1-1,1a","2D.11","30 x 24","—","45 x 36"),
 ("Off-Interstate Route (1 or 2 digits)","M1-2,3","2D.11","24 x 24","—","36 x 36"),
 ("Off-Interstate Route (3 digits)","M1-2,3","2D.11","30 x 24","—","45 x 36"),
 ("U.S. Route (1 or 2 digits)","M1-4","2D.11","24 x 24","—","36 x 36"),
 ("U.S. Route (3 digits)","M1-4","2D.11","30 x 24","—","45 x 36"),
 ("State Route (1 or 2 digits)","M1-5","2D.11","24 x 24","—","36 x 36"),
 ("State Route (3 digits)","M1-5","2D.11","30 x 24","—","45 x 36"),
 ("County Route","M1-6","2D.11","24 x 24","—","36 x 36"),
 ("Forest Route","M1-7","2D.11","24 x 24","18 x 18","36 x 36"),
 ("Junction (plaque)","M2-1P","2D.13","21 x 15","—","30 x 21"),
 ("Combination Junction (2 route signs)","M2-2","2D.14","60 x 48*","—","—"),
 ("Cardinal Direction (plaque)","M3-1P,2P,3P,4P","2D.15","24 x 12","—","36 x 18"),
 ("Alternate (plaque)","M4-1P,1aP","2D.17","24 x 12","—","36 x 18"),
 ("By-Pass (plaque)","M4-2P","2D.18","24 x 12","—","36 x 18"),
 ("Business (plaque)","M4-3P","2D.19","24 x 12","—","36 x 18"),
 ("Truck (plaque)","M4-4P","2D.20","24 x 12","—","36 x 18"),
 ("To (plaque)","M4-5P","2D.21","24 x 12","—","36 x 18"),
 ("End (plaque)","M4-6P","2D.22","24 x 12","—","36 x 18"),
 ("Temporary (plaque)","M4-7P,7aP","2D.24","24 x 12","—","36 x 18"),
 ("Emergency Route","M4-11","2D.59","30 x 30","—","—"),
 ("Emergency Route","M4-11a","2D.59","30 x 30","—","—"),
 ("Emergency Route To (plaque)","M4-11bP, 11cP","2D.59","30 x 18","—","—"),
 ("End Emergency Route","M4-12","2D.59","24 x 18","—","—"),
 ("Begin (plaque)","M4-14P","2D.23","24 x 12","—","36 x 18"),
 ("Advance Turn Arrow (plaque)","M5-1P,2P,3P","2D.26","21 x 15","—","30 x 21"),
 ("Lane Designation (plaque)","M5-4P,5P,6P","2D.27","24 x 18","—","36 x 24"),
 ("Directional Arrow (plaque)","M6-1P,2P,2aP, 3P,4P,5P,6P,7P","2D.28","21 x 15","—","30 x 21"),
 ("National Scenic Byway","M10-1","2D.57","24 x 24","—","—"),
 ("National Scenic Byway (plaque)","M10-1aP","2D.57","24 x 12","—","—"),
 ("Byway Identification","M10-2","2D.58","24 x 24","—","—"),
 ("Byway Identification (plaque)","M10-2aP","2D.58","24 x 12","—","—"),
 ("State Scenic Byway System","M10-3","2D.58","24 x 24","—","—"),
 ("State Scenic Byway - Simple Graphic and Byway Identification","M10-3a","2D.58","24 x 24","—","—"),
 ("Scenic Byway (plaque)","M10-3bP","2D.58","24 x 12","—","—"),
 ("National Historic Trail - Identification","M11-1","2D.58","24 x 24","—","—"),
 ("National Historic Trail - Historic Route (plaque)","M11-1aP","2D.58","24 x 12","—","—"),
 ("National Historic Trail - Crossing (plaque)","M11-1bP","2D.58","24 x 12","—","—"),
 ("National Historic Trail - Auto Tour Route (plaque)","M11-1cP","2D.58","24 x 12","—","—"),
 ("National Historic Trail - Distance (plaque)","M11-1dP","2D.58","24 x 12","—","—"),
 ("Destination (1 line)","D1-1","2D.36","Varies x 18","—","—"),
 ("Destination and Distance (1 line)","D1-1a","2D.36","Varies x 18","—","—"),
 ("Circular Intersection Destination (1 line)","D1-1d","2D.39","Varies x 18","—","—"),
 ("Circular Intersection Departure Guide","D1-1e","2D.39","Varies x 42*","—","—"),
 ("Destination (2 lines)","D1-2","2D.36","Varies x 30","—","—"),
 ("Destination and Distance (2 lines)","D1-2a","2D.36","Varies x 30","—","—"),
 ("Circular Intersection Destination (2 lines)","D1-2d","2D.39","Varies x 30","—","—"),
]

_2D1_S2 = [
 ("Destination (3 lines)","D1-3","2D.36","Varies x 42","—","—"),
 ("Destination and Distance (3 lines)","D1-3a","2D.36","Varies x 42","—","—"),
 ("Circular Intersection Destination (3 lines)","D1-3d","2D.39","Varies x 42","—","—"),
 ("Circular Intersection Diagrammatic Destination","D1-5","2D.39","Varies x 72*","—","—"),
 ("Circular Intersection Diagrammatic Destination, Right-Turn Bypass","D1-5a","2D.39","Varies x 78*","—","—"),
 ("Distance (1 line)","D2-1","2D.43","Varies x 18","—","—"),
 ("Distance (2 lines)","D2-2","2D.43","Varies x 30","—","—"),
 ("Distance (3 lines)","D2-3","2D.43","Varies x 42","—","—"),
 ("Street Name (1 line)","D3-1,1a","2D.45","Varies x 12","Varies x 8","Varies x 18"),
 ("Overhead Street Name (1 line)","D3-1,1a","2D.45","Varies x 24","—","—"),
 ("Street Name (2 lines)","D3-1,1a","2D.45","Varies x 24","Varies x 15","Varies x 33"),
 ("Overhead Street Name (2 lines)","D3-1,1a","2D.45","Varies x 48","—","—"),
 ("Advance Street Name (2 lines)","D3-2","2D.46","Varies x 30","—","—"),
 ("Advance Street Name (3 lines)","D3-2","2D.46","Varies x 42","—","—"),
 ("Advance Street Name (4 lines)","D3-2","2D.46","Varies x 54","—","—"),
 ("Parking Area Directional","D4-1","2D.47","30 x 24","18 x 15","—"),
 ("Park - Ride","D4-2","2D.48","30 x 36","24 x 30","36 x 48"),
 ("Advance Weigh Station Distance","D8-1","2D.51","78 x 60","60 x 48","96 x 72"),
 ("Weigh Station Ahead","D8-1a","2D.51","66 x 48","48 x 36","—"),
 ("Weigh Station Advance Direction","D8-2","2D.51","84 x 72","66 x 54","108 x 90"),
 ("Weigh Station Entrance Direction","D8-3","2D.51","66 x 60","48 x 42","84 x 78"),
 ("Crossover","D13-1,2","2D.52","60 x 30","—","78 x 42"),
 ("Freeway Entrance","D13-3","2D.50","48 x 30","—","—"),
 ("Freeway Entrance (Directional)","D13-3a","2D.50","48 x 42","—","—"),
 ("Combination Lane Use / Destination","D15-1","2D.38","Varies x 96","—","—"),
 ("Next Truck Lane","D17-1","2D.53","42 x 48","—","60 x 66"),
 ("Advance Truck Lane","D17-2","2D.53","42 x 42","—","60 x 54"),
 ("Next Passing Lane","D17-3","2D.53","42 x 48","—","60 x 66"),
 ("Advance Passing Lane","D17-4","2D.53","42 x 42","—","60 x 54"),
 ("Advance Emergency Turn-Out","D17-5","2D.54","60 x 36","—","78 x 54"),
 ("Emergency Turn-Out (Directional)","D17-6","2D.54","60 x 36","—","78 x 60"),
 ("Advance Slow Vehicle Turn-Out","D17-7","2D.54","72 x 36","—","96 x 54"),
]

T.append(_2d1(1, 248, _2D1_S1))
T.append(_2d1(2, 249, _2D1_S2))

# ---- Table 2D-2 ----------------------------------------------------------
# The page interleaves GROUP HEADINGS ("A. Intersection or Interchange Advance
# Guide Signs", then "Interstate or Off-Interstate Business Route Signs") with
# the data rows beneath them. A row reading "Numerals | 6 | 9 | 14 ..." means
# nothing on its own, so the headings are carried as their own columns and
# every row is self-contained.
def _lh(text):
    """A cell is either a letter height in inches or a shield size w x h."""
    if text == "—":
        return V(text="—", missing="none")
    if "x" in text:
        return sz(text)
    return V(text=text, number=float(text), unit="in")

_2D2_COLS = ["Group", "Sub-group", "Type of Sign",
             "Single-Lane — Less than 30 mph", "Single-Lane — 30-40 mph",
             "Single-Lane — Greater than 40 mph",
             "Multi-Lane — Less than 30 mph", "Multi-Lane — 30-40 mph",
             "Multi-Lane — Greater than 40 mph"]

_A = "A. Intersection or Interchange Advance Guide Signs and Entrance Direction Guide Signs"
_B = "B. Destination and Other Guide Signs"

_2D2_S1 = [
 (_A,"Interstate or Off-Interstate Business Route Signs","Numerals**","6","9","14","9","9","14"),
 (_A,"Interstate or Off-Interstate Business Route Signs","1- or 2-Digit Shields","18 x 18","24 x 24","36 x 36","24 x 24","24 x 24","36 x 36"),
 (_A,"Interstate or Off-Interstate Business Route Signs","3-Digit Shields","22.5 x 18","30 x 24","45 x 36","30 x 24","30 x 24","45 x 36"),
 (_A,"U.S. or State Route Signs","Numerals","9","12","18","12","12","18"),
 (_A,"U.S. or State Route Signs","1- or 2-Digit Shields","18 x 18","24 x 24","36 x 36","24 x 24","24 x 24","36 x 36"),
 (_A,"U.S. or State Route Signs","3-Digit Shields","22.5 x 18","30 x 24","45 x 36","30 x 24","30 x 24","45 x 36"),
 (_A,"County Route Signs","Numerals","6","8","10","8","8","10"),
 (_A,"County Route Signs","1-, 2-, or 3-Digit Shields","18 x 18","24 x 24","36 x 36","24 x 24","24 x 24","36 x 36"),
 (_A,"U.S. or State Route Text Identification (Examples: US 56, Md 2)","Numerals & Letters","8","12","15","10","12","15"),
 (_A,"Cardinal Directions (NORTH, SOUTH, EAST, WEST)","First Letter - Upper-Case","6","8","10","8","8","10"),
 (_A,"Cardinal Directions (NORTH, SOUTH, EAST, WEST)","Rest of Word - Upper-Case","5","6","8","6","6","8"),
 (_A,"Auxiliary and Alternative Route Legends (Examples: JCT, TO, ALT, BUSINESS)","Words - Upper-Case","5","6","8","6","6","8"),
 (_A,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Leading Upper-Case Letter or Numerals","6","8","10.67","8","10.67","13.33"),
 (_A,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Following Lower-Case Letters or Ordinals**","4.5","6","8","6","8","10"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Numerals","6","6","8","6","8","10"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Fraction Numerals","4.5","4.5","6","4.5","6","8"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Words - Upper-Case","4.5","4.5","6","4.5","6","8"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Action Message Words - Upper-Case","6","6","8","6","8","10"),
 (_B,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Leading Upper-Case Letter or Numerals","4","6","8","6","8","10.67"),
 (_B,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Following Lower-Case Letters or Ordinals***","3","4.5","6","4.5","6","8"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Numerals","4","6","8","6","6","8"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Fraction Numerals","3","4.5","6","4.5","4.5","6"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Words - Upper-Case","3","4.5","6","4.5","4.5","6"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Action Message Words - Upper-Case","4","6","8","6","6","8"),
]

# Printed at the foot of sheet 2, governing both sheets.
_2D2_NOTES = [
    Footnote(marker="*", text="Except as provided otherwise in this Manual"),
    Footnote(marker="**", text="Minimum size listed for 3-digit shields. Larger numeral sizes "
                               "used for 1-digit, some 2-digit, and some 3-digit shields. See "
                               "the Standard Highways Signs publication for more information on "
                               "Route Sign numeral heights and Standard Alphabet series."),
    Footnote(marker="***", text="Lower-case letter height (loop height) is determined by the "
                                "initial upper-case letter height (see Sec. 2A.08)"),
    Footnote(marker="Note 1", text="Sizes are shown in inches and where applicable are shown as "
                                   "width x height"),
    Footnote(marker="Note 2", text="For Street Name (D3-1 Series) signs, see Table 2D-6"),
    Footnote(marker="Note 3", text="The 18-inch route shield size is not for independent use, "
                                   "such as in Directional or Confirmation Assemblies."),
]

T.append(Table(
    table_id="Table 2D-2", sheet=1, sheet_of=2, part="A - Post-Mounted Signs",
    page_pdf=251, page_printed="251",
    title="Recommended Minimum Letter and Numeral Sizes for Conventional Road "
          "Guide Signs According to Speed* — A: Post-Mounted Signs",
    crop_file="table_2D-2_s1_p0251.png", kind="numeric",
    column_labels=_2D2_COLS, row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]),
           V(text=r[2].rstrip("*"),
             footnotes=["**"] if r[2].endswith("**") and not r[2].endswith("***")
                       else (["***"] if r[2].endswith("***") else []))]
          + [_lh(x) for x in r[3:]] for r in _2D2_S1],
    footnotes=list(_2D2_NOTES),
))

# Sheet 2 prints "8 (min.) / 10.67 (des.)" in one cell: a minimum AND a
# desirable value. Collapsing that to one number would lose the distinction
# between what is required and what is preferred -- exactly the kind of
# condition a calculator must keep.
def _md(text):
    if "(min.)" not in text:
        return _lh(text)
    lo, hi = [p.strip() for p in text.split("/")]
    lo_v = float(lo.replace("(min.)", "").strip())
    hi_v = float(hi.replace("(des.)", "").strip())
    return V(text=text, quantities=[Q(name="minimum", value=lo_v, unit="in"),
                                    Q(name="desirable", value=hi_v, unit="in")])

from mrag.vine.table_data import Quantity as Q

_2D2_S2_COLS = ["Group", "Sub-group", "Type of Sign", "Less than 35 mph",
                "35-55 mph", "Greater than 55 mph"]

_2D2_S2 = [
 (_A,"Interstate or Off-Interstate Business Route Signs","Numerals**","6","9","14"),
 (_A,"Interstate or Off-Interstate Business Route Signs","1- or 2-Digit Shields","18 x 18","24 x 24","36 x 36"),
 (_A,"Interstate or Off-Interstate Business Route Signs","3-Digit Shields","22.5 x 18","30 x 24","45 x 36"),
 (_A,"U.S. or State Route Signs","Numerals","9","12","18"),
 (_A,"U.S. or State Route Signs","1- or 2-Digit Shields","18 x 18","24 x 24","36 x 36"),
 (_A,"U.S. or State Route Signs","3-Digit Shields","22.5 x 18","30 x 24","45 x 36"),
 (_A,"County Route Signs","Numerals","6","8","10"),
 (_A,"County Route Signs","1-, 2-, or 3-Digit Shields","18 x 18","24 x 24","36 x 36"),
 (_A,"U.S. or State Route Text Identification (Examples: US 56, Md 2)","Numerals & Letters","8","12","15"),
 (_A,"Cardinal Directions (NORTH, SOUTH, EAST, WEST)","First Letter - Upper-Case","6","8","12"),
 (_A,"Cardinal Directions (NORTH, SOUTH, EAST, WEST)","Rest of Word - Upper-Case","5","6","10"),
 (_A,"Auxiliary and Alternative Route Legends (Examples: JCT, TO, ALT, BUSINESS)","Words - Upper-Case","5","6","10"),
 (_A,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Leading Upper-Case Letter or Numerals","6","8 (min.) / 10.67 (des.)","13.33 (min.) / 16 (des.)"),
 (_A,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Following Lower-Case Letters or Ordinals**","4.5","6 (min.) / 8 (des.)","10 (min.) / 12 (des.)"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Numerals","6","6 (min.) / 8 (des.)","12 (min.) / 15 (des.)"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Fraction Numerals","4.5","4.5 (min.) / 6 (des.)","8 (min.) / 10 (des.)"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Words - Upper-Case","4.5","4.5 (min.) / 6 (des.)","8 (min.) / 10 (des.)"),
 (_A,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Action Message Words - Upper-Case","6","6 (min.) / 8 (des.)","8 (min.) / 10 (des.)"),
 (_B,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Leading Upper-Case Letter or Numerals","6","8 (min.) / 10.67 (des.)","13.33 (min.) / 16 (des.)"),
 (_B,"Names of Destinations or Roads (Examples: Springfield, Main St, 2nd Ave)","Following Lower-Case Letters or Ordinals**","4.5","6 (min.) / 8 (des.)","10 (min.) / 12 (des.)"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Numerals","6","6 (min.) / 8 (des.)","12 (min.) / 15 (des.)"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Fraction Numerals","4.5","4.5 (min.) / 6 (des.)","8 (min.) / 10 (des.)"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Distance Words - Upper-Case","4.5","4.5 (min.) / 6 (des.)","8 (min.) / 10 (des.)"),
 (_B,"Distance or Action Messages (Examples: 2 MILES, 1/2 MILE, KEEP RIGHT)","Action Message Words - Upper-Case","6","6 (min.) / 8 (des.)","8 (min.) / 10 (des.)"),
]

T.append(Table(
    table_id="Table 2D-2", sheet=2, sheet_of=2, part="B - Overhead-Mounted Signs",
    page_pdf=252, page_printed="252",
    title="Recommended Minimum Letter and Numeral Sizes for Conventional Road "
          "Guide Signs According to Speed* — B: Overhead-Mounted Signs",
    crop_file="table_2D-2_s2_p0252.png", kind="numeric",
    column_labels=_2D2_S2_COLS, row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]),
           V(text=r[2].rstrip("*"), footnotes=["**"] if r[2].endswith("**") else [])]
          + [_md(x) for x in r[3:]] for r in _2D2_S2],
    footnotes=list(_2D2_NOTES),
))
