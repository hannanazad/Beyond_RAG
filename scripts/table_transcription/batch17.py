"""Table 9A-1 — Bicycle Facility Sign and Plaque Minimum Sizes (3 sheets)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch2 import sz

SRC = "vlm transcription from a PDF render, unverified"
T = []

def _s9(text):
    if text.lower().endswith("dia."):
        return V(text=text, number=float(text.lower().replace("dia.", "").strip()), unit="in")
    v = sz(text.rstrip("*"))
    if text.endswith("*"):
        v.text = text
        v.footnotes = ["*"]
    return v

# The two size columns each carry TWO markers: "Off Roadway^1,5" and
# "Roadway^2,5". Note 2 is the important one -- if the sign applies to
# motorists as well as bicyclists, the size comes from a DIFFERENT table
# entirely. A verifier reading only this table would use the wrong size.
_9A1_NOTES = [
    Footnote(marker="1", text="Includes shared-use paths and bicycle-only facilities outside "
             "of the roadway.", applies_to="column:3"),
    Footnote(marker="2", text="If the sign or plaque applies to motorists and bicyclists, then "
             "the size shall be as shown for conventional roads in Tables 2B-1, 2C-1, 2D-1, "
             "or 8B-1.", applies_to="column:4"),
    Footnote(marker="5", text="Separated bicycle lanes (see definition in Section 1C.02) can be "
             "located within the roadway or outside the roadway, and the minimum sign sizes for "
             "these facilities are shown in the off roadway and roadway columns respectively.",
             applies_to="column:3,column:4"),
    Footnote(marker="*", text="For use on shared-use paths only.", applies_to="cell"),
    Footnote(marker="3", text="Larger signs may be used when appropriate."),
    Footnote(marker="4", text="Dimensions are shown in inches and are shown as width x height."),
]

def _9a1(n, page, rows):
    return Table(
        table_id="Table 9A-1", sheet=n, sheet_of=3, page_pdf=page, page_printed=str(page),
        title="Bicycle Facility Sign and Plaque Minimum Sizes",
        crop_file=f"table_9A-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=["Sign or Plaque", "Sign Designation", "Section",
                       "Off Roadway\u00b9\u02d2\u2075", "Roadway\u00b2\u02d2\u2075"],
        row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2]), _s9(r[3]), _s9(r[4])]
              for r in rows],
        footnotes=list(_9A1_NOTES),
    )

_S1 = [
 ("Stop","R1-1","9B.01","18 x 18","—"),
 ("Yield","R1-2","9B.01","18 x 18 x 18","—"),
 ("Bike Lane (plaque)","R3-5hP","9B.04","—","30 x 12"),
 ("Except Bicycles (plaque)","R3-7bP","9B.02","—","24 x 12"),
 ("Advance Intersection Lane Control with Bike Lane","R3-8x Series","9B.03","—","Varies x 36"),
 ("Bike Lane","R3-17","9B.04","—","24 x 18"),
 ("Ahead, Ends (plaques)","R3-17aP, R3-17bP","9B.04","—","24 x 9"),
 ("Movement Restriction","R4-1,2,3,7,16","9B.24","12 x 18","—"),
 ("Begin Right Turn Lane Yield to Bikes","R4-4","9B.05","—","36 x 30"),
 ("Bicycle Passing Clearance","R4-19","9B.15","—","30 x 30"),
 ("Bicycle Wrong Way","R5-1b","9B.06","12 x 18","12 x 18"),
 ("No Motor Vehicles","R5-3","9B.07","24 x 24","24 x 24"),
 ("No Bicycles","R5-6","9B.08","18 x 18","—"),
 ("On Freeway (plaque)","R5-10dP","9B.17","—","24 x 6"),
 ("No Parking Bike Lane","R7-9,9a","9B.09","—","12 x 18"),
 ("Back-In Parking","R7-10","9B.10","—","12 x 18"),
 ("No Pedestrian Crossing","R9-3","9B.08","18 x 18","—"),
 ("Ride With Traffic (plaque)","R9-3cP","9B.06","12 x 12","12 x 12"),
 ("Bicycles Use Pedestrian Signal","R9-5","9B.11","12 x 18","12 x 18"),
 ("Bicycles Yield to Pedestrians","R9-6","9B.12","12 x 18","12 x 18"),
 ("Shared-Use Path Restriction","R9-7","9B.13","12 x 18*","—"),
 ("No Skaters","R9-13","9B.08","18 x 18","18 x 18"),
 ("No Equestrians","R9-14","9B.08","18 x 18","18 x 18"),
 ("No Snowmobiles","R9-15","9B.08","18 x 18","18 x 18"),
 ("No All-Terrain Vehicles","R9-16","9B.08","18 x 18","18 x 18"),
 ("Bicycles Allowed Use of Full Lane","R9-20","9B.14","—","30 x 30"),
 ("Bicycles Use Shoulder Only","R9-21","9B.16","—","24 x 30"),
 ("Bicycles Must Exit","R9-22","9B.17","—","24 x 30"),
 ("Bicycle All Turns from Bike Lane","R9-23","9B.18","—","12 x 18"),
 ("Bicycle Left Turn from Bike Lane","R9-23a","9B.18","—","12 x 18"),
 ("Bicycle Left Turn Must Use Turn Box","R9-23b, R9-23c","9B.18","—","12 x 18"),
 ("Bicycle All Turns","R9-24,24a","9B.19","—","24 x 6"),
 ("Bicycle U and Left Turns","R9-25,25a,25b","9B.19","—","24 x 9"),
 ("Bicycle U Turn","R9-26,26a,26b","9B.19","—","24 x 6"),
 ("Bicycle Left Turn","R9-27,27a,27b","9B.19","—","24 x 6"),
 ("Push Button for Green","R10-4","9B.20","9 x 12","9 x 12"),
 ("Left Turn Yield to Bicycle","R10-12b","9B.21","—","30 x 36"),
 ("Bicycle Detector","R10-22","9B.20","12 x 18","12 x 18"),
 ("Bike Push Button for Green Light","R10-24","9B.20","9 x 15","9 x 15"),
 ("Push Button for Warning Lights - Wait for Gap","R10-25","9B.20","9 x 12","9 x 12"),
 ("Bike Push Button for Green Light (arrow)","R10-26","9B.20","9 x 15","9 x 15"),
 ("Bicycle Signal","R10-40, R10-40a, R10-41, R10-41a, R10-41b, R10-41c","9B.22","12 x 21","12 x 21"),
 ("Overhead Bicycle Signal","R10-40, R10-40a, R10-41, R10-41a, R10-41b, R10-41c","9B.22","—","24 x 36"),
 ("Grade Crossing (Crossbuck)","R15-1","9B.23","24 x 4.5","48 x 9"),
 ("Number of Tracks (plaque)","R15-2P","9B.23","13.5 x 9","27 x 18"),
 ("Look","R15-8","9B.23","18 x 9","36 x 18"),
 ("Horizontal Alignment","W1-1,2,3,4,5","9C.01","18 x 18","—"),
 ("Large Arrow","W1-6,7","9C.01","24 x 12","—"),
 ("Intersection Warning","W2-1,2,3,4,5","9C.02","18 x 18","—"),
]

T.append(_9a1(1, 1090, _S1))

_S2 = [
 ("Stop Ahead, Yield Ahead, Signal Ahead","W3-1,2,3","9C.08","18 x 18","—"),
 ("Narrow Bridge","W5-2","9C.08","18 x 18","—"),
 ("Path Narrows","W5-4a","9C.08","18 x 18","—"),
 ("Hill","W7-5","9C.08","18 x 18","30 x 30"),
 ("Bump, Dip","W8-1,2","9C.03","18 x 18","—"),
 ("Pavement Ends","W8-3","9C.03","18 x 18","—"),
 ("Bicycle Surface Condition","W8-10","9C.03","18 x 18","30 x 30"),
 ("Slippery When Wet (plaque)","W8-10P","9C.03","12 x 9","12 x 9"),
 ("Bicycle Lane Ends","W9-5","9C.07","—","30 x 30"),
 ("Bicycles Merging","W9-5a","9C.07","18 x 18","30 x 30"),
 ("Grade Crossing Advance Warning","W10-1","9C.08","24 Dia.","36 Dia."),
 ("No Train Horn (plaque)","W10-9P","9C.08","18 x 12","30 x 24"),
 ("Skewed Crossing","W10-12","9C.08","18 x 18","36 x 36"),
 ("Bicycle","W11-1","9C.04, 9C.08","18 x 18","—"),
 ("Pedestrian","W11-2","9C.08","18 x 18","—"),
 ("Trail Crossing","W11-15","9C.04","18 x 18","—"),
 ("Trail Crossing (plaque)","W11-15P","9C.04","18 x 12","—"),
 ("Low Clearance","W12-2","9C.08","18 x 18","—"),
 ("Playground","W15-1","9C.08","18 x 18","—"),
 ("In Road (plaque)","W16-1P","9C.08","—","18 x 12"),
 ("In Street (plaque)","W16-1aP","9C.08","—","18 x 12"),
 ("XX Feet (2-line plaque)","W16-2P","9C.04","18 x 12","—"),
 ("XX Ft (1-line plaque)","W16-2aP","9C.04","12 x 9","—"),
 ("Downward Diagonal Arrow (plaque)","W16-7P","9C.04","12 x 9","—"),
 ("Ahead (plaque)","W16-9P","9C.04","—","24 x 12"),
 ("Except Bicycles (plaque)","W16-20P","9C.05","—","24 x 12"),
 ("2-Way Bicycle Cross Traffic (plaque)","W16-21P","9C.06","—","24 x 12"),
 ("Object Marker Type 3","OM3-L,C,R","9C.09","6 x 18","12 x 36"),
 ("Destination (1 line)","D1-1, D1-1a","9D.01","Varies x 6","—"),
 ("Bicycle Destination (1 line)","D1-1b, D1-1c","9D.01","Varies x 6","Varies x 6"),
 ("Destination (2 lines)","D1-2, D1-2a","9D.01","Varies x 12","—"),
 ("Bicycle Destination (2 lines)","D1-2b, D1-2c","9D.01","Varies x 12","Varies x 12"),
 ("Destination (3 lines)","D1-3, D1-3a","9D.01","Varies x 18","—"),
 ("Bicycle Destination (3 lines)","D1-3b, D1-3c","9D.01","Varies x 18","Varies x 18"),
 ("Distance (1 line)","D2-1","9D.01","Varies x 6","—"),
 ("Bike Route Destination and Distance (1 Line)","D2-1a","9D.01","Varies x 12","Varies x 12"),
 ("Distance (2 line)","D2-2","9D.01","Varies x 9","—"),
 ("Bike Route Destination and Distance (2 Lines)","D2-2a","9D.01","Varies x 15","Varies x 15"),
 ("Distance (3 line)","D2-3","9D.01","Varies x 12","—"),
 ("Bike Route Destination and Distance (3 Lines)","D2-3a","9D.01","Varies x 18","Varies x 18"),
 ("Street Name (1 line)","D3-1","9D.01","Varies x 6","Varies x 6"),
 ("Street Name (2 lines)","D3-1","9D.01","Varies x 12","Varies x 12"),
 ("Bicycle Parking Area Directional","D4-3","9D.09","18 x 12","18 x 12"),
 ("Bicycle-Sharing Station Directional","D4-4","9D.09","12 x 18","12 x 18"),
 ("Bicycle Lockers Directional","D4-4a","9D.09","12 x 18","12 x 18"),
 ("Reference Location (1-digit)","D10-1","9D.10","6 x 9","—"),
 ("Intermediate Reference Location (2-digits)","D10-1a","9D.10","6 x 15","—"),
 ("Reference Location (2-digits)","D10-2","9D.10","6 x 15","—"),
 ("Intermediate Reference Location (3-digits)","D10-2a","9D.10","6 x 21","—"),
]

_S3 = [
 ("Reference Location (3-digits)","D10-3","9D.10","6 x 21","—"),
 ("Intermediate Reference Location (4-digits)","D10-3a","9D.10","6 x 24","—"),
 ("Bike Route","D11-1","9D.02","24 x 18","24 x 18"),
 ("Bike Route (plaque)","D11-1bP","9D.03","18 x 6","18 x 6"),
 ("Bike Route with Destination","D11-1c","9D.02","24 x 18","24 x 18"),
 ("Shared-Use Path Destination (1 line)","D11-10a","9D.12","Varies x 6*","—"),
 ("Shared-Use Path Destination (2 lines)","D11-10b","9D.12","Varies x 12*","—"),
 ("Shared-Use Path Destination (3 lines)","D11-10c","9D.12","Varies x 18*","—"),
 ("Shared-Use Path Destination and Distance (1 line)","D11-10d","9D.12","Varies x 6*","—"),
 ("Shared-Use Path Destination and Distance (2 lines)","D11-10e","9D.12","Varies x 12*","—"),
 ("Shared-Use Path Destination and Distance (3 lines)","D11-10f","9D.12","Varies x 18*","—"),
 ("Bicycles Directional","D11-11","9D.11","18 x 18","—"),
 ("Pedestrians Directional","D11-12","9D.11","18 x 18","—"),
 ("Skaters Directional","D11-13","9D.11","18 x 18","—"),
 ("Equestrians Directional","D11-14","9D.11","18 x 18","—"),
 ("Bicycle Turn Box Guide Signs","D11-20, D11-20a","9D.13","—","12 x 18"),
 ("State or Local Bicycle Route","M1-8, M1-8a","9D.05","12 x 18","18 x 24"),
 ("Non-Numbered Bicycle Route","M1-8b, M1-8c","9D.06","12 x 12","18 x 18"),
 ("U.S. Bicycle Route","M1-9","9D.07","12 x 18","18 x 24"),
 ("Bicycle Route Auxiliary Signs (plaque)","M2-1P, M3-1P,2P,3P,4P, M4-1P,1aP,2P,3P,5P,6P,7P, 7aP,8P,14P","9D.08","12 x 6","12 x 6"),
 ("Bicycle Route Arrow Signs (plaque)","M5-1P, 2P, M6-1P, 2P, 3P, 4P, 5P, 6P, 7P","9D.08","12 x 9","12 x 9"),
]

T.append(_9a1(2, 1091, _S2))
T.append(_9a1(3, 1092, _S3))
