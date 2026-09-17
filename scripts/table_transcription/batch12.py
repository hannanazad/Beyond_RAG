"""Emergency management and recreational symbol tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V
from batch2 import sz

SRC = "vlm transcription from a PDF render, unverified"
T = []

def _sz(text):
    v = sz(text.rstrip("*"))
    if text.endswith("*"):
        v.text = text
        v.footnotes = ["*"]
    return v

T.append(Table(
    table_id="Table 2N-1", page_pdf=573, page_printed="573",
    title="Emergency Management Sign Sizes",
    crop_file="table_2N-1_p0573.png", kind="numeric",
    column_labels=["Sign or Plaque", "Sign Designation", "Section", "Minimum Size"],
    row_key_columns=[0, 1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=a), V(text=b), V(text=c), _sz(d)] for a, b, c, d in [
        ("Evacuation Route","EM1-1, EM1-1a, EM1-2","2N.03","24 x 24*"),
        ("Area Closed","EM2-1","2N.04","30 x 24"),
        ("Traffic Control Point","EM2-2","2N.05","30 x 24"),
        ("Maintain Top Safe Speed","EM2-3","2N.06","24 x 30"),
        ("Permit Required","EM2-4","2N.07","24 x 30"),
        ("Emergency Aid Center","EM3-1, EM3-1a, EM3-1b, EM3-1c","2N.08","30 x 24"),
        ("Shelter Directional","EM4-1, EM4-1a, EM4-1b, EM4-1c","2N.09","30 x 24"),
    ]],
    footnotes=[
        Footnote(marker="*", text="A minimum size of 18 x 18 may be used on low-volume roadways "
                                  "or roadways with speeds of 25 mph or less", applies_to="cell"),
        Footnote(marker="Note 1", text="Larger signs may be used when appropriate"),
        Footnote(marker="Note 2", text="Dimensions are shown as width x height, in inches"),
    ],
))

# 2M-1 is printed as six separate boxed lists on one page. They are one
# logical table keyed by symbol name, with the box heading as the category.
# The "*" governs the SYMBOL, restricting where it may be used at all.
_2M1 = [
 ("General", [("Bear Viewing Area","RS-012"),("Bus Stop *","RS-031"),("Campfires *","RS-042"),
  ("Deer Viewing Area","RS-011"),("Fire Extinguisher *","RS-090"),("Lighthouse","RS-007"),
  ("Lookout Tower","RS-006"),("Nature Study Area","RS-141"),("Pick-Up Trucks *","RS-140"),
  ("Recycling *","RS-200"),("Sea Plane","RS-115"),("Smoking*","RS-002"),("Tunnel *","RS-005"),
  ("Viewing Area","RS-036")]),
 ("Accommodations", [("Men's Restroom *","RS-021"),("Parking","RS-034"),
  ("Recreational Vehicle Site *","RS-104"),("Restrooms *","RS-022"),
  ("Sleeping Shelter","RS-037"),("Trailer Site *","RS-040"),("Women's Restroom *","RS-023")]),
 ("Services", [("Electrical Hook-Up *","RS-150"),("First Aid *","RS-024"),
  ("Laundromat *","RS-085"),("Picnic Shelter","RS-039"),("Picnic Site","RS-044"),
  ("Post Office *","RS-026"),("Showers *","RS-035"),("Tramway","RS-071"),
  ("Trash Dumpster *","RS-091")]),
 ("Land Recreation", [("All-Terrain Trail","RS-095"),("Archery","RS-116"),("Baseball","RS-096"),
  ("Climbing","RS-082"),("Golfing","RS-128"),("Hiking Trail","RS-068"),("Horse Trail","RS-064"),
  ("In-Line Skating *","RS-125"),("Skateboarding *","RS-098"),("Spelunking/Caves *","RS-084"),
  ("Technical Rock Climbing *","RS-081"),("Tennis","RS-129"),("Wildlife Viewing","RS-076")]),
 ("Water Recreation", [("Beach","RS-145"),("Boat Ramp","RS-054"),("Canoeing","RS-079"),
  ("Fishing Area","RS-063"),("Hand Launch/Small Boat Launch *","RS-117"),
  ("Jet Ski/Personal Watercraft","RS-121"),("Marina *","RS-053"),("Motorboating","RS-055"),
  ("Scuba Diving","RS-060"),("Seal Viewing","RS-106"),("Swimming","RS-061"),
  ("Waterskiing","RS-058"),("Whale Viewing","RS-107")]),
 ("Winter Recreation", [("Chair Lift/Ski Lift","RS-105"),("Cross Country Skiing","RS-046"),
  ("Dog Sledding","RS-143"),("Sledding","RS-049"),("Snow Tubing","RS-144"),
  ("Snowshoeing","RS-078"),("Winter Recreational Area","RS-077")]),
]

T.append(Table(
    table_id="Table 2M-1", page_pdf=562, page_printed="562",
    title="Category Chart for Recreational and Cultural Interest Area Symbols",
    crop_file="table_2M-1_p0562.png", kind="text",
    column_labels=["Category", "Symbol", "Sign Designation"],
    row_key_columns=[1], source=SRC, note_chunk_ids=[],
    rows=[[V(text=cat),
           V(text=name.rstrip(" *"), footnotes=["*"] if name.rstrip().endswith("*") else []),
           V(text=code)]
          for cat, items in _2M1 for name, code in items],
    footnotes=[Footnote(marker="*", text="For use only within recreational and cultural interest "
                                         "areas where speed limits are 25 mph or less.",
                        applies_to="cell")],
))
