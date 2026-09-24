"""Markings, signal-face and TTC guide-sign tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch2 import sz
from batch8 import ft, mph

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

T.append(Table(
    table_id="Table 3B-1", page_pdf=584, page_printed="584",
    title="Minimum Passing Sight Distances for No-Passing Zone Markings",
    crop_file="table_3B-1_p0584.png", kind="numeric",
    column_labels=["85th-Percentile or Speed Limit", "Minimum Passing Sight Distance"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[mph(s), ft(d)] for s, d in [
        ("25 mph","450 feet"),("30 mph","500 feet"),("35 mph","550 feet"),
        ("40 mph","600 feet"),("45 mph","700 feet"),("50 mph","800 feet"),
        ("55 mph","900 feet"),("60 mph","1,000 feet"),("65 mph","1,100 feet"),
        ("70 mph","1,200 feet"),
    ]],
))

# The title carries the scope: these counts apply ONLY where the speed is
# 45 mph or higher. Without it a lookup returns face counts for a road the
# table never covered.
T.append(Table(
    table_id="Table 4D-1", page_pdf=710, page_printed="710",
    title="Recommended Minimum Number of Primary Signal Faces for Through Traffic "
          "on Approaches with Posted, Statutory, or 85th-Percentile Speed of "
          "45 mph or Higher",
    crop_file="table_4D-1_p0710.png", kind="numeric",
    column_labels=["Number of Through Lanes on the Approach",
                   "Total Number of Primary Through Signal Faces for the Approach*",
                   "Minimum Number of Overhead-Mounted Primary Through Signal Faces "
                   "for the Approach"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[
        [V(text="1", number=1, unit="lanes"), V(text="2", number=2, unit="faces"),
         V(text="1", number=1, unit="faces")],
        [V(text="2", number=2, unit="lanes"), V(text="2", number=2, unit="faces"),
         V(text="1", number=1, unit="faces")],
        [V(text="3", number=3, unit="lanes"), V(text="3", number=3, unit="faces"),
         V(text="2", number=2, unit="faces", footnotes=["**"])],
        [V(text="4 or more", minimum=4, unit="lanes"),
         V(text="4 or more", minimum=4, unit="faces"),
         V(text="3", number=3, unit="faces", footnotes=["**"])],
    ],
    footnotes=[
        Footnote(marker="*", text="A minimum of two through signal faces is always required "
            "(see Section 4D.05). These recommended numbers of through signal faces may be "
            "exceeded. Also, see cone of vision requirements otherwise indicated in Section "
            "4D.07.", applies_to="column:1"),
        Footnote(marker="**", text="If practical, all of the recommended number of primary "
            "through signal faces should be located overhead.", applies_to="cell"),
        Footnote(marker="scope", text="Applies to approaches with a posted, statutory, or "
            "85th-percentile speed of 45 mph or higher."),
    ],
))

T.append(Table(
    table_id="Table 4D-2", page_pdf=711, page_printed="711",
    title="Minimum Sight Distance for Signal Visibility",
    crop_file="table_4D-2_p0711.png", kind="numeric",
    column_labels=["85th-Percentile Speed", "Minimum Sight Distance"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[mph(s), ft(d)] for s, d in [
        ("20 mph","175 feet"),("25 mph","215 feet"),("30 mph","270 feet"),
        ("35 mph","325 feet"),("40 mph","390 feet"),("45 mph","460 feet"),
        ("50 mph","540 feet"),("55 mph","625 feet"),("60 mph","715 feet"),
    ]],
    footnotes=[Footnote(marker="Note", text="Distances in this table are derived from stopping "
        "sight distance plus an assumed queue length for shorter cycle lengths "
        "(60 to 75 seconds).")],
))

T.append(Table(
    table_id="Table 6I-1", page_pdf=852, page_printed="852",
    title="Temporary Traffic Control Zone Guide Sign and Plaque Sizes",
    crop_file="table_6I-1_p0852.png", kind="numeric",
    column_labels=["Sign or Plaque", "Sign Designation", "Section",
                   "Conventional Road", "Freeway or Expressway", "Minimum"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=r[0]), V(text=r[1]), V(text=r[2])] + [sz(x) for x in r[3:]]
          for r in [
        ("Exit Open","E5-2","6H.12","48 x 36","48 x 36","—"),
        ("Exit Closed","E5-2a","6H.12","48 x 36","48 x 36","—"),
        ("Exit Only","E5-3","6H.13","48 x 36","48 x 36","—"),
        ("Detour","M4-8P","6I.02","24 x 12","30 x 15","—"),
        ("End Detour","M4-8a","6I.02","24 x 18","24 x 18","—"),
        ("End (plaque)","M4-8bP","6I.02","24 x 12","24 x 12","—"),
        ("Detour","M4-9","6I.02","30 x 24","48 x 36","—"),
        ("Bike/Pedestrian Detour","M4-9a","6I.02","30 x 24","—","—"),
        ("Pedestrian Detour","M4-9b","6I.02","30 x 24","—","—"),
        ("Bike Detour (with arrow)","M4-9c","6I.02","30 x 24","—","—"),
        ("Detour","M4-10","6I.02","48 x 18","—","—"),
    ]],
    footnotes=[
        Footnote(marker="Note 1", text="Larger signs may be used wherever necessary for greater "
                                       "legibility or emphasis"),
        Footnote(marker="Note 2", text="Dimensions are shown in inches and are shown as "
                                       "width x height"),
    ],
))
