"""Table 8B-1 — Grade Crossing Sign and Plaque Minimum Sizes (2 sheets)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch17 import _s9          # handles "36 Dia." as well as w x h

SRC = "vlm transcription from a PDF render, unverified"
T = []

_8B1_NOTES = [
    Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
    Footnote(marker="Note 2", text="Dimensions in inches are shown as width x height"),
    # A routing rule: for a sign facing a shared-use path the size comes from
    # Table 9A-1 instead, which is the reverse of 9A-1's own Note 2.
    Footnote(marker="Note 3", text="Table 9A-1 shows the minimum sizes that may be used for "
             "grade crossing signs and plaques that face shared-use paths and pedestrian "
             "facilities"),
]

def _8b1(n, page, rows):
    return Table(
        table_id="Table 8B-1", sheet=n, sheet_of=2, page_pdf=page, page_printed=str(page),
        title="Grade Crossing Sign and Plaque Minimum Sizes",
        crop_file=f"table_8B-1_s{n}_p{page:04d}.png", kind="numeric",
        column_labels=["Sign or Plaque", "Sign Designation", "Section",
                       "Conventional Road — Single Lane", "Conventional Road — Multi-Lane",
                       "Expressway", "Minimum", "Oversized"],
        row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
        rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [_s9(x) for x in r[3:]]
              for r in rows],
        footnotes=list(_8B1_NOTES),
    )

_S1 = [
 ("Stop","R1-1","8B.04, 8B.05","30 x 30","36 x 36","36 x 36","—","48 x 48"),
 ("Yield","R1-2","8B.04, 8B.05","30 x 30 x 30","36 x 36 x 36","36 x 36 x 36","—","48 x 48 x 48"),
 ("No Right Turn - Train (symbol)","R3-1a","8D.10","24 x 30","30 x 36","—","—","—"),
 ("No Left Turn - Train (symbol)","R3-2a","8D.10","24 x 30","30 x 36","—","—","—"),
 ("Do Not Stop on Tracks","R8-8","8B.07","24 x 30","24 x 30","36 x 48","—","36 x 48"),
 ("Tracks Out of Service","R8-9","8B.08","24 x 24","24 x 24","36 x 36","—","36 x 36"),
 ("Stop Here When Flashing","R8-10","8B.09","24 x 36","24 x 36","—","—","36 x 48"),
 ("Stop Here When Flashing","R8-10a","8B.09","24 x 30","24 x 30","—","—","36 x 42"),
 ("Stop Here on Red","R10-6","8B.10","24 x 36","24 x 36","—","—","36 x 48"),
 ("Stop Here on Red","R10-6a","8B.10","24 x 30","24 x 30","—","—","36 x 42"),
 ("Left (Right) Lane Signal","R10-10b","8D.11","24 x 30","30 x 36","—","24 x 30","—"),
 ("Left (Right) Turn Lane Signal","R10-10c","8D.11","24 x 30","30 x 36","—","24 x 30","—"),
 ("Grade Crossing (Crossbuck)","R15-1","8B.03","48 x 9","48 x 9","—","—","—"),
 ("Number of Tracks (plaque)","R15-2P","8B.03","27 x 18","27 x 18","—","—","—"),
 ("Exempt (plaque)","R15-3P","8B.11","24 x 12","24 x 12","—","—","—"),
 ("Light Rail Only Right Lane","R15-4a","8B.12","24 x 30","24 x 30","—","—","—"),
 ("Light Rail Only Left Lane","R15-4b","8B.12","24 x 30","24 x 30","—","—","—"),
 ("Light Rail Only Center Lane","R15-4c","8B.12","24 x 30","24 x 30","—","—","—"),
 ("Light Rail Do Not Pass (symbol)","R15-5","8B.13","24 x 30","24 x 30","—","—","—"),
 ("Do Not Pass Stopped Train","R15-5a","8B.13","24 x 30","24 x 30","—","—","—"),
 ("No Motor Vehicles On Tracks (symbol)","R15-6","8B.14","24 x 24","24 x 24","—","—","—"),
 ("Do Not Drive On Tracks","R15-6a","8B.14","24 x 30","24 x 30","—","—","—"),
 ("Light Rail Divided Highway (symbol)","R15-7","8B.15","24 x 24","24 x 24","—","—","—"),
 ("Light Rail Divided Highway (T-Intersection) (symbol)","R15-7a","8B.15","24 x 24","24 x 24","—","—","—"),
 ("Look","R15-8","8E.03","—","—","—","18 x 9","—"),
 ("Grade Crossing Advance Warning","W10-1","8B.06","36 Dia.","36 Dia.","48 Dia.","—","48 Dia."),
 ("Exempt (plaque)","W10-1aP","8B.11","24 x 12","24 x 12","—","—","—"),
 ("Grade Crossing and Intersection Advance Warning (symbol)","W10-2,3,4","8B.06","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("Low Ground Clearance (symbol)","W10-5","8B.16","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("Low Ground Clearance (plaque)","W10-5P","8B.16","30 x 24","30 x 24","—","—","—"),
 ("Light Rail Activated Blank-Out (symbol)","W10-7","8B.17","24 x 24","24 x 24","—","—","—"),
 ("Trains May Exceed 80 MPH","W10-8","8B.19","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("No Train Horn","W10-9","8B.20","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("No Train Horn (plaque)","W10-9P","8B.20","30 x 24","30 x 24","—","—","—"),
 ("Storage Space (symbol)","W10-11","8B.21","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("Storage Space XX Feet between Tracks & Highway","W10-11a","8B.21","30 x 36","30 x 36","—","—","—"),
 ("Storage Space XX Feet between Highway & Tracks Behind You","W10-11b","8B.21","30 x 36","30 x 36","—","—","—"),
 ("Skewed Crossing (symbol)","W10-12","8B.22","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("No Gates or Lights (plaque)","W10-13P","8B.23","30 x 24","30 x 24","—","—","—"),
 ("Next Crossing (plaque)","W10-14P","8B.24","30 x 24","30 x 24","—","—","—"),
 ("Use Next Crossing (plaque)","W10-14aP","8B.24","30 x 24","30 x 24","—","—","—"),
]

_S2 = [
 ("Rough Crossing (plaque)","W10-15P","8B.25","30 x 24","30 x 24","—","—","36 x 30"),
 ("Another Train Coming Activated Blank-Out","W10-16","8B.18","30 x 30","30 x 30","—","—","—"),
 ("Busway Crossing","W10-21","8B.06","36 x 36","36 x 36","48 x 48","—","48 x 48"),
 ("Signal Ahead (plaque)","W10-21aP","8B.06","30 x 24","30 x 24","—","—","—"),
 ("Emergency Notification","I13-1","8B.27","—","—","—","12 x 9","—"),
 ("Push to Exit","I13-2","8E.06","—","—","—","18 x 9","—"),
]

T.append(_8b1(1, 1035, _S1))
T.append(_8b1(2, 1036, _S2))
