"""Table 6H-1 — Temporary Traffic Control Zone Warning Sign and Plaque Sizes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch17 import _s9

SRC = "vlm transcription from a PDF render, unverified"
T = []

_6H1_NOTES = [
    # The manual prints this footnote but NO reference mark anywhere in the
    # grid -- checked every run on both pages; the only "*" is the footnote
    # line itself. Left table-wide rather than attached to a cell that does
    # not exist, so the condition still reaches every value.
    Footnote(marker="*", text="See Table 2C-1 for minimum size required for signs facing "
             "traffic on multi-lane conventional roads", applies_to="table"),
    Footnote(marker="Note 1", text="Larger signs may be used wherever necessary for greater "
             "legibility or emphasis"),
    Footnote(marker="Note 2", text="Dimensions are shown in inches and are shown as "
             "width x height"),
]

def _6h1(n, page, rows):
    return Table(
        table_id="Table 6H-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="Temporary Traffic Control Zone Warning Sign and Plaque Sizes",
        crop_file=f"table_6H-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=["Sign or Plaque", "Sign Designation", "Section",
                       "Conventional Road", "Freeway or Expressway", "Minimum"],
        row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [_s9(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_6H1_NOTES),
    )

_S1 = [
 ("Turn and Curve Signs","W1-1,2,3,4","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Reverse Curve (2 or more lanes)","W1-4b,4c","6H.30","36 x 36","48 x 48","30 x 30"),
 ("Large Arrow (1-direction)","W1-6","6H.01","48 x 24","60 x 30","—"),
 ("Chevron Alignment","W1-8","6H.01","18 x 24","30 x 36","—"),
 ("Stop Ahead","W3-1","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Yield Ahead","W3-2","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Signal Ahead","W3-3","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Be Prepared to Stop","W3-4","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Reduced Speed Limit Ahead","W3-5","6H.01","36 x 36","48 x 48","30 x 30"),
 ("XX MPH Speed Zone Ahead","W3-5a","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Merging Traffic","W4-1,5","6H.01","36 x 36","48 x 48","36 x 36"),
 ("Lane Ends","W4-2","6H.08","36 x 36","48 x 48","30 x 30"),
 ("Added Lane","W4-3,6","6H.01","36 x 36","48 x 48","30 x 30"),
 ("No Merge Area (plaque)","W4-5aP","6H.01","18 x 24","24 x 30","—"),
 ("Road Narrows","W5-1","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Narrow Bridge","W5-2","6H.01","36 x 36","48 x 48","30 x 30"),
 ("One Lane Bridge","W5-3","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Ramp Narrows","W5-4","6H.10","36 x 36","48 x 48","30 x 30"),
 ("Divided Highway","W6-1","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Divided Highway Ends","W6-2","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Two-Way Traffic","W6-3","6H.16","36 x 36","48 x 48","30 x 30"),
 ("Narrow Two-Way Traffic","W6-4","6H.17","12 x 18","12 x 18","—"),
 ("Hill","W7-1","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Next XX Miles (plaque)","W7-3aP","6H.33","24 x 18","36 x 30","—"),
 ("Bump","W8-1","6H.01","36 x 36","48 x 48","24 x 24"),
 ("Dip","W8-2","6H.01","36 x 36","48 x 48","24 x 24"),
 ("Pavement Ends","W8-3","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Soft Shoulder","W8-4","6H.26","36 x 36","48 x 48","30 x 30"),
 ("Slippery When Wet","W8-5","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Truck Crossing","W8-6","6H.21","36 x 36","48 x 48","30 x 30"),
 ("Loose Gravel","W8-7","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Rough Road","W8-8","6H.01","36 x 36","48 x 48","24 x 24"),
 ("Low Shoulder","W8-9","6H.26","36 x 36","48 x 48","24 x 24"),
 ("Uneven Lanes","W8-11","6H.27","36 x 36","48 x 48","30 x 30"),
 ("No Center Line","W8-12","6H.29","36 x 36","48 x 48","30 x 30"),
 ("Fallen Rocks","W8-14","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Grooved Pavement","W8-15","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Motorcycle (plaque)","W8-15aP","6H.34","24 x 18","30 x 24","—"),
 ("Metal Bridge Deck","W8-16","6H.34","36 x 36","48 x 48","30 x 30"),
 ("Shoulder Drop-Off (symbol)","W8-17","6H.26","36 x 36","48 x 48","30 x 30"),
 ("Shoulder Drop-Off (plaque)","W8-17P","6H.26","24 x 18","30 x 24","—"),
 ("Road May Flood","W8-18","6H.01","36 x 36","48 x 48","24 x 24"),
 ("No Shoulder","W8-23","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Steel Plate Ahead","W8-24","6H.28","36 x 36","48 x 48","30 x 30"),
 ("Shoulder Ends","W8-25","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Lane Ends","W9-1,2","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Merge Here Take Turns","W9-2a","6N.19","36 x 48","36 x 48","—"),
 ("Interior Lane Shift Ahead","W9-3","6H.07","36 x 36","48 x 48","30 x 30"),
]

_S2 = [
 ("Bicycles Merging","W9-5a","6P.01","30 x 30","—","18 x 18"),
 ("Grade Crossing Advance Warning","W10-1","6H.01","36 dia.","48 Dia.","—"),
 ("Truck","W11-10","6H.21","36 x 36","48 x 48","24 x 24"),
 ("Double Arrow","W12-1","6H.01","30 x 30","36 x 36","—"),
 ("Low Clearance","W12-2","6H.01","36 x 36","48 x 48","30 x 30"),
 ("Advisory Speed (plaque)","W13-1P","6H.32","18 x 18","24 x 24","18 x 18"),
 ("On Ramp (plaque)","W13-4P","6H.09","36 x 36","36 x 36","—"),
 ("No Passing Zone (pennant)","W14-3","6H.01","48 x 48 x 36","64 x 64 x 48","40 x 40 x 30"),
 ("XX Feet (2-line plaque)","W16-2P","6H.01","24 x 18","30 x 24","—"),
 ("Road Work (with distance)","W20-1","6H.03","36 x 36","48 x 48","30 x 30"),
 ("Path Work (with distance)","W20-1b","6P.01","36 x 36","—","30 x 30"),
 ("Detour (with distance)","W20-2","6H.04","36 x 36","48 x 48","30 x 30"),
 ("Bike Detour (with distance)","W20-2a","6P.01","36 x 36","—","30 x 30"),
 ("Road Closed (with distance)","W20-3","6H.05","36 x 36","48 x 48","30 x 30"),
 ("Path Closed (with distance)","W20-3a","6P.01","36 x 36","—","30 x 30"),
 ("One Lane Road (with distance)","W20-4","6H.06","36 x 36","48 x 48","30 x 30"),
 ("Lane(s) Closed (with distance)","W20-5,5a","6H.07","36 x 36","48 x 48","30 x 30"),
 ("Bike Lane Closed (with distance)","W20-5b","6P.01","36 x 36","—","30 x 30"),
 ("Flagger (symbol)","W20-7","6H.15","36 x 36","48 x 48","30 x 30"),
 ("Flagger","W20-7a","6H.15","36 x 36","48 x 48","30 x 30"),
 ("Slow (on Stop/Slow Paddle)","W20-8","6D.02","18 x 18","—","—"),
 ("Workers","W21-1,1a","6H.18","36 x 36","48 x 48","30 x 30"),
 ("Fresh Oil","W21-2","6H.19","36 x 36","48 x 48","30 x 30"),
 ("Road Machinery Ahead","W21-3","6H.20","36 x 36","48 x 48","30 x 30"),
 ("Slow Moving Vehicle","W21-4","6N.05","36 x 18","—","—"),
 ("Shoulder Work","W21-5","6H.22","36 x 36","48 x 48","30 x 30"),
 ("Shoulder Closed","W21-5a","6H.22","36 x 36","48 x 48","30 x 30"),
 ("Shoulder Closed (with distance)","W21-5b","6H.22","36 x 36","48 x 48","30 x 30"),
 ("Survey Crew","W21-6","6H.23","36 x 36","48 x 48","30 x 30"),
 ("Utility Work (with distance)","W21-7","6H.24","36 x 36","48 x 48","30 x 30"),
 ("Mowing Ahead","W21-8","6N.05","36 x 36","48 x 48","30 x 30"),
 ("Blasting Zone Ahead","W22-1","6H.25","36 x 36","48 x 48","30 x 30"),
 ("End Blasting Zone","W22-3","6H.25","42 x 36","42 x 36","36 x 30"),
 ("Slow Traffic Ahead","W23-1","6H.11","48 x 24","48 x 24","—"),
 ("New Traffic Pattern Ahead","W23-2","6H.14","36 x 36","48 x 48","30 x 30"),
 ("Double Reverse Curve (1 lane)","W24-1","6H.31","36 x 36","48 x 48","30 x 30"),
 ("Double Reverse Curve (2 lanes)","W24-1a","6H.31","36 x 36","48 x 48","30 x 30"),
 ("Double Reverse Curve (3 lanes)","W24-1b","6H.31","36 x 36","48 x 48","30 x 30"),
 ("All Lanes (plaque)","W24-1cP","6H.31","24 x 18","30 x 24","—"),
 ("Road Work Next XX Miles","G20-1","6H.35","36 x 18","48 x 24","—"),
 ("End Road Work","G20-2","6H.36","36 x 18","48 x 24","—"),
 ("Pilot Car Follow Me","G20-4","6H.37","36 x 18","—","—"),
]

T.append(_6h1(1, 844, _S1))
T.append(_6h1(2, 845, _S2))
