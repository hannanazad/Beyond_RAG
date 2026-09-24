"""Table 2L-3 — Examples of Message Construction for CMS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch14 import _msg

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

_2L3 = [
 ("1","1","EXIT 10","EXIT 10 / CLOSED",
  "Diversionary message: Each message phase should convey a complete thought independent of "
  "the other message phase. The entire message should also make sense regardless of which "
  "phase is read first."),
 ("1","2","CLOSED / USE / EXIT 12","USE / EXIT 12",""),
 ("2","1","ROADWORK / AHEAD","ROAD WORK / AHEAD",
  "Advance warning message: Condensing ROAD and WORK into single word is not necessary since "
  "sign width will accommodate the conventional 2-word message. A general CAUTION message is "
  "not specific enough to be actionable by the road user. Message should not be repeated to "
  "fill sign. Phase 2 of the improved message can be eliminated without any loss of meaning "
  "to Phase 1."),
 ("2","2","CAUTION / CAUTION / CAUTION","FINES / DOUBLE",""),
 ("3","1","RIGHT / LANE / CLOSED","RIGHT LANE / CLOSED / 1 MILE",
  "Advance warning message: Use of single phase message reduces time necessary to read and "
  "glances away from the road. Second phase does not provide a complete message."),
 ("3","2","1 MILE","N/A Single-Phase Message",""),
 ("4","1","RT LN CLSD / 1 MI","RIGHT LANE / CLOSED / 1 MILE",
  "Advance warning message: Less common abbreviations (see Table 1D-2) are not warranted when "
  "the sign can accommodate the full message. Abbreviations in Table 1D-2 should be limited "
  "only to portable CMS where the number of characters per line is limited."),
 ("4","2","N/A Single-Phase Message","N/A Single-Phase Message",""),
 ("5","1","9TH AVENUE / SOUTHWEST / KEEP RIGHT","9TH AVE SW / KEEP RIGHT",
  "Directional message: Conventional abbreviations for street name descriptors (see Table "
  "2D-3) are used for consistency with standard signs to improve recognition and reduce the "
  "apparent amount of legend."),
 ("5","2","N/A Single-Phase Message","N/A Single-Phase Message",""),
 ("6","1","EXPWY CONGESTED / USE 101 / FOR AIRPORT","US 19 / CONGESTED",
  "Diversionary message: Lack of Expressway route number is vague to unfamiliar road user. "
  "Adding exit number for diversion route simplifies message. Diversion message is stated in "
  "reverse order and requires more words as a result."),
 ("6","2","N/A Single-Phase Message","AIRPORT / USE EXIT 101",""),
 ("7","1","TRAVEL TIME TO / I-89 / 13 MINUTES","I-89 JCT / 12 MILES / 13 MINS",
  "Travel time information: TRAVEL TIME legend is extraneous and out of context for the "
  "distance message. Changing only one line of legend between phases compromises recognition "
  "of the message."),
 ("7","2","TRAVEL TIME TO / I-89 / 12 MILES","N/A Single-Phase Message",""),
 ("8","1","SEAT BELTS / SAVE LIVES","STATE LAW / FASTEN / SEAT BELTS",
  "Safety campaign regulatory message: Slogan-type message does not convey the legal "
  "requirement. As an alternative, the STATE LAW legend could be eliminated and the fine for "
  "violations displayed on a second phase to convey the regulatory nature of the message."),
 ("8","2","N/A Single-Phase Message","N/A Single-Phase Message",""),
 ("9","1","DONT TEXT / JUST DRIVE","NO HAND-HELD / PHONE / BY DRIVER",
  "Regulatory message. Slogan-type message does not convey the legal requirement. Phase 2 of "
  "the improved message can be eliminated without any loss of meaning to Phase 1."),
 ("9","2","IT CAN WAIT","$250 FINE / AND POINTS",""),
]

T.append(Table(
    table_id="Table 2L-3", page_pdf=558, page_printed="517",
    title="Examples of Message Construction for CMS",
    crop_file="table_2L-3_p0558.png", kind="text",
    column_labels=["Example", "Phase", "Potential Message", "Improved Message", "Comments"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=e, number=float(e), unit="example"),
           V(text=p, number=float(p), unit="phase"),
           _msg(pot), _msg(imp), V(text=com)] for e, p, pot, imp, com in _2L3],
    footnotes=[Footnote(marker="Note", text="Examples shown are for single-color CMS with pixel "
        "spacing greater than 20 mm and use all upper-case lettering. Multi-color, full-matrix "
        "CMS with pixel spacing of 20 mm or less should use upper- and lower-case lettering "
        "where appropriate and proper legend and background colors.")],
))
