"""Toll road and specific-service sign tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Quantity as Q, Table, Value as V
from batch2 import sz
from batch5 import _lh

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

# 2F-1 prints "312* x 30": the asterisk sits on the WIDTH, not on the cell,
# and its note says that width is a MINIMUM to be increased to match the guide
# sign. Treating it as a fixed 312 would under-build the sign.
def _tollsz(text):
    if text == "—":
        return V(text="—", missing="none")
    if "*" not in text:
        return sz(text)
    w, h = [p.strip() for p in text.split("x")]
    wv = float(w.rstrip("*"))
    return V(text=text, footnotes=["*"],
             quantities=[Q(name="width", value=wv, unit="in", comparator=">="),
                         Q(name="height", value=float(h), unit="in")])

_2F1 = [
 ("Toll Rate","R3-28","2F.04","—","—","114 x 48","114 x 48","—","—"),
 ("Pay Toll (plaque)","R3-29P","2F.04","—","—","24 x 18","24 x 18","—","—"),
 ("Take Ticket (plaque)","R3-30P","2F.04","—","—","24 x 18","24 x 18","—","—"),
 ("ETC Account-Only","R3-31","2F.05","24 x 24","24 x 24","36 x 36","36 x 36","24 x 24","36 x 36"),
 ("No Cash (plaque)","R3-32P","2F.05","24 x 12","24 x 12","36 x 18","36 x 18","24 x 12","36 x 18"),
 ("Pay Toll XX Miles Cars (price)","W9-6","2F.06","96 x 66","96 x 66","96 x 66","96 x 66","—","—"),
 ("Stop Ahead Pay Toll Cars (price)","W9-6a","2F.08","114 x 66","114 x 66","114 x 66","114 x 66","—","—"),
 ("Pay Toll XX Miles Cars (price) (plaque)","W9-6bP","2F.07","312* x 30","312* x 30","312* x 30","312* x 30","—","—"),
 ("Stop Ahead Pay Toll (plaque)","W9-6cP","2F.09","264* x 30","264* x 30","264* x 30","264* x 30","—","—"),
 ("Stop Ahead Pay Toll (plaque)","W9-6dP","2F.09","114 x 48","114 x 48","114 x 48","114 x 48","—","—"),
 ("Take Ticket XX Miles","W9-6e","2F.06","114 x 48","114 x 48","114 x 48","114 x 48","—","—"),
 ("Stop Ahead Take Ticket","W9-6f","2F.08","114 x 48","114 x 48","114 x 48","114 x 48","—","—"),
 ("Take Ticket XX Miles (plaque)","W9-6gP","2F.07","216 x 30","216 x 30","216 x 30","216 x 30","—","—"),
 ("Stop Ahead Take Ticket (plaque)","W9-6hP","2F.09","282 x 30","282 x 30","282 x 30","282 x 30","—","—"),
 ("Last Exit Before Toll (1-line) (plaque)","W16-16P","2F.10","—","—","252* x 36","252* x 36","—","—"),
 ("Last Exit Before Toll (2-line) (plaque)","W16-16aP","2F.10","—","—","144 x 54","144 x 54","—","—"),
 ("Toll (plaque)","W16-17P","2F.11","24 x 12","24 x 12","36 x 18","36 x 18","24 x 12","36 x 18"),
 ("Toll Collector Symbol Panel","M4-17","2F.12","—","—","48 x 48","48 x 48","—","—"),
 ("Exact Change Symbol Panel","M4-18","2F.12","—","—","48 x 48","48 x 48","—","—"),
]

T.append(Table(
    table_id="Table 2F-1", page_pdf=422, page_printed="422",
    title="Toll Road Sign and Plaque Minimum Sizes",
    crop_file="table_2F-1_p0422.png", kind="numeric",
    column_labels=["Sign or Plaque", "Sign Designation", "Section",
                   "Conventional Road — Single Lane", "Conventional Road — Multi-Lane",
                   "Expressway", "Freeway", "Minimum", "Oversized"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [_tollsz(x) for x in r[3:]]
          for r in _2F1],
    footnotes=[
        Footnote(marker="*", text="The width shown represents the minimum dimension. The width "
                                  "shall be increased as appropriate to match the width of the "
                                  "guide sign.", applies_to="cell"),
        Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
        Footnote(marker="Note 2", text="Dimensions are shown as width x height, in inches"),
    ],
))

T.append(Table(
    table_id="Table 2J-1", page_pdf=539, page_printed="539",
    title="Minimum Letter and Numeral Sizes for Specific Service Signs "
          "According to Sign Type",
    crop_file="table_2J-1_p0539.png", kind="numeric",
    column_labels=["Group", "Type of Sign", "Freeway or Expressway",
                   "Conventional Road or Ramp"],
    row_key_columns=[1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=g), V(text=n), _lh(a), _lh(b)] for g, n, a, b in [
        ("A. Specific Service Signs","Service Categories","10","6"),
        ("A. Specific Service Signs","Exit Number Words","10","—"),
        ("A. Specific Service Signs","Exit Number Numerals and Letters","10","—"),
        ("A. Specific Service Signs","Action Message Words","10","6"),
        ("A. Specific Service Signs","Distance Numerals","—","6"),
        ("A. Specific Service Signs","Distance Fraction Numerals","—","4"),
        ("B. Business Identification Sign Panels",
         "Words and Numerals (Non-Trademark/Graphic Logo)","8","4"),
        ("B. Business Identification Sign Panels","Supplemental Message Words and Numerals",
         "5","2.5"),
    ]] + [[V(text="B. Business Identification Sign Panels"),
           V(text="Trademark/Graphic Logo"),
           # "Proportional" is a rule, not a size: no fixed height is given
           V(text="Proportional", missing="not_applicable"),
           V(text="Proportional", missing="not_applicable")]],
    footnotes=[Footnote(marker="Note", text="Sizes are shown in inches")],
))

T.append(Table(
    table_id="Table 2J-2", page_pdf=540, page_printed="540",
    title="Maximum Business Identification Sign Panel Sizes by Roadway Classification",
    crop_file="table_2J-2_p0540.png", kind="numeric",
    column_labels=["Roadway Classification", "Sign Panel Size"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text="Freeway or Expressway"), sz("60 x 36")],
          [V(text="Conventional Road or Ramp"), sz("30 x 18")]],
    footnotes=[Footnote(marker="Note", text="Sizes are shown in inches as width x height")],
))
