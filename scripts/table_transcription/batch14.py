"""Preferential lane marking tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

# Several cells list ALTERNATIVES, each tied to a different condition
# ("where crossing is prohibited" / "discouraged" / "permitted") and each
# pointing at its own drawing. They are kept as one cell with the
# alternatives separated, because choosing between them is a decision the
# verifier must make on the crossing rule, not something to flatten away.
T.append(Table(
    table_id="Table 3E-1", page_pdf=648, page_printed="648",
    title="Standard Edge Line and Lane Line Markings for Preferential Lanes",
    crop_file="table_3E-1_p0648.png", kind="text",
    column_labels=["Type of Preferential Lane", "Left-Hand Line", "Right-Hand Line"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a), V(text=b), V(text=c)] for a, b, c in [
        ("Barrier-Separated, Non-Reversible",
         "A normal solid single yellow edge line",
         "A normal solid single white edge line (see Drawing A in Figure 3E-1)"),
        ("Barrier-Separated, Reversible",
         "A normal solid single white edge line",
         "A normal solid single white edge line (see Drawing B in Figure 3E-1)"),
        ("Buffer-Separated, Left-Hand Side",
         "A normal solid single yellow edge line",
         "A wide solid double white line along both edges of the buffer space where crossing "
         "is prohibited (see Drawing A in Figure 3E-2); "
         "A wide solid single white line along both edges of the buffer space where crossing "
         "is discouraged (see Drawing B in Figure 3E-2); "
         "A wide broken single white line along both edges of the buffer space, or a wide "
         "broken single white line within the buffer space (resulting in wider lanes), where "
         "crossing is permitted (see Drawing C in Figure 3E-2)"),
        ("Buffer-Separated, Right-Hand Side",
         "A wide solid double white line along both edges of the buffer space where crossing "
         "is prohibited, or a wide solid single white line along both edges of the buffer "
         "space where crossing is discouraged (see Drawing D in Figure 3E-2); "
         "A wide broken single white line along both edges of the buffer space, or a wide "
         "broken single white line within the buffer space (resulting in wider lanes), where "
         "crossing is permitted (see Drawing D in Figure 3E-2); "
         "A wide dotted single white line within the buffer space (resulting in wider lanes) "
         "where crossing is permitted for any vehicle to perform a right-turn maneuver "
         "(see Drawing D in Figure 3E-2)",
         "A normal solid single white edge line (if warranted)"),
        ("Contiguous, Left-Hand Side",
         "A normal solid single yellow edge line",
         "A wide solid double white lane line where crossing is prohibited (see Drawing A in "
         "Figure 3E-3); A wide solid single white lane line where crossing is discouraged "
         "(see Drawing B in Figure 3E-3); A wide broken single white lane line where crossing "
         "is permitted (see Drawing C in Figure 3E-3)"),
        ("Contiguous, Right-Hand Side",
         "A wide solid double white lane line where crossing is prohibited (see Drawing D in "
         "Figure 3E-3); A wide solid single white lane line where crossing is discouraged "
         "(see Drawing D in Figure 3E-3); A wide broken single white lane line where crossing "
         "is permitted (see Drawing D in Figure 3E-3); A wide dotted single white lane line "
         "where crossing is permitted for any vehicle to perform a right-turn maneuver "
         "(see Drawing D in Figure 3E-3)",
         "A normal solid single white lane line (if warranted)"),
    ]],
    footnotes=[
        Footnote(marker="Note 1", text="If there are two or more preferential lanes, the lane "
            "lines between the preferential lanes shall be normal broken white lines."),
        Footnote(marker="Note 2", text="The standard lane markings listed in this table are "
            "provided in a tabular format for reference."),
    ],
))

T.append(Table(
    table_id="Table 3E-2", page_pdf=650, page_printed="650",
    title="Standard Center Line and Edge Line Markings for Counter-Flow Preferential "
          "Lanes on Divided Highways",
    crop_file="table_3E-2_p0650.png", kind="text",
    column_labels=["Type of Preferential Lane", "Center Line on Left-Hand Side",
                   "Edge Line on Left-Hand Side"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a), V(text=b), V(text=c)] for a, b, c in [
        ("Part-Time Contiguous", "A normal width broken double yellow line",
         "A normal solid single white line (if warranted)"),
        ("Part-Time Buffer-Separated",
         "A normal width broken double yellow line along both edges of the buffer space",
         "A normal solid single white line (if warranted)"),
        ("Full-Time Contiguous", "A normal width solid double yellow line",
         "A normal solid single white line (if warranted)"),
        ("Full-Time Buffer-Separated",
         "A normal width solid double yellow line along both edges of the buffer space",
         "A normal solid single white line (if warranted)"),
    ]],
))

# 2L-4's messages are printed as images of CMS displays; the text is
# transcribed with a "/" between display lines. "N/A Single-Phase Message"
# means the improved version needs no second phase at all -- a real outcome,
# not a missing value.
def _msg(text):
    if text.startswith("N/A"):
        return V(text="N/A - Single-Phase Message", missing="not_applicable")
    return V(text=text)

_2L4 = [
 ("1","1","EXIT 10","EXIT 10 / CLOSED",
  "Diversionary message: Each phase conveys a complete thought."),
 ("1","2","CLOSED / USE / EXIT 12","USE / EXIT 12",""),
 ("2","1","ROADWORK / AHEAD","ROAD / WORK / AHEAD",
  "Advance warning message: Condensing ROAD and WORK into a single word is unnecessary "
  "because the sign width will accommodate the conventional 2-word phrase. A general CAUTION "
  "message is not specific enough to be useful to the road user. Message should not be "
  "repeated to fill the sign. Phase 2 of the improved message can be eliminated without any "
  "loss of meaning to Phase 1."),
 ("2","2","CAUTION / CAUTION / CAUTION","FINES / DOUBLE",""),
 ("3","1","RIGHT / LANE / CLOSED","RIGHT LN / CLOSED / 1 MILE",
  "Advance warning message: Separation of the message into 2 phases is unnecessary. Second "
  "phase does not provide a complete message."),
 ("3","2","1 MILE","N/A Single-Phase Message",""),
 ("4","1","RT LN / CLSD / 1 MI","RIGHT LN / CLOSED / 1 MILE",
  "Advance warning message: Less common abbreviations (see Table 1D-2) are not warranted "
  "when the sign can accommodate the full message."),
 ("4","2","N/A Single-Phase Message","N/A Single-Phase Message",""),
 ("5","1","9TH / AVENUE / SW","9 AVE SW / KEEP / RIGHT",
  "Directional message: Conventional abbreviations for street name descriptors (see Table "
  "2D-3) are used for consistency with standard signs to improve recognition and reduce the "
  "apparent amount of legend."),
 ("5","2","KEEP / RIGHT","N/A Single-Phase Message",""),
 ("6","1","ROAD / WORK","ROADWORK / NEXT / 3 MILES",
  "Advance warning message: Condensing ROAD and WORK into single word (see Table 1D-2) "
  "accommodates a single-phase message."),
 ("6","2","NEXT / 3 / MILES","N/A Single-Phase Message",""),
 ("7","1","SEAT / BELTS","FASTEN / SEAT / BELTS",
  "Safety campaign regulatory message: Slogan-type message does not convey the legal "
  "requirement. As an alternative, the STATE LAW legend could be eliminated and the fine for "
  "violations displayed on a second phase to convey the regulatory nature of the message. "
  "Phase 2 of the improved message can be eliminated without any loss of meaning to Phase 1."),
 ("7","2","SAVE / LIVES","STATE / LAW",""),
 ("8","1","DONT / TEXT","NO HAND- / HELD / PHONE",
  "Regulatory message: Slogan-type message does not convey the legal requirement."),
 ("8","2","JUST / DRIVE","BY / DRIVER",""),
]

T.append(Table(
    table_id="Table 2L-4", page_pdf=559, page_printed="559",
    title="Examples of Message Construction for Portable CMS*",
    crop_file="table_2L-4_p0559.png", kind="text",
    column_labels=["Example", "Phase", "Potential Message", "Improved Message", "Comments"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=e, number=float(e), unit="example"),
           V(text=p, number=float(p), unit="phase"),
           _msg(pot), _msg(imp), V(text=com)] for e, p, pot, imp, com in _2L4],
    footnotes=[Footnote(marker="*", text="Examples shown are for a portable CMS where the "
        "display width is generally limited to 8 characters per line of legend.")],
))
