"""Chapter 2E tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V
from batch2 import sz
from batch5 import _lh

SRC = "vlm transcription from a PDF render, unverified"
T = []

T.append(Table(
    table_id="Table 2E-6", page_pdf=392, page_printed="392",
    title="Overhead Arrow-per-Lane Arrow Height Based on Principal Legend Letter Height",
    crop_file="table_2E-6_p0392.png", kind="numeric",
    column_labels=["Principal Legend Letter Height", "Through Arrow", "Turn Arrow",
                   "Through with Turn Arrow", "Split Arrow"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2E-6_01"],
    rows=[
        [V(text="20", number=20, unit="in"), V(text="48", number=48, unit="in"),
         V(text="38", number=38, unit="in"), V(text="48", number=48, unit="in"),
         V(text="42", number=42, unit="in")],
        # "16 or less" is a threshold, so a 12-inch legend matches this row
        [V(text="16 or less", maximum=16, unit="in"), V(text="39", number=39, unit="in"),
         V(text="30.875", number=30.875, unit="in"), V(text="39", number=39, unit="in"),
         V(text="34.125", number=34.125, unit="in")],
    ],
    footnotes=[Footnote(marker="Note", text="Letter and arrow heights are shown in inches.")],
))

# ---- Table 2E-2 ----------------------------------------------------------
_2E2_NOTES = [
    # printed on the "Overhead" column heading, so it governs that column
    # only, not every size in the table
    Footnote(marker="*", text="Where a larger size is shown for the interchange classification "
                              "of the interchange, that larger size is used for overhead-mounted "
                              "guide signs for that interchange.", applies_to="column:7"),
    Footnote(marker="**", text="Minimum size listed for 3-digit shields. Larger numeral sizes "
                               "used for 1-digit, some 2-digit, and some 3-digit shields. See "
                               "the Standard Highways Signs publication for more information on "
                               "Route Sign numeral heights and Standard Alphabet series."),
    Footnote(marker="Note", text="Sizes are shown in inches and where applicable are shown as "
                                 "width x height"),
]
_A2 = "A. Advance Guide, Exit Direction, and Overhead Guide Signs"
_B2 = "B. Gore Signs"

_2E2 = [
 (_A2,"Exit Number Plaques","Words","10","10","10","8","10"),
 (_A2,"Exit Number Plaques","Numerals & Letters","15","15","15","12","15"),
 (_A2,"Interstate Route Signs","Numerals**","14","—","—","—","14"),
 (_A2,"Interstate Route Signs","1- or 2-Digit Shields","36 x 36","—","—","—","36 x 36"),
 (_A2,"Interstate Route Signs","3-Digit Shields","45 x 36","—","—","—","45 x 36"),
 (_A2,"U.S. or State Route Signs","Numerals","18","18","18","12","18"),
 (_A2,"U.S. or State Route Signs","1- or 2-Digit Shields","36 x 36","36 x 36","36 x 36","24 x 24","36 x 36"),
 (_A2,"U.S. or State Route Signs","3-Digit Shields","45 x 36","45 x 36","45 x 36","30 x 24","45 x 36"),
 (_A2,"U.S. or State Route Text Identification (Example: US 56)","Numerals & Letters","18","15","15","12","15"),
 (_A2,"Cardinal Directions","First Letters","18","15","12","10","15"),
 (_A2,"Cardinal Directions","Rest of Word","15","12","10","8","12"),
 (_A2,"Auxiliary and Alternative Route Legends (Examples: JCT, TO, ALT, BUSINESS)","Words","15","12","10","8","12"),
 (_A2,"Names of Destinations","Upper-Case Letters","20","16","13.33","10.67","16"),
 (_A2,"Names of Destinations","Lower-Case Letters","15","12","10","8","12"),
 (_A2,"Names of Destinations","Distance Numbers","18","15","12","10","15"),
 (_A2,"Names of Destinations","Distance Fraction Numerals","12","10","10","8","10"),
 (_A2,"Names of Destinations","Distance Words","12","10","10","8","10"),
 (_A2,"Names of Destinations","Action Message Words","10","10","10","8","10"),
 (_B2,"","Words","10","10","10","8","—"),
 (_B2,"","Numerals & Letters","12","12","12","10","—"),
]

T.append(Table(
    table_id="Table 2E-2", page_pdf=338, page_printed="338",
    title="Minimum Letter and Numeral Sizes for Expressway Guide Signs "
          "According to Interchange Classification",
    crop_file="table_2E-2_p0338.png", kind="numeric",
    column_labels=["Group", "Sub-group", "Type of Sign",
                   "Type of Interchange — Major — Category a",
                   "Type of Interchange — Major — Category b",
                   "Type of Interchange — Intermediate",
                   "Type of Interchange — Minor", "Overhead*"],
    row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]),
           V(text=r[2].rstrip("*"), footnotes=["**"] if r[2].endswith("**") else [])]
          + [_lh(x) for x in r[3:]] for r in _2E2],
    footnotes=list(_2E2_NOTES),
))

# ---- Table 2E-3: printed in two side-by-side columns, one logical list ----
_2E3 = [
 ("A. Pull-Through Signs","","Destinations — Upper-Case Letters","13.33"),
 ("A. Pull-Through Signs","","Destinations — Lower-Case Letters","10"),
 ("A. Pull-Through Signs","Route Signs","Numerals*","14"),
 ("A. Pull-Through Signs","Route Signs","1- or 2-Digit Shields","36 x 36"),
 ("A. Pull-Through Signs","Route Signs","3-Digit Shields","45 x 36"),
 ("A. Pull-Through Signs","","Cardinal Directions — First Letters","12"),
 ("A. Pull-Through Signs","","Cardinal Directions — Rest of Word","10"),
 ("B. Supplemental Guide Signs","","Exit Number — Words","8"),
 ("B. Supplemental Guide Signs","","Exit Number — Numerals and Letters","12"),
 ("B. Supplemental Guide Signs","","Place Names — Upper-Case Letters","10.67"),
 ("B. Supplemental Guide Signs","","Place Names — Lower-Case Letters","8"),
 ("B. Supplemental Guide Signs","","Action Messages","8"),
 ("B. Supplemental Guide Signs","Route Signs","Numerals*","9"),
 ("B. Supplemental Guide Signs","Route Signs","1- or 2-Digit Shield","24 x 24"),
 ("B. Supplemental Guide Signs","Route Signs","3-Digit Shield","30 x 24"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Words — Upper-Case Letters","10.67"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Words — Lower-Case Letters","8"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Numerals","10.67"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","","Fraction Numerals","8"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","Numerals*","9"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","1- or 2-Digit Shield","24 x 24"),
 ("C. Interchange Sequence or Community Interchanges Identification Signs","Route Signs","3-Digit Shield","30 x 24"),
 ("D. Next XX Exits Sign","","Place Names — Upper-Case Letters","10.67"),
 ("D. Next XX Exits Sign","","Place Names — Lower-Case Letters","8"),
 ("D. Next XX Exits Sign","","NEXT XX EXITS — Words","8"),
 ("D. Next XX Exits Sign","","NEXT XX EXITS — Number","12"),
 ("E. Distance Signs","","Words — Upper-Case Letters","8"),
 ("E. Distance Signs","","Words — Lower-Case Letters","6"),
 ("E. Distance Signs","","Numerals","8"),
 ("E. Distance Signs","Route Signs","Numerals*","6"),
 ("E. Distance Signs","Route Signs","1- or 2-Digit Shield","18 x 18"),
 ("E. Distance Signs","Route Signs","3-Digit Shield","22.5 x 18"),
 ("F. General Service Signs (see Chapter 2I)","","Exit Number — Words","8"),
 ("F. General Service Signs (see Chapter 2I)","","Exit Number — Numerals and Letters","12"),
 ("F. General Service Signs (see Chapter 2I)","","Services","8"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Words","10"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Numerals","12"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Fraction Numerals","8"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Distance Words","8"),
 ("G. Rest Area, Scenic Area, and Roadside Area Signs (see Chapter 2I)","","Action Message Words","10"),
 ("H. Reference Location Signs (see Chapter 2H)","","Words","4"),
 ("H. Reference Location Signs (see Chapter 2H)","","Numerals","10"),
 ("I. Boundary and Orientation Signs (see Chapter 2H)","","Words — Upper-Case Letters","8"),
 ("I. Boundary and Orientation Signs (see Chapter 2H)","","Words — Lower-Case Letters","6"),
 ("J. Next Exit and Next Services Signs","","Words and Numerals","8"),
 ("K. Exit Only Signs","","Words","12"),
]

T.append(Table(
    table_id="Table 2E-3", page_pdf=339, page_printed="339",
    title="Minimum Letter and Numeral Sizes for Expressway Guide Signs According to Sign Type",
    crop_file="table_2E-3_p0339.png", kind="numeric",
    column_labels=["Group", "Sub-group", "Type of Sign", "Minimum Size"],
    row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]),
           V(text=r[2].rstrip("*"), footnotes=["*"] if r[2].endswith("*") else []),
           _lh(r[3])] for r in _2E3],
    footnotes=[
        Footnote(marker="*", text="Minimum size listed for 3-digit shields. Larger numeral sizes "
                                  "used for 1-digit, some 2-digit, and some 3-digit shields. See "
                                  "the Standard Highways Signs publication for more information "
                                  "on Route Sign numeral heights and Standard Alphabet series."),
        Footnote(marker="Note", text="Sizes are shown in inches and where applicable are shown "
                                     "as width x height"),
        Footnote(marker="L", text="L. Overhead Arrow-per-Lane and Diagrammatic Signs: "
                                  "See Table 2E-5"),
    ],
))

# ---- Table 2E-4 ----------------------------------------------------------
# Note 2 on the sheet: "Slanted line (/) signifies separation of desirable and
# minimum sizes". So "18/14" is TWO requirements in one cell, and
# "48 x 48/36 x 36" is two SIZES. Reading either as a single value would drop
# the minimum a design actually has to meet.
def _ds(text):
    if text == "—":
        return V(text="—", missing="none")
    if "/" not in text:
        return _lh(text)
    des, mini = [p.strip() for p in text.split("/")]
    qs = []
    for label, part in (("desirable", des), ("minimum", mini)):
        if "x" in part:
            w, h = [float(x) for x in part.split("x")]
            qs += [Q(name=f"{label}_width", value=w, unit="in"),
                   Q(name=f"{label}_height", value=h, unit="in")]
        else:
            qs.append(Q(name=label, value=float(part), unit="in"))
    return V(text=text, quantities=qs)

_2E4 = [
 (_A2,"Exit Number Plaques","Words","10","10","10","10","10"),
 (_A2,"Exit Number Plaques","Numerals & Letters","15","15","15","15","15"),
 (_A2,"Interstate Route Signs","Numerals**","18/14","—","—","—","14"),
 (_A2,"Interstate Route Signs","1- or 2-Digit Shields","48 x 48/36 x 36","—","—","—","36 x 36"),
 (_A2,"Interstate Route Signs","3-Digit Shields","60 x 48/45 x 36","—","—","—","45 x 36"),
 (_A2,"U.S. or State Route Signs","Numerals","24/18","18","18","12","18"),
 (_A2,"U.S. or State Route Signs","1- or 2-Digit Shields","48 x 48/36 x 36","36 x 36","36 x 36","24 x 24","36 x 36"),
 (_A2,"U.S. or State Route Signs","3-Digit Shields","60 x 48/45 x 36","45 x 36","45 x 36","30 x 24","45 x 36"),
 (_A2,"U.S. or State Route Text Identification (Example: US 56)","Numerals & Letters","18","18/15","15","12","15"),
 (_A2,"Cardinal Directions","First Letters","18","15","15","10","15"),
 (_A2,"Cardinal Directions","Rest of Words","15","12","12","8","12"),
 (_A2,"Auxiliary and Alternative Route Legends (Examples: JCT, TO, ALT, BUSINESS)","Words","15","12","12","8","12"),
 (_A2,"Names of Destinations","Upper-Case Letters","20","20","16","13.33","16"),
 (_A2,"Names of Destinations","Lower-Case Letters","15","15","12","10","12"),
 (_A2,"Names of Destinations","Distance Numbers","18","18/15","15","12","15"),
 (_A2,"Names of Destinations","Distance Fraction Numerals","12","12/10","10","8","10"),
 (_A2,"Names of Destinations","Distance Words","12","12/10","10","8","10"),
 (_A2,"Names of Destinations","Action Message Words","12","12/10","10","8","10"),
 (_B2,"","Words","12","12","12","8","—"),
 (_B2,"","Numeral & Letters","18","18","18","12","—"),
]

T.append(Table(
    table_id="Table 2E-4", page_pdf=340, page_printed="340",
    title="Minimum Letter and Numeral Sizes for Freeway Guide Signs "
          "According to Interchange Classification",
    crop_file="table_2E-4_p0340.png", kind="numeric",
    column_labels=["Group", "Sub-group", "Type of Sign",
                   "Type of Interchange — Major — Category a",
                   "Type of Interchange — Major — Category b",
                   "Type of Interchange — Intermediate",
                   "Type of Interchange — Minor", "Overhead*"],
    row_key_columns=[2], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]),
           V(text=r[2].rstrip("*"), footnotes=["**"] if r[2].endswith("**") else [])]
          + [_ds(x) for x in r[3:]] for r in _2E4],
    footnotes=[
        Footnote(marker="*", text="Where a larger size is shown for the interchange "
                                  "classification of the interchange, that larger size is used "
                                  "for overhead-mounted guide signs for that interchange.",
                 applies_to="column:7"),
        Footnote(marker="**", text="Minimum size listed for 3-digit shields. Larger numeral "
                                   "sizes used for 1-digit, some 2-digit, and some 3-digit "
                                   "shields. See the Standard Highways Signs publication for "
                                   "more information on Route Sign numeral heights and Standard "
                                   "Alphabet series."),
        Footnote(marker="Note 1", text="Sizes are shown in inches and where applicable are shown "
                                       "as width x height"),
        Footnote(marker="Note 2", text="Slanted line (/) signifies separation of desirable and "
                                       "minimum sizes"),
    ],
))
