"""Table 2B-1 — Regulatory Sign and Plaque Sizes (6 sheets, pages 109-114)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

# Sizes print as "30 x 30" (width x height) and, for the triangular YIELD
# sign, "36 x 36 x 36" (three sides). A trailing * carries footnote "*".
def sz(text):
    if text == "—":
        return V(text="—", missing="none")
    if text == "":
        # R7-21aP leaves these four cells genuinely EMPTY rather than printing
        # an em-dash. Blank and em-dash are different facts.
        return V(text="", missing="blank")
    star = text.endswith("*")
    body = text.rstrip("*").strip()
    parts = [p.strip() for p in body.replace("\u00d7", "x").split("x")]
    names = (["width", "height"] if len(parts) == 2
             else [f"side{i+1}" for i in range(len(parts))])
    # "Varies x 30": the width is not a number. Record the dimension that IS
    # given rather than dropping the cell or inventing a value.
    qs = []
    for name, part in zip(names, parts):
        try:
            qs.append(Q(name=name, value=float(part), unit="in"))
        except ValueError:
            continue
    v = V(text=text, quantities=qs)
    if star:
        v.footnotes = ["*"]
    return v

_COLS = ["Sign or Plaque", "Sign Designation", "Section",
         "Conventional Road — Single Lane", "Conventional Road — Multi-Lane",
         "Expressway", "Freeway", "Minimum", "Oversized"]

_S1 = [
 ("Stop", "R1-1", "2B.04", "30 x 30", "36 x 36", "36 x 36", "—", "30 x 30*", "48 x 48"),
 ("Yield", "R1-2", "2B.05", "36 x 36 x 36", "48 x 48 x 48", "48 x 48 x 48",
  "60 x 60 x 60", "30 x 30 x 30*", "—"),
 ("To Oncoming Traffic (plaque)", "R1-2aP", "2B.18", "24 x 18", "24 x 18",
  "36 x 30", "48 x 36", "24 x 18", "—"),
 ("To Traffic in Circle (plaque)", "R1-2bP", "2B.18", "24 x 15", "24 x 15",
  "—", "—", "24 x 15", "36 x 24"),
 ("To All Lanes (plaque)", "R1-2cP", "2B.18", "24 x 15", "24 x 15",
  "—", "—", "24 x 15", "36 x 24"),
 ("All Way (plaque)", "R1-3P", "2B.04", "18 x 6", "18 x 6", "—", "—", "—", "30 x 12"),
 ("Yield Here to Pedestrians", "R1-5", "2B.19", "—", "36 x 36", "—", "—", "—", "36 x 36"),
 ("Stop Here for Pedestrians", "R1-5b", "2B.19", "—", "36 x 36", "—", "—", "—", "36 x 36"),
 ("Yield Here to (Stop Here for) Trail Crossing", "R1-5d,5e", "2B.19",
  "—", "36 x 42", "—", "—", "—", "—"),
 ("In-Street Pedestrian Crossing - Yield (Stop)", "R1-6,6a", "2B.20",
  "12 x 36", "12 x 36", "—", "—", "—", "—"),
 ("In-Street Trail Crossing - Yield (Stop)", "R1-6d,6e", "2B.20",
  "12 x 36", "12 x 36", "—", "—", "—", "—"),
 ("Overhead Pedestrian Crossing - Yield (Stop)", "R1-9,9a", "2B.20",
  "90 x 24", "90 x 24", "—", "—", "—", "—"),
 ("Overhead Trail Crossing", "R1-9d,9e", "2B.20", "72 x 24", "72 x 24",
  "—", "—", "—", "—"),
 ("Except Right Turn (plaque)", "R1-10P", "2B.04", "24 x 18", "24 x 18",
  "—", "—", "—", "—"),
 ("Speed Limit", "R2-1", "2B.21", "24 x 30", "30 x 36", "36 x 48", "48 x 60",
  "18 x 24", "30 x 36"),
 ("Truck Speed Limit (plaque)", "R2-2P", "2B.22", "24 x 24", "24 x 24",
  "36 x 36", "48 x 48", "—", "36 x 36"),
 ("Bus Speed Limit (plaque)", "R2-2aP", "2B.22", "24 x 24", "24 x 24",
  "36 x 36", "48 x 48", "—", "36 x 36"),
 ("Truck-Bus Speed Limit (plaque)", "R2-2bP", "2B.22", "24 x 30", "24 x 30",
  "36 x 42", "48 x 54", "—", "36 x 42"),
 ("Vehicles Over X Tons Speed Limit (plaque)", "R2-2cP", "2B.22", "24 x 30",
  "24 x 30", "36 x 42", "48 x 54", "—", "36 x 42"),
 ("Night Speed Limit (plaque)", "R2-3P", "2B.23", "24 x 24", "24 x 24",
  "36 x 36", "48 x 48", "—", "36 x 36"),
 ("Minimum Speed Limit (plaque)", "R2-4P", "2B.24", "24 x 24", "24 x 24",
  "36 x 36", "48 x 48", "—", "36 x 36"),
 ("Combined Maximum and Minimum Speed Limits", "R2-4a", "2B.24", "24 x 48",
  "24 x 48", "36 x 72", "48 x 96", "—", "36 x 72"),
 ("Unless Otherwise Posted (plaque)", "R2-5P", "2B.21", "24 x 18", "24 x 18",
  "36 x 24", "36 x 24", "—", "36 x 24"),
 ("Citywide (plaque)", "R2-5aP", "2B.21", "24 x 6", "24 x 6", "—", "—", "—", "30 x 9"),
 ("Neighborhood (plaque)", "R2-5bP", "2B.21", "24 x 6", "24 x 6", "—", "—", "—", "30 x 9"),
 ("Residential (plaque)", "R2-5cP", "2B.21", "24 x 6", "24 x 6", "—", "—", "—", "30 x 9"),
 ("Fines Higher (plaque)", "R2-6P", "2B.25", "24 x 18", "24 x 18", "36 x 24",
  "48 x 36", "—", "36 x 24"),
 ("Fines Double (plaque)", "R2-6aP", "2B.25", "24 x 18", "24 x 18", "36 x 24",
  "48 x 36", "—", "36 x 24"),
 ("$XX Fine (plaque)", "R2-6bP", "2B.25", "24 x 18", "24 x 18", "36 x 24",
  "48 x 36", "—", "36 x 24"),
 ("Begin Higher Fines Zone", "R2-10", "2B.25", "24 x 30", "24 x 30", "36 x 48",
  "48 x 60", "—", "36 x 48"),
 ("End Higher Fines Zone", "R2-11", "2B.25", "24 x 30", "24 x 30", "36 x 48",
  "48 x 60", "—", "36 x 48"),
 ("End Variable Speed Limit", "R2-13", "2B.21", "24 x 30", "24 x 30", "36 x 48",
  "48 x 60", "—", "36 x 48"),
 ("End Truck Speed Limit", "R2-14", "2B.21", "24 x 30", "24 x 30", "36 x 48",
  "48 x 60", "—", "36 x 48"),
 ("Movement Prohibition", "R3-1,2,3,4,18,27", "2B.26", "24 x 24", "36 x 36",
  "36 x 36", "—", "—", "48 x 48"),
 ("Movement Prohibition - Trucks", "R3-1b", "2B.26", "24 x 36", "24 x 36",
  "36 x 54", "36 x 54", "—", "—"),
 ("Movement Prohibition - Trucks Buses", "R3-1c", "2B.26", "24 x 42", "24 x 42",
  "36 x 60", "36 x 60", "—", "—"),
 ("Movement Prohibition - Trucks Over X Tons", "R3-1d", "2B.26", "24 x 48",
  "24 x 48", "36 x 66", "36 x 66", "—", "—"),
 ("Movement Prohibition - Except Buses", "R3-1e", "2B.26", "24 x 36", "24 x 36",
  "36 x 54", "36 x 54", "—", "—"),
 ("Movement Prohibition - Except Buses Taxis", "R3-1f", "2B.26", "24 x 42",
  "24 x 42", "36 x 66", "36 x 66", "—", "—"),
 ("Movement Prohibition - Time and Day", "R3-1g", "2B.26", "24 x 36", "24 x 36",
  "36 x 54", "36 x 54", "—", "—"),
]

# Printed once, at the foot of sheet 6, but they govern every sheet: the "*"
# on STOP's minimum size is defined there, and "dimensions in inches, width x
# height" is what makes every cell in the table interpretable. Attaching them
# to each sheet keeps a sheet self-contained for a calculator that loads one.
_2B1_NOTES = [
    Footnote(marker="*", text="See Table 9A-1 for minimum size required for signs on "
                              "bicycle facilities"),
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions in inches are shown as width x height"),
]


def sheet(n, page, rows, footnotes=None):
    return Table(
        table_id="Table 2B-1", sheet=n, sheet_of=6, page_pdf=page,
        page_printed=str(page), title="Regulatory Sign and Plaque Sizes",
        crop_file=f"table_2B-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=_COLS, row_key_columns=[0, 1], source=SRC,
        note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [sz(x) for x in r[3:]]
              for r in rows],
        footnotes=footnotes or list(_2B1_NOTES),
    )

T.append(sheet(1, 109, _S1))

_S2 = [
 ("Movement Prohibition - Multiple Times and Day", "R3-1h", "2B.26", "24 x 42", "24 x 42", "36 x 66", "36 x 66", "—", "—"),
 ("Mandatory Movement Lane Control", "R3-5,5a", "2B.28", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Left Lane (plaque)", "R3-5bP", "2B.28", "30 x 12", "30 x 12", "—", "—", "—", "—"),
 ("HOV 2+ (plaque)", "R3-5cP", "2B.28", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Taxi Lane (plaque)", "R3-5dP", "2B.28", "30 x 12", "30 x 12", "—", "—", "—", "—"),
 ("Right Lane (plaque)", "R3-5fP", "2B.28", "30 x 12", "30 x 12", "—", "—", "—", "—"),
 ("Bus Lane (plaque)", "R3-5gP", "2B.28", "30 x 12", "30 x 12", "—", "—", "—", "—"),
 ("Optional Movement Lane Control Thru and Turn", "R3-6", "2B.29", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Optional Movement U and Left Turn", "R3-6a", "2B.29", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Optional Movement Left Turns", "R3-6b", "2B.29", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Right (Left) Lane Must Turn Right (Left)", "R3-7", "2B.28", "30 x 30", "36 x 36", "48 x 48", "—", "—", "48 x 48"),
 ("Except Buses (plaque)", "R3-7aP", "2B.28", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Except Bicycles (plaque)", "R3-7bP", "2B.28", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Advance Intersection Lane Control", "R3-8,8a,8b, 8xa, 8xb,8xc", "2B.30", "Varies x 30", "Varies x 30", "—", "—", "—", "Varies x 36"),
 ("Advance Circular Intersection Lane Control (2 Lanes)", "R3-8zd, R3-8ze, R3-8zf, R3-8zg", "2B.27", "—", "36 x 36", "—", "—", "—", "—"),
 ("Two-Way Left Turn Only (overhead)", "R3-9a", "2B.32", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Two-Way Left Turn Only (post-mounted)", "R3-9b", "2B.32", "24 x 36", "24 x 36", "—", "—", "—", "36 x 48"),
 ("Begin (plaque)", "R3-9cP", "2B.33", "24 x 12", "24 x 12", "—", "—", "—", "36 x 18"),
 ("End (plaque)", "R3-9dP", "2B.33", "24 x 12", "24 x 12", "—", "—", "—", "36 x 18"),
 ("Reversible Lane Control (overhead)", "R3-9e", "2B.34", "108 x 48", "108 x 48", "—", "—", "—", "—"),
 ("Reversible Lane Control (post-mounted)", "R3-9f", "2B.34", "30 x 42", "36 x 54", "—", "—", "—", "—"),
 ("Advance Reversible Lane Control Transition", "R3-9g,9h", "2B.34", "108 x 36", "108 x 36", "—", "—", "—", "—"),
 ("End Reverse Lane", "R3-9i", "2B.34", "108 x 48", "108 x 48", "—", "—", "—", "—"),
 ("Lane for Left Turn Only", "R3-19", "2B.28", "30 x 24", "30 x 24", "—", "—", "—", "—"),
 ("Lane for U Turn Only", "R3-19a", "2B.28", "30 x 24", "30 x 24", "—", "—", "—", "—"),
 ("Lane For U and Left Turns Only", "R3-19b", "2B.28", "30 x 30", "30 x 30", "—", "—", "—", "—"),
 ("Begin Right (Left) Turn Lane", "R3-20", "2B.28", "24 x 36", "24 x 36", "—", "—", "—", "—"),
 ("All Turns (U-Turn) from Right Lane", "R3-23,23a", "2B.35", "60 x 36", "60 x 36", "—", "—", "—", "—"),
 ("All Turns (U-Turn) Directional", "R3-24,24b, 25,25b,26a", "2B.35", "72 x 18", "72 x 18", "—", "—", "—", "—"),
 ("U-Turns and Left Turns Directional", "R3-24a, 25a,26", "2B.35", "60 x 24", "60 x 24", "—", "—", "—", "—"),
 ("Right (Left) Lane Must Exit", "R3-33", "2B.31", "—", "—", "78 x 36", "78 x 36", "—", "—"),
 ("Right (Left) Lane Must Exit", "R3-33a", "2B.31", "—", "—", "42 x 60", "42 x 60", "—", "—"),
 ("Do Not Pass", "R4-1", "2B.36", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24*", "36 x 48"),
 ("Pass With Care", "R4-2", "2B.37", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24*", "36 x 48"),
 ("Slower Traffic Keep Right", "R4-3", "2B.38", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24*", "36 x 48"),
 ("Trucks Use Right Lane", "R4-5", "2B.38", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("Keep Right", "R4-7,7a,7b", "2B.39", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24*", "36 x 48"),
 ("Narrow Keep Right", "R4-7c", "2B.39", "18 x 30", "18 x 30", "—", "—", "—", "—"),
 ("Keep Left", "R4-8,8a,8b", "2B.39", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24", "36 x 48"),
 ("Narrow Keep Left", "R4-8c", "2B.39", "18 x 30", "18 x 30", "—", "—", "—", "—"),
 ("Stay in Lane", "R4-9", "2B.40", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24", "36 x 48"),
 ("Runaway Vehicles Only", "R4-10", "2B.41", "48 x 48", "48 x 48", "—", "—", "—", "—"),
]

T.append(sheet(2, 110, _S2))

_S3 = [
 ("Slow Vehicles with XX or More Following Vehicles Must Use Turn-Out", "R4-12", "2B.42", "42 x 24", "42 x 24", "—", "—", "—", "72 x 42"),
 ("Slow Vehicles Must Use Turn-Out Ahead", "R4-13", "2B.42", "42 x 24", "42 x 24", "—", "—", "—", "—"),
 ("Slow Vehicles Must Turn Out", "R4-14", "2B.42", "30 x 42", "30 x 42", "—", "—", "—", "—"),
 ("Keep Right Except to Pass", "R4-16", "2B.38", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24*", "36 x 48"),
 ("Do Not Drive on Shoulder", "R4-17", "2B.43", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24", "36 x 48"),
 ("Do Not Pass on Shoulder", "R4-18", "2B.43", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "18 x 24", "36 x 48"),
 ("All Traffic", "R4-20", "2B.44", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("Right (Left) Turn Only", "R4-21", "2B.44", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("Do Not Enter", "R5-1", "2B.46", "30 x 30", "36 x 36", "36 x 36", "48 x 48", "—", "36 x 36"),
 ("Wrong Way", "R5-1a", "2B.47", "36 x 24", "42 x 30", "36 x 24", "42 x 30", "30 x 18", "42 x 30"),
 ("No Trucks", "R5-2", "2B.45", "24 x 24", "24 x 24", "30 x 30", "36 x 36", "—", "36 x 36"),
 ("Except Local Deliveries (plaque)", "R5-2aP", "2B.45", "24 x 12", "24 x 12", "30 x 15", "36 x 18", "—", "36 x 18"),
 ("No Thru Trucks", "R5-2b", "2B.45", "24 x 30", "24 x 30", "30 x 36", "36 x 48", "—", "36 x 48"),
 ("No Motor Vehicles", "R5-3", "2B.45", "24 x 24", "24 x 24", "—", "—", "24 x 24", "—"),
 ("No Commercial Vehicles", "R5-4", "2B.45", "24 x 30", "24 x 30", "36 x 48", "36 x 48", "—", "—"),
 ("No Vehicles with Lugs", "R5-5", "2B.45", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "—"),
 ("No Bicycles", "R5-6", "2B.45", "24 x 24", "24 x 24", "30 x 30", "36 x 36", "24 x 24*", "48 x 48"),
 ("No Non-Motorized Traffic", "R5-7", "2B.45", "30 x 24", "30 x 24", "42 x 24", "48 x 30", "—", "42 x 24"),
 ("No Motor-Driven Cycles", "R5-8", "2B.45", "30 x 24", "30 x 24", "42 x 24", "48 x 30", "—", "42 x 24"),
 ("No Pedestrians, Bicycles, Motor-Driven Cycles", "R5-10", "2B.45", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("No Pedestrians, Bicycles, Motor-Driven Cycles On Freeway", "R5-10a", "2B.45", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("No Pedestrians or Bicycles", "R5-10b", "2B.45", "30 x 18", "30 x 18", "—", "—", "—", "—"),
 ("No Pedestrians", "R5-10c", "2B.45", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Authorized Vehicles Only", "R5-11", "2B.45", "30 x 24", "30 x 24", "—", "—", "—", "—"),
 ("No Thru Traffic", "R5-12", "2B.45", "24 x 30", "24 x 30", "—", "—", "—", "30 x 36"),
 ("One Way", "R6-1", "2B.49", "36 x 12", "48 x 18", "48 x 18", "48 x 18", "—", "72 x 24"),
 ("One Way", "R6-2", "2B.49", "24 x 30", "30 x 36", "36 x 48", "48 x 60", "18 x 24", "36 x 48"),
 ("Divided Highway Crossing", "R6-3,3a", "2B.50", "30 x 24", "30 x 24", "36 x 30", "—", "—", "36 x 30"),
 ("Roundabout Circulation (plaque)", "R6-5P", "2B.51", "30 x 30", "30 x 30", "—", "—", "—", "—"),
 ("Begin One Way", "R6-6", "2B.49", "24 x 30", "30 x 36", "—", "—", "—", "—"),
 ("End One Way", "R6-7", "2B.49", "24 x 30", "30 x 36", "—", "—", "—", "—"),
 ("Parking Restrictions", "R7-1,2,2a,3, 4,4a, 5,6,8,10, 107,108", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Van Accessible (plaque)", "R7-8aP", "2B.52, 2B.53", "12 x 6", "12 x 6", "—", "—", "—", "—"),
 ("Parking Fee Station, Multispace Meter", "R7-20", "2B.52, 2B.53", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Metered Parking", "R7-21", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Mobile Parking Payment (plaque)", "R7-21aP", "2B.52, 2B.53", "12 x 6", "12 x 6", "", "", "", ""),
 ("Metered Parking", "R7-22", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("No Parking Bus Stop", "R7-107a", "2B.52, 2B.53", "12 x 24", "12 x 24", "—", "—", "—", "—"),
 ("No Parking Bus Stop (with transit pictograph)", "R7-107b", "2B.52, 2B.53", "12 x 30", "12 x 30", "—", "—", "—", "—"),
]

T.append(sheet(3, 111, _S3))

_S4 = [
 ("No Parking Except Electric Vehicles", "R7-111", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("No Parking Except Electric Vehicles (part-time)", "R7-111a", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Electric Vehicle Parking (time limit)", "R7-112", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Electric Vehicle Parking (time limit part-time)", "R7-112a", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Electric Vehicle Parking (time limit part-time)", "R7-112b", "2B.52, 2B.53", "12 x 21", "12 x 21", "—", "—", "—", "—"),
 ("No Parking Except While Charging", "R7-113", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Vehicle Must Be Plugged In (plaque)", "R7-113aP", "2B.52, 2B.53", "12 x 6", "12 x 6", "—", "—", "—", "—"),
 ("Vacate Stall When Charging Completed (plaque)", "R7-113bP", "2B.52, 2B.53", "12 x 6", "12 x 6", "—", "—", "—", "—"),
 ("Vehicle Charging Only (time limit)", "R7-114", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Vehicle Charging Only (time limit, part-time)", "R7-114a", "2B.52, 2B.53", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Vehicle Charging Only (time limit part-time)", "R7-114b", "2B.52, 2B.53", "12 x 21", "12 x 21", "—", "—", "—", "—"),
 ("No Parking/Restricted Parking (combined sign)", "R7-200", "2B.52, 2B.53", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("No Parking/Restricted Parking (combined sign)", "R7-200a", "2B.52, 2B.53", "12 x 36", "12 x 36", "—", "—", "—", "—"),
 ("Tow Away Zone (plaque)", "R7-201P, 201aP", "2B.52, 2B.53", "12 x 6", "12 x 6", "—", "—", "—", "—"),
 ("This Side of Sign (plaque)", "R7-202P", "2B.52, 2B.53", "12 x 6", "12 x 6", "—", "—", "—", "—"),
 ("Snow Emergency Route", "R7-203", "2B.52, 2B.53", "18 x 24", "18 x 24", "—", "—", "—", "24 x 30"),
 ("No Parking on Pavement", "R8-1", "2B.52, 2B.53", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("No Parking Except on Shoulder", "R8-2", "2B.52, 2B.53", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("No Parking (symbol)", "R8-3", "2B.52, 2B.53", "24 x 24", "30 x 30", "36 x 36", "48 x 48", "12 x 12", "36 x 36"),
 ("No Parking", "R8-3a", "2B.52, 2B.53", "24 x 30", "24 x 30", "36 x 36", "48 x 48", "18 x 24", "36 x 36"),
 ("On Pavement", "R8-3c", "2B.52, 2B.53", "24 x 36", "24 x 36", "—", "—", "18 x 30", "36 x 54"),
 ("On Bridge", "R8-3d", "2B.52, 2B.53", "24 x 36", "24 x 36", "—", "—", "18 x 30", "36 x 54"),
 ("On Tracks", "R8-3e", "2B.52, 2B.53", "24 x 36", "24 x 36", "—", "—", "18 x 30", "36 x 54"),
 ("Except on Shoulder", "R8-3f", "2B.52, 2B.53", "24 x 36", "24 x 36", "—", "—", "18 x 30", "36 x 54"),
 ("Emergency Parking Only", "R8-4", "2B.55", "30 x 24", "30 x 24", "30 x 24", "48 x 36", "—", "48 x 36"),
 ("No Stopping on Pavement", "R8-5", "2B.53, 2B.54", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("No Stopping Except on Shoulder", "R8-6", "2B.53, 2B.54", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("Emergency Stopping Only", "R8-7", "2B.55", "30 x 24", "30 x 24", "48 x 36", "48 x 36", "—", "48 x 36"),
 ("Walk on Left Facing Traffic", "R9-1", "2B.56", "18 x 24", "18 x 24", "—", "—", "—", "—"),
 ("Cross Only at Crosswalks", "R9-2", "2B.57", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("No Pedestrian Crossing (symbol)", "R9-3", "2B.57", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("No Pedestrian Crossing", "R9-3a", "2B.57", "12 x 18", "12 x 18", "—", "—", "—", "—"),
]

T.append(sheet(4, 112, _S4))

_S5 = [
 ("Use Crosswalk (plaque)", "R9-3bP", "2B.57", "18 x 12", "18 x 12", "—", "—", "—", "—"),
 ("No Hitchhiking (symbol)", "R9-4", "2B.56", "18 x 18", "18 x 18", "—", "—", "—", "24 x 24"),
 ("No Hitchhiking", "R9-4a", "2B.56", "18 x 24", "18 x 24", "—", "—", "12 x 18", "—"),
 ("No Skaters", "R9-13", "2B.45", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("No Equestrians", "R9-14", "2B.45", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("No Snowmobiles", "R9-15", "2B.45", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("No All-Terrain Vehicles", "R9-16", "2B.45", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("Except on Shoulder (plaque)", "R9-19P", "2B.45", "18 x 12", "18 x 12", "24 x 18", "30 x 24", "—", "30 x 24"),
 ("Cross Only On Green", "R10-1", "2B.58", "12 x 18", "12 x 18", "—", "—", "—", "—"),
 ("Pedestrian Signs", "R10-2,3, 3b,3c,3d,4", "2B.58", "9 x 12", "9 x 12", "—", "—", "—", "—"),
 ("Pedestrian Signs", "R10-3a,3e,3f, 3g,3h,3i,4a", "2B.58", "9 x 15", "9 x 15", "—", "—", "—", "—"),
 ("Left on Green Arrow Only", "R10-5", "2B.59", "30 x 36", "30 x 36", "30 x 36", "—", "24 x 30", "48 x 60"),
 ("Stop Here on Red", "R10-6", "2B.59", "24 x 36", "24 x 36", "—", "—", "—", "36 x 48"),
 ("Stop Here on Red", "R10-6a", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "36 x 42"),
 ("Do Not Block Intersection", "R10-7", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("Use Lane with Green Arrow", "R10-8", "2B.59", "30 x 36", "30 x 36", "36 x 42", "—", "—", "60 x 72"),
 ("Left (Right) Turn Signal", "R10-10", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "30 x 36"),
 ("U- Turn Signal", "R10-10a", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "30 x 36"),
 ("No Turn on Red", "R10-11", "2B.60", "24 x 30", "24 x 30", "—", "—", "—", "36 x 48"),
 ("No Turn on Circular Red", "R10-11a", "2B.60", "24 x 30", "24 x 30", "—", "—", "—", "36 x 48"),
 ("No Turn on Red", "R10-11b", "2B.60", "24 x 24", "24 x 24", "—", "—", "—", "36 x 36"),
 ("No Turn on Red Except From Right Lane", "R10-11c", "2B.60", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("No Turn on Red From This Lane", "R10-11d", "2B.60", "30 x 42", "30 x 42", "—", "—", "—", "—"),
 ("Left Turn Yield on Green", "R10-12", "2B.59", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Left Turn Yield on Flashing Yellow Arrow", "R10-12a", "2B.59", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Left Turn Yield to Bicycle", "R10-12b", "2B.59", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Emergency Signal", "R10-13", "2B.59", "36 x 24", "36 x 24", "—", "—", "—", "42 x 30"),
 ("Emergency Signal - Stop on Flashing Red", "R10-14", "2B.59", "36 x 42", "36 x 42", "—", "—", "—", "—"),
 ("Emergency Signal - Stop on Flashing Red (overhead)", "R10-14a", "2B.59", "60 x 24", "60 x 24", "—", "—", "—", "—"),
 ("Stop Here on Flashing Red", "R10-14b", "2B.59", "24 x 36", "24 x 36", "—", "—", "—", "36 x 48"),
 ("Turning Vehicles Yield to Pedestrians", "R10-15", "2B.59", "30 x 30", "30 x 30", "—", "—", "—", "—"),
 ("Turning Vehicles Stop for Pedestrians", "R10-15a", "2B.59", "30 x 30", "30 x 30", "—", "—", "—", "—"),
 ("U-Turn Yield to Right Turn", "R10-16", "2B.59", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("Right on Red Arrow After Stop", "R10-17a", "2B.60", "30 x 36", "30 x 36", "—", "—", "—", "36 x 48"),
 ("Traffic Laws Photo Enforced", "R10-18", "2B.69", "36 x 24", "36 x 24", "48 x 30", "54 x 36", "—", "54 x 36"),
 ("Traffic Signal Photo Enforced", "R10-18a", "2B.69", "30 x 42", "30 x 42", "30 x 42", "—", "—", "36 x 54"),
 ("Photo Enforced (symbol plaque)", "R10-19P", "2B.69", "24 x 12", "24 x 12", "36 x 18", "48 x 24", "—", "48 x 24"),
 ("Photo Enforced (plaque)", "R10-19aP", "2B.69", "24 x 18", "24 x 18", "36 x 24", "48 x 36", "—", "48 x 36"),
 ("MON—FRI (and times) (3 lines) (plaque)", "R10-20aP", "2B.60", "24 x 24", "24 x 24", "—", "—", "—", "—"),
 ("SUNDAY (and times) (2 lines) (plaque)", "R10-20aP", "2B.60", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Crosswalk - Stop on Red", "R10-23", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "—"),
]

T.append(sheet(5, 113, _S5))

_S6 = [
 ("Stop on Red - Yield on Flashing Red After Stop", "R10-23a", "2B.59", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("Push Button For Warning Lights - Wait for Gap in Traffic", "R10-25", "2B.58", "9 x 12", "9 x 12", "—", "—", "—", "—"),
 ("Left Turn Yield on Flashing Red Arrow After Stop", "R10-27", "2B.59", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("XX Vehicles per Green", "R10-28", "2B.61", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("XX Vehicles per Green Each Lane", "R10-29", "2B.61", "36 x 24", "36 x 24", "—", "—", "—", "—"),
 ("Right Turn on Red Must Yield to U-Turn", "R10-30", "2B.60", "30 x 36", "30 x 36", "—", "—", "—", "—"),
 ("At Signal (plaque)", "R10-31P", "2B.59", "24 x 9", "24 x 9", "—", "—", "—", "—"),
 ("Push Button for 2 Seconds for Extra Crossing Time (plaque)", "R10-32P", "2B.58", "9 x 12", "9 x 12", "—", "—", "—", "—"),
 ("Keep Off Median", "R11-1", "2B.62", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("Road Closed", "R11-2,2a, 2b,2c", "2B.63", "48 x 30", "48 x 30", "—", "—", "—", "—"),
 ("Road Closed - Local Traffic Only", "R11-3,3a, 3b,4", "2B.63", "60 x 30", "60 x 30", "—", "—", "—", "—"),
 ("Weight Limit", "R12-1, 2", "2B.64", "24 x 30", "24 x 30", "36 x 48", "—", "—", "36 x 48"),
 ("Weight Limit - Axle, Gross", "R12-4", "2B.64", "36 x 24", "36 x 24", "—", "—", "—", "—"),
 ("Weight Limit", "R12-5", "2B.64", "24 x 36", "24 x 36", "36 x 48", "48 x 60", "—", "—"),
 ("Weight Limit - Specialized Hauling Vehicles", "R12-6", "2B.64", "30 x 42", "36 x 48", "36 x 48", "48 x 60", "—", "48 x 60"),
 ("Weight Limit - Emergency Vehicles", "R12-7", "2B.64", "30 x 36", "30 x 36", "48 x 60", "48 x 60", "—", "48 x 60"),
 ("Weight Limit - Emergency Vehicles (plaque)", "R12-7aP", "2B.64", "30 x 30", "30 x 30", "48 x 48", "48 x 48", "—", "48 x 48"),
 ("Weigh Station", "R13-1", "2B.65", "72 x 54", "72 x 54", "96 x 72", "132 x 90", "—", "—"),
 ("Truck Route", "R14-1", "2B.66", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Hazardous Material", "R14-2,3", "2B.67", "24 x 24", "24 x 24", "30 x 30", "36 x 36", "—", "42 x 42"),
 ("National Network", "R14-4,5", "2B.68", "30 x 30", "30 x 30", "36 x 36", "36 x 36", "—", "42 x 42"),
 ("Move Over or Reduce Speed", "R16-3", "2B.71", "—", "60 x 48", "84 x 60", "102 x 72", "—", "84 x 60"),
 ("Minor Crashes Move Vehicles from Travel Lanes", "R16-4", "2B.70", "—", "60 x 42", "84 x 54", "96 x 60", "—", "84 x 54"),
 ("Lights On When Using Wipers or Raining", "R16-5,6", "2B.73", "24 x 30", "24 x 30", "36 x 48", "48 x 60", "—", "36 x 48"),
 ("Turn On Headlights Next XX Miles", "R16-7", "2B.73", "60 x 18", "60 x 18", "96 x 30", "132 x 36", "—", "96 x 30"),
 ("Turn On, Check Headlights", "R16-8,9", "2B.73", "42 x 18", "42 x 18", "60 x 30", "78 x 36", "—", "60 x 30"),
 ("Begin, End Daytime Headlight Section", "R16-10,11", "2B.73", "60 x 18", "60 x 18", "96 x 30", "120 x 36", "—", "96 x 30"),
 ("No Hand-Held Phone Use By Driver", "R16-15", "2B.72", "—", "—", "72 x 48", "72 x 48", "—", "—"),
 ("No Hand-Held Phone Use By Driver", "R16-15a", "2B.72", "30 x 42", "30 x 42", "—", "—", "—", "—"),
]

T.append(sheet(6, 114, _S6))
