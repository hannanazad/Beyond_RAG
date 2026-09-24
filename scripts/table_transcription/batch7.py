"""Tables 2E-5 and 2E-1."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V
from batch2 import sz
from batch5 import _lh
from batch6 import _ds

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

# In 2E-5 the slash means something DIFFERENT from 2E-4: footnote ** says
# "Sizes shown as XX/XX correspond to 20-inch/16-inch destination letter
# legend sizes" — so it is a legend-size pairing, not desirable/minimum.
def _leg(text):
    if "/" not in text:
        return _lh(text)
    a, b = [float(x) for x in text.split("/")]
    return V(text=text, quantities=[Q(name="for_20in_legend", value=a, unit="in"),
                                    Q(name="for_16in_legend", value=b, unit="in")])

_2E5 = [
 ("A. Pull-Through Signs","","Destinations — Upper-Case Letters","16"),
 ("A. Pull-Through Signs","","Destinations — Lower-Case Letters","12"),
 ("A. Pull-Through Signs","Route Signs","Numerals*","14"),
 ("A. Pull-Through Signs","Route Signs","1- or 2-Digit Shields","36 x 36"),
 ("A. Pull-Through Signs","Route Signs","3-Digit Shields","45 x 36"),
 ("A. Pull-Through Signs","","Cardinal Directions — First Letter","15"),
 ("A. Pull-Through Signs","","Cardinal Directions — Rest of Word","12"),
 ("B. Supplemental Guide Signs","","Exit Number Words","10"),
 ("B. Supplemental Guide Signs","","Exit Number Numerals and Letters","15"),
 ("B. Supplemental Guide Signs","","Place Names — Upper-Case Letters","13.33"),
 ("B. Supplemental Guide Signs","","Place Names — Lower-Case Letters","10"),
 ("B. Supplemental Guide Signs","","Action Messages","8"),
 ("B. Supplemental Guide Signs","Route Signs","Numerals*","9"),
 ("B. Supplemental Guide Signs","Route Signs","1- or 2-Digit Shield","24 x 24"),
 ("B. Supplemental Guide Signs","Route Signs","3-Digit Shield","30 x 24"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Words — Upper-Case Letters","13.33"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Words — Lower-Case Letters","10"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Numerals","13.33"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Fraction Numerals","10"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","Numerals*","9"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","1- or 2-Digit Shield","24 x 24"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","3-Digit Shield","30 x 24"),
 ("D. Next X Exits Sign","","Place Names — Upper-Case Letters","13.33"),
 ("D. Next X Exits Sign","","Place Names — Lower-Case Letters","10"),
 ("D. Next X Exits Sign","","NEXT X EXITS — Words","10"),
 ("D. Next X Exits Sign","","NEXT X EXITS — Number","15"),
 ("E. Distance Signs","","Words — Upper-Case Letters","8"),
 ("E. Distance Signs","","Words — Lower-Case Letters","6"),
 ("E. Distance Signs","","Numerals","8"),
 ("E. Distance Signs","Route Signs","Numerals*","6"),
 ("E. Distance Signs","Route Signs","1- or 2-Digit Shield","18 x 18"),
 ("E. Distance Signs","Route Signs","3-Digit Shield","22.5 x 18"),
 ("F. General Service Signs (see Chapter 2I)","","Exit Number Words","10"),
 ("F. General Service Signs (see Chapter 2I)","","Exit Number Numerals and Letters","15"),
 ("F. General Service Signs (see Chapter 2I)","","Services","10"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Words","12"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Numerals","15"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Fraction Numerals","10"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Words","10"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Action Message Words","12"),
 ("H. Reference Location Signs (see Chapter 2H)","","Words","4"),
 ("H. Reference Location Signs (see Chapter 2H)","","Numerals","10"),
 ("I. Boundary and Orientation Signs (see Chapter 2H)","","Words — Upper-Case Letters","8"),
 ("I. Boundary and Orientation Signs (see Chapter 2H)","","Words — Lower-Case Letters","6"),
 ("J. Next Exit and Next Services Signs","","Words and Numerals","8"),
 ("K. Exit Only Signs","","Words","12"),
 ("L. Overhead Arrow-per-Lane Signs**","","Arrowhead (Type D Directional Arrow)","20/16.25"),
 ("L. Overhead Arrow-per-Lane Signs**","","Arrow Shaft Width","7.5/6.094"),
 ("L. Overhead Arrow-per-Lane Signs**","Arrow Height","Through","48/39"),
 ("L. Overhead Arrow-per-Lane Signs**","Arrow Height","Left Only","38/30.875"),
 ("L. Overhead Arrow-per-Lane Signs**","Arrow Height","Right Only","38/30.875"),
 ("L. Overhead Arrow-per-Lane Signs**","Arrow Height","Optional-Diverge (Through with Left or Right)","48/39"),
 ("L. Overhead Arrow-per-Lane Signs**","Arrow Height","Optional-Split (Left and Right)","42/34.125"),
 ("L. Overhead Arrow-per-Lane Signs**","","Vertical Separator Width","2"),
 ("L. Overhead Arrow-per-Lane Signs**","","Vertical Space between Vertical Separator and Top of Nearest Arrow","6.5/5.0"),
 ("L. Overhead Arrow-per-Lane Signs**","","Horizontal Space between Vertical Separator and Top of Nearest Through Arrow","12/9"),
 ("L. Overhead Arrow-per-Lane Signs**","","Horizontal Space between Arrow Shaft and EXIT and ONLY Panels","12"),
 ("L. Overhead Arrow-per-Lane Signs**","","EXIT and ONLY Panels","54 x 18"),
 ("M. Diagrammatic Signs","","Arrowhead (Type D Directional Arrow)","13.5"),
 ("M. Diagrammatic Signs","","Stem Height to Upper Point of Departure","30"),
 ("M. Diagrammatic Signs","","Horizontal Space between Arrowhead and Route Shield or Destination","12"),
]

T.append(Table(
    table_id="Table 2E-5", page_pdf=341, page_printed="341",
    title="Minimum Letter and Numeral Sizes for Freeway Guide Signs According to Sign Type",
    crop_file="table_2E-5_p0341.png", kind="numeric",
    column_labels=["Group", "Sub-group", "Type of Sign", "Minimum Size"],
    row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0].rstrip("*"), footnotes=["**"] if r[0].endswith("**") else []),
           V(text=r[1]),
           V(text=r[2].rstrip("*"), footnotes=["*"] if r[2].endswith("*") else []),
           _leg(r[3])] for r in _2E5],
    footnotes=[
        Footnote(marker="*", text="Minimum size listed for 3-digit shields. Larger numeral sizes "
                                  "used for 1-digit, some 2-digit, and some 3-digit shields. See "
                                  "the Standard Highways Signs publication for more information "
                                  "on Route Sign numeral heights and Standard Alphabet series."),
        Footnote(marker="**", text="Overhead Arrow-per-Lane sign example layouts and design "
                                   "elements sizing are provided in the Standard Highway Sign "
                                   "publication. Sizes shown as XX/XX correspond to 20-inch/"
                                   "16-inch destination letter legend sizes respectively."),
        Footnote(marker="Note", text="Sizes are shown in inches and where applicable are shown "
                                     "as width x height."),
    ],
))

# ---- Table 2E-1 (3 sheets) ----------------------------------------------
# "Varies" is a real value here: the sign size depends on the legend, so the
# cell records that no fixed size is given rather than a number.
def _mz(text):
    if text == "—":
        return V(text="—", missing="none")
    if text.startswith("Varies") and "x" not in text:
        return V(text="Varies", missing="not_applicable")
    # Note 3 on sheet 3: "Where two sizes are shown, the larger size is for
    # freeways (F) and the smaller size is for expressways (E)". Keeping only
    # one would apply a freeway size to an expressway, or the reverse.
    if "(F)" in text and "(E)" in text:
        f, e = [x.strip() for x in text.split("/")]
        fw, fh = [float(v) for v in f.replace("(F)", "").strip().split("x")]
        ew, eh = [float(v) for v in e.replace("(E)", "").strip().split("x")]
        return V(text=text, quantities=[
            Q(name="freeway_width", value=fw, unit="in"),
            Q(name="freeway_height", value=fh, unit="in"),
            Q(name="expressway_width", value=ew, unit="in"),
            Q(name="expressway_height", value=eh, unit="in")])
    return sz(text)

_2E1_COLS = ["Sign or Plaque", "Sub-group", "Sign Designation", "Section", "Minimum Size"]

# Printed at the foot of sheet 3, governing all three sheets.
_2E1_NOTES = [
    Footnote(marker="*", text="The size shown is for a typical sign as illustrated in the "
                              "figures in Chapters 2D and 2E. The size should be determined "
                              "based on the amount of legend required for the sign."),
    Footnote(marker="**", text="The width shown represents the minimum dimension. The width "
                               "shall be increased as appropriate to match the width of the "
                               "guide sign."),
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions in inches are shown as width x height"),
    Footnote(marker="Note 3", text="Where two sizes are shown, the larger size is for freeways "
                                   "(F) and the smaller size is for expressways (E)"),
]


def _2e1(n, page, rows, footnotes=None):
    return Table(
        table_id="Table 2E-1", sheet=n, sheet_of=3, page_pdf=page, page_printed=str(page),
        title="Freeway or Expressway Guide Sign and Plaque Sizes",
        crop_file=f"table_2E-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=_2E1_COLS, row_key_columns=[0, 2], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2]), V(text=r[3]), _mz(r[4])]
              for r in rows],
        footnotes=footnotes or list(_2E1_NOTES),
    )

_2E1_S1 = [
 ("Interchange Advance Guide (1 destination)","","E1-1","2E.23","Varies"),
 ("Interchange Advance Guide (2 destinations)","","E1-2","2E.23","Varies"),
 ("Interchange Advance Guide (3 destinations)","","E1-3","2E.23","Varies"),
 ("1-, 2-Digit Exit Number","Exit Number (plaque)","E1-5P","2E.23","114 x 30"),
 ("3-Digit Exit Number","Exit Number (plaque)","E1-5aP","2E.23","132 x 30"),
 ("1-, 2-Digit Exit Number (with single-letter suffix)","Exit Number (plaque)","E1-5bP","2E.23","138 x 30"),
 ("3-Digit Exit Number (with single-letter suffix)","Exit Number (plaque)","E1-5cP","2E.23","156 x 30"),
 ("1-, 2-Digit Exit Number (with dual-letter suffix)","Exit Number (plaque)","E1-5dP","2E.23","168 x 30"),
 ("3-Digit Exit Number (with dual-letter suffix)","Exit Number (plaque)","E1-5eP","2E.23","186 x 30"),
 ("1-, 2-Digit Exit Number","Left Exit Number (plaque)","E1-5fP","2E.23","114 x 54"),
 ("3-Digit Exit Number","Left Exit Number (plaque)","E1-5gP","2E.23","132 x 54"),
 ("1-, 2-Digit Exit Number (with single-letter suffix)","Left Exit Number (plaque)","E1-5hP","2E.23","138 x 54"),
 ("3-Digit Exit Number (with single-letter suffix)","Left Exit Number (plaque)","E1-5iP","2E.23","156 x 54"),
 ("1-, 2-Digit Exit Number (with dual-letter suffix)","Left Exit Number (plaque)","E1-5jP","2E.23","168 x 54"),
 ("3-Digit Exit Number (with dual-letter suffix)","Left Exit Number (plaque)","E1-5kP","2E.23","186 x 54"),
 ("Left (plaque)","","E1-5mP","2E.23","72 x 30"),
 ("Next Exit (1 line) (plaque)","","E2-1P","2E.46","Varies x 24"),
 ("Next Exit (2 lines) (plaque)","","E2-1aP","2E.46","Varies x 36"),
 ("Supplemental (1 destination)","","E3-1","2E.51","Varies"),
 ("Supplemental (2 destinations)","","E3-2","2E.51","Varies"),
 ("Exit Direction (1 destination)","","E4-1","2E.25","Varies"),
 ("Exit Direction (2 destinations)","","E4-2","2E.25","Varies"),
 ("Exit Direction (3 destinations)","","E4-3","2E.25","Varies"),
 ("Exit Gore","","E5-1","2E.26","72 x 60"),
 ("1-, 2-Digit Exit Number","Exit Gore (with exit number)","E5-1a","2E.26","78 x 60"),
 ("3-Digit Exit Number","Exit Gore (with exit number)","E5-1a","2E.26","96 x 60"),
 ("1-Digit Exit Number (with single-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","90 x 60"),
 ("2-Digit Exit Number (with single-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","108 x 60"),
 ("3-Digit Exit Number (with single-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","126 x 60"),
 ("1-Digit Exit Number (with dual-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","120 x 60"),
 ("2-Digit Exit Number (with dual-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","138 x 60"),
 ("3-Digit Exit Number (with dual-letter suffix)","Exit Gore (with exit number)","E5-1a","2E.26","156 x 60"),
 ("1-, 2-Digit Exit Number","Exit Number (plaque)","E5-1bP","2E.26","42 x 30"),
 ("3-Digit Exit Number","Exit Number (plaque)","E5-1bP","2E.26","60 x 30"),
 ("1-Digit Exit Number (with single-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","54 x 30"),
 ("2-Digit Exit Number (with single-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","72 x 30"),
 ("3-Digit Exit Number (with single-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","90 x 30"),
 ("1-Digit Exit Number (with dual-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","84 x 30"),
 ("2-Digit Exit Number (with dual-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","102 x 30"),
 ("3-Digit Exit Number (with dual-letter suffix)","Exit Number (plaque)","E5-1bP","2E.26","120 x 30"),
 ("Narrow Exit Gore","","E5-1c","2E.26","60 x 90*"),
 ("Pull-Through","","E6-1","2E.27","Varies"),
 ("Pull-Through (Destination)","","E6-1a","2E.27","Varies"),
 ("Pull-Through (Down Arrows)","","E6-2","2E.27","Varies"),
]

T.append(_2e1(1, 335, _2E1_S1))

_2E1_S2 = [
 ("Pull-Through (Destination, Down Arrows)","","E6-2a","2E.27","Varies"),
 ("Post-Interchange Distance","","E7-1","2E.48","Varies"),
 ("Post-Interchange Distance","","E7-2","2E.48","Varies"),
 ("Post-Interchange Distance","","E7-3","2E.48","Varies"),
 ("Post-Interchange Travel Time","","E7-4","2E.49","Varies"),
 ("Distance and Travel Time","","E7-5","2E.50","Varies"),
 ("Comparative Travel Time","","E7-6","2E.50","Varies"),
 ("Interchange Sequence (2 interchanges)","","E9-1","2E.24","Varies"),
 ("Interchange Sequence (3 interchanges)","","E9-2","2E.24","Varies"),
 ("Next Exits (1 destination)","","E9-3","2E.53","Varies"),
 ("Next Exits (2 destinations)","","E9-3a","2E.53","Varies"),
 ("Community Interchanges (2 interchanges)","","E9-4","2E.52","Varies"),
 ("Community Interchanges (3 interchanges)","","E9-5","2E.52","Varies"),
 ("Exit Only (with arrow)","","E11-1,1d","2E.28","174 x 36"),
 ("Exit","","E11-1a","2E.28","66 x 18"),
 ("Only","","E11-1b","2E.28","66 x 18"),
 ("Exit Only","","E11-1c","2E.28","120 x 18"),
 ("Exit Only (with two arrows)","","E11-1e,1f","2E.28","222 x 36"),
 ("Left (panel)","","E11-2","2E.24","60 x 18"),
 ("Exit Direction Advisory Speed (panel)","","E13-2","2E.25","162 x 24"),
 ("Interstate Route (1, 2 digits)","","M1-1","2E.55","36 x 36"),
 ("Interstate Route (3 digits)","","M1-1","2E.55","45 x 36"),
 ("Off-Interstate Route (1, 2 digits)","","M1-2,3","2E.55","36 x 36"),
 ("Off-Interstate Route (3 digits)","","M1-2,3","2E.55","45 x 36"),
 ("U.S. Route (1, 2 digits)","","M1-4","2E.55","36 x 36"),
 ("U.S. Route (3 digits)","","M1-4","2E.55","45 x 36"),
 ("State Route (1, 2 digits)","","M1-5","2D.11","36 x 36"),
 ("State Route (3 digits)","","M1-5","2D.11","45 x 36"),
 ("County Route","","M1-6","2D.11","36 x 36"),
 ("Forest Route","","M1-7","2D.11","36 x 36"),
 ("Eisenhower Interstate System","","M1-10,10a","2E.56","36 x 36"),
 ("Junction (plaque)","","M2-1P","2D.13","30 x 21"),
 ("Combination Junction (2 route signs)","","M2-2","2D.14","60 x 48*"),
 ("Cardinal Direction (plaque)","","M3-1P,2P,3P,4P","2D.15","36 x 18"),
 ("Alternate (plaque)","","M4-1P,1aP","2D.17","36 x 18"),
 ("By-Pass (plaque)","","M4-2P","2D.18","36 x 18"),
 ("Business (plaque)","","M4-3P","2D.19","36 x 18"),
 ("Truck (plaque)","","M4-4P","2D.20","36 x 18"),
 ("To (plaque)","","M4-5P","2D.21","36 x 18"),
 ("End (plaque)","","M4-6P","2D.22","36 x 18"),
 ("Temporary (plaque)","","M4-7P,7aP","2D.24","36 x 18"),
 ("Begin (plaque)","","M4-14P","2D.23","36 x 18"),
 ("Advance Turn Arrow (plaque)","","M5-1P,2P,3P","2D.26","30 x 21"),
 ("Lane Designation (plaque)","","M5-4P,5P,6P","2D.27","36 x 24"),
 ("Directional Arrow (plaque)","","M6-1P,2P, 2aP,3P,4P,5P,6P,7P","2D.28","30 x 21"),
 ("National Scenic Byway","","M10-1","2D.57","24 x 24"),
 ("National Scenic Byway (plaque)","","M10-1aP","2D.57","24 x 12"),
 ("Destination (1 line)","","D1-1","2D.36","Varies x 24"),
]

_2E1_S3 = [
 ("Destination and Distance (1 line)","","D1-1a","2D.36","Varies x 24"),
 ("Destination (2 lines)","","D1-2","2D.36","Varies x 42"),
 ("Destination and Distance (2 lines)","","D1-2a","2D.36","Varies x 42"),
 ("Destination (3 lines)","","D1-3","2D.36","Varies x 60"),
 ("Destination and Distance (3 lines)","","D1-3a","2D.36","Varies x 60"),
 ("Distance (1 line)","","D2-1","2D.43","Varies x 24"),
 ("Distance (2 lines)","","D2-2","2D.43","Varies x 36"),
 ("Distance (3 lines)","","D2-3","2D.43","Varies x 48"),
 ("Street Name (1 line)","","D3-1,1a","2D.45","Varies x 18"),
 ("Overhead Street Name (1 line)","","D3-1,1a","2D.45","Varies x 24"),
 ("Street Name (2 lines)","","D3-1,1a","2D.45","Varies x 33"),
 ("Overhead Street Name (2 lines)","","D3-1,1a","2D.45","Varies x 48"),
 ("Advance Street Name (2 lines)","","D3-2","2D.46","Varies x 36"),
 ("Advance Street Name (3 lines)","","D3-2","2D.46","Varies x 48"),
 ("Advance Street Name (4 lines)","","D3-2","2D.46","Varies x 66"),
 ("Park - Ride","","D4-2","2D.48","36 x 48"),
 ("Advance Weigh Station Distance","","D8-1","2E.54","96 x 72 (F) / 78 x 60 (E)"),
 ("Weigh Station Advance Direction","","D8-2","2E.54","108 x 90 (F) / 84 x 72 (E)"),
 ("Weigh Station Entrance Direction","","D8-3","2E.54","84 x 78 (F) / 66 x 60 (E)"),
 ("Crossover","","D13-1,2","2D.52","78 x 42"),
 ("Freeway Entrance","","D13-3","2D.50","48 x 30"),
 ("Freeway Entrance (Directional)","","D13-3a","2D.50","48 x 42"),
 ("Combination Lane Use / Destination","","D15-1","2D.38","Varies x 96"),
 ("Next Truck Lane","","D17-1","2D.53","60 x 66"),
 ("Advance Truck Lane","","D17-2","2D.53","60 x 54"),
 ("Next Passing Lane","","D17-3","2D.53","60 x 66"),
 ("Advance Passing Lane","","D17-4","2D.53","60 x 54"),
 ("Advance Emergency Turn-Out","","D17-5","2D.54","78 x 54"),
 ("Emergency Turn-Out (Directional)","","D17-6","2D.54","78 x 60"),
 ("Advance Slow Vehicle Turn-Out","","D17-7","2D.54","96 x 54"),
]

T.append(_2e1(2, 336, _2E1_S2))
T.append(_2e1(3, 337, _2E1_S3))

# the "**" on sheet 2's Exit Only widths marks a minimum that may be widened
for _t in T:
    if _t.table_id == "Table 2E-1" and _t.sheet == 2:
        for _r in _t.rows:
            if _r[2].text in ("E11-1,1d", "E11-1e,1f"):
                _r[4].footnotes = ["**"]
