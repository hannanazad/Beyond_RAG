"""Table 2G-1 — Managed and Preferential Lanes Sign and Plaque Minimum Sizes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch7 import _mz          # "Varies" -> not_applicable, otherwise w x h

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

_2G1_NOTES = [
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions are shown as width x height, in inches"),
]

def _2g1(n, page, rows):
    return Table(
        table_id="Table 2G-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="Managed and Preferential Lanes Sign and Plaque Minimum Sizes",
        crop_file=f"table_2G-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=["Sign or Plaque", "Sign Designation", "Section",
                       "Conventional Road — Single Lane", "Conventional Road — Multi-Lane",
                       "Expressway", "Freeway", "Oversized"],
        row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [_mz(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_2G1_NOTES),
    )

_S1 = [
 ("Preferential Lane Vehicle Occupancy Definition (post-mounted)","R3-10,10a","2G.04","30 x 42","30 x 42","36 x 60","78 x 96","78 x 96"),
 ("Preferential Lane Operation - High-Occupancy Vehicles (post-mounted)","R3-11 series","2G.05","30 x 42","30 x 42","36 x 60","78 x 96","78 x 96"),
 ("Motorcycles Allowed (plaque)","R3-11hP","2G.05","30 x 15","30 x 15","36 x 18","78 x 36","78 x 36"),
 ("Preferential Lane Ahead or Ends - High-Occupancy Vehicles (post-mounted)","R3-12, 12a, 12b, 12c, 12d, 12e","2G.06 2G.07","30 x 42","30 x 42","36 x 60","48 x 84","48 x 84"),
 ("Preferential Lane Ahead or Ends (post-mounted)","R3-12f, 12g","2G.06 2G.07","30 x 36","30 x 36","36 x 48","48 x 60","48 x 60"),
 ("Preferential Lane Ends (post-mounted)","R3-12h","2G.07","36 x 48","36 x 48","48 x 66","60 x 84","60 x 84"),
 ("Preferential Lane Vehicle Occupancy Definition (overhead)","R3-13,13a","2G.04","66 x 36","66 x 36","84 x 48","144 x 78","144 x 78"),
 ("HOV Lane Operation (overhead)","R3-14,14a","2G.05","72 x 60","72 x 60","96 x 72","144 x 108","144 x 108"),
 ("HOV Lane Operation (overhead)","R3-14b","2G.05","72 x 60","72 x 60","96 x 72","120 x 96","120 x 96"),
 ("Preferential Lane Operation (overhead)","R3-14c","2G.05","90 x 60","90 x 60","108 x 72","156 x 102","156 x 102"),
 ("HOV Lane Ahead (overhead)","R3-15","2G.06","66 x 36","66 x 36","84 x 48","102 x 60","102 x 60"),
 ("HOV Lane Begins XX Miles (overhead)","R3-15a","2G.06","78 x 48","114 x 72","144 x 84","150 x 108","150 x 108"),
 ("HOV Lane Ends (overhead)","R3-15b,15c","2G.07","66 x 36","66 x 36","84 x 48","102 x 60","102 x 60"),
 ("Preferential Lane Ahead or Ends (overhead)","R3-15d,15e","2G.06 2G.07","42 x 36","42 x 36","54 x 48","72 x 60","72 x 60"),
 ("Priced Managed Lane Vehicle Occupancy Definition (post-mounted)","R3-40","2G.18","—","—","54 x 66","54 x 66","66 x 78"),
 ("Priced Managed Lane Ends (post-mounted)","R3-42","2G.18","—","—","48 x 60","48 x 60","60 x 78"),
 ("Priced Managed Lane Ends Advance (post-mounted)","R3-42a","2G.18","—","—","48 x 66","48 x 66","60 x 84"),
 ("Priced Managed Lane Restriction Ends (post-mounted)","R3-42b","2G.18","—","—","48 x 60","48 x 60","60 x 78"),
 ("Priced Managed Lane Restriction Ends Advance (post-mounted)","R3-42c","2G.18","—","—","48 x 66","48 x 66","60 x 84"),
 ("Priced Managed Lane Vehicle Occupancy Definition","R3-43","2G.18","—","—","138 x 66","138 x 66","—"),
 ("Priced Managed Lane Operation (overhead)","R3-44","2G.18","—","—","90 x 84","90 x 84","—"),
 ("Priced Managed Lane Operation (overhead)","R3-44a","2G.18","—","—","132 x 84","132 x 84","—"),
 ("Priced Managed Lane Operation (overhead)","R3-44b","2G.18","—","—","90 x 72","90 x 72","—"),
 ("Priced Managed Lane Ends (overhead)","R3-45","2G.18","—","—","90 x 66","90 x 66","—"),
 ("Priced Managed Lane Restriction Ends (overhead)","R3-45a","2G.18","—","—","114 x 66","114 x 66","—"),
 ("Priced Managed Lane Toll Rate","R3-48","2G.18","—","—","Varies","Varies","—"),
 ("Priced Managed Lane Toll Rate","R3-48a","2G.18","—","—","Varies","Varies","—"),
 ("Part-Time Travel on Shoulder Operation","R3-51","2G.21","—","—","66 x 78","66 x 78","—"),
 ("No Trucks (plaque)","R3-51aP","2G.21","—","—","66 x 12","66 x 12","—"),
 ("No Trucks or Buses (plaque)","R3-51bP","2G.21","—","—","66 x 24","66 x 24","—"),
 ("Emergency Stopping Only Other Times (plaque)","R3-51cP","2G.21","—","—","54 x 42","54 x 42","—"),
]

_S2 = [
 ("Part-Time Travel on Shoulder Variable Operation","R3-51d","2G.21","—","—","66 x 84","66 x 84","—"),
 ("Part-Time Travel on Shoulder on Green Arrow","R3-51e","2G.24","—","—","66 x 84","66 x 84","—"),
 ("Part-Time Travel on Shoulder Ends","R3-52","2G.21","—","—","66 x 72","66 x 72","—"),
 ("Part-Time Travel on Shoulder Ends Advance","R3-52a","2G.21","—","—","66 x 72","66 x 72","—"),
 ("Shoulder Must Exit Advance","R3-52b","2G.21","—","—","66 x 72","66 x 72","—"),
 ("Part-Time Travel on Shoulder Begins Advance","R3-52c","2G.21","—","—","66 x 72","66 x 72","—"),
 ("Begin Exit Lane","R3-56","2G.21","—","—","48 x 72","48 x 72","—"),
 ("To Traffic on Shoulder (plaque)","R3-57P","2G.21","—","—","36 x 18","36 x 18","—"),
 ("Traffic Using Shoulder","W3-9","2G.22","—","—","36 x 48","48 x 60","—"),
 ("High-Occupancy Vehicles (plaque)","W16-11P","2G.09","24 x 12","24 x 12","30 x 18","30 x 18","30 x 18"),
 ("Preferential Lane Entrance Gore","E8-1","2G.10","—","—","48 x 96","48 x 96","—"),
 ("Preferential Lane Intermediate Entrance Gore","E8-1a","2G.10","—","—","48 x 84","48 x 84","—"),
 ("Preferential Lane Entrance Direction (overhead)","E8-2","2G.10","—","—","228 x 72","228 x 72","—"),
 ("Preferential Lane Entrance Direction (post-mounted)","E8-2a","2G.10","—","—","186 x 108","186 x 108","—"),
 ("Preferential Lane Entrance Advance","E8-3","2G.10","—","—","186 x 96","186 x 96","—"),
 ("Preferential Lane Direct Exit Gore","E8-4","2G.15","—","—","60 x 78","60 x 78","—"),
 ("Preferential Lane Intermediate Egress Direction","E8-5","2G.13","—","—","Varies x 90","Varies x 90","—"),
 ("Preferential Lane Intermediate Egress Advance","E8-6","2G.13","—","—","Varies x 84","Varies x 84","—"),
]

T.append(_2g1(1, 448, _S1))
T.append(_2g1(2, 449, _S2))
