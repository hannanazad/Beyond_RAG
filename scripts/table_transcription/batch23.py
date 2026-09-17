"""Table 1D-1 — Acceptable Abbreviations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "vlm transcription from a PDF render, unverified"
T = []

# "(See Table 1D-2)" is not an abbreviation: it routes to a different table
# for that word. Recorded as not_applicable so a verifier cannot use it as
# the abbreviation itself.
def _abbr(text):
    if text.startswith("(See"):
        return V(text=text, missing="not_applicable")
    marks = []
    for m in ("***", "**", "*"):
        if text.endswith(m):
            marks = [m]
            break
    return V(text=text, footnotes=marks)

_GEN = [
 ("Afternoon / Evening","PM"),("Alternate","ALT"),("AM Radio","AM"),("Avenue","Ave*"),
 ("Bicycle(s)","BIKE, BIKES"),("Boulevard","Blvd*"),("Bridge","(See Table 1D-2)"),
 ("CB Radio","CB"),("Center","Ctr**"),("Circle","Cir*"),("Civil Defense","CD"),
 ("Compressed Natural Gas","CNG"),("Court","Ct*"),
 ("Crossing (other than highway-rail)","X-ING"),("Drive","Dr*"),("East","E"),
 ("Electric Vehicle","EV"),("Expressway","Expwy*"),("Feet","FT"),("FM Radio","FM"),
 ("Freeway","Fwy*"),("Hazardous Material(s)","HAZMAT, HAZMATS"),
 ("High Occupancy Vehicle(s)","HOV"),("Highway","Hwy*"),("Hospital","HOSP"),
 ("Hour(s)","HR, HRS"),("Information","INFO"),
 ("Inherently Low Emission Vehicle","ILEV"),("International","Intl"),
 ("Interstate","(See Table 1D-2)"),("Junction / Intersection","JCT"),
 ("Lane","(See Table 1D-2)"),("Liquified Petroleum Gas","LP-GAS"),("Maximum","MAX"),
 ("Mile(s)","MI"),("Miles per Hour","MPH"),("Minimum","MIN"),
 ("Minute(s)","MIN, MINS"),("Morning / Late Night","AM"),("Mount","Mt**"),
 ("Mountain","Mtn**"),("National","Natl**"),("North","N"),("Northeast","NE"),
 ("Northwest","NW"),("Parkway","Pkwy*"),("Pedestrian(s)","PED, PEDS"),("Place","Pl*"),
 ("Pounds","LBS"),("Road","Rd*"),("Saint","St**"),("South","S"),("Southeast","SE"),
 ("Southwest","SW"),
 ("State, county, or other non-US or non-Interstate numbered route","(See Table 1D-2)"),
 ("Street","St*"),("Telephone","PHONE"),("Temporary","TEMP"),("Terrace","Ter*"),
 ("Thruway","Thwy*"),("Ton(s)","T"),("Trail","Tr*"),("Turnpike","Tpk*"),
 ("Two-Way Intersection, Two-Way Traffic","2-WAY"),
 ("US Numbered Route","(See Table 1D-2)"),("West","W"),
]
_DAYS = [("Sunday","SUN"),("Monday","MON"),("Tuesday","TUES***"),("Wednesday","WED"),
         ("Thursday","THURS***"),("Friday","FRI"),("Saturday","SAT")]

_1D1_NOTES = [
    Footnote(marker="*", text="Abbreviation shall not be used for any application other than "
        "the name of a roadway. See Table 2D-3 for complete list of street name descriptors. "
        "Examples include: Bayshore Fwy, Cross County Hwy, Mid-County Pkwy", applies_to="cell"),
    Footnote(marker="**", text="Abbreviation shall not be used for any application other than "
        "as a descriptor or title within a proper name. Examples include: Vestal Ctr, Mt Hope, "
        "Pocono Mtn, Eldorado Natl Forest, St Louis", applies_to="cell"),
    Footnote(marker="***", text="Tuesday and Thursday may be abbreviated on a Changeable "
        "Message Sign (CMS) to TUE and THU, respectively, when the number of Characters in a "
        "message to be displayed cannot be practically reduced through rewording to fit the "
        "number of characters supported by the CMS, such as might occur at times on a portable "
        "CMS.", applies_to="cell"),
    Footnote(marker="Note", text="Abbreviations shown in upper- and lower-case lettering may be "
        "in all upper-case lettering when displayed on a changeable message sign with lower "
        "resolution that will not accommodate lower-case letter forms. See Chapter 2L of this "
        "Manual."),
]

T.append(Table(
    table_id="Table 1D-1", page_pdf=76, page_printed="76",
    title="Acceptable Abbreviations",
    crop_file="table_1D-1_p0076.png", kind="text",
    column_labels=["Group", "Word Message", "Standard Abbreviation"],
    row_key_columns=[1], source=SRC, note_chunk_ids=[],
    rows=[[V(text="General Abbreviations"), V(text=w), _abbr(a)] for w, a in _GEN]
         + [[V(text="Days of the Week"), V(text=w), _abbr(a)] for w, a in _DAYS],
    footnotes=list(_1D1_NOTES),
))
