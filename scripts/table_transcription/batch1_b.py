import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mrag.vine.table_data import Footnote, Table, Value as V

SRC = "transcribed from a PDF render; checked against the source by the project author"
T = []

_1d2_s1 = [
    ("Access", "ACCS", "—", "Road", "ACCS ROAD"),
    ("Ahead", "AHD", "Fog", "—", "FOG AHD"),
    ("Blocked", "BLKD", "Lane", "—", "2 LANES BLKD"),
    ("Bridge", "BR*", "[Name]", "—", "BAY BR"),
    ("Cannot", "CANT", "—", "—", "—"),
    ("Center", "CNTR", "—", "Lane", "CNTR LANE, CNTR LN"),
    ("Chemical", "CHEM", "—", "Spill", "CHEM SPILL"),
    ("Condition", "COND", "Traffic", "—", "TRAFFIC COND"),
    ("Congested", "CONG", "Traffic", "—", "TRAFFIC CONG AHD"),
    ("Construction", "CONST", "—", "Ahead", "CONST AHEAD"),
    ("Crossing", "XING", "—", "—", "PED XING"),
    ("Do Not", "DONT", "—", "—", "—"),
    ("Downtown", "DWNTN", "—", "Traffic", "DWNTN TRAFFIC"),
    ("Eastbound", "EAST", "Route Number, Road Name", "—", "I-4 EAST"),
    ("Eastbound", "E-BND", "—", "Lane, Traffic", "E-BND LANE"),
    ("Emergency", "EMER", "—", "—", "EMER VEHICLES"),
    ("Entrance, Enter", "ENT", "—", "—", "ENT TO I-90"),
    ("Exit", "EX", "Next", "—", "NEXT EX"),
    ("Express", "EXP", "—", "Lane", "EXP LANE OPEN"),
    ("Frontage", "FRNTG", "—", "Road", "FRNTG RD"),
    ("Hazardous", "HAZ", "—", "Driving", "HAZ DRIVING"),
    ("Highway-Rail Grade Crossing", "RR XING", "—", "—", "RR XING"),
    ("Interstate", "I-*", "—", "[Number]", "I-80"),
    ("It Is", "ITS", "—", "—", "—"),
    ("Lane(s) (travel lanes of a highway)", "LN, LNS", "Right, Left, Center", "—",
     "LEFT LN ONLY; 2 RIGHT LNS"),
    ("Left", "LFT", "Keep, Next", "—", "NEXT LFT"),
    ("Left", "LFT", "—", "Lane", "LFT LANE"),
    ("Local", "LOC", "—", "Traffic", "LOC TRAFFIC ONLY"),
    ("Lower", "LWR", "—", "Level", "LWR LEVEL"),
    ("Maintenance", "MAINT", "—", "—", "ROAD MAINT"),
    ("Major", "MAJ", "—", "Crash", "MAJ CRASH"),
    ("Minor", "MNR", "—", "Crash", "MNR CRASH"),
    ("Normal", "NORM", "—", "—", "—"),
    ("Northbound", "NORTH", "Route Number, Road Name", "—", "US 1 NORTH"),
    ("Northbound", "N-BND", "—", "Lane, Traffic", "N-BND TRAFFIC"),
    ("Oversized", "OVRSZ", "—", "Load", "OVRSZ LOAD"),
    ("Parking", "PKING", "—", "—", "—"),
    ("Pavement", "PVMT", "Icy", "—", "ICY PVMT"),
    ("Prepare", "PREP", "—", "To Stop", "PREP TO STOP"),
    ("Quality", "QLTY", "Air", "—", "AIR QLTY"),
    ("Right", "RT", "Keep, Next", "—", "KEEP RT"),
    ("Right", "RT", "—", "Lane", "RT LANE"),
    ("Road Work", "RD WK", "—", "Ahead, [Distance]", "RD WK 1 MILE"),
    ("Route", "RTE", "Best", "—", "BEST RTE"),
    ("Service", "SERV", "—", "—", "SERV AREA OPEN"),
    ("Shoulder", "SHLDR", "—", "—", "SHLDR CLOSED"),
]

def _dash(t):
    return V(text="—", missing="none") if t == "—" else V(text=t)

T.append(Table(
    table_id="Table 1D-2", sheet=1, sheet_of=2, page_pdf=77, page_printed="77",
    title="Abbreviations that Shall be Used Only for Temporary Messages on "
          "Portable Changeable Message Signs",
    crop_file="table_1D-2_s1_p0077.png", kind="text",
    column_labels=["Word Message", "Standard Abbreviation",
                   "Prompt Word Preceding the Abbreviation",
                   "Prompt Word Following the Abbreviation", "Example"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_1D-2_01"],
    rows=[[_dash(a), _dash(b), _dash(c), _dash(d), _dash(e)] for a, b, c, d, e in _1d2_s1],
))

_1d2_s2 = [
    ("Slippery", "SLIP", "—", "—", "—"),
    ("Southbound", "SOUTH", "Route Number, Road Name", "—", "CA 1 SOUTH"),
    ("Southbound", "S-BND", "—", "Lane, Traffic", "S-BND TRAFFIC"),
    ("Speed", "SPD", "—", "—", "SPD LIMIT"),
    ("State, County, or other non-U.S. or non-Interstate numbered route",
     "[Route Abbreviation determined by highway agency]*", "—", "[Number]**", "NY 7, CR 43"),
    ("Tires With Lugs", "LUGS", "—", "—", "—"),
    ("Traffic", "TRAF", "—", "—", "—"),
    ("Travelers", "TRVLRS", "—", "—", "—"),
    ("Two-Wheeled Vehicles", "CYCLES", "—", "—", "—"),
    ("Upper", "UPR", "—", "Level", "UPR LEVEL"),
    ("U.S. Numbered Route", "US*", "—", "[Number]**", "US 202"),
    ("Vehicle(s)", "VEH, VEHS", "—", "—", "—"),
    ("Warning", "WARN", "—", "—", "—"),
    ("Westbound", "WEST", "Route Number, Road Name", "—", "IL 53 WEST"),
    ("Westbound", "W-BND", "—", "Lane, Traffic", "W-BND LANES"),
    ("Will Not", "WONT", "—", "—", "—"),
]

def _mk(t):
    v = _dash(t)
    if t.endswith("**"): v.footnotes = ["**"]
    elif t.endswith("*"): v.footnotes = ["*"]
    return v

T.append(Table(
    table_id="Table 1D-2", sheet=2, sheet_of=2, page_pdf=78, page_printed="78",
    title="Abbreviations that Shall be Used Only for Temporary Messages on "
          "Portable Changeable Message Signs",
    crop_file="table_1D-2_s2_p0078.png", kind="text",
    column_labels=["Word Message", "Standard Abbreviation",
                   "Prompt Word Preceding the Abbreviation",
                   "Prompt Word Following the Abbreviation", "Example"],
    row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_1D-2_01"],
    rows=[[_mk(a), _mk(b), _mk(c), _mk(d), _mk(e)] for a, b, c, d, e in _1d2_s2],
    footnotes=[
        Footnote(marker="*", text="Abbreviation, when accompanied by the prompt word, may be "
                                  "used on traffic control devices other than portable message "
                                  "signs. See Table 1D-1 for uses and format."),
        Footnote(marker="**", text="A space and no hyphen shall be placed between the "
                                   "abbreviation and the number of the route."),
        Footnote(marker="Note", text="See Chapter 2L of this Manual for additional information "
                                     "on changeable message signs."),
    ],
))

# ---- Table 2A-2: an X-matrix of legend colour x background colour ---------
_2A2_COLS = (["Type of Sign"]
             + [f"Legend — {c}" for c in
                ["Black", "Green", "Red", "White", "Yellow", "Orange",
                 "Fluorescent Yellow-Green", "Fluorescent Pink"]]
             + [f"Background — {c}" for c in
                ["Black", "Blue", "Brown", "Green", "Orange", "Red", "White",
                 "Yellow", "Purple", "Fluorescent Yellow-Green", "Fluorescent Pink"]])

# each entry: (row label, {col index: mark})   mark is "X" or "X<footnote>"
_2A2_ROWS = [
    ("Regulatory",                 {1: "X", 3: "X", 4: "X", 9: "X", 15: "X", 16: "X"}),
    ("Prohibitive",                {3: "X", 4: "X2", 15: "X2", 16: "X"}),
    ("Permissive",                 {2: "X", 16: "X"}),
    ("Warning",                    {1: "X", 17: "X"}),
    ("Pedestrian",                 {1: "X", 17: "X", 19: "X"}),
    ("Bicycle",                    {1: "X", 17: "X", 19: "X"}),
    ("Guide",                      {4: "X", 12: "X"}),
    ("Interstate Route",           {4: "X", 10: "X", 15: "X"}),
    ("State Route",                {1: "X", 16: "X"}),
    ("U.S. Route",                 {1: "X", 16: "X"}),
    ("County Route",               {5: "X", 10: "X"}),
    ("Forest Route",               {4: "X", 11: "X"}),
    ("Street Name",                {4: "X", 12: "X"}),
    ("Destination",                {4: "X", 12: "X"}),
    ("Reference Location",         {4: "X", 12: "X"}),
    ("Information",                {4: "X", 10: "X", 12: "X"}),
    ("Evacuation Route",           {4: "X", 10: "X"}),
    ("Road User Service",          {4: "X", 10: "X"}),
    ("Recreational",               {4: "X", 11: "X", 12: "X"}),
    ("Temporary Traffic Control",  {1: "X", 13: "X"}),
    ("Incident Management",        {1: "X", 13: "X", 19: "X"}),
    ("School",                     {1: "X", 18: "X"}),
    ("ETC-Account Only",           {1: "X", 17: "X5"}),
    ("Changeable Message Signs",   {}),
    ("Changeable Message Signs — Regulatory",                {3: "X4", 4: "X", 9: "X"}),
    ("Changeable Message Signs — Warning",                   {5: "X", 9: "X"}),
    ("Changeable Message Signs — Temporary Traffic Control", {5: "X", 6: "X", 9: "X"}),
    ("Changeable Message Signs — Guide",                     {4: "X", 9: "X", 12: "X3"}),
    ("Changeable Message Signs — Motorist Services",         {4: "X", 9: "X", 10: "X3"}),
    ("Changeable Message Signs — Incident Management",       {5: "X", 8: "X", 9: "X"}),
    ("Changeable Message Signs — School, Pedestrian, Bicycle", {5: "X", 7: "X", 9: "X"}),
]

def _x(mark):
    if not mark:
        return V(text="", missing="blank")
    v = V(text="X")
    if len(mark) > 1:
        v.footnotes = [mark[1:]]
    return v

T.append(Table(
    table_id="Table 2A-2", page_pdf=85, page_printed="85",
    title="Common Uses of Sign Colors",
    crop_file="table_2A-2_p0085.png", kind="text",
    column_labels=_2A2_COLS, row_key_columns=[0], source=SRC,
    note_chunk_ids=["MUTCD11e_TBLNOTE_2A-2_01", "MUTCD11e_TBLNOTE_2A-2_02",
                    "MUTCD11e_TBLNOTE_2A-2_03", "MUTCD11e_TBLNOTE_2A-2_04",
                    "MUTCD11e_TBLNOTE_2A-2_05", "MUTCD11e_TBLNOTE_2A-2_06"],
    rows=[[V(text=label)] + [_x(marks.get(i)) for i in range(1, len(_2A2_COLS))]
          for label, marks in _2A2_ROWS],
    footnotes=[
        Footnote(marker="1", text="Fluorescent versions of these background colors may also be used."),
        Footnote(marker="2", text="Legend and background color combination for use only as "
                                  "identified for specific signs in this Manual or Standard "
                                  "Highway Signs."),
        Footnote(marker="3", text="These alternative background colors would be provided by blue "
                                  "or green lighted pixels such that the entire CMS would be "
                                  "lighted, not just the legend."),
        Footnote(marker="4", text="Red is used only for the circle and diagonal or other red "
                                  "elements of a similar static regulatory sign."),
        Footnote(marker="5", text="The use of purple on signs is restricted per the provisions "
                                  "of Chapter 2F."),
        Footnote(marker="Note 1", text="The purpose of the information in this table is to provide "
                                       "a general overview of common color combinations. The color "
                                       "combinations and orientations for signs with standardized "
                                       "designs shall not be modified. For signs with unique legends, "
                                       "the shape and color shall be the same as standard signs of "
                                       "the same functional type."),
        Footnote(marker="Note 2", text="The colors shown for changeable message signs are for those "
                                       "with electronic displays."),
    ],
))
