"""General information sign sizes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V

SRC = "vlm transcription from a PDF render, unverified"
T = []

# Cells carry up to three things at once: a standard size, an OVERSIZED
# alternative marked "(O)" (Note 2), and a marker. "12 x 30 / 18 x 54 (O)" is
# two sizes for the same sign, and dropping the second loses the oversized
# option entirely.
def _sz2h(text):
    if text == "\u2014":
        return V(text="\u2014", missing="none")
    marks = []
    for m in ("***", "**", "*"):
        if m in text:
            marks = [m]
            break
    body = text.replace("***", "").replace("**", "").replace("*", "").strip()
    parts = [p.strip() for p in body.split("/")]
    qs = []
    for part in parts:
        over = part.endswith("(O)")
        part = part.replace("(O)", "").strip()
        pre = "oversized_" if over else ""
        w, h = [x.strip() for x in part.split("x")]
        for name, val in (("width", w), ("height", h)):
            try:
                qs.append(Q(name=pre + name, value=float(val), unit="in"))
            except ValueError:
                pass            # "Varies": no number is given for that side
    return V(text=text, quantities=qs, footnotes=marks)

_2H1 = [
 ("Next EV Charging","D9-17a","2H.14, 2J.06","—","126 x 60"),
 ("Alternative Fuels Corridor","D9-19","2H.14","24 x 24","36 x 36"),
 ("Alternative Fuels Corridor (1 line) (plaque)","D9-19aP","2H.14","30 x 9","42 x 12"),
 ("Alternative Fuels Corridor (2 lines) (plaque)","D9-19bP","2H.14","30 x 12","42 x 18"),
 ("Reference Location (1 digit)","D10-1","2H.11","10 x 18","12 x 24"),
 ("Intermediate Reference Location (2 digits)","D10-1a","2H.11","10 x 27","12 x 36"),
 ("Reference Location (2 digits)","D10-2","2H.11","10 x 27","12 x 36"),
 ("Intermediate Reference Location (3 digits)","D10-2a","2H.11","10 x 36","12 x 48"),
 ("Reference Location (3 digits)","D10-3","2H.11","10 x 36","12 x 48"),
 ("Intermediate Reference Location (4 digits)","D10-3a","2H.11","10 x 48","12 x 60"),
 ("Enhanced Reference Location","D10-4","2H.12","12 x 30 / 18 x 54 (O)","18 x 54"),
 ("Intermediate Enhanced Reference Location","D10-5","2H.12","12 x 36 / 18 x 60 (O)","18 x 60"),
 ("Traffic Signal Speed","I1-1","2H.04","24 x 36","—"),
 ("Jurisdictional Boundary","I2-1","2H.05","Varies x 18** / Varies x 24 (O)","Varies x 36** / Varies x 42 (O)"),
 ("Geographical Feature","I2-2","2H.06","Varies x 18** / Varies x 24 (O)","Varies x 36**"),
 ("Grade Separation Identification","I2-3","2H.10","—","Varies x 18"),
 ("Grade Separation Identification (2 lines)","I2-3a","2H.10","—","Varies x 24"),
 ("Future Interstate Corridor","I2-4","2H.08","54 x 36","72 x 48"),
 ("Future I-XX Corridor","I2-4a","2H.08","48 x 36","66 x 48"),
 ("Project Information","I2-5","2H.09","96 x 48","156 x 72"),
 ("Airport","I3-5","2H.01","24 x 24","30 x 30"),
 ("Bus Station","I3-6","2H.01","24 x 24","30 x 30"),
 ("Train Station","I3-7","2H.01","24 x 24","30 x 30"),
 ("Light Rail Transit Station","I3-8","2H.01","24 x 24","—"),
 ("Vehicle Ferry Terminal","I3-9","2H.01","24 x 24","30 x 30"),
 ("Passenger Only Ferry Terminal","I3-10","2H.01","24 x 24","30 x 30"),
 ("Ferry (plaque)","I3-10P","2H.01","24 x 12","30 x 18"),
 ("Library","I4-1","2H.01","24 x 24","—"),
 ("Recycling Center","I4-2","2H.01","30 x 36","—"),
 ("Acknowledgment","I20-1","2H.13","36 x 30*","72 x 48*"),
 ("Acknowledgment","I20-2","2H.13","36 x 30*","72 x 48*"),
 ("Acknowledgment","I20-3","2H.13","42 x 24*","96 x 36*"),
 ("Acknowledgment - Rest Area","I20-4","2H.13","56 x 36*","72 x 48*"),
 ("Acknowledgment - Welcome Center","I20-4a","2H.13","56 x 36*","72 x 48*"),
 ("Acknowledgment (plaque)","I20-5P","2H.13","Varies x Varies***","Varies x Varies***"),
 ("Last In Corridor (plaque)","W16-19P","2H.14","24 x 18","24 x 18"),
]

T.append(Table(
    table_id="Table 2H-1", page_pdf=502, page_printed="502",
    title="General Information Sign and Plaque Sizes",
    crop_file="table_2H-1_p0502.png", kind="numeric",
    column_labels=["Sign", "Sign Designation", "Section", "Conventional Road",
                   "Freeway or Expressway"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2]), _sz2h(r[3]), _sz2h(r[4])]
          for r in _2H1],
    footnotes=[
        Footnote(marker="*", text="The size shown is the maximum size for the corresponding "
            "roadway classification. The size of the sign and acknowledgment logo should be "
            "appropriately reduced where shorter legends are used.", applies_to="cell"),
        Footnote(marker="**", text="The size shown is for the typical sign illustrated in the "
            "figure. The size should be determined based on the number of lines of legend on "
            "the sign.", applies_to="cell"),
        Footnote(marker="***", text="Limitations on the size of Acknowledgment plaques are "
            "provided in Section 2H.13.", applies_to="cell"),
        Footnote(marker="Note 1", text="Larger signs may be used when appropriate, except for "
            "the I20 series signs and plaque"),
        Footnote(marker="Note 2", text="(O) denotes Oversized"),
        Footnote(marker="Note 3", text="Dimensions are in inches shown as width x height"),
    ],
))

# ---- Table 6G-1 ----------------------------------------------------------
from batch2 import sz

def _s6g(text):
    v = sz(text.rstrip("*"))
    if text.endswith("*"):
        v.text = text
        v.footnotes = ["*"]
    return v

_6G1 = [
 ("Stop","R1-1","6G.02","30 x 30*","—","—"),
 ("Stop (on Stop/Slow Paddle)","R1-1","6D.02","18 x 18","—","—"),
 ("Yield","R1-2","6G.02","36 x 36 x 36*","—","30 x 30 x 30"),
 ("To Oncoming Traffic (plaque)","R1-2aP","6G.02","36 x 30","48 x 36","24 x 18"),
 ("Wait on Stop","R1-7","6L.03","24 x 30","24 x 30","—"),
 ("Wait on Stop - Go on Slow","R1-7a","6L.03","30 x 36","30 x 36","—"),
 ("Go on Slow","R1-8","6L.03","24 x 30","24 x 30","—"),
 ("Speed Limit","R2-1","6G.08","24 x 30*","36 x 48","—"),
 ("Fines Higher (plaque)","R2-6P","6G.08","24 x 18","36 x 24","—"),
 ("Fines Double (plaque)","R2-6aP","6G.08","24 x 18","36 x 24","—"),
 ("$XX Fine (plaque)","R2-6bP","6G.08","24 x 18","36 x 24","—"),
 ("Begin Higher Fines Zone","R2-10","6G.08","24 x 30","36 x 48","—"),
 ("End Higher Fines Zone","R2-11","6G.08","24 x 30","36 x 48","—"),
 ("End Work Zone Speed Limit","R2-12","6G.08","24 x 36","36 x 54","—"),
 ("Movement Prohibition","R3-1,2,3,4","6G.02","24 x 24*","36 x 36","—"),
 ("Mandatory Movement Lane Control - Turn Only","R3-5","6G.02","30 x 36","—","—"),
 ("Optional Movement Lane Control - Thru and Turn","R3-6","6G.02","30 x 36","—","—"),
 ("Right (Left) Lane Must Turn Right (Left)","R3-7","6G.02","30 x 30*","—","—"),
 ("Advance Intersection Lane Control (2 lanes)","R3-8","6G.02","30 x 30","—","—"),
 ("Movement Prohibition - No U or Left Turn","R3-18","6G.02","24 x 24*","36 x 36","—"),
 ("Movement Prohibition - No Straight Through","R3-27","6G.02","24 x 24*","36 x 36","—"),
 ("Do Not Pass","R4-1","6G.02","24 x 30","36 x 48","—"),
 ("Pass With Care","R4-2","6G.02","24 x 30","36 x 48","—"),
 ("Keep Right","R4-7","6G.02","24 x 30","36 x 48","—"),
 ("Narrow Keep Right","R4-7c","6G.02","18 x 30","—","—"),
 ("Stay in Lane","R4-9","6G.07","24 x 30","36 x 48","—"),
 ("Stay In Lane To Merge Point","R4-9a","6G.07","36 x 48","36 x 48","—"),
 ("Do Not Enter","R5-1","6G.02","30 x 30*","36 x 36","—"),
 ("Wrong Way","R5-1a","6G.02","36 x 24*","42 x 30","—"),
 ("One Way","R6-1","6G.02","36 x 12*","48 x 18","—"),
 ("One Way","R6-2","6G.02","24 x 30*","36 x 48","—"),
 ("No Parking (symbol)","R8-3","6G.02","24 x 24*","36 x 36","—"),
 ("Pedestrian Crosswalk","R9-8","6G.09","36 x 18","—","—"),
 ("Sidewalk Closed","R9-9","6G.10","24 x 12","—","—"),
 ("Sidewalk Closed, Use Other Side","R9-10","6G.10","24 x 12","—","—"),
 ("Sidewalk Closed Ahead, Cross Here","R9-11","6G.10","24 x 18","—","—"),
 ("Sidewalk Closed, Cross Here","R9-11a","6G.10","24 x 12","—","—"),
 ("Bike Lane Closed","R9-12","6P.01","24 x 12","—","—"),
 ("Stop Here on Red","R10-6","6L.04","24 x 36","—","—"),
 ("Road Closed","R11-2, 2a, 2b, 2c","6G.04","48 x 30","—","—"),
 ("Road Closed - Local Traffic Only","R11-3, 3a, 3b, 4","6G.05","60 x 30","—","—"),
 ("Weight Limit","R12-1, 2","6G.06","24 x 30","36 x 48","—"),
 ("Weight Limit","R12-5","6G.06","24 x 36","36 x 48","—"),
 ("Turn Off 2-Way Radio and Cell Phone","R22-2","6G.11","42 x 36","42 x 36","—"),
 ("Work Zone (plaque)","G20-5aP","6G.08","24 x 18","30 x 24","—"),
]

T.append(Table(
    table_id="Table 6G-1", page_pdf=837, page_printed="837",
    title="Temporary Traffic Control Zone Regulatory Sign and Plaque Sizes",
    crop_file="table_6G-1_p0837.png", kind="numeric",
    column_labels=["Sign or Plaque", "Sign Designation", "Section",
                   "Conventional Road", "Freeway or Expressway", "Minimum"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [_s6g(x) for x in r[3:]]
          for r in _6G1],
    footnotes=[
        Footnote(marker="*", text="See Table 2B-1 for minimum size required for signs facing "
            "traffic on multi-lane conventional roads", applies_to="cell"),
        Footnote(marker="Note 1", text="Larger signs may be used wherever necessary for greater "
            "legibility or emphasis"),
        Footnote(marker="Note 2", text="Dimensions are shown in inches and are shown as "
            "width x height"),
    ],
))
