"""School area sizes and the typical-application symbol key."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch2 import sz

SRC = "vlm transcription from a PDF render, unverified"
T = []

_7B1_COLS = ["Sign or Plaque", "Sign Designation", "Section",
             "Conventional Road", "Minimum", "Oversized"]
_7B1_NOTES = [
    Footnote(marker="Note 1", text="Larger sizes may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions are shown in inches and are shown as "
                                   "width x height"),
    # This one is a rule, not a caption: it tells a verifier which column to
    # read for a multi-lane conventional road.
    Footnote(marker="Note 3", text="Minimum sign sizes for multi-lane conventional roads shall "
                                   "be as shown in the Conventional Road column"),
]

_7B1_SIGNS = [
 ("School","S1-1","7B.02","36 x 36","30 x 30","48 x 48"),
 ("School Bus Stop Ahead","S3-1","7B.04","36 x 36","30 x 30","48 x 48"),
 ("School Bus Turn Ahead","S3-2","7B.04","36 x 36","30 x 30","48 x 48"),
 ("Reduced School Speed Limit Ahead","S4-5, S4-5a","7B.05","36 x 36","30 x 30","48 x 48"),
 ("School Speed Limit XX When Flashing","S5-1","7B.05","24 x 48","—","36 x 72"),
 ("End School Zone","S5-2","7B.02","24 x 30","—","36 x 48"),
 ("End School Speed Limit","S5-3","7B.05","24 x 30","—","36 x 48"),
 ("Yield (Stop) Here for School Crossing","R1-5a, R1-5c","7B.03","36 x 36","—","—"),
 ("In-Street Ped or School Crossing","R1-6, R1-6a, R1-6b, R1-6c","7B.03","12 x 36","—","—"),
 ("Overhead School Crossing","R1-9b, R1-9c","7B.03","90 x 24","—","—"),
 ("Speed Limit (School Use)","R2-1","7B.05","24 x 30","—","36 x 48"),
 ("Begin Higher Fines Zone","R2-10","7B.06","24 x 30","—","36 x 48"),
 ("End Higher Fines Zone","R2-11","7B.06","24 x 30","—","36 x 48"),
]
_7B1_PLAQUES = [
 ("Time of Day X:XX to X:XX AM X:XX to X:XX PM","S4-1P","7B.06","24 x 12","—","36 x 18"),
 ("When Children Are Present","S4-2P","7B.06","24 x 12","—","36 x 18"),
 ("School","S4-3P","7B.02, 7B.05","24 x 9","—","36 x 12"),
 ("When Flashing","S4-4P","7B.05, 7B.06","24 x 12","—","36 x 18"),
 ("Days of Week Mon-Fri","S4-6P","7B.05","24 x 12","—","36 x 18"),
 ("All Year","S4-7P","7B.02","24 x 12","—","30 x 18"),
 ("Fines Higher","R2-6P","7B.06","24 x 18","—","36 x 24"),
 ("Fines Double","R2-6aP","7B.06","24 x 18","—","36 x 24"),
 ("$XX Fine","R2-6bP","7B.06","24 x 18","—","36 x 24"),
 ("XX Feet (2-line)","W16-2P","7B.02, 7B.03","24 x 18","—","30 x 24"),
 ("XX Ft (1-line)","W16-2aP","7B.02, 7B.03","24 x 12","—","30 x 18"),
 ("Directional Arrow","W16-5P","7B.02, 7B.03","21 x 15","—","30 x 21"),
 ("Advance Turn Arrow","W16-6P","7B.02, 7B.03","21 x 15","—","30 x 21"),
 ("Downward Diagonal Arrow","W16-7P","7B.02, 7B.03","21 x 15","—","30 x 21"),
 ("Ahead","W16-9P","7B.02, 7B.03","24 x 12","—","30 x 18"),
]

# The page prints SIGNS and PLAQUES as two separate grids under one caption.
def _7b1(part, rows):
    return Table(
        table_id="Table 7B-1", part=part, page_pdf=1012, page_printed="1012",
        title=f"School Area Sign and Plaque Sizes \u2014 {part}",
        crop_file="table_7B-1_p1012.png", kind="numeric",
        column_labels=_7B1_COLS, row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [sz(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_7B1_NOTES),
    )

T.append(_7b1("Signs", _7B1_SIGNS))
T.append(_7b1("Plaques", _7B1_PLAQUES))

# 6P-2 is a SYMBOL KEY: the left column is a picture, so there is nothing to
# transcribe there. It is kept because the Part 6 typical-application notes
# point at it ("See Table 6P-2 for the meanings of the symbols used in this
# figure"), and a cross-reference verifier following that pointer needs the
# meanings to exist.
T.append(Table(
    table_id="Table 6P-2", page_pdf=900, page_printed="900",
    title="Meaning of Symbols on Typical Application Diagrams",
    crop_file="table_6P-2_p0900.png", kind="text",
    column_labels=["Symbol", "Meaning"], row_key_columns=[1], source=SRC,
    note_chunk_ids=[],
    rows=[[V(text="(diagram symbol)", missing="not_applicable"), V(text=m)] for m in [
        "Arrow board",
        "Arrow board support or trailer (shown facing down)",
        "Changeable message sign or support trailer",
        "Channelizing device",
        "Crash cushion",
        "Direction of temporary traffic detour",
        "Direction of travel",
        "Flagger",
        "High-level warning device (Flag tree)",
        "Longitudinal channelizing device",
        "Luminaire",
        "Pavement markings that should be removed for a long-term project",
        "Shadow vehicle",
        "Sign (shown facing left)",
        "Surveyor",
        "Temporary barrier",
        "Temporary barrier with warning light",
        "Traffic or pedestrian signal",
        "Truck-mounted attenuator",
        "Type 3 barricade",
        "Warning light",
        "Work space",
        "Work vehicle",
    ]],
))

# ---- Table 2I-1 (2 sheets) ----------------------------------------------
from batch7 import _mz          # handles "X (F) / Y (E)" and "Varies"
from mrag.vine.table_data import Quantity as Q

def _s2i(text):
    marks = []
    for m in ("***", "**", "*"):
        if m in text:
            marks = [m]
            break
    body = text.replace("***", "").replace("**", "").replace("*", "").strip()
    body = " / ".join(p.strip() for p in body.split("\n")) if "\n" in body else body
    v = _mz(body)
    v.text = text
    if marks:
        v.footnotes = marks
    return v

_2I1_NOTES = [
    Footnote(marker="*", text="The size shown is for a sign with a REST AREA, PARKING AREA, "
        "PICNIC AREA, SCENIC AREA, and/or TOURIST INFO CENTER legend. The size should be "
        "appropriately adjusted if an alternate legend is used.", applies_to="cell"),
    Footnote(marker="**", text="The size shown is for a sign with four lines of services. The "
        "size should be appropriately adjusted depending on the amount of legend displayed.",
        applies_to="cell"),
    Footnote(marker="***", text="The Standard Highway Signs publication contains layouts for the "
        "18 x 18-inch and 24 x 24-inch alternative fuels symbol signs mounted with the "
        "Alternative Fuels Corridor sign in accordance with Section 2H.14.", applies_to="cell"),
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate."),
    Footnote(marker="Note 2", text="Dimensions in inches are shown as width x height"),
    Footnote(marker="Note 3", text="Where two sizes are shown, the larger size is for freeways "
        "(F) and the smaller size is for expressways (E)"),
]

def _2i1(n, page, rows):
    return Table(
        table_id="Table 2I-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="General Service Sign and Plaque Sizes",
        crop_file=f"table_2I-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=["Sign or Plaque", "Sign Designation", "Section",
                       "Conventional Road", "Freeway or Expressway"],
        row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2]), _s2i(r[3]), _s2i(r[4])]
              for r in rows],
        footnotes=list(_2I1_NOTES),
    )

_2I1_S1 = [
 ("Rest Area Advance","D5-1","2I.05","78 x 36*","132 x 60* (F) / 114 x 48* (E)"),
 ("Rest Area Advance Direction","D5-1a","2I.05","78 x 36*","132 x 60* (F) / 114 x 48* (E)"),
 ("Rest Area Entrance Direction","D5-2","2I.05","78 x 36*","132 x 66* (F) / 114 x 60 (E)"),
 ("Rest Area Gore","D5-2a","2I.05","42 x 48*","78 x 78* (F) / 66 x 66* (E)"),
 ("Rest Area Directional","D5-5","2I.05","42 x 48*","—"),
 ("Next Rest Area","D5-6","2I.05","78 x 54*","132 x 78* (F) / 108 x 66* (E)"),
 ("Rest Area Tourist Info Center Advance","D5-7","2I.08","90 x 72*","156 x 108* (F) / 132 x 96* (E)"),
 ("Rest Area Tourist Info Center Advance Direction","D5-7a","2I.08","90 x 72*","156 x 108* (F) / 132 x 96* (E)"),
 ("Rest Area Tourist Info Center Entrance Direction","D5-8","2I.08","84 x 72*","138 x 108* (F) / 120 x 96* (E)"),
 ("Parking Area Advance","D5-9","2I.05","96 x 36*","162 x 60* (F) / 138 x 48* (E)"),
 ("Parking Area Entrance Direction","D5-9a","2I.05","96 x 36*","162 x 60* (F) / 138 x 54* (E)"),
 ("Parking Area Gore","D5-9b","2I.05","60 x 48*","108 x 78* (F) / 84 x 66* (E)"),
 ("Picnic Area (Roadside Table, Roadside Park) Advance","D5-10","2I.05","84 x 36*","144 x 60* (F) / 120 x 48* (E)"),
 ("Picnic Area (Roadside Table, Roadside Park) Entrance Direction","D5-10a","2I.05","84 x 36*","144 x 60* (F) / 120 x 54* (E)"),
 ("Picnic Area (Roadside Table, Roadside Park) Gore","D5-10b","2I.05","54 x 48*","84 x 78* (F) / 72 x 66* (E)"),
 ("Scenic Area (Scenic View, Scenic Overlook) Advance","D5-11","2I.05","84 x 36*","144 x 60* (F) / 120 x 48* (E)"),
 ("Scenic Area (Scenic View, Scenic Overlook) Entrance Direction","D5-11a","2I.05","84 x 36*","144 x 60* (F) / 120 x 54* (E)"),
 ("Scenic Area (Scenic View, Scenic Overlook) Gore","D5-11b","2I.05","54 x 48*","90 x 78* (F) / 78 x 66* (E)"),
 ("Interstate Oasis","D5-12","2I.04","—","198 x 60 (F) / 162 x 48 (E)"),
 ("Interstate Oasis (plaque)","D5-12aP","2I.04","—","114 x 48"),
 ("Interstate Oasis Directional","D5-12b","2I.04","—","48 x 36"),
 ("Brake Check Area Advance","D5-13","2I.06","96 x 54","132 x 66"),
 ("Brake Check Area Entrance Direction","D5-14","2I.06","96 x 54","132 x 78"),
 ("Chain-Up Area Advance","D5-15","2I.07","72 x 54","102 x 66"),
 ("Chain-Up Area Entrance Direction","D5-16","2I.07","72 x 54","102 x 78"),
 ("Telephone","D9-1","2I.02","24 x 24","30 x 30"),
 ("Hospital","D9-2","2I.02","24 x 24","30 x 30"),
 ("Camping","D9-3","2I.02","24 x 24","30 x 30"),
 ("Litter Container","D9-4","2I.02","24 x 30","36 x 48"),
 ("International Symbol of Accessibility","D9-6","2I.02","24 x 24","30 x 30"),
 ("Van Accessible (plaque)","D9-6P","2I.02","18 x 9","—"),
 ("Gas","D9-7","2I.02","24 x 24","30 x 30"),
 ("Food","D9-8","2I.02","24 x 24","30 x 30"),
 ("Lodging","D9-9","2I.02","24 x 24","30 x 30"),
 ("Tourist Information","D9-10","2I.02","24 x 24","30 x 30"),
 ("Diesel Fuel","D9-11","2I.02","24 x 24","30 x 30"),
 ("Alternative Fuel - Compressed Natural Gas","D9-11a","2I.02","24 x 24***","30 x 30***"),
 ("Electric Vehicle Charging","D9-11b","2I.02","24 x 24***","30 x 30***"),
 ("Electric Vehicle Charging (plaque)","D9-11bP","2I.02","24 x 18","30 x 24"),
 ("Alternative Fuel - Ethanol","D9-11c","2I.02","24 x 24","30 x 30"),
]

_2I1_S2 = [
 ("Alternative Fuel - Liquefied Natural Gas","D9-11d","2I.02","24 x 24***","30 x 30***"),
 ("Alternative Fuel - Liquefied Petroleum Gas","D9-11e","2I.02","24 x 24***","30 x 30***"),
 ("Alternative Fuel - Hydrogen","D9-11f","2I.02","24 x 24***","30 x 30***"),
 ("Alternative Fuel - Biofuel","D9-11g","2I.02","24 x 24","30 x 30"),
 ("RV Sanitary Station","D9-12","2I.02","24 x 24","30 x 30"),
 ("Emergency Medical Services","D9-13","2I.02","24 x 24","30 x 30"),
 ("Hospital (plaque)","D9-13aP","2I.02","24 x 12","30 x 12"),
 ("Ambulance Station (plaque)","D9-13bP","2I.02","24 x 12","30 x 15"),
 ("Emergency Medical Care (plaque)","D9-13cP","2I.02","24 x 18","30 x 24"),
 ("Trauma Center (plaque)","D9-13dP","2I.02","24 x 12","30 x 15"),
 ("Police","D9-14","2I.02","24 x 24","30 x 30"),
 ("Truck Parking","D9-16","2I.03","24 x 24","30 x 30"),
 ("Truck External Power (plaque)","D9-16aP","2I.03","24 x 24","30 x 30"),
 ("Truck Parking Availability - Exit Number","D9-16b","2I.15","Varies x 144","Varies x 144"),
 ("Truck Parking Availability - Distance","D9-16c","2I.15","Varies x 144","Varies x 144"),
 ("Truck Parking Availability - Rest Area","D9-16d","2I.15","Varies x Varies","Varies x Varies"),
 ("Truck Parking Availability - Combined","D9-16e","2I.15","Varies x Varies","Varies x Varies"),
 ("Next Services Advance (plaque)","D9-17P","2I.02","72 x 24","114 x 30"),
 ("General Services (up to 6 symbols) with Exit Number","D9-18","2I.03","108 x 84","132 x 114 (F) / 132 x 108 (E)"),
 ("General Services with Exit Number","D9-18a","2I.03","72 x 60","132 x 108** (F) / 102 x 84** (E)"),
 ("General Services (up to 6 symbols) with Action Message","D9-18b","2I.03","108 x 84","132 x 114 (F) / 132 x 108 (E)"),
 ("General Services with Action Message","D9-18c","2I.03","72 x 60**","132 x 108** (F) / 102 x 84** (E)"),
 ("Rural Interchange General Services (up to 3 symbols) (plaque)","D9-18dP","2I.03","—","120 x 36"),
 ("Rural Interchange General Services (1 line) (plaque)","D9-18eP","2I.03","—","Varies x 24"),
 ("Rural Interchange General Services (2 line) (plaque)","D9-18fP","2I.03","—","Varies x 42"),
 ("Pharmacy","D9-20","2I.02","24 x 24","30 x 30"),
 ("24-Hour (plaque)","D9-20aP","2I.02","24 x 12","30 x 12"),
 ("Telecommunications Device for the Deaf","D9-21","2I.02","24 x 24","30 x 30"),
 ("Wireless Internet","D9-22","2I.02","24 x 24","30 x 30"),
 ("Radio - Weather Information","D12-1","2I.09","84 x 48","132 x 84"),
 ("Radio - Traffic Information","D12-1a","2I.09","96 x 48","120 x 60"),
 ("Urgent Message When Flashing (plaque)","D12-1bP","2I.09","84 x 30","108 x 36"),
 ("Carpool Information","D12-2","2I.14","60 x 42","96 x 66"),
 ("Channel 9 Monitored","D12-3","2I.10","84 x 48","132 x 84"),
 ("Emergency Call 911","D12-4","2I.11","66 x 30","96 x 48"),
 ("Travel Info Call 511 (pictograph)","D12-5","2I.12","48 x 60","66 x 72"),
 ("Travel Info Call 511","D12-5a","2I.12","48 x 36","66 x 48"),
 ("Roadside Assistance","D12-6","2I.13","60 x 42","78 x 54"),
]

T.append(_2i1(1, 517, _2I1_S1))
T.append(_2i1(2, 518, _2I1_S2))
