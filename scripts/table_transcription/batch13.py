"""Changeable message sign and automation tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

# 2L-1's cells are RANGES printed with a hyphen and vulgar fractions:
# "4 ½ - 7" is 4.5 to 7 inches, not a single value.
def _rng(text):
    t = text.replace("\u00bd", ".5").replace(" .5", ".5")
    lo, hi = [float(x.strip()) for x in t.split("-")]
    return V(text=text, minimum=lo, maximum=hi, unit="in")

T.append(Table(
    table_id="Table 2L-1", page_pdf=554, page_printed="554",
    title="Spacing between Message Characters, Words, and Lines of Text",
    crop_file="table_2L-1_p0554.png", kind="numeric",
    column_labels=["Height of Letters Used on CMS",
                   "Spacing between Characters in Words",
                   "Horizontal Spacing between Words",
                   "Vertical Spacing between Lines of Text"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text="12", number=12, unit="in"), _rng("3 - 5"), _rng("9 - 12"), _rng("6 - 9")],
          [V(text="18", number=18, unit="in"), _rng("4 \u00bd - 7"),
           _rng("13 \u00bd - 18"), _rng("9 - 13 \u00bd")]],
    footnotes=[Footnote(marker="Note", text="All units are in inches")],
))

T.append(Table(
    table_id="Table 2L-2", page_pdf=556, page_printed="556",
    title="Example of Units of Information",
    crop_file="table_2L-2_p0556.png", kind="mixed",
    column_labels=["Question", "Answer", "Number of Information Units"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=q), V(text=a), V(text="1", number=1, unit="units")]
          for q, a in [
        ("What happened?", "MAJOR CRASH"),
        ("Where?", "AT EXIT 12"),
        ("Who is the advisory for?", "Drivers heading TO NEW YORK"),
        ("What is advised?", "USE ROUTE 46"),
    ]],
    footnotes=[Footnote(marker="Note", text="The following is an example of a two-phase message "
        "that could be developed from the four information units shown in this table: "
        "Phase 1 \u2014 MAJOR CRASH AT EXIT 12; Phase 2 \u2014 USE ROUTE 46 TO NEW YORK")],
))

T.append(Table(
    table_id="Table 5A-1", page_pdf=801, page_printed="801",
    title="Automation Levels",
    crop_file="table_5A-1_p0801.png", kind="text",
    column_labels=["Automation Level", "Description", "Automation Category",
                   "Automation Type"],
    row_key_columns=[0], source=SRC, note_chunk_ids=[],
    rows=[[V(text=lvl), V(text=desc),
           V(text=cat.rstrip("*"), footnotes=["*"] if cat.endswith("*") else []),
           V(text=typ)] for lvl, desc, cat, typ in [
        ("Level 0", "The full-time performance by the human driver of all aspects of the "
         "Dynamic Driving Task, even when enhanced by warning or momentary intervention "
         "systems.", "None*", "None"),
        ("Level 1", "The driving mode specific execution by a sustained driver assistance "
         "system of either steering or acceleration/deceleration using information about the "
         "driving environment and with the expectation that the human driver performs all "
         "remaining aspects of the Dynamic Driving Task.",
         "Advanced Driver Assistance Systems (ADAS)", "Driving Automation System"),
        ("Level 2", "The driving mode specific execution by one or more sustained driver "
         "assistance systems of both steering and acceleration/deceleration using information "
         "about the driving environment and with the expectation that the human driver performs "
         "all remaining aspects of the Dynamic Driving Task.",
         "Advanced Driver Assistance Systems (ADAS)", "Driving Automation System"),
        ("Level 3", "The driving mode specific sustained performance by an ADS of all aspects "
         "of the Dynamic Driving Task within a given ODD with the expectation that the human "
         "driver will respond appropriately to a request to intervene.",
         "Automated Driving System (ADS)", "Driving Automation System"),
        ("Level 4", "The driving mode specific sustained performance by an ADS of all aspects "
         "of the Dynamic Driving Task, even if a human driver does not respond appropriately "
         "to a request to intervene.",
         "Automated Driving System (ADS)", "Driving Automation System"),
        ("Level 5", "The full-time sustained performance by an ADS of all aspects of the "
         "Dynamic Driving Task under all roadway and environmental conditions that can be "
         "managed by a human driver.",
         "Automated Driving System (ADS)", "Driving Automation System"),
    ]],
    footnotes=[Footnote(marker="*", text="Level 0 might include some ADAS features, but they are "
        "considered to be warning or momentary intervention systems at this level.",
        applies_to="cell")],
))
