"""Table 2C-1 — Warning Sign and Plaque Sizes (4 sheets, pages 189-192)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch2 import sz

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

_COLS = ["Sign or Plaque", "Sign Designation", "Section",
         "Conventional Road — Single Lane", "Conventional Road — Multi-Lane",
         "Expressway", "Freeway", "Minimum", "Oversized"]

# Defined at the foot of sheet 4 but governing all four. NOTE: this "*" is
# NOT the same footnote as Table 2B-1's, which points at Table 9A-1 for
# bicycle facilities. Assuming it carried over would have attached the wrong
# condition to every starred size in a 170-row table.
_NOTES = [
    Footnote(marker="*", text="The minimum size required for diamond-shaped warning signs "
                              "facing traffic on multi-lane conventional roads shall be "
                              "36 x 36 per Section 2C.03"),
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions are shown as width x height, in inches"),
]

def sheet(n, page, rows):
    return Table(
        table_id="Table 2C-1", sheet=n, sheet_of=4, page_pdf=page,
        page_printed=str(page), title="Warning Sign and Plaque Sizes",
        crop_file=f"table_2C-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=_COLS, row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [sz(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_NOTES),
    )

_S1 = [
 ("Horizontal Alignment", "W1-1,2,3,4,5", "2C.07", "30 x 30*", "36 x 36", "36 x 36", "36 x 36", "—", "48 x 48"),
 ("One-Direction Large Arrow", "W1-6", "2C.10", "48 x 24", "48 x 24", "60 x 30", "60 x 30", "—", "60 x 30"),
 ("Two-Direction Large Arrow", "W1-7", "2C.43", "48 x 24", "48 x 24", "—", "—", "—", "60 x 30"),
 ("Chevron Alignment", "W1-8", "2C.08", "18 x 24", "18 x 24", "30 x 36", "36 x 48", "—", "24 x 30"),
 ("Combination Horizontal Alignment/Intersection", "W1-10,10a,10b, 10c,10d,10e", "2C.09", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "—", "—"),
 ("Hairpin Curve", "W1-11", "2C.07", "30 x 30", "30 x 30", "36 x 36", "48 x 48", "—", "48 x 48"),
 ("Truck Rollover", "W1-13", "2C.11", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "—", "48 x 48"),
 ("270-degree Curve", "W1-15", "2C.07", "30 x 30", "30 x 30", "36 x 36", "48 x 48", "—", "48 x 48"),
 ("Intersection Warning", "W2-1,2,3,3a, 4,5,6,7,8", "2C.41", "30 x 30", "30 x 30", "36 x 36", "—", "24 x 24", "48 x 48"),
 ("Traffic Entering When Flashing", "W2-10", "2C.42", "36 x 36", "36 x 36", "48 x 48", "—", "—", "—"),
 ("Traffic Approaching When Flashing", "W2-11", "2C.42", "36 x 36", "36 x 36", "48 x 48", "—", "—", "—"),
 ("Stop, Yield, Signal Ahead", "W3-1,2,3", "2C.35", "30 x 30", "30 x 30", "48 x 48", "48 x 48", "30 x 30", "—"),
 ("Be Prepared to Stop", "W3-4", "2C.35", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30", "—"),
 ("Reduced Speed Limit Ahead", "W3-5", "2C.40", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("XX MPH Speed Zone Ahead", "W3-5a", "2C.40", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Variable Speed Zone Ahead", "W3-5b", "2C.40", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("XX MPH Truck Speed Zone Ahead", "W3-5c", "2C.40", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Draw Bridge", "W3-6", "2C.36", "36 x 36", "36 x 36", "48 x 48", "—", "—", "60 x 60"),
 ("Ramp Meter Ahead", "W3-7", "2C.37", "36 x 36", "36 x 36", "—", "—", "—", "—"),
 ("Ramp Metered When Flashing", "W3-8", "2C.37", "36 x 36", "36 x 36", "—", "—", "—", "—"),
 ("Merge", "W4-1", "2C.45", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Lane Ends", "W4-2", "2C.47", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Added Lane", "W4-3", "2C.46", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Cross Traffic Does Not Stop (plaque)", "W4-4P", "2C.66", "24 x 12", "24 x 12", "36 x 18", "—", "—", "48 x 24"),
 ("Traffic From Left (Right) Does Not Stop (plaque)", "W4-4aP", "2C.66", "24 x 12", "24 x 12", "36 x 18", "—", "—", "48 x 24"),
 ("Oncoming Traffic Does Not Stop (plaque)", "W4-4bP", "2C.66", "24 x 12", "24 x 12", "36 x 18", "—", "—", "48 x 24"),
 ("Entering Roadway Merge", "W4-5", "2C.45", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("No Merge Area (plaque)", "W4-5aP", "2C.45", "18 x 24", "18 x 24", "24 x 30", "24 x 30", "—", "—"),
 ("Entering Roadway Added Lane", "W4-6", "2C.46", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Heavy Merge from Right (Left)", "W4-7", "2C.49", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", ""),
 ("Single Lane Transition", "W4-8", "2C.48", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "—", "48 x 48"),
 ("Road Narrows", "W5-1", "2C.17", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Narrow Bridge", "W5-2", "2C.18", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Narrow Underpass", "W5-2a", "2C.18", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", ""),
 ("One Lane Bridge", "W5-3", "2C.19", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("One Lane Underpass", "W5-3a", "2C.19", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", ""),
 ("Divided Highway", "W6-1", "2C.20", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Divided Highway Ends", "W6-2", "2C.21", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Two-Way Traffic", "W6-3", "2C.51", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Two-Way Traffic (3-Lane)", "W6-5", "2C.52", "36 x 36", "36 x 36", "48 x 48", "—", "—", "—"),
 ("Two-Way Traffic (3-Lane)", "W6-5a", "2C.52", "36 x 36", "36 x 36", "48 x 48", "—", "—", "—"),
 ("Hill", "W7-1", "2C.14", "30 x 30*", "36 x 36", "36 x 36", "36 x 36", "24 x 24*", "48 x 48"),
 ("Hill with Grade", "W7-1a", "2C.14", "30 x 30*", "36 x 36", "36 x 36", "36 x 36", "24 x 24*", "48 x 48"),
]

T.append(sheet(1, 189, _S1))

_S2 = [
 ("Use Low Gear (plaque)", "W7-2P", "2C.64", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Trucks Use Lower Gear (plaque)", "W7-2bP", "2C.64", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("XX% Grade (plaque)", "W7-3P", "2C.64", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Next XX Miles (plaque)", "W7-3aP", "2C.61", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("XX% Grade, XX Miles (plaque)", "W7-3bP", "2C.64", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Runaway Truck Ramp XX Miles", "W7-4", "2C.15", "84 x 48", "84 x 48", "120 x 72", "120 x 72", "—", "—"),
 ("Runaway Truck Ramp Entrance Direction", "W7-4b", "2C.15", "84 x 54", "84 x 54", "120 x 78", "120 x 78", "—", "—"),
 ("Truck Escape Ramp", "W7-4c", "2C.15", "78 x 60", "78 x 60", "78 x 60", "78 x 60", "—", "—"),
 ("Sand, Gravel, Paved (plaques)", "W7-4dP, 4eP,4fP", "2C.15", "24 x 12", "24 x 12", "24 x 12", "24 x 12", "—", "—"),
 ("Hill Blocks View", "W7-6", "2C.16", "30 x 30*", "36 x 36", "36 x 36", "—", "—", "48 x 48"),
 ("Bump or Dip", "W8-1,2", "2C.26", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Pavement Ends", "W8-3", "2C.28", "36 x 36", "36 x 36", "48 x 48", "—", "30 x 30*", "—"),
 ("Soft Shoulder", "W8-4", "2C.29", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "24 x 24*", "48 x 48"),
 ("Slippery When Wet", "W8-5", "2C.30", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Road Condition (plaques)", "W8-5P,5bP,5cP", "2C.30", "24 x 18", "24 x 18", "30 x 24", "36 x 30", "—", "36 x 30"),
 ("Ice (plaque)", "W8-5aP", "2C.30", "24 x 12", "24 x 12", "30 x 18", "30 x 18", "—", "—"),
 ("Truck Crossing", "W8-6", "2C.54", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Loose Gravel", "W8-7", "2C.30", "36 x 36", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Rough Road", "W8-8", "2C.30", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Low Shoulder", "W8-9", "2C.29", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Uneven Lanes", "W8-11", "2C.30", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "—", "48 x 48"),
 ("No Center Line", "W8-12", "2C.32", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "—", "—"),
 ("Bridge Ices Before Road", "W8-13", "2C.30", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Fallen Rocks", "W8-14", "2C.30", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Grooved Pavement", "W8-15", "2C.31", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Motorcycle (plaque)", "W8-15aP", "2C.31", "24 x 18", "24 x 18", "30 x 24", "36 x 30", "—", "36 x 30"),
 ("Metal Bridge Deck", "W8-16", "2C.31", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Shoulder Drop-Off", "W8-17", "2C.29", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Shoulder Drop-Off (plaque)", "W8-17P", "2C.29", "24 x 18", "24 x 18", "30 x 24", "36 x 30", "—", "36 x 30"),
 ("Road May Flood", "W8-18", "2C.34", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Depth Gauge", "W8-19", "2C.34", "12 x 72", "12 x 72", "—", "—", "—", "—"),
 ("Gusty Winds Area", "W8-21", "2C.34", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Fog Area", "W8-22", "2C.34", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("No Shoulder", "W8-23", "2C.29", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Shoulder Ends", "W8-25", "2C.29", "30 x 30*", "36 x 36", "36 x 36", "48 x 48", "24 x 24*", "48 x 48"),
 ("Road Ends", "W8-26", "2C.24", "30 x 30", "36 x 36", "—", "—", "—", "—"),
 ("Street Ends", "W8-26a", "2C.24", "30 x 30", "36 x 36", "—", "—", "—", "—"),
 ("Right (Left) Lane Ends", "W9-1", "2C.47", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "30 x 30*", "48 x 48"),
 ("Lanes Merge", "W9-4", "2C.48", "36 x 36", "36 x 36", "36 x 36", "48 x 48", "30 x 30*", "48 x 48"),
 ("Right (Left) Lane for Exit Only", "W9-7", "2C.50", "60 x 36", "60 x 36", "96 x 60", "132 x 72", "—", "—"),
 ("Bicycle", "W11-1", "2C.54", "30 x 30", "30 x 30", "36 x 36", "—", "—", "48 x 48"),
 ("Pedestrian", "W11-2", "2C.55", "30 x 30*", "36 x 36", "36 x 36", "—", "—", "48 x 48"),
 ("Large Animals", "W11-3,4,16,17, 18,19,20,21,22", "2C.55", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Farm Vehicle", "W11-5", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Snowmobile", "W11-6", "2C.55", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Equestrian", "W11-7", "2C.55", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
]

T.append(sheet(2, 190, _S2))

_S3 = [
 ("Emergency Vehicle", "W11-8", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Handicapped", "W11-9", "2C.55", "30 x 30*", "36 x 36", "36 x 36", "—", "—", "48 x 48"),
 ("Truck", "W11-10", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Golf Cart", "W11-11", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Emergency Signal Ahead (plaque)", "W11-12P", "2C.54", "36 x 30", "36 x 30", "36 x 30", "—", "—", "—"),
 ("Horse-Drawn Vehicle", "W11-14", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Trail Crossing", "W11-15", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Trail Crossing", "W11-15a", "2C.54", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Trail Crossing (plaque)", "W11-15P", "2C.54", "24 x 18", "24 x 18", "30 x 24", "—", "—", "36 x 30"),
 ("Double Arrow", "W12-1", "2C.23", "30 x 30*", "36 x 36", "36 x 36", "—", "—", "—"),
 ("Low Clearance Advance", "W12-2", "2C.25", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "30 x 30*", "—"),
 ("Low Clearance Overhead", "W12-2a", "2C.25", "84 x 24", "84 x 24", "84 x 24", "84 x 24", "—", "—"),
 ("Low Clearance - Lane Overhead", "W12-2b", "2C.25", "102 x 24", "102 x 24", "102 x 24", "102 x 24", "—", "—"),
 ("Advisory Speed (plaque)", "W13-1P", "2C.59", "18 x 18", "18 x 18", "24 x 24", "30 x 30", "—", "30 x 30"),
 ("Advisory Speed Confirmation (plaque)", "W13-1aP", "2C.59", "48 x 15", "48 x 15", "60 x 18", "60 x 18", "48 x 15", "72 x 24"),
 ("Advisory Exit or Ramp Speed", "W13-2,3", "2C.12", "24 x 30", "24 x 30", "36 x 48", "36 x 48", "—", "48 x 60"),
 ("Combination Horizontal Alignment/Advisory Exit or Ramp Speed Loop", "W13-6,7,8,9", "2C.12", "24 x 42", "24 x 42", "36 x 66", "36 x 66", "—", "48 x 84"),
 ("Combination Horizontal Alignment/Advisory Exit or Ramp Speed Turn", "W13-10,11", "2C.12", "24 x 36", "24 x 36", "36 x 54", "36 x 54", "—", "48 x 72"),
 ("Combination Horizontal Alignment/Advisory Exit or Ramp Speed - Truck Rollover", "W13-12,13", "2C.12", "24 x 42", "24 x 42", "36 x 66", "36 x 66", "—", "48 x 84"),
 ("Vehicle Speed Feedback Sign", "W13-20", "2C.13", "24 x 30", "30 x 36", "36 x 48", "48 x 60", "—", "—"),
 ("Vehicle Speed Feedback (plaque)", "W13-20aP", "2C.13", "24 x 18", "30 x 24", "36 x 30", "48 x 36", "—", "—"),
 ("Dead End, No Outlet", "W14-1,2", "2C.24", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("Dead End, No Outlet (with arrow)", "W14-1a,2a", "2C.24", "36 x 9", "36 x 9", "—", "—", "—", "—"),
 ("No Passing Zone", "W14-3", "2C.53", "48 x 48 x 36", "48 x 48 x 36", "64 x 64 x 48", "64 x 64 x 48", "40 x 40 x 30", "64 x 64 x 48"),
 ("Playground", "W15-1", "2C.56", "30 x 30*", "36 x 36", "36 x 36", "—", "24 x 24*", "48 x 48"),
 ("In Road (plaque)", "W16-1P", "2C.67", "18 x 12", "18 x 12", "24 x 18", "—", "—", "24 x 18"),
 ("In Street (plaque)", "W16-1aP", "2C.67", "18 x 12", "18 x 12", "24 x 18", "—", "—", "24 x 18"),
 ("XX Feet (2-line plaque)", "W16-2P", "2C.61", "24 x 18", "24 x 18", "30 x 24", "30 x 24", "—", "30 x 24"),
 ("XX Ft (1-line plaque)", "W16-2aP", "2C.61", "24 x 12", "24 x 12", "—", "—", "—", "30 x 18"),
 ("XX Miles (2-line plaque)", "W16-3P", "2C.61", "30 x 24", "30 x 24", "—", "—", "—", "—"),
 ("XX Miles (1-line plaque)", "W16-3aP", "2C.61", "30 x 12", "30 x 12", "—", "—", "—", "—"),
 ("Next XX Feet (plaque)", "W16-4P", "2C.61", "30 x 24", "30 x 24", "—", "—", "—", "—"),
 ("Supplemental Arrow (plaque)", "W16-5P,6P", "2C.62", "21 x 15", "21 x 15", "—", "—", "—", "30 x 21"),
 ("Diagonal Downward Arrow (plaque)", "W16-7P", "2C.63", "21 x 15", "21 x 15", "—", "—", "—", "30 x 21"),
 ("Dual Downward Diagonal Arrow (plaque)", "W16-7aP", "2C.63", "21 x 15", "21 x 15", "—", "—", "—", "30 x 21"),
 ("Advance Street Name (1-line plaque)", "W16-8P", "2C.65", "Varies x 8", "Varies x 8", "—", "—", "—", "—"),
 ("Advance Street Name (2-line plaque)", "W16-8aP", "2C.65", "Varies x 15", "Varies x 15", "—", "—", "—", "—"),
 ("Ahead (plaque)", "W16-9P", "2C.55", "24 x 12", "24 x 12", "30 x 18", "—", "—", "30 x 18"),
 ("Photo Enforced (symbol plaque)", "W16-10P", "2C.69", "24 x 12", "24 x 12", "36 x 18", "—", "—", "48 x 24"),
 ("Photo Enforced (plaque)", "W16-10aP", "2C.69", "24 x 18", "24 x 18", "36 x 30", "—", "—", "48 x 36"),
]

T.append(sheet(3, 191, _S3))

_S4 = [
 ("Traffic Circle (plaque)", "W16-12P", "2C.41", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("Roundabout (plaque)", "W16-12aP", "2C.41", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("When Flashing (plaque)", "W16-13P", "2C.55", "24 x 18", "24 x 18", "—", "—", "—", "—"),
 ("New (plaque)", "W16-15P", "2C.60", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Notice (plaque)", "W16-18P", "2A.11", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Except Bicycles (plaque)", "W16-20P", "2C.68", "24 x 12", "24 x 12", "—", "—", "—", "—"),
 ("Speed Hump", "W17-1", "2C.27", "30 x 30*", "36 x 36", "—", "—", "24 x 24*", "48 x 48"),
 ("No Traffic Signs", "W18-1", "2C.33", "30 x 30*", "36 x 36", "—", "—", "24 x 24*", "36 x 36"),
 ("Freeway Ends XX Miles", "W19-1", "2C.22", "—", "—", "—", "144 x 48", "—", "—"),
 ("Expressway Ends XX Miles", "W19-2", "2C.22", "—", "—", "144 x 48", "—", "—", "—"),
 ("Freeway Ends", "W19-3", "2C.22", "—", "—", "—", "48 x 48", "—", "—"),
 ("Expressway Ends", "W19-4", "2C.22", "—", "—", "48 x 48", "—", "—", "—"),
 ("All Traffic Must Exit", "W19-5", "2C.22", "—", "—", "90 x 48", "90 x 48", "—", "—"),
 ("New Traffic Pattern Ahead", "W23-2", "2C.38", "36 x 36", "36 x 36", "—", "—", "—", "—"),
 ("New Signal Operation Ahead", "W23-2a", "2C.38", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
 ("Oncoming Traffic Has (May Have) Extended Green", "W25-1,2", "2C.44", "24 x 30", "24 x 30", "—", "—", "—", "—"),
 ("Watch for Stopped Traffic", "W26-1", "2C.39", "36 x 36", "36 x 36", "48 x 48", "48 x 48", "—", "—"),
]

T.append(sheet(4, 192, _S4))
