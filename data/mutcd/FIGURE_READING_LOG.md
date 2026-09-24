# MUTCD 11th Edition — figure reading log

## Method (engineer's instruction, 22 September 2026)

Read the manual **as a person sees it**: each page rendered as an image and looked at.
No text extraction, no chunk files, no table files, no splitting of the raw material.
The figures were the gap left by the first pass, which read tables from images but
figures from the text layer only.

For every figure: caption, every panel, every dimension and callout drawn on the
artwork, colours and backgrounds, the notes, and anything the text layer cannot show
(schedules drawn inside figures, artwork legends, sign faces).

Same flag types as the reading log: DATA (our material differs from the page),
CHECK (a figure agrees with its section), FIND (something the figure adds that the
text does not state), QUESTION (only where the manual's own rules cannot settle it).

**Scale:** 485 figures over roughly 605 pages.

---

## Part 2 — Chapter 2A

### Figure 2A-1 — Examples of Enhanced Conspicuity for Signs (PDF 89)
Seven panels: **A** W16-15P NEW plaque above a regulatory sign (drawn over a No Left Turn);
**B** two **red** flags angled above a Speed Limit sign; **C** W16-18P NOTICE plaque above a
Weight Limit sign; **D** a **black-and-yellow diagonally striped** retroreflective border
around a yellow advisory EXIT 25 MPH sign; **E** a vertical retroreflective strip down the
sign support, with a fluorescent yellow-green pedestrian sign and arrow plaque;
**F** one yellow supplemental beacon **above** a yellow intersection warning sign;
**G** white LEDs set **inside the border** of a STOP sign.
- **FIND (figure-only dimension)**: panel E dimensions the strip as ending **2 ft MAX above
  the ground**. Check against 2A.11's text when the section is revisited.
- **CHECK**: panel G matches 2A.12 ¶16 (LEDs within the border or one border width inside the
  background for STOP, YIELD, DO NOT ENTER, WRONG WAY).

### Figure 2A-2 — Heights and Lateral Locations of Sign Installations (PDF 92)
**A** rural roadside: 12 ft MIN lateral, 5 ft MIN height. **B** rural with shoulder wider than
6 ft: 6 ft MIN from the shoulder edge, 5 ft MIN. **C** business/commercial/residential: 2 ft MIN
from the curb, 7 ft MIN\* height (\*where parking or pedestrian movements are likely).
**D** warning sign with advisory speed plaque, rural: 12 ft MIN lateral, **4 ft MIN to the bottom
of the plaque**. **E** roadside assembly, rural: 12 ft MIN, 5 ft MIN. **F** sign on the nose of a
median: **7 ft MIN** to the sign, **4 ft MIN** to the object marker below it. **G** freeway or
expressway sign with a secondary sign: 12 ft MIN lateral / 6 ft MIN from the shoulder,
**8 ft MIN to the primary sign, 5 ft MIN to the secondary sign**. **H** overhead sign:
**17 ft MIN** vertical clearance, 6 ft MIN lateral from the shoulder.
Note on the figure: see 2A.16 for reduced lateral offsets where space is limited.
- **CHECK**: agrees with 2A.15 (5 ft rural, 7 ft urban and above sidewalks) and 2A.16 (offsets).
- **FIND**: the 4 ft minimum under a plaque, the 8 ft / 5 ft pair on freeway assemblies, and the
  7 ft / 4 ft pair on a median nose are stated only in the artwork.

### Figure 2A-3 — Locations for Some Typical Signs at Intersections (PDF 93, Rev. 1)
**A** acute-angle intersection, **B** channelized (2 ft MIN from island edges), **C** minor
crossroad, **D** urban intersection (**4 ft MIN** back from the crosswalk, 2 ft MIN from the
curb), **E** divisional island (2 ft MIN), **F** wide-throat intersection (**50 ft MAX**).
Figure note: lateral offset is a minimum of 6 ft from the shoulder edge or 12 ft from the
traveled-way edge; see 2A.16 for lower minimums in urban areas.
- **FIND (figure-only dimension)**: the **50 ft MAX** placement at a wide-throat intersection, and
  the 4 ft setback from a crosswalk. To be checked against 2B.10 and 2A.13 when revisited.

### Figure 2A-4 — Relative Locations of Regulatory, Warning and Guide Signs on an Intersection
Approach (PDF 94–97, 4 sheets; sheets 1 and 4 marked Rev. 1)
**Sheet 1**: **A** single-lane approach — destination sign at **200 ft MIN** from the
intersection, route signs at **400 ft MIN**, junction assembly at **600 ft MIN**, W2-1 crossroad
warning at **800 ft MIN**, each successive sign 200 ft MIN from the last. **B** multi-lane —
STOP, optional intersection lane control signs, destination sign, W3-1 with street-name plaque,
each 200 ft MIN apart. Figure notes: \* Table 2C-3 for the recommended minimum distance;
\*\* 2C.41 for W2-1 and 2C.35 for W3-1; \*\*\* 2B.27 for Intersection Lane Control signs.
**Sheet 2 (C)**: multi-lane approach with **optional** movement turn lanes; overhead guide sign
at **50 ft** from the stop line, spacing "Varies", then 200 ft min, 200 ft min; alternate signing
at the overhead location shown two ways.
**Sheet 3 (D)**: the same for **mandatory** movement turn lanes, with R3-7 LEFT LANE MUST TURN
LEFT on the roadside.
**Sheet 4 (E)**: multi-lane approach to a **circular intersection** with optional movement turn
lanes; R3-8 series twice, W2-6 at 200 ft min.
- **FIND (tables drawn inside figures)**: sheets 2, 3 and 4 each carry a **"Sign Schedule"**
  listing sign designation, Section and sign name — e.g. R3-5 → 2B.28, R3-6 → 2B.29, R3-8 → 2B.30,
  W3-3 → 2C.35, W16-8P → 2C.65, D3-1 → 2D.45, D3-2 → 2D.46, D series → 2D.36 and 2D.37, and on
  sheet 4 W2-6 → 2C.41. **These are tables without a "Table" number, so they are not in our tables
  file and were not read in the first pass.** Watch for more of them.
- **CHECK**: the 200-ft spacing ladder matches 2A.13 ¶3 (signs requiring separate decisions spaced
  far enough apart) and Table 2C-3.

---

## Figures already read from the page during the first pass or on 22 September

Recorded here so the pass is not repeated: Table-bearing pages (all 50 tables) plus
Figure 4D-1, Figure 4D-2, Figure 6L-3, Figure 3C-1, Figure 2C-8, Figure 2C-15,
Figure 2G-16, Figure 2G-17, Figure 2G-19, Figure 8B-2 area, Table 6P-2's symbol plate,
and Appendix A2's tables. Findings from those are in MANUAL_READING_LOG.md
(Rulings 4, 5 and 6 rest on Figures 2G-17, 2G-19 and 3C-1).

### Figure 2A-5 — Intersection Configuration at a Divided Highway Crossing (PDF 105)
**A** separate intersections — the paths of opposing left-turning vehicles **cross**;
**B** single intersection — the paths **do not cross**. Legend distinguishes direction of travel
from the path of a left-turning vehicle. Accompanying Support: median widths **between 30 and 85 ft**
may function as one or two intersections, with factors A–H (geometry, positive offset left-turn
lanes, length of the median opening, median nose design, skew and variable median width, sight
distance, design vehicle, observed driver behaviour).
- **CHECK**: this is the picture behind 4C.01's "a wide median may be one or two intersections" for
  signal warrants. The **test drawn here is whether opposing left-turn paths cross**, which the
  warrant text does not state.

## Part 2 — Chapter 2B (sign plates)

### Figure 2B-1 — STOP and YIELD Signs and Plaques (PDF 115)
R1-1 STOP (white on red octagon); **R1-3P ALL WAY — white legend and border on red**;
R1-2 YIELD (red border, white field, red legend); plaques **black on white**: R1-2aP TO ONCOMING
TRAFFIC, R1-2bP TO TRAFFIC IN CIRCLE, R1-2cP TO ALL LANES, R1-10P EXCEPT RIGHT TURN.
- **CHECK**: the ALL WAY plaque's colours match 2B.04 ¶4 ("white legend and border on a red
  background"); the other plaques follow the regulatory black-on-white pattern.

### Figure 2B-2 — Unsignalized Pedestrian Crosswalk Signs (PDF 123)
Post-mounted R1-5, R1-5b (pedestrian) and **R1-5d, R1-5e** (pedestrian **and bicycle**);
in-street R1-6, R1-6a, R1-6d, R1-6e (yellow STATE LAW header, white centre panel, yellow
IN CROSSWALK foot); overhead R1-9, R1-9a, R1-9d, R1-9e (yellow STATE LAW band, white body).
Figure footnotes: **the STATE LAW legend is optional**; **fluorescent yellow-green may be used
instead of yellow**; **"Signs are not shown in proportion to their designated sizes."**
- **DATA (closes an earlier flag)**: 3B.19 ¶1 prints "R-5e"; the figure confirms the sign is
  **R1-5e**. Our record by sign name was right.
- **FIND**: the d/e variants add the bicycle symbol for trail crossings — the pedestrian and
  bicycle versions are distinct signs, which matters when a rule names "R1-5 series".

### Figure 2B-3 — Speed Limit Signs and Plaques (PDF 127, Rev. 1)
R2-1; truck/bus plaques R2-2P, R2-2aP, R2-2bP, R2-2cP; **R2-3P NIGHT — white legend on a black
background**; R2-4P MINIMUM; R2-4a combined SPEED LIMIT / MINIMUM; R2-5P UNLESS OTHERWISE POSTED;
R2-5aP CITYWIDE, R2-5bP NEIGHBORHOOD, R2-5cP RESIDENTIAL; R2-6P FINES HIGHER, R2-6aP FINES DOUBLE,
R2-6bP $150 FINE; R2-10 BEGIN / R2-11 END HIGHER FINES ZONE; R2-13 END VARIABLE SPEED LIMIT;
R2-14 END TRUCK SPEED LIMIT.
- **FIND (colour only in the artwork)**: the **NIGHT plaque is white on black**, reversed from every
  other speed plaque. Table 2A-2 records colours by sign class, so this reversal needs its own entry.

### Figure 2B-4 — Movement Prohibition and Lane Control Signs and Plaques (PDF 131–132, 2 sheets;
sheet 2 Rev. 1)
Sheet 1: R3-1 series (including time-of-day and EXCEPT BUSES/TAXIS variants), R3-2, R3-3 NO TURNS,
R3-4, R3-5/R3-5a ONLY arrows, plaques R3-5bP LEFT LANE, R3-5fP RIGHT LANE, **R3-5cP HOV 2+**,
R3-5dP TAXI LANE, R3-5gP BUS LANE, R3-6 series, R3-7L/R, R3-7aP EXCEPT BUSES, R3-7bP EXCEPT
BICYCLES, R3-8 series. **R3-8xa, R3-8xb, R3-8xc draw the bicycle lane as a white symbol on a black
panel.**
Sheet 1 footnote: **the diamond symbol may be used instead of the "HOV" word message; the minimum
occupancy level may vary (2+, 3+, 4+); the words LANE or ONLY may be used.**
Sheet 2: R3-8zd–R3-8zg, R3-18, R3-19, R3-19a, R3-19b LANE FOR U AND LEFT TURNS ONLY, R3-20L/R
BEGIN LEFT (RIGHT) TURN LANE, R3-27, R3-33 / R3-33a RIGHT LANE MUST EXIT.
- **CHECK**: the white-on-black bicycle lane panels are exactly what 9B.03 ¶8 requires ("contrasting
  white legend on a black background … shall not use the color green"). Ruling 4's reasoning about
  regulatory legends on white also fits the R3-5cP HOV 2+ plaque.
- **OPEN (do not guess)**: R3-8zd–zg each show a **solid black dot** at the left-hand edge of the
  lane diagram. Its meaning is not given on the figure; resolve against 2B.30's text and the
  Standard Highway Signs plates before recording anything.

### Figure 2B-5 — Intersection Lane Control Sign Arrow Options for Roundabouts (PDF 133, Rev. 1)
Two sets: **A standard arrows**, **B curved-stem arrows**. Callouts on the artwork:
"Match arrow(s) with desired lane-use configuration" and, pointing at a small circle at the foot of
the left-turn arrow, **"Optional for left-most lane"**.
- **OPEN, now partly resolved**: the solid black dot on R3-8zd–zg (Figure 2B-4 sheet 2) is this
  optional element from the roundabout arrow set. **What it depicts is still not named on either
  page** — do not record a meaning until the Standard Highway Signs plate or a text passage says so.
- **CHECK**: 2B.27 ¶8 (Option) allows R3-5, R3-6 and R3-8 signs at roundabouts to display any of the
  arrow options in Figure 2B-5 — the figure is the list.

### Figure 2B-6 — Center and Reversible Lane Control Signs and Plaques (PDF 136)
R3-9a, R3-9b (CENTER LANE ONLY), plaques R3-9cP BEGIN / R3-9dP END, **R3-9e** (three-panel sign:
red X / black arrows with times), **R3-9f** post-mounted, R3-9g / R3-9h (END and BEGIN REVERSE LANE,
with street name **or** a distance such as 400 FEET), R3-9i.
- **FIND (colour only in the artwork; checked at high zoom)**: R3-9f is a **white sign with black
  legend**, with its added top band **"CENTER LANE" reversed to white on black**. 2B.34 ¶3 requires
  that added legend but gives it no colours; ¶6 gives the sign white with black legend, red only for
  the R3-9e X. The figure supplies the reversed band. No conflict, but the graph should carry it.
- Table 2B-2 (meanings of the symbols) sits on the same page and was read in the first pass.

### Figure 2B-7 — Location of Reversible Two-Way Left-Turn Signs (PDF 137)
Plan view with signs facing both directions (the far-side signs drawn mirrored). **Signs repeat at
¼-mile intervals**; BEGIN / END REVERSE LANE signs at the ends with "400 FEET" or a street name;
R3-9e sets overhead and R3-9f post-mounted alternatives shown as "OR" pairs.
- **FIND (figure-only dimension)**: the **¼-mile repeat spacing**. Check against 2B.34's text when
  the section is revisited.

### Figure 2B-8 — Jughandle Regulatory Signs (PDF 139)
R3-23 / R3-23a word-message signs; **R3-24 series with a diagonal up-right arrow**; **R3-25 series
with a horizontal right arrow**; **R3-26 series with a straight-up arrow**; legends ALL TURNS,
U AND LEFT TURNS, U TURN.
- **CHECK**: the arrow direction is the whole distinction — 2B.35 ¶5 (diagonal where the jughandle
  entrance is an exit-ramp design; horizontal where it is an intersection) and ¶6 (straight up where
  the entrance is downstream of where the turn would normally be made). Nothing but the artwork
  separates the three series.

### Figure 2B-9 — Applications of Jughandle Regulatory and Guide Signing (PDF 140–142, 3 sheets;
sheet 1 Rev. 1)
**A** turns made prior to the intersection; **B** traditional jughandle (with an inset showing the
U-turn-only variant). In every case the **white regulatory sign is mounted directly below the green
guide sign** (ALL TURNS FROM RIGHT LANE, U AND LEFT TURNS, U TURN FROM RIGHT LANE), and the advance
guide sign carries NEXT RIGHT.
- **CHECK**: matches 2B.35 ¶7 (the R3-24, R3-25 and R3-26 series are designed to be mounted below
  conventional guide signs) and supports the same pattern relied on in Ruling 4 — regulatory content
  rides on a white panel attached to a green guide sign, never on the green field.

### Figure 2B-9 sheet 3 (PDF 142)
**C** turns made **beyond** the intersection: the straight-up-arrow sign (R3-26 series, U AND LEFT
TURNS) below the green guide sign at the intersection, the diagonal series at the jughandle itself,
ALL TURNS FROM RIGHT LANE in advance, and a KEEP RIGHT legend on the advance guide sign.
- **CHECK**: matches 2B.35 ¶6 (straight-up arrow where the entrance is downstream of where the turn
  would normally be made).

### Figure 2B-10 — Passing, Keep Right, and Slow Traffic Signs (PDF 144)
R4-1 DO NOT PASS, R4-2 PASS WITH CARE, R4-3 SLOWER TRAFFIC KEEP RIGHT, R4-5 TRUCKS USE RIGHT LANE,
R4-7 / R4-7a / R4-7b / R4-7c (narrow) keep-right symbols and word signs, R4-8 series keep-left,
R4-9 STAY IN LANE, R4-10 RUNAWAY VEHICLES ONLY, **R4-12 "SLOW VEHICLES WITH 5 OR MORE FOLLOWING
VEHICLES MUST USE TURN-OUT"**, R4-13, R4-14, R4-16, R4-17, R4-18, R4-20 ALL TRAFFIC, R4-21.
- **FIND**: R4-12 carries a **numeric threshold inside the legend (5 or more following vehicles)** —
  a rule that exists only as sign text.
- Related text read on the same spread: the narrow R4-7c may be used on a median island **less than
  4 ft wide** and shall not be used where the island is **4 ft or more** (2B.39 ¶10–¶11) — a clean
  partition, worth pairing with the figure.

### Figure 2B-11 — Keep Right and Keep Left Sign Placement (PDF 146)
Four plan views: divisional islands, median noses, channelized approaches and a loop. Shows the
symbol signs (R4-7, R4-8) on island approach ends and the **word-message alternatives** (R4-7a/7b,
R4-8a/8b) or R4-20 ALL TRAFFIC where the island turns traffic away from the approach direction.
- **CHECK**: matches 2B.39 ¶5 (word legend instead of symbol where the island channelizes traffic
  away from the approach direction).

### Figure 2B-12 — Selective Exclusion Signs and Plaques (PDF 148)
Symbol signs with red circle and slash (R5-2 No Trucks, R5-6 No Bicycles, R9-3 No Pedestrians,
R9-13 No Skaters, R9-14 No Equestrians, R9-15 No Snowmobiles, R9-16 No ATVs) and word-message signs
(R5-2b NO THRU TRUCKS, R5-3, R5-4, R5-5, R5-7, R5-8, R5-10, R5-10a ON FREEWAY, R5-10b, R5-10c,
R5-11 AUTHORIZED VEHICLES ONLY, R5-12 NO THRU TRAFFIC); plaques R5-2aP EXCEPT LOCAL DELIVERY and
**R9-19P EXCEPT ON SHOULDER**.
- **FIND**: the same prohibition exists in both symbol and word form; a rule naming "the R5-6 sign"
  is the symbol version, not the word version.

### Figure 2B-13 — DO NOT ENTER, WRONG WAY, ONE WAY and Related Signs (PDF 150)
R5-1 DO NOT ENTER (white legend on a red disc on a white sign), R5-1a WRONG WAY (white on red),
**R6-1 horizontal ONE WAY — white legend and arrow on black**, **R6-2 vertical ONE WAY — black
legend and arrow on white**, R6-3 / R6-3a DIVIDED HIGHWAY, R6-5P roundabout circulation,
R6-6 BEGIN ONE WAY, R6-7 END ONE WAY.
- **FIND (colour only in the artwork)**: the two ONE WAY signs are **opposite colour schemes**.
  Any rule that says "a ONE WAY sign" therefore covers two different-looking signs.

### Figure 2B-14 — DO NOT ENTER and WRONG WAY Signing at Divided Highway Crossings that Function as
Two Separate Intersections (PDF 151)
Plan view with DO NOT ENTER signs facing the wrong-way approaches on both median openings and
WRONG WAY signs beyond them; several marked **Optional** with a star; legend includes the
**vehicle path of a left turn (see 2A.23)**, tying the figure back to Figure 2A-5's two-intersection
test. Note: pavement markings shown for clarification only.

### Figure 2B-15 — Regulatory Signing and Pavement Markings at an Exit Ramp Termination to Deter
Wrong-Way Entry (PDF 153)
Shows, on the ramp terminal: DO NOT ENTER pairs facing the ramp, **WRONG WAY signs further down the
ramp**, ONE WAY signs on the crossroad median and far side, No Left/Right Turn symbol signs
(optional), ONE WAY plaques, STOP or YIELD at the ramp end with the note **"(use a stop line if a
STOP sign is installed)"**, and wrong-way arrows on the pavement. Legend distinguishes wrong-way
arrows from lane-use arrows; starred items are optional.
- **CHECK**: matches 2B.47 (WRONG WAY placed farther from the crossroad than the DO NOT ENTER sign,
  on the same side) and 3B.20's wrong-way arrows.

### Figure 2B-16 — Regulatory Signing and Pavement Markings at an Entrance Ramp Terminal (PDF 154)
**A** design does **not** clearly indicate the direction of flow — ONE WAY on the crossroad, a No
Left Turn symbol sign facing the ramp, an optional ONE WAY plaque at a supplemental location, and
optional wrong-way arrows on the ramp. **B** design **does** clearly indicate the direction of flow —
the ONE WAY and NO TURNS signs are both starred optional.
- **FIND**: the figure makes the geometry the trigger — whether the design itself shows the flow
  direction decides whether signs are required or optional.

### Figure 2B-17 — Low-Mounted WRONG WAY Signs with DO NOT ENTER Signs (PDF 156)
Six fully dimensioned assemblies, in two groups (**for a 7-ft mounting height of the primary sign**
and **for a 5-ft mounting height**):
- DO NOT ENTER 30 × 30 over WRONG WAY 36 × 24, **24 in apart**, bottom **36 in** above ground.
- DO NOT ENTER 36 × 36 over WRONG WAY 42 × 30, **18 in apart**, bottom 36 in.
- DO NOT ENTER 48 × 48 over WRONG WAY 42 × 30, **18 in apart**, bottom 36 in.
Footnote: with the 42 × 30 WRONG WAY sign the assembly sits **higher than the nominal 5-ft mounting
height, because that sign's size controls**.
- **FIND (figure-only)**: all of the separations, the 36-in ground clearance, and the note that the
  larger WRONG WAY sign governs the assembly height.

### Figure 2B-18 — Locations of ONE WAY Signs (PDF 157, Rev. 1)
Four cases: one-way street crossing a two-way street; a T-intersection; and a divided highway
crossing, which also shows END ONE WAY, DO NOT ENTER, LEFT LANE MUST TURN LEFT and two-way traffic
warning signs with AHEAD plaques. Starred items optional.
- Related text: Divided Highway Crossing signs **may be omitted where the divided highway has less
  than 400 AADT and a speed limit of 25 mph or less** (2B.50 ¶2) — a threshold pair to capture.

### Figure 2B-19 — ONE WAY Signing for Divided Highway Crossings that Function as Two Separate
Intersections (PDF 158)
Full plan view plus a **"Typical mounting"** detail: ONE WAY above the STOP sign, with the Divided
Highway Crossing sign mounted beneath, on one support. Legend repeats the **400 AADT / 25 mph**
exception and marks the vehicle path of a left turn (2A.23).
- **CHECK**: 2B.50 ¶4 (R6-3 at four-leg intersections, R6-3a at T-intersections) and ¶5 (near right
  corner, beneath a STOP or YIELD sign or on a separate support) — the figure is the picture of both.

### Figure 2B-20 — ONE WAY, DO NOT ENTER and WRONG WAY Signing for Divided Highway Crossings that
Function as a **Single** Intersection (PDF 159)
- **FIND (rule stated only in a figure legend)**: "**Near-right and far-left ONE WAY signs are
  optional if Keep Right signs are installed**" and "**Keep Right signs are optional if ONE WAY signs
  are installed**". A mutual either/or between two different sign types, with no equivalent sentence
  found in 2B.49 or 2B.39 so far. Flag for the merge: the graph must not require both.

### Figure 2B-21 — Regulatory and Warning Signs for a Mini-Roundabout (PDF 160)
One leg signed: YIELD with the Roundabout Circulation plaque (R6-5P) at the entry; optional
Circular Intersection warning (W2-6) with a street-name plaque in advance; optional pedestrian
crossing signs with diagonal arrow plaques at the crosswalk; optional keep-right / object-marker
style plaque at the splitter island. Notes: signs shown for only one leg; 2D.39 for guide signs;
Chapter 3D for markings. The mini-roundabout's central island is drawn as a **traversable (domed)
island**, not a raised one.

### Figure 2B-22 — Regulatory and Warning Signs for a One-Lane Roundabout (PDF 161, Rev. 1)
One leg signed. Central island: **ONE WAY signs (horizontal R6-1 "OR" vertical R6-2) each drawn on a
post with a yellow object marker beneath**. Entry: YIELD with the R6-5P circulation plaque; optional
Yield Ahead; optional pedestrian crossing signs with diagonal arrow plaques at the crosswalk;
optional W2-6 circular-intersection warning with a street-name plaque in advance.
- **FIND**: the object marker under the central-island ONE WAY signs is a mounting detail carried
  only in the artwork.

### Figure 2B-23 — Two-Lane Roundabout with Consecutive Double Lefts (PDF 162, Rev. 1)
Same signing pattern as 2B-22, plus **four alternative R3-8 lane-control signs joined by "OR"**.
Examined at high zoom: the four are **standard arrows and curved-stem arrows, each shown with and
without a filled dot at the tail of the left-most lane's arrow**.
- **OPEN, narrowed**: this confirms the dot is the optional element of Figure 2B-5 ("Optional for
  left-most lane"), appears at the **tail** (start) of the arrow, and is available in both arrow
  styles. **The manual still does not state what it represents** — leave unrecorded until a text
  passage or the Standard Highway Signs plate names it.

### Figure 2B-24 — Regulatory and Warning Signs for a Neighborhood Traffic Circle (PDF 163, Rev. 1)
Central island carries a **Keep Right sign with diagonal arrow (R4-7b)**, optionally above a yellow
object marker — not the ONE WAY signs used at a roundabout. Entry: YIELD with R6-5P (pointing to
2B.51 ¶1); optional W2-6 with street-name plaque. Yield-line triangles drawn at the entry.
- **CHECK**: matches 2B.39 ¶6 (Keep Right with diagonal arrow in the central island of a
  neighborhood traffic circle, mounting height at least 4 ft) and distinguishes the traffic circle
  from the roundabout by the sign used in the island.

### Figure 2B-25 — Parking, Standing and Stopping Signs and Plaques (PDF 165–166, 2 sheets)
Sheet 1: **A prohibitive signs — red legend on white** (R7-1, R7-2, R7-2a, R7-3, R7-4, R7-4a, R7-6,
R7-107 series, R7-201P tow-away symbol, R7-202P THIS SIDE OF SIGN, **R7-203 Snow Emergency Route
with a white-on-red upper section**, R8-1, R8-2, R8-3 series, R8-5, R8-6). **B permissive signs —
green legend on white** (R7-5, R7-10 BACK-IN PARKING ONLY, R7-20 multi-space meter, R7-21, R7-21aP,
R7-22, R7-108).
Sheet 2: **C combination signs** (red prohibition panel beside or above a green permissive panel,
R7-200 / R7-200a); **D accessible parking** (R7-8 with the wheelchair symbol, R7-8aP VAN ACCESSIBLE,
both green on white); **E electric-vehicle parking and charging** (R7-111 to R7-114b, mixing red
prohibitive and green permissive panels, with plaques VEHICLE MUST BE PLUGGED IN and VACATE STALL
WHEN CHARGING COMPLETED).
- **FIND (colour convention shown, not stated on the page)**: prohibitive = **red on white**,
  permissive = **green on white**, and a combination sign carries both panels. Time-limit and
  day-of-week legends appear inside the panels.
- Related text on sheet 2: the times and days **shall be posted** if the regulation is not in effect
  at all times (2B.53 ¶8); arrows may be replaced by BEGIN, END, HERE TO CORNER, HERE TO ALLEY,
  THIS SIDE OF SIGN (¶9).

### Figure 2B-26 — Emergency Restriction Signs (PDF 168)
R8-4 EMERGENCY PARKING ONLY and R8-7 EMERGENCY STOPPING ONLY, **black legend and border on white**
(2B.55 ¶1), i.e. deliberately not the red parking-sign colours.

### Figure 2B-27 — Pedestrian Signs and Plaques (PDF 170–171, 2 sheets; sheet 1 Rev. 1)
Sheet 1: R9-1 WALK ON LEFT FACING TRAFFIC, R9-2, R9-3 (symbol), R9-3a, R9-3bP USE CROSSWALK,
R9-4 (no hitchhiking symbol), R9-4a, **R10-1 CROSS ONLY ON GREEN with a green disc**, R10-2 CROSS
ONLY ON SIGNAL, R10-3 / R10-3a push-button signs, and the educational series **R10-3b to R10-3h**,
which depict the actual pedestrian indications (white walking person, Portland-orange hand,
countdown numerals), with variants for crossing **to a median** and versions carrying the street
name. R10-3c substitutes the word legends WALK / DONT WALK.
Sheet 2: R10-3i, R10-4 and R10-4a (both with a **green disc**), R10-25 PUSH BUTTON FOR WARNING
LIGHTS / WAIT FOR GAP IN TRAFFIC, and **R10-32P "PUSH BUTTON FOR 2 SECONDS FOR EXTRA CROSSING TIME"**.
- **CHECK**: R10-32P's printed legend confirms the pairing logged during the reading — the plaque
  says 2 seconds while 4K.05 ¶2 sets the extended-press threshold at 1 second or more.
- **FIND**: the educational signs reproduce signal indications **in colour inside a regulatory sign**;
  a colour model keyed only to sign class would miss the orange hand and green disc.

### Figure 2B-28 — Traffic Signal Signs and Plaques (PDF 173–174, 2 sheets)
Sheet 1: R10-5, R10-6 / R10-6a STOP HERE ON RED (with arrow), R10-7 DO NOT BLOCK INTERSECTION,
R10-8, R10-10 / R10-10a signal signs, R10-11 series No Turn on Red (**R10-11a carries a red disc**),
R10-11c EXCEPT FROM RIGHT LANE, R10-11d FROM THIS LANE with a downward arrow, **R10-12 LEFT TURN
YIELD ON GREEN with a green disc**, R10-12a ON FLASHING YELLOW ARROW, **R10-12b LEFT TURN YIELD TO
(bicycle symbol)**, R10-13 EMERGENCY SIGNAL, R10-14 / R10-14a / R10-14b.
Sheet 2: **R10-15 / R10-15a TURNING VEHICLES YIELD TO (STOP FOR) PEDESTRIANS — yellow header band
over a white panel, starred "a fluorescent yellow-green background color may be used instead of
yellow"**; R10-16 U TURN YIELD TO RIGHT TURN; R10-17a; R10-20aP time plaques; **R10-23 CROSSWALK
STOP ON RED with a red disc**; R10-23a; **R10-27 LEFT TURN YIELD ON FLASHING RED ARROW AFTER STOP**;
R10-30; R10-31P AT SIGNAL.
- **CHECK**: R10-27's printed legend matches 2B.59's "LEFT (RIGHT) TURN YIELD ON FLASHING RED ARROW
  AFTER STOP", the sign named in 4F.04, 4F.08, 4F.11 and 4F.15.
- Related Standard on sheet 2: R10-15a (STOP FOR) **only in jurisdictions whose law requires a driver
  to stop for a pedestrian** (2B.59 ¶17), with placement A–C by corner and movement (¶18).

### Figure 2B-29 — Ramp Metering Signs (PDF 176)
R10-28 ONE VEHICLE PER GREEN; R10-29 1 VEHICLE PER GREEN EACH LANE. Text beside it: the first is for
ramps with **one** controlled lane, the second for ramps with **more than one** controlled lane.

### Figure 2B-30 — Road Closed and Weight Limit Signs (PDF 177)
R11-1 KEEP OFF MEDIAN; R11-2 ROAD CLOSED; R11-3 / R11-3a / R11-3b with **distances and LOCAL TRAFFIC
ONLY** (including a fractional distance, "7½ MILES AHEAD"); R11-4 ROAD CLOSED TO THRU TRAFFIC;
weight limits R12-1, R12-2, R12-4, **R12-5 and R12-6 which carry truck silhouettes against tonnages
by axle count (2–3 axles 12T, 4–5 axles 15T, 6+ axles 18T, and combination-vehicle rows)**,
R12-7 / R12-7aP emergency vehicle weight limits (single axle, tandem, gross).
- **FIND**: R12-5 and R12-6 are **tables drawn inside a sign** — vehicle type against weight limit.
  Like the Sign Schedules, this content is not in our tables file.

### Figure 2B-31 — Truck Signs (PDF 180)
R13-1 weigh-station word sign; R14-1 TRUCK ROUTE; **R14-2 "HM" in a green circle** (designated
hazardous-materials route) and **R14-3 "HM" in a red circle with slash** (prohibited); **R14-4 truck
symbol in a green circle** (National Network route) and **R14-5 truck symbol in a red circle with
slash** (prohibited).
- **FIND (colour carries the meaning)**: the same symbol means **permitted/designated in a green
  circle** and **prohibited in a red circle with a slash**. A symbol-only reading of these signs
  would invert the rule.

### Figure 2B-32 — Photo Enforcement Signs and Plaques (PDF 181)
R10-18 (camera symbol over TRAFFIC LAWS PHOTO ENFORCED), **R10-18a — a full-colour signal face
(red, yellow, green on black) above PHOTO ENFORCED**, R10-19P camera-symbol plaque, R10-19aP word
plaque.
- Related Standards on the page: R10-18a **shall not** be installed where red-light cameras are not
  present on any approach, and **shall not** share a support with a Signal Ahead (W3-3) sign; the
  plaques are black on white.

### Figure 2B-33 — Other Regulatory Signs (PDF 181)
R16-3 MOVE OVER OR REDUCE SPEED, R16-4 MINOR CRASHES MOVE VEHICLES FROM TRAVEL LANES, R16-15 /
R16-15a NO HAND-HELD PHONE USE BY DRIVER — each with a **yellow STATE LAW header band** over a
white body. Text: the word legend **may be modified to reflect the State's law** (2B.70 ¶2,
2B.71 ¶2, 2B.72 ¶2).

### Figure 2B-34 — Headlight Use Signs (PDF 182)
R16-5, R16-6, R16-7 (TURN ON HEADLIGHTS NEXT XX MILES), R16-8, R16-9 CHECK HEADLIGHTS,
R16-10 BEGIN / R16-11 END DAYTIME HEADLIGHT SECTION — all black on white.
**Chapter 2B figures complete (2B-1 to 2B-34).**

## Part 2 — Chapter 2C (warning signs)

### Figure 2C-1 — Horizontal Alignment Signs and Plaques (PDF 194)
W1-1 to W1-5 (turn, curve, reverse turn, reverse curve, winding road), W1-6 large arrow, W1-8
chevron, **W1-10 series (intersections in a curve, five variants)**, W1-11 hairpin, **W1-13 truck
rollover**, W1-15 loop; advisory plaques W13-1P and W13-1aP; exit/ramp advisory speed signs W13-2,
W13-3, W13-6 to W13-11, and **W13-12 / W13-13 with the truck-rollover symbol**.
- **FIND (figure note)**: "**Turn arrows and reverse turn arrows may be substituted for the curve
  arrows and reverse curve arrows on the W1-10 series signs where appropriate**" — a substitution
  rule carried in the figure's note.

### Figure 2C-2 — Warning Signs for Changes in Horizontal Alignment (PDF 197–198, 2 sheets;
sheet 1 Rev. 1)
**A Curve** and **B Turn**, each showing the full sequence: advance W1-2 (curve) or W1-1 (turn) with
a W13-1P advisory speed plaque, optional W1-6 large arrow with W13-1aP, "OR" a W1-8 chevron, and
chevrons through the curve on both sides (W1-8L / W1-8R). Notes: **Table 2C-3** for advance
placement, **Table 2C-4** for selecting the alignment sign, **Table 2C-5** for chevron spacing, and
"a 35-mph (15-mph) advisory speed is shown for illustrative purposes only".
- **CHECK**: the three tables named in the notes are the ones read during the first pass; the figure
  ties them together into one sequence — advance sign, advisory plaque, then chevrons or a large
  arrow, with the large arrow and chevrons as alternatives ("OR").

### Figure 2C-3 — Exit Ramp Advisory Speed and Other Warning Signs (PDF 202–206, 5 sheets;
sheets 1, 3 and 4 Rev. 1)
Five ramp cases, each labelled on the artwork with the geometric concept that drives the signing:
- **A Loop ramp with constant controlling curvature** — callouts "**Controlling curve for speed along
  ramp proper**" and "**Transition to ramp speed**"; W13-2 **or** the combination W13-6R at the exit;
  W1-6R with optional W13-1aP on the ramp; "Exit Direction sign (if post-mounted)".
- **B Loop ramp with downstream limiting curvature** — the ramp exit advisory (30 mph) and then a
  **separate, lower advisory (20 mph) at the "downstream limiting curve at ramp terminal"**, with
  W1-1R, optional W1-13R truck rollover and chevrons.
- **C Directional ramp** — controlling curve along the ramp proper and a downstream limiting curve,
  each signed; W1-11L hairpin at the far terminal; W13-2 45 mph at the exit.
- **D Diagonal ramp** — W1-6L on the ramp and **W3-1 Stop Ahead "OR" W3-3 Signal Ahead** at the ramp
  terminal, with W13-2 35 mph at the exit.
- **E Short ramp length with limiting curve near the ramp terminal** — callout "**limiting curve at
  ramp terminal, no transition to ramp speed**"; here the **yellow W13-1aP advisory plaque is mounted
  directly on the green Exit Direction sign (E5-1c)**, with W13-10R on the mainline.
- **CHECK**: sheet E is the arrangement 4S.01 ¶4 names when it allows a Warning Beacon within a sign
  border for "Exit Direction signs with advisory speed panels (2E.25)" — the figure shows the panel
  on the guide sign.
- **FIND**: the figures name three distinct geometric objects — the controlling curve on the ramp
  proper, the downstream limiting curve at the terminal, and the transition to ramp speed — and the
  signing differs for each. The text alone does not draw these apart as clearly.

### Figure 2C-4 — Vehicle Speed Feedback Sign and Plaque (PDF 207, Rev. 1)
W13-20 sign and W13-20aP plaque: **black YOUR SPEED legend on yellow retroreflective background,
with the changeable speed shown as a yellow luminous legend on an opaque black background**.
- Related Standards on the same page: the plaque **only** below a Speed Limit sign; the W13-20 sign
  **only** as an independent installation near the point of curvature of a horizontal curve, to
  supplement the advisory speed; the changeable speed displayed **as an integer**; no flashing,
  strobing, colour change or animation; **no legend displayed when no vehicles are approaching**.

### Figure 2C-5 — Vertical Grade Signs and Plaques (PDF 208)
W7-1 hill symbol, **W7-1a hill symbol with the percent grade in the sign**, plaques W7-2P USE LOW
GEAR, W7-2bP TRUCKS USE LOWER GEAR, W7-3P (percent grade), W7-3aP (distance), **W7-3bP combining
grade and distance**, truck-escape signs W7-4, W7-4b, W7-4c, surface plaques W7-4dP SAND /
W7-4eP GRAVEL / W7-4fP PAVED, and W7-6 HILL BLOCKS VIEW.
- **FIND (a table written as prose)**: the Guidance beside the figure sets Hill signing by grade and
  length — **5 % over 3,000 ft, 6 % over 2,000 ft, 7 % over 1,000 ft, 8 % over 750 ft, 9 % over
  500 ft** — with repeat signs at roughly **1-mile** intervals on long grades. Computable.

### Figure 2C-6 — Miscellaneous Warning Signs (PDF 210)
W5-1 ROAD NARROWS, W5-2 / W5-2a narrow bridge and underpass, W5-3 / W5-3a one-lane bridge and
underpass, W6-1 / W6-2 divided highway begins and ends (symbol), W12-1 double arrow,
**W12-2 / W12-2a / W12-2b low clearance signs carrying feet-and-inches legends**, W14-1 DEAD END and
W14-1a plaque, W14-2 NO OUTLET and W14-2a plaque, W18-1 NO TRAFFIC SIGNS, W19 series freeway and
expressway ends (including 1-MILE versions), W19-5 ALL TRAFFIC MUST EXIT.

### Figure 2C-7 — Roadway and Weather Condition Signs and Plaques (PDF 215)
W8-1 BUMP, W8-2 DIP, W8-3 PAVEMENT ENDS, W8-4 SOFT SHOULDER, **W8-5 slippery-when-wet symbol** with
plaques W8-5P WHEN WET / W8-5aP ICE / W8-5bP STEEL DECK / W8-5cP EXCESS OIL, W8-7 LOOSE GRAVEL,
W8-8 ROUGH ROAD, W8-9 LOW SHOULDER, W8-11 UNEVEN LANES, W8-12 NO CENTER LINE, W8-13 BRIDGE ICES
BEFORE ROAD, W8-14 FALLEN ROCKS, W8-15 GROOVED PAVEMENT and W8-16 METAL BRIDGE DECK **each with an
optional motorcycle plaque (W8-15aP)**, **W8-17 shoulder drop-off symbol with the W8-17P plaque**,
W8-18 ROAD MAY FLOOD, **W8-19 flood gauge — a vertical sign scaled in feet**, W8-21 GUSTY WINDS AREA,
W8-22 FOG AREA, W8-23 NO SHOULDER, W8-25 SHOULDER ENDS, W17-1 SPEED HUMP.
- Pairs with the reading: LOW SHOULDER ≤ 3 in vs Shoulder Drop-Off > 3 in (6H.26) — the figure shows
  both signs and the drop-off symbol.

### Figure 2C-8 — Advance Traffic Control Signs (PDF 218)
Read earlier today while settling question 4: W3-1 Stop Ahead, W3-2 Yield Ahead, W3-3 Signal Ahead
(all with the device symbol in colour — red octagon, red-and-white triangle, red/yellow/green signal
face), W3-4 BE PREPARED TO STOP, W3-6 DRAW BRIDGE, W3-7 RAMP METER AHEAD, **W3-8 RAMP METERED WHEN
FLASHING**, W23-2 / W23-2a NEW TRAFFIC PATTERN and NEW SIGNAL OPERATION AHEAD, W26-1 WATCH FOR
STOPPED TRAFFIC.
- **CHECK**: the symbol signs carry the device's own colours inside a yellow warning sign.

### Figure 2C-9 — Reduced Speed Limit Ahead and Speed Zone Signs (PDF 220)
**W3-5 carries a miniature Speed Limit sign inside the yellow diamond**; W3-5a XX MPH SPEED ZONE
AHEAD; W3-5b VARIABLE SPEED ZONE AHEAD; W3-5c TRUCK SPEED ZONE AHEAD.

### Figure 2C-10 — Intersection Warning Signs and Plaques (PDF 220)
W1-7 double arrow; W2-1 cross road, W2-2 / W2-3 / W2-3a side road, W2-4 T, W2-5 Y, **W2-6 circular
intersection with optional W16-12P TRAFFIC CIRCLE "OR" W16-12aP ROUNDABOUT plaque**, W2-7L / W2-7R
(offset side roads), W2-8, W2-10 TRAFFIC ENTERING WHEN FLASHING, W2-11 TRAFFIC APPROACHING WHEN
FLASHING, plaques W4-4P CROSS TRAFFIC DOES NOT STOP, W4-4aP TRAFFIC FROM LEFT DOES NOT STOP,
W4-4bP ONCOMING TRAFFIC DOES NOT STOP, and **W25-1 ONCOMING TRAFFIC HAS EXTENDED GREEN /
W25-2 ONCOMING TRAFFIC MAY HAVE EXTENDED GREEN**.
- **CHECK**: W25-1 and W25-2 are the signs required by 4F.01's "yellow trap" conditions (B.4 and
  F.5) — confirmed as printed signs, not just legends in the text.

### Figure 2C-11 — Merging and Passing Signs and Plaques (PDF 223)
W4-1 merge, W4-2 lane ends symbol, W4-3 added lane, W4-5 entering roadway merge with the
**W4-5aP NO MERGE AREA plaque**, W4-6 entering roadway added lane, W4-7 HEAVY MERGE FROM RIGHT,
W4-8 added lane symbol, W6-3 two-way traffic, W6-5 / W6-5a two-way traffic on divided roadways,
W8-26 / W8-26a ROAD (STREET) ENDS 500 FT, W9-1 RIGHT LANE ENDS, W9-4 LANES MERGE,
W9-7 RIGHT LANE FOR EXIT ONLY, and **W14-3 NO PASSING ZONE — the only pennant-shaped sign, drawn
pointing right**.
- **FIND**: the pennant shape and its orientation are visual facts; the sign is mounted on the left
  of the roadway (2C.53), which only makes sense with the shape shown here.

### Figure 2C-12 — Merge and Added Lane Sign Placement for Entering and Converging Roadways (PDF 225)
**A converging and entering roadways**: W4-1R on the major roadway and **W4-1L on the entering
roadway**, plus a second W4-1R downstream. **B added lane**: W4-3R on the major roadway and
**W4-6R on the entering roadway**, shown twice (acute entry and right-angle entry).
- **FIND**: the figure fixes which sign faces which roadway — the same event is signed differently to
  the through driver and to the entering driver. The sign faces themselves differ by the dotted line
  (merge vs added lane).

### Figure 2C-13 — Example Sequences for Lane Ends and Lane Merge Signs (PDF 226–230, 5 sheets;
sheets 1, 2, 3 and 5 Rev. 1)
- **A freeway or expressway, lane ends**: W4-2R at the Table 2C-3 advance distance, optional W9-1R
  RIGHT LANE ENDS with a **W16-2P distance plaque (1000 FEET)** further upstream; "**optional dotted
  lane line**" called out on the artwork; note pointing to 3B.12 for lane-reduction markings.
- **B right lane on a conventional road**: the same pair at shorter spacing.
- **C left lane on an undivided roadway** (with yellow diagonal median markings) and **D left lane on
  a divided or one-way roadway**: W4-2L and optional W9-1L, placed **facing approaching traffic on
  the left-hand side** where the median permits.
- **E lane ends beyond a major intersection or side road**: callout "**less than advance placement
  distance**", so the W4-2R goes on the **far side of the intersection** and the W9-1R upstream with
  a distance plaque.
- **F reduction of two lanes to one with merging manoeuvres for each lane**: **W4-8 single-lane
  transition** with optional W9-4 LANES MERGE and a 500 FEET plaque.
- **CHECK / FIND**: sheet 3's accompanying **Standard — "The W4-2 and W9-1 signs shall not be used in
  dropped lane situations"**, where regulatory lane-control signs (2B.28) are used instead. The
  figures thus separate three cases the graph must keep apart: **lane ends (merge)**, **lane drop
  into a mandatory turn lane**, and **two lanes merging into one (W4-8)**.
- Related Guidance on the sheets: Lane Ends signs **not** in advance of the downstream end of an
  acceleration lane; W9-7 RIGHT LANE FOR EXIT ONLY upstream of the first EXIT ONLY panel or the first
  R3-33, whichever is farther upstream, with a distance legend where the dropped lane runs more than
  **1 mile** to the ramp.

### Figure 2C-14 — Vehicular Traffic Warning Signs and Plaques (PDF 232)
W8-6 TRUCK CROSSING (word alternate to the W11-10 symbol), **W11-1 bicycle\***, W11-5 farm vehicle,
W11-8 fire station, W11-10 truck, W11-11 golf cart, W11-12P EMERGENCY SIGNAL AHEAD, W11-14
horse-drawn vehicle, **W11-15 bicycle/pedestrian\* with the W11-15P TRAIL X-ING plaque\***, and
**W11-15a TRAIL CROSSING\***.
- **FIND**: the star ("a fluorescent yellow-green background color may be used") is attached **only**
  to the bicycle and trail signs — not to the truck, farm, fire, golf-cart or horse-drawn signs. The
  artwork is where that restriction is visible.

### Figure 2C-15 — Non-Vehicular Warning Signs (PDF 234)
Read earlier today: W11-2 pedestrian\*, W11-3 deer, W11-4 cattle, W11-6 snowmobile, W11-7 equestrian,
**W11-9 accessibility symbol\***, W11-16 bear, W11-17 sheep, W11-18 bighorn sheep, W11-19 donkey,
W11-20 elk, W11-21 moose, W11-22 wild horse, W15-1 playground\*. Same star convention — FYG only on
the pedestrian, accessibility and playground signs.

### Figure 2C-16 — Supplemental Warning Plaques (PDF 236)
Distance and location plaques (W16-1P IN ROAD, W16-1aP IN STREET, W16-2P/2aP feet, W16-3P/3aP miles,
W16-4P NEXT XX FT), arrow plaques (W16-5P, W16-6P, **W16-7P diagonal downward**, **W16-7aP
double-headed**), street-name plaques (W16-8P, W16-8aP), W16-9P AHEAD, W16-10P photo-enforcement
symbol, W16-10aP PHOTO ENFORCED, **W16-13P WHEN FLASHING**, W16-15P NEW, W16-18P NOTICE,
W16-20P EXCEPT BICYCLES.
- **CHECK**: W16-13P is the plaque at the centre of Ruling 6 — it is a **yellow warning plaque**, and
  the figure's note says "**The background color (yellow or fluorescent yellow-green) shall match the
  color of the warning sign that it supplements**", matching 2C.58 ¶1.

### Figure 2C-17 — Object Markers (PDF 240)
**Type 1 (obstructions within the roadway)**: OM1-1 nine yellow retroreflectors on a yellow diamond,
OM1-2 on a black diamond, OM1-3 all-yellow diamond. **Type 2 (adjacent)**: OM2-1V / OM2-1H three
retroreflectors on white, OM2-2V / OM2-2H all-yellow rectangles. **Type 3 (adjacent or within)**:
OM3-L, OM3-C, OM3-R striped markers — **stripes slope downward toward the side on which traffic is
to pass**, the centre version chevroned both ways. **Type 4 (end of roadway)**: OM4-1, OM4-2, OM4-3
in **red**.
- Dimensions from the text beside the figure: diamonds **≥ 18 in** on a side, retroreflectors
  **≥ 3 in** diameter, Type 2 signs **≥ 6 × 12 in**, Type 3 markers **12 × 36 in** with stripes at
  **45°** and **≥ 3 in** wide; mounting **≥ 4 ft** to the bottom for obstructions within 8 ft of the
  shoulder or curb, and **≥ 4 ft clearance** where more than 8 ft away.

## Part 2 — Chapter 2D (guide signs)

### Figure 2D-1 — Color-Coded Destination Guide Signs (PDF 247)
Green guide signs, each with a **coloured square panel carrying a white letter (magenta "A",
blue "B") placed to the left of its destination group**.
- **CHECK (across Parts)**: this is the mechanism 9D.12 ¶24 requires for shared-use path destination
  signs — colour coding by square or rectangular panels beside the destination, never by recolouring
  the sign.

### Figure 2D-2 — Uses of Abbreviations on Guide Signs (PDF 253, Rev. 1)
Three groups, each sign annotated word by word: **A cardinal directions and orientations** — a street
**name** ("South Ave") shall not be abbreviated, a **pre-directional designation** ("S Randolphville
Rd") may be, the **cardinal direction of travel** ("EAST", in small capitals) shall not be, and a
**street-name descriptor** ("Avenue" → "Ave") should be. **B quadrant and cardinal directions** —
"SE Boulevard" (quadrant abbreviated, name spelled out) against "Southeast Blvd" (name spelled out,
descriptor abbreviated). **C other descriptors within proper names** — "Avalanche Peak" (no
recognizable abbreviation, so **shall not** be abbreviated) against "Mount Olive" **or** "Mt Olive".
Footnote: Tables 1D-1 and 2D-3 list the acceptable abbreviations.
- **FIND**: the same word is treated differently depending on whether it is the **name** or the
  **descriptor** — a distinction carried almost entirely by these annotated examples.

### Figure 2D-4 — Route Signs (PDF 258)
M1-1 Interstate (one/two digits and three digits), **M1-1a Interstate with the State name in white on
blue**, **M1-2 Off-Interstate Business LOOP and M1-3 Business SPUR — cutout shields, white on green**,
M1-4 U.S. Route (black on white cutout), M1-5 State Route (black on white circle), **M1-6 County
Route — yellow on blue pentagon**, **M1-7 Forest Route — yellow on brown**.
- **DATA (closes an earlier flag)**: the first pass recorded that Table 2A-1's text layer listed the
  National Forest Route sign as "M1-1"; the plate confirms it is **M1-7**. Our record by sign name
  was right.
- Related Standards on the page: Interstate shields **24 × 24 in** (one or two digits) and
  **30 × 24 in** (three digits); M1-1a only in Route Sign assemblies; Business Loop/Spur shields the
  **same shape and size as the Interstate shield**, and **never carrying the word INTERSTATE**.

### Figure 2D-5 — Route Sign Auxiliary Plaques and Combination Junction Sign (PDF 260)
M2-1P JCT; **M2-2 Combination Junction — white legend and border on green, with route shields inside**;
cardinal direction plaques M3-1P to M3-4P; alternative-route plaques M4-1P ALTERNATE, M4-1aP ALT,
M4-2P BY-PASS, M4-3P BUSINESS, M4-4P TRUCK, M4-5P TO, M4-6P END, M4-7P TEMPORARY, M4-7aP TEMP,
M4-14P BEGIN.
- **CHECK (visible in the artwork)**: on the cardinal plaques the **first letter is drawn larger**,
  matching 2D.15 ¶2 ("ten percent larger, rounded up to the nearest whole number size").
- Related Standard: a route sign combined with its plaques into a single guide sign is **green with
  white legends**, and **auxiliary plaques are never mounted directly to a guide sign**.

### Figure 2D-6 — Advance Turn and Directional Arrow Auxiliary Plaques (PDF 263)
Advance turn arrows M5-1P (left), M5-2P (slight left), M5-3P (loop/U); lane designation plaques
**M5-4P LEFT LANE, M5-5P CENTER LANE, M5-6P RIGHT LANE**; directional arrows M6-1P (right),
M6-2P (diagonal up-right), **M6-2aP (diagonal downward)**, M6-3P (up/through), **M6-4P (double-headed)**,
M6-5P (diagonal double-headed), M6-6P and M6-7P (turn-and-through combinations).
- Related Standards: lane designation plaques **only where the designated lane is a mandatory
  movement lane**, adjacent to its full-width portion, and **never adjacent to a through lane in
  advance of, or along the taper of, a lane being added**; a **double-headed arrow shall not** be used
  in a Directional assembly in advance of or at a circular intersection; the **M6-2aP diagonal
  downward arrow** only at the far corner for an immediate ramp entry, never on the approach or near
  side.

### Figures 2D-7 and 2D-8 — Consolidation of Route Sign Assemblies into Guide Signs; Illustration of
Directional Assemblies and Other Route Signs (PDF 265–267 and following sheets)
Plan views of rural intersections with the full sign chain and its spacings:
**distance sign (D2-2) at 300 ft ±**, **confirming assembly 25 to 200 ft beyond the intersection**,
**destination guide sign 100 to 200 ft in advance** (50 to 100 ft in one variant),
**junction assembly 200 ft minimum in advance**, and **400 ft minimum** between the junction assembly
and the destination sign; directional assemblies shown "OR" consolidated into a single green guide
sign. Cases: **A minor roadway approach to a stop-controlled intersection**, **B major roadway or
signalized approach**, **C where overlapping routes join or separate**.
- **FIND (figure-only spacings)**: these distances appear on the artwork, with a note that they are
  **rural** and that 2D.29 to 2D.44 govern low-speed or urban conditions.
- **FIND**: the figures show the **same information as either a stack of shields or one consolidated
  green guide sign** — the choice, and what may be merged, is conveyed by the drawings.

### Figure 2D-8 sheets 2–4 (PDF 268–270)
More intersection types with the same spacing chain: overlapping routes separating, a **Y-intersection**
(directional assemblies "enlarged, if necessary"), a **signalized crossroads with a 600-ft minimum**
between the advance route turn assembly and the junction assembly, a **street-name-only approach**
(D3-1 with a D1-1 destination sign), and a **two-route split with LEFT LANE / RIGHT LANE plaques on
the advance route turn assembly**. Distance signs are drawn rotated where they face a crossing road.
- **FIND**: the drawings distinguish a **Directional assembly** (shields with arrows at the
  intersection), an **Advance route turn assembly** (shields with turn arrows upstream), a
  **Confirming assembly** (shields just beyond the intersection) and a **Junction assembly** (JCT
  plaque above a shield) — four assemblies that differ only by content and position.

### Figure 2D-9 — Destination and Distance Signs (PDF 274)
D1-1, D1-2, D1-3 (one, two and three destinations with arrows); D1-1a, D1-2a, D1-3a (the same **with
distances**); D2-1, D2-2, D2-3 distance signs (destination and mileage, no arrows); and
**D15-1 — a green guide sign with a white ONLY lane-control panel set inside it**, shown as a street
name version "OR" a route shield version.
- **FIND**: the same pattern relied on in Ruling 4 — a **regulatory panel inside a green guide sign**.
- Related Standards: **no more than three destination names** on a Destination sign where the advance
  and supplemental guide signs show three or fewer; four where they show four; and with a
  four-name sign, **a heavy line across the sign or separate signs must separate destinations by
  direction**.

### Figure 2D-10 — Overhead Signs at an Intersection (PDF 276–278, 3 sheets; sheet 2 Rev. 1)
**A combination of mandatory and optional movement lanes**: an **Overhead Arrow-per-Lane guide sign**
spanning the lanes with **yellow ONLY panels (black legend) inside the green sign**, beside a
**conventional guide sign** for the destination served by mandatory lanes. Figure notes: the
Arrow-per-Lane sign is **only** for destinations that include an **optional movement lane**; a
**conventional guide sign** is used for destinations with one or more **mandatory movement lanes**.
**B mandatory movement lanes**: conventional guide signs for every destination, each with its own
yellow ONLY panel and arrow.
- **FIND**: the choice between the two sign types is driven by whether the movement lane is optional
  or mandatory — stated in the figure's own notes.
- Related Guidance on sheet 1: no more than one destination per movement and three per sign; the
  diverging movement's arrowhead **lower** than the through movement's; the **vertical white
  separator line** not descending below the top of the through arrowheads.
- **Table 2D-5** (on sheet 2, Rev. 1) — minimum arrow heights by principal legend letter height:
  **13.33 → 32 (straight) / 25.333 (turn); 10.67 → 25.5 / 20.188; 8 → 21 / 16.625 inches.**
  Option: **curved-stem arrows** may be substituted on multi-lane approaches to a circular
  intersection with an option lane.

### Figure 2D-10 sheet 3 (PDF 278)
**C mandatory movement lanes with dual turn lanes**: conventional guide signs for every destination,
each with its own yellow ONLY panel; two left-only lanes served by one sign with two arrows.

### Figure 2D-11 — Destination Signs for Circular Intersections (PDF 280)
D1-1d, D1-1e, D1-2d, D1-3d — destination signs with **curved arrows**; and **D1-5 / D1-5a — the
diagrammatic form, drawing the circulatory roadway itself with destinations, route shields and
cardinal directions placed around it**.
- Related Guidance/Standards on the page: Destination signs **200 ft or more in advance** in
  high-speed areas and at least 200 ft from a Junction or Advance Route Turn assembly (shorter in
  urban areas); Distance signs list **no more than three** places with the **distance to the nearest
  mile**, numerals to the **right** of the names.

### Figure 2D-12 — Guide Signs for Circular Intersections (PDF 281–284, 4 sheets)
Four cases, each with the full chain and rural spacings (200 ft min, 300 ft ±, 25 to 200 ft beyond,
100 to 200 ft, 400 ft min): **a rural roundabout on numbered routes** (directional assemblies drawn
**rotated to face each approach**, D1-2 "OR" D1-2d with curved arrows); **a county-route roundabout**
with **exit destination signs at the exits** (each above a yellow object marker) and a
**D3-2 advance street-name sign reading "NEXT CIRCLE"**; a variant with the same layout; and
**a multi-lane approach to a circular intersection** where **overhead destination signs with yellow
ONLY panels** are shown "OR" **overhead destination signs alongside separate R3-5 series mandatory
movement lane control signs**.
- **FIND**: at roundabouts the destination signs use **curved arrows**, and the directional shield
  assemblies are **turned to face the approach they serve** — both visual conventions.
- **CHECK**: the "alternate signing at overhead location" panel repeats the Ruling 4 pattern — either
  a regulatory panel inside the guide sign, or separate regulatory signs beside it.

### Figure 2D-13 — Signing for Intersections with Indirect Left Turns (PDF 285–287, 3 sheets;
sheets 1 and 2 Rev. 1)
**A intercepted crossroad with left turns prohibited** — guide signs carrying **NEXT LEFT**,
**KEEP LEFT** and **KEEP RIGHT** legends, shown as two separate signs "OR" one combined sign; a
STOP with a RIGHT TURN ONLY plaque, a ONE WAY sign and a Keep Right sign above a yellow object
marker. **B intercepted crossroad (median U-turn)** — an inset schematic of the whole layout, with
overhead guide signs carrying **yellow ONLY panels and downward arrows**, and a **post-mounted sign
on the left-hand side of the roadway** (drawn rotated). **C continuous flow intersection** — dense
signing with WRONG WAY, DO NOT ENTER, No Left Turn, KEEP LEFT, LANE FOR LEFT TURN ONLY, lane-control
signs and object markers, for both **channelized and non-channelized left-turn lanes**.
- **FIND (layout depends on mounting)**: sheet 3 draws the same guide sign twice — "**location and
  layout when overhead-mounted**" (arrow beside the legend) and "**when post-mounted**" (arrow below
  the legend).

### Figure 2D-14 — Street Name and Parking Signs (PDF 288)
D3-1 street name; **D3-1a with a route shield incorporated**; **D3-2 advance street name signs** with
legends **NEXT INTERSECTION / 2ND INTERSECTION**, **NEXT SIGNAL** and **NEXT CIRCLE**, shown as
stacked panels "OR" a single sign with arrows; D4-1 PARKING (P symbol with arrow) and D4-2 PARK-RIDE.
- Related Guidance: Street Name signs at all urban intersections; **not** at a freeway or expressway
  exit ramp's crossroad intersection displaying the freeway's name to crossroad traffic (to minimise
  wrong-way entries); letter heights per **Table 2D-6**.

### Figure 2D-15 — Interchange Crossroad Guide Signing for a One-Lane Approach (PDF 294)
The full crossroad chain: **JCT shield assembly "OR" a JUNCTION guide sign**, then a
**destination/distance sign**, then **advance route turn assemblies shown three ways — a green guide
sign with shield and arrows, "OR" a single shield sign with cardinal panels, "OR" separate
shield-and-arrow assemblies on one post** — then the ramp direction sign with the Interstate shield
and destination.
- **FIND**: the same information is shown in **three permitted forms** at the same location; the
  choice is illustrated, not written.

### Figure 2D-16 — Minor Interchange Crossroad Guide Signing (PDF 295)
Shield-based signing only: a JCT assembly, then a cardinal-direction shield pair with arrows at the
intersection, then the ramp direction shields. Related **Standard** on the same page: the
**post-mounted Advance Entrance Direction diagrammatic sign shall display only the two successive
turns** from the same side, one of which is the entrance ramp, and **shall not depict lane use with
lane lines, multiple arrow shafts, action messages or other representations**.

### Figure 2D-17 — Multi-Lane Crossroad Guide Signing for a Diamond Interchange (PDF 296)
The chain in green guide signs: JCT assembly "OR" JUNCTION sign; stacked destination signs with
**NEXT LEFT**, **KEEP LEFT** and **KEEP RIGHT** legends, shown as separate signs "OR" one combined
sign; overhead alternatives marked "**mounted overhead**" beside their post-mounted equivalents.

### Figure 2D-18 — Multi-Lane Crossroad Guide Signing for a Partial Cloverleaf (PDF 297)
Adds the **FREEWAY ENTRANCE signs D13-3 and D13-3a** (the latter with a diagonal downward arrow) as
alternatives to a Directional assembly at the ramp, and the ramp-counting legends **NEXT LEFT** and
**SECOND LEFT**. Notes point to 2B.48 and Figure 2B-15 for wrong-way entry treatment.

### Figure 2D-19 — Multi-Lane Crossroad Signing for a Cloverleaf (PDF 298)
Ramp-counting legends **NEXT RIGHT / SECOND RIGHT**, distance legends **EXIT ¼ MILE / EXITS ¼ MILE**,
and a placement instruction written on the artwork: "**Locate on or in front of bridge if freeway
goes over crossroad**".

### Figure 2D-20 — Crossroad Guide Signing for an Entrance Ramp with a Nearby Frontage Road (PDF 299)
Shows a **diagrammatic guide sign drawing the ramp and the frontage road as two branches** "OR" a
conventional sign reading SECOND RIGHT, with a starred note: "**Location for directional assembly or
alternate location for guide sign depending on distance between ramp and frontage road
intersections**".
- **FIND**: the choice between the diagrammatic and the conventional sign is driven by how close the
  ramp and frontage road intersections are — stated only as a figure note.

### Figure 2D-21 — Transposed Alignment Crossroad Guide Signing at a Diamond Interchange (PDF 300)
A diverging diamond: shield assemblies with **TO** banners, combined guide signs pairing a route
shield with "TO" another route, and a JUNCTION sign carrying **½ MILE**.

### Figure 2D-22 — Crossroad Intersection Guide Signs for a Single-Point Urban Interchange (PDF 301)
Plan view of a SPUI with guide signs turned to face each approach, DO NOT ENTER and WRONG WAY signs
at both ramp ends, YIELD signs on the channelized right turns, yellow object markers, and
**tubular markers shown in the legend as a line of dots** along the crossover path. Notes: approach
guide signing per Figures 2D-16 and 2D-17; regulatory signs and signals shown for reference only.

### Figure 2D-23 — Weigh Station Signing, Conventional Road (PDF 303, Rev. 1)
Sequence upstream to downstream: **D8-1a WEIGH STATION AHEAD "OR" D8-1 WEIGH STATION ½ MILE**,
**R13-1 TRUCKS OVER 10 TONS MUST ENTER WEIGH STATION NEXT RIGHT**, **D8-2 WEIGH STATION NEXT RIGHT
with a changeable OPEN / CLOSED panel**, then **D8-3 at the ramp**.
- Figure notes: the D8-1a, D8-1 or D8-2 sign should display the **changeable message OPEN or CLOSED**,
  on the sign or a supplemental panel; the **R13-1 sign only where State law requires trucks of a
  certain weight to enter**.

### Figure 2D-24 — Crossover Signs (PDF 304)
D13-1 CROSSOVER with an arrow; D13-2 CROSSOVER ¼ MILE.

### Figure 2D-25 — Truck and Passing Lane Signs (PDF 304, Rev. 1)
**D17-1 NEXT TRUCK LANE XX MILES**, **D17-2 TRUCK LANE ½ MILE**, **D17-3 NEXT PASSING LANE XX MILES**,
**D17-4 PASSING LANE ½ MILE**.
- Related Guidance: an **extra lane on the right** for trucks gets the Advance Truck Lane sign; an
  **extra lane on the left** for passing gets the Advance Passing Lane sign; where a **series** of
  such lanes exists, the "NEXT …" sign follows each segment.

### Figure 2D-26 — Signing for a Truck Lane (PDF 305, Rev. 1)
The full sequence for an added right-hand truck lane: **D17-1 in advance**, R4-5 TRUCKS USE RIGHT
LANE at the start and repeated, W4-2R lane-ends warning with optional W9-1 and a 1000 FEET plaque at
the end, and **D17-2 beyond** for the next segment; "**optional dotted lane line**" called out.

### Figure 2D-27 — Signing for an Intermittent Passing Lane (PDF 306, Rev. 1)
The mirror case on the left: **D17-3**, yellow diagonal markings at the lane's start and end,
**R4-16 KEEP RIGHT EXCEPT TO PASS**, W4-2L with optional W9-1L and 1000 FEET plaque, and **D17-4**
beyond.
- **FIND**: truck lanes and passing lanes are signed as **mirror images on opposite sides**, with
  different regulatory signs (R4-5 on the right, R4-16 on the left).

### Figure 2D-28 — Emergency and Slow Vehicle Turn-Out Signs (PDF 307, Rev. 1)
D17-5 EMERGENCY TURN-OUT 500 FEET, D17-6 EMERGENCY TURN-OUT with a diagonal arrow, D17-7 SLOW VEHICLE
TURN-OUT ½ MILE. Related Guidance: the advance sign **between ¼ mile and 500 ft** in advance; the
directional sign **near the beginning of the turn-out**; turn-outs used where **no shoulder is
available for emergency stopping or where there is part-time shoulder use (2G.23)**.

### Figure 2D-29 — Signing for an Emergency Turn-Out (PDF 308)
Inside the turn-out: the regulatory **R8-7 EMERGENCY STOPPING ONLY** sign and an **enhanced reference
location sign (D10-5)** showing the route shield with the mile point to a tenth (418.8), so a
stranded driver can report an exact location. Advance signs D17-5 shown as **¼ MILE "OR" 500 FEET**.

### Figures 2D-30 to 2D-32 — Community Wayfinding Guide Signs (PDF 309–311)
- **2D-30**: example signs in **non-standard background colours (blue, purple)** with an **arched
  identification marker** (community logo) above the sign panel.
- **2D-31**: how the system hands off from a freeway — a **brown supplemental guide sign with the exit
  number**, then a **brown destination guide sign** on the crossroad, then the **coloured community
  signs** within the area.
- **2D-32**: a **colour-coded system**, each neighbourhood with its own colour and a header band
  naming it (South Hill purple, Lakefront green, Downtown maroon, Collegetown blue), plus a green
  ENTERING sign at the boundary.
- Related Standards: community wayfinding signs **only on conventional roads**, **never overhead**,
  **never on freeway or expressway mainlines or ramps**, and **never for primary destinations or
  routes**; colour coding applies to a **neighbourhood or geographic subarea, never to types of
  destination**, by **panels to the left of the area name, no more than twice the height of the
  principal legend's upper-case letters**.
- **FIND (a sign that must not be retroreflective)**: pedestrian wayfinding signs "**should not be
  retroreflective**" at night, and should be placed away from the street or turned toward the
  sidewalk — the reverse of the Manual's usual retroreflectivity requirement.

### Figure 2D-33 — National Scenic Byways Sign and Plaque, and Examples of Use (PDF 314)
**A** the M10-1 sign and M10-1aP plaque (the America's Byways logo). **B** three assemblies:
**independent Directional** (M10-1 above an arrow plaque), **independent Confirming** (M10-1 alone),
and **Confirming** (route shield with the M10-1aP plaque beneath).

### Figure 2D-34 — Byway Identification, State Scenic Byway and National Historic Trail Signs (PDF 316)
**A** the sign and plaque set (M10-2 byway name, M10-2aP plaque, M10-3 STATE SCENIC BYWAY, M10-3a
combined, M10-3bP plaque; M11-1 trail marker with M11-1aP HISTORIC ROUTE, M11-1bP CROSSING,
M11-1cP AUTO TOUR ROUTE, M11-1dP NEXT XX MILES) — **all white on brown**.
**B** Directional assemblies shown two ways: "**byway identification emphasized**" (the byway name
sign on top) and "**byway system emphasized**" (the America's Byways or STATE SCENIC BYWAY marker on
top), each above a turn arrow. **C** Directional and Confirming assemblies for historic trails,
including an **END** banner above the trail marker.
- **FIND**: the **order of the signs in the assembly is itself the message** — which of the two is
  emphasised depends on which sits on top.

### Figure 2D-35 — Guide and Directional Signing for a National Historic Trail (PDF 318)
A whole trail network in plan, with the legend distinguishing the **historic trail's original
alignment**, the **trail on the roadway**, the **designated auto tour route** and **other roads**,
plus **trail-related sites**. Signs are drawn rotated to face each approach; BEGIN and END banners
mark trail segments; site identification signs stand at the sites themselves.

### Figure 2D-36 — Historic Trails Signing from an Expressway or Freeway (PDF 319)
**Green** advance and exit direction guide signs carrying the exit number, with a **brown
supplemental guide sign repeating the same exit number** below them, then a **brown destination guide
sign** on the crossroad — shown with three alternative legends.

### Figure 2D-37 — Signs and Plaques for Rerouting Because of Traffic Incidents (PDF 321)
M4-11 EMERGENCY ROUTE with a letter designation and arrow (white on green), **M4-11a with a yellow
EMERGENCY ROUTE header**, M4-11bP / M4-11cP plaques (green and yellow versions), M4-12 END EMERGENCY
ROUTE, and examples of full guide signs pairing the emergency route legend with a route shield.
- **CHECK (supports Ruling 6)**: the advance rerouting sign is drawn as a **yellow "WHEN FLASHING /
  I-78 CLOSED AHEAD" panel over a white "USE EMERGENCY ROUTE NEXT RIGHT" panel, with two Warning
  Beacons mounted above the sign** — the Manual's own illustration of how a WHEN FLASHING message is
  activated, by beacons rather than LEDs in the legend.

### Figure 2D-38 — Permanent Guide Signing for Rerouting Because of Traffic Incidents (PDF 322)
A corridor map with numbered sign locations, a legend distinguishing **single routing** from
**multiple routings**, and, for each case, the alternatives: static emergency-route guide signs "OR"
a **two-phase CMS** ("I-78 CLOSED AHEAD" then "USE EMERGENCY ROUTE EXIT 242"). Optional END EMERGENCY
ROUTE signs are starred.
- **FIND**: the figure pairs **static signs and CMS phases as equivalents** for the same message, and
  shows the CMS wording split across exactly two phases.

### Figure 2D-39 — System of Major Guide Signs for an Airport Roadway Network (PDF 324–326, 3 sheets;
sheet 1 Rev. 1)
Sheet 1 is a **numbered key map** of an airport: terminals, hourly and daily parking, economy lots,
rental cars, cargo, the terminal loop and the freeway exits, with **numbered circles keyed to sign
images on sheets 2 and 3**. Notes: only major guide signs are shown; **the terminal loop is a one-way
counterclockwise roadway**.

### Figure 2D-39 sheets 2–3 — the airport sign catalogue (PDF 325–326)
Seventy-four numbered guide signs keyed to the map: terminals identified by **coloured letter panels
(A, B, C)** carried consistently across arrivals, departures, parking and exit signs; blue general
information signs (AIRPORT INFO TUNE RADIO, GAS LODGING); a PARKING RATES sign; and embedded panels —
a **yellow "CLEARANCE 7'-6"" panel inside a green parking sign** and a **white "NO COMMERCIAL
VEHICLES" panel** beneath another.
- **FIND**: the airport system uses the same colour-coding-by-panel device as community wayfinding
  (Figure 2D-1, 2D-32), here for terminals rather than neighbourhoods.

## Part 2 — Chapter 2E (freeway and expressway guide signs)

### Figure 2E-1 — Designation of Destination for Interchanges in Opposing Directions of Travel (PDF 333)
A corridor with four interchanges, signed for **both directions**, showing that the **destinations
named differ by direction of travel** — each sign names the place ahead of the driver on the
crossroad, so the same interchange carries different legends northbound and southbound.

### Figure 2E-2 — Typical Sequence of Interchange Guide Signs (PDF 346, Rev. 1)
The master diagram, in three match-lined strips, with the whole chain and its spacings:
- **Post-interchange sequence**: end of the acceleration lane taper → **500 ft** → post-interchange
  confirming route assembly (M3-1P + M1-1) → **1,000 ft** → post-interchange Speed Limit sign (R2-1)
  → **1,000 ft** → post-interchange Distance sign (E7-3).
- **Specific service signs** (camping, lodging, food, gas), each **800 ft minimum** apart.
- **Approach sequence**: advance guide sign at **1 MILE**, supplemental guide sign, advance guide sign
  at **½ MILE**, exit direction sign at the **theoretical gore**, and the **E5-1 EXIT gore sign at the
  physical gore**; **800 ft minimum** between signs and **½ mile** between the advance signs; an
  optional **W13-2 advisory exit speed sign** before the ramp.
- **FIND**: the drawing names **"theoretical gore" and "physical gore"** as separate points and hangs
  different signs on each — a distinction the graph needs for exit signing.

### Figure 2E-3 — Interchange Exit Numbering (PDF 348, Rev. 1)
Four schemes: **A without suffixes**, **B with A/B suffixes**, **C** and **D** for closely spaced and
split interchanges, including **numbers reserved for a future interchange**. Legend distinguishes the
**exit number** from the **reference location** (milepost).

### Figure 2E-4 — Interstate Loops and Spurs (PDF 348)
Three-digit Interstate numbering illustrated: **loops** (circumferential, returning to the parent
route) and **spurs** (leaving and not returning), with a legend separating Interstate, non-Interstate
and city boundary.

### Figure 2E-5 — Interchange Numbering for Mainline and Circumferential Routes (PDF 349, Rev. 1)
A beltway with radial routes, numbering interchanges around the circumferential route and along the
mainlines, with **junctions of two Interstate routes marked**, **reference locations** shown, and a
**future interchange** drawn dashed with its number reserved.

### Figures 2E-6 and 2E-7 — Interchange Numbering for Mainline and Loop (Spur) Routes
(PDF 350–351, Rev. 1)
Numbering carried around a loop route and along a spur, with magnified insets showing the exit
numbering inside complex interchanges, and A/B suffixes at the junctions.
- **FIND (figure footnote, an either/or)**: "**The freeway/freeway interchange where the beginning of
  the loop or spur route intersects with the mainline route may be called either Exit 1 or Exit 0 on
  the loop or spur route.**"

### Figure 2E-8 — Interchange Numbering for Overlapping Routes (PDF 352, Rev. 1)
Where two Interstate routes overlap, the interchanges through the shared section carry **one route's
numbering** (the 200-series in the example), with the other route's numbers resuming beyond the
junction.

### Figure 2E-9 — Interchange Advance Guide Signs, Exit Number Plaques and LEFT Plaque (PDF 354)
Advance guide signs with **"2 MILES" "OR" "EXITS 2 MILES"**, and the note "**Delete word EXIT(S) if
exit number is used**"; exit number plaques E1-5P through E1-5eP (single, three-digit, suffixed and
paired "33 A-B" forms); and the **LEFT versions E1-5fP to E1-5kP, each carrying a yellow LEFT panel
inside the green plaque**, plus the standalone **E1-5mP yellow LEFT plaque**.
- **FIND**: a fifth instance of the coloured-panel pattern — the exceptional condition (a left-hand
  exit) is carried on a **yellow panel within the green sign**.

### Figure 2E-10 — Interchange Sequence Sign (PDF 355)
An E9-2 listing three interchanges with distances (¾, 1½, 2).
- Related Standards and Guidance on the page: sequence signs show the **next two (E9-1) or three
  (E9-2)** interchanges with **distances to the nearest ¼ mile**; used **instead of** Interchange
  Advance guide signs where there is **less than 800 ft between the theoretical gores** of successive
  ramps; **installed in a series**, the first in advance of the first interchange's advance guide
  sign; a **LEFT panel immediately to the right of the name or route number** where the exit is to
  the left; and they **shall not be substituted for Exit Direction signs**.

### Figure 2E-11 — Series of Interchange Sequence Signs for Closely-Spaced Interchanges
(PDF 356, Rev. 1)
A corridor with three closely spaced interchanges, showing the sequence signs (E9-1 and E9-2) in the
**median**, interleaved with each interchange's own exit direction and ½-mile advance signs, and the
reference locations marked. Demonstrates the "sign spreading" idea: each interchange still gets its
own exit-number plaques, while the sequence signs carry the distances.

### Figure 2E-12 — Exit Direction Signs (PDF 357, Rev. 1)
E4 series with exit number plaques above, and the LEFT versions (yellow LEFT panel over the plaque,
or the standalone yellow LEFT plaque above an unnumbered left exit sign).
- Related Standards/Guidance: **populations shall not be displayed** on Exit Direction signs;
  post-mounted at the **beginning of the deceleration taper**, overhead **near the theoretical gore**,
  and **overhead if there is less than 300 ft from the beginning of the taper to the theoretical
  gore**; for right exits the exit-number plaque goes **above the top right-hand edge**, for left
  exits **above the top left-hand edge**.

### Figure 2E-13 — Exit Direction Sign Placement (PDF 358, Rev. 1)
Three cases drawn side by side: **less than 300 ft** between theoretical gore and beginning of taper
→ **overhead at the theoretical gore**; **300 ft minimum** → **post-mounted at the beginning of the
taper**; and a third with the exit gore sign at the physical gore. The W13-2 advisory exit speed sign
is starred "location varies, see Chapter 2C".
- Related **Standard**: where a **through lane is dropped** at an exit, the Exit Direction sign
  **shall be overhead at the theoretical gore** (unless Overhead Arrow-per-Lane signs are used).

### Figure 2E-14 — Exit Direction Signs with Advisory Speed Panels and Flashing Yellow Beacons
(PDF 359)
An Exit Direction sign with a **yellow E13-2 advisory speed panel inside the green sign**, shown
"OR" the same sign with **two flashing yellow beacons mounted within the sign border**, one on each
side of the panel.
- **CHECK**: this is the arrangement 4S.01 ¶4 excepts from the rule that beacons are never within a
  sign border. Standard ¶17 here: the beacons' nearest edges **at least 12 in** from the edges of the
  E13-2 panel, from the sign edges and from any other legend.

### Figure 2E-15 — Exit Gore Signs and Plaques (PDF 360)
**E5-1 EXIT with arrow**, **E5-1a EXIT 44 with arrow**, **E5-1c narrow version** (for gores of limited
width), the **E5-1bP number plaque**, the **W13-1aP yellow advisory speed plaque**, and assemblies
combining them.
- Related Standards: the **gore is defined as the area between the main roadway and the ramp just
  beyond where the ramp branches**; an Exit Gore sign at **each exit** from a freeway, expressway or
  collector-distributor roadway; suffix letters **separated from the number by ½ to ¾ of the suffix
  letter's height**; **breakaway or yielding supports**; the narrow E5-1c only where lateral offset
  is insufficient, and where mounted **14 ft or higher the arrow may point diagonally downward**.
- Option: a **Type 1 object marker 4 ft above the ground on each sign support** below the gore sign.

### Figure 2E-16 — Pull-Through Signs (PDF 361)
E6-1 (route shield with cardinal direction) and E6-1a (shield, cardinal direction and control city);
note: **the E6-2 and E6-2a designs are the same with a down arrow added**.
- Related Standard/Guidance: Pull-Through signs **shall display the route shield and cardinal
  direction**; used where the through roadway is not obvious, where through lanes curve while the
  exit runs straight, or where through lanes are reduced; **not at exits with option lanes where
  full-width Overhead Arrow-per-Lane signs are used**.

### Figure 2E-17 — EXIT ONLY and LEFT Sign Panels (PDF 362, Rev. 1)
**E11-1 EXIT ⬇ ONLY** (black on yellow), the retrofit panels **E11-1a EXIT / E11-1b ONLY /
E11-1c EXIT ONLY**, the diagonal-arrow versions **E11-1d** (single-lane drop, arrow between the
words) and **E11-1e** (two-lane drop, arrows outside the words), **E11-1f** with two down arrows, and
the **E11-2 yellow LEFT panel**.
- Related Standards: for lane drops the **bottom portion of the overhead Exit Direction sign shall be
  yellow with a black border and a diagonally upward-pointing black arrow for each dropped lane**;
  **the number of arrows shall correspond to the number of dropped lanes**; each arrow **over the
  approximate centre of the lane being dropped**; retrofit panels placed **either side of the white
  down arrow** on an existing sign.

### Figures 2E-18 and 2E-19 — Guide Signs for a Single-Lane Exit to the Left / Right with a Dropped
Lane (PDF 363–364)
Three-sign sequences (1 mile, ½ mile, exit) with the yellow EXIT ONLY panel on every sign.
- **FIND (arrow convention)**: the EXIT ONLY panel carries a **downward arrow on the advance guide
  signs** and a **diagonal arrow matching the direction of departure on the Exit Direction sign**.
  The left-hand version adds the yellow LEFT panel above each sign.

### Figure 2E-20 — Overhead Guide Signs for a Dropped Auxiliary Lane between Separate Interchange
Ramps (PDF 366, Rev. 1)
Spacings ¼, ¼ and ½ mile; a **pull-through sign with two down arrows** for the through lanes; the
W4-3R added-lane warning where the auxiliary lane begins; W13-2 advisory exit speed near the gore.
- **FIND**: the **1-mile advance sign carries no EXIT ONLY panel** — the panel appears only from the
  point where the auxiliary lane exists.

### Figure 2E-21 — Post-Mounted Advance Guide and Supplemental Warning Signs for a Dropped Auxiliary
Lane (PDF 367)
- **FIND (wording changes with mounting)**: the overhead sign carries **"EXIT ↗ ONLY"**, while the
  **post-mounted** advance sign carries the word panel **"RIGHT LANE ONLY"** with no arrow, plus a
  yellow **W9-7 RIGHT LANE FOR EXIT ONLY** warning sign **600 ft** ahead of the gore.

### Figure 2E-22 — Guide Signs for an Auxiliary Lane of at Least One-Half Mile in Length (PDF 368)
Four signs (1 mile, ½ mile, ¼ mile, exit), the **auxiliary lane length marked "½ mile MIN."**, the
taper marked "varies", and the EXIT ONLY panels appearing from the ½-mile sign onward.

### Figure 2E-23 — Signing for Mainline Terminations within an Interchange (PDF 369, Rev. 1)
**A at an exit ramp**: W4-2 lane-ends warning, yellow **LANE ENDS 500 FEET** and **LANE ENDS ½ MILE**
signs "OR" a post-mounted **RIGHT LANE ENDS ½ MILE**, with the advance guide sign shown post-mounted
"OR" overhead (the overhead version carrying a white down arrow). **B within the interchange**:
W4-2 and optional W9-1R with a 1000 FEET plaque.
- **FIND (an explicit either/or Standard on the artwork)**: "**Either an overhead sign or a
  post-mounted sign, but not both, shall be used.**"

### Figure 2E-24 — Signing for an Intermediate Interchange within a Major Interchange (PDF 370)
Shows both sign systems interleaved on the approach: **JCT 2 MILES**, then the exit sequence at
1 mile, then the intermediate interchange's own signs, plus an **END route sign** where one Interstate
terminates and a **"Woodmore Rd USE I-62 WEST"** sign for a destination reached by another route.

### Figure 2E-25 — Signing for an Interchange Exit Ramp with a Downstream Split
(PDF 371–372, 2 sheets)
**Sheet 1** a single-lane exit that splits on the ramp: the exit sign names both destinations, and the
split itself is signed on the ramp with separate left/right destination signs and a
shield-with-cardinal-directions sign at the ramp gore. **Sheet 2** a **two-lane exit** with the split:
the advance sign carries **"⬇ EXIT ONLY ⬇"** and the ½-mile sign **"↗ EXIT ONLY ↗"** — **two arrows
for two dropped lanes** — with the two destinations divided by a vertical line on the sign.
- **CHECK**: confirms the counting rule from 2E.28 (one arrow per dropped lane) and the arrow
  convention (down on advance signs, diagonal at the exit).

### Figure 2E-26 — Guide Signs for a Minor Interchange (PDF 373, Rev. 1)
The minimum sequence: a ½-mile advance guide sign, an exit direction sign, an exit gore sign, and a
street-name sign on the crossroad; reference locations marked.

### Figure 2E-27 — Guide Signs for a Diamond Interchange (PDF 375, Rev. 1)
The full sequence in both directions (signs for the opposite direction drawn inverted), including the
post-interchange **distance sign ("Newport 4 / Jackson 40")** and the confirming route shield after
the entrance ramp.

### Figure 2E-28 — Guide Signs for a Diamond Interchange in an Urban Area (PDF 376, Rev. 1)
The same sequence compressed for urban spacing, with the street-name sign shown **"OR"** a version
with directional arrows, and, in place of separate advance signs for the next interchanges, an
**interchange sequence sign listing three exits with distances** shown **"OR"** a
**"Springfield NEXT 3 EXITS"** sign.
- **FIND**: the urban case substitutes **one sequence or "NEXT n EXITS" sign** for a series of advance
  guide signs — the same sign-spreading idea seen in Figure 2E-11.

### Figure 2E-29 — Guide Signs for a Full Cloverleaf Interchange (PDF 377, Rev. 1)
Distant advance signs combine both exits as **"EXITS 102 A-B"** (2 miles, 1 mile); the signing then
**splits into separate signs for 102 A and 102 B** at ¼ mile and at each exit; a post-interchange
distance sign follows.

### Figure 2E-30 — Full Cloverleaf with Collector-Distributor Roadways (PDF 379, Rev. 1)
The same interchange with C-D roadways: the mainline carries **one exit to the C-D roadway**, and the
individual ramp signing happens **on the C-D roadway**, with alternatives shown "OR" (a combined
"EXITS 102 A-B" sign, or separate A and B signs; pull-through shields on the C-D roadway).

### Figure 2E-31 — Partial Cloverleaf Interchange (PDF 380, Rev. 1)
Both directions drawn (opposite-direction signs inverted); exit direction sign, ½- and 1- and 2-mile
advance signs, exit gore sign, and **optional crossroad shield assemblies** at the ramp terminals.

### Figure 2E-32 — Successive Interchanges with Collector-Distributor Roadways
(PDF 381–382, 2 sheets, Rev. 1)
Sheet 1: two successive interchanges sharing a C-D roadway, signed with a **combined "EXITS 36-37"**
sign on the mainline and separate exit signs on the C-D roadway. Sheet 2: three successive exits with
a combined **"EXITS 68-67-66"** sign, pull-through signs with down arrows, and **specific service
signing shown in two forms — a small blue word sign ("GAS-FOOD EXIT 66") "OR" a full blue logo panel
sign**, plus a "GAS-FOOD-LODGING NEXT RIGHT" sign.
- **FIND**: the same service message may be a **word sign or a logo panel sign**; the figures treat
  them as equivalents.

### Figure 2E-33 — Guide Signs for a Freeway-to-Freeway Interchange (PDF 383–384, 2 sheets)
**A: a two-lane exit ramp with two dropped lanes and a bifurcation beyond the mainline gore.**
The approach carries **pull-through signs with a down arrow for the through route** opposite each
exit sign; the exit signs carry **two arrows on the EXIT ONLY panel** (down on the advance signs,
diagonal at the exit) and **split the two destinations (I-17 NORTH Miami / I-17 SOUTH Portland) by a
vertical divider**; beyond the gore the ramp's own bifurcation is signed with separate
shield-and-arrow signs.

### Figure 2E-33 sheet 2 (PDF 384)
**B: successive exit ramps with a dropped lane at the second exit.** Combined **"EXITS 215 A-B"**
advance signs with the EXIT ONLY panel; separate signs for 215 A and 215 B nearer the exits; and
**pull-through signs whose number of down arrows tracks the number of through lanes remaining**
(two arrows upstream, one after the drop), some marked optional.

### Figure 2E-34 — Guide Signs for a Split with Dedicated Lanes (PDF 386)
A split where each route has its own dedicated lanes: the left route's sign carries the yellow
**EXIT ONLY panel with two arrows** (two dedicated lanes), the continuing route's sign carries plain
**down arrows over its own lanes**, and both are repeated at 2 miles, 1 mile and two half-mile points,
with a yellow **LEFT** panel over the left route's exit number.

### Figure 2E-35 — Overhead Arrow-per-Lane Guide Sign for a Multi-Lane Exit with an Option Lane
(PDF 387, Rev. 1)
The sign itself: **one upward arrow per lane**, the **option lane drawn as a bifurcated arrow**
(straight plus curving right), destinations divided by a vertical line, and the yellow **EXIT** and
**ONLY** panels placed **beneath the particular arrows they apply to**.
- Related Standards (2E.40): Arrow-per-Lane signs **shall** be used at all new or reconstructed
  freeway and expressway multi-lane exits and splits with an option lane; the sign at the exit is
  located **where the exiting lanes begin to diverge**, and **shall not be at or near the theoretical
  gore**; **new installations of Exit Direction and Pull-Through signs are not permitted with
  Arrow-per-Lane signs**; Guidance places them at about **½ mile and 1 mile** in advance, and **2
  miles** where space allows.

### Figure 2E-36 — Two-Lane Exit to the Right with an Option Lane (PDF 389)
The full sequence with Arrow-per-Lane signs at 1 mile and ½ mile: three straight arrows for the
through lanes, a bifurcated arrow for the option lane, a curved arrow for the exit lane, and the
EXIT / ONLY panels beneath those two.

### Figure 2E-37 — Two-Lane Exit to the Right with an Option Lane, Through Lanes Curving Left
(PDF 390)
- **FIND (arrows follow the real geometry)**: because the through lanes **curve left while the exit
  runs straight**, the through arrows are drawn **curving left**, the option lane is bifurcated, and
  the **straight-up arrow belongs to the exit**, with EXIT ONLY beneath it. The arrows depict the
  actual paths, not a schematic straight-ahead.

### Figure 2E-38 — Overhead Arrow-per-Lane Guide Signs for a Split with an Option Lane (PDF 391)
The same design at a split: a left-curving arrow for the left route, a **Y-shaped bifurcated arrow
for the option lane**, a right-curving arrow for the right route, EXIT and ONLY panels beneath, and
the sequence repeated at 2 miles, 1 mile and the split.

### Figures 2E-39 and 2E-40 — Guide Signing for a Narrow Gore at a Split / Two-Lane Exit with an
Option Lane (PDF 393–394, Rev. 1)
Drawn in match-lined strips. The Arrow-per-Lane signs sit back at the **beginning of the lane
diverge**; separate conventional destination signs (with diagonal arrows and an EXIT ONLY panel)
appear at the **theoretical gore**; the **narrow E5-1c gore sign** is used in the narrow gore; the
distance between the two points is marked **800 ft MIN**.

### Figure 2E-41 — Diagrammatic Advance Guide Signs (PDF 395, Rev. 1)
Four cases: **A through route on an off-movement**, **B through route with complex geometry and
reduced speed** (carrying a **yellow "RAMP 35 MPH" panel inside the green sign**), **C split at the
terminus of an expressway route**, **D successive exit ramps from opposite sides of a roadway**.
- Related Guidance (2E.41 ¶4 A–G): **no more than one destination per movement**; the **arrowhead for
  the diverging movement positioned lower** than the through movement's (equal heights at splits);
  **arrow shaft widths equal for all movements**; shields, cardinal directions and destinations
  placed so they clearly relate to their arrowhead; the **control destination for the through route
  omitted** where two exits are shown; and rules for where the distance legend goes.

### Figure 2E-42 — Diagrammatic Advance Guide Sign Use (PDF 396)
The full approach: a 2¼-mile diagrammatic sign, then conventional advance signs at 2 miles, 1½ miles,
1 mile and ½ mile for each exit, then the exit direction signs — with the yellow LEFT panel on the
left-hand exit's signs throughout.

### Figure 2E-44 — Two-Lane Intermediate or Minor Interchange Exit with an Option Lane and a Dropped
Lane, using **Partial-Width** Overhead Arrow-per-Lane Signs (PDF 398)
The sign spans **only the option and exit lanes**, not the full roadway, at 1 mile, ½ mile and the
exit; an **inset** shows the alternative where an **existing sign support structure is retained** —
a conventional sign with the two-arrow EXIT ONLY panel.

### Figure 2E-45 — Two-Lane Intermediate or Minor Interchange Exit with Option and Auxiliary Lanes,
using Partial-Width Overhead Arrow-per-Lane Signs (PDF 399)
Same idea with an auxiliary lane; the artwork labels the two permitted positions — "**located at the
point of departure of the option lane**" and, in the inset, "**located at the theoretical gore**"
where an existing structure is retained, the latter using **diagonal arrows** instead of the
per-lane arrows.
- **FIND**: the sign's **legend changes with its position** — per-lane arrows at the point of
  departure, diagonal arrows at the theoretical gore.

### Figures 2E-46 and 2E-47 — Two-Lane Intermediate or Minor Interchange Exit with an Option Lane
(conventional signing) (PDF 400–401)
The non-Arrow-per-Lane alternative: conventional guide signs with **two-arrow EXIT ONLY panels**
(diagonal at the exit, down on the advance signs) or, with an auxiliary lane, **two diagonal arrows
and no EXIT ONLY panel**; **optional post-mounted R3-8 lane control signs** between them; spacings
marked **800 ft MIN** and ½ mile.

### Figure 2E-48 — Sign Spreading (PDF 403)
Two gantries before and after spreading, with each sign's **"units of information"** counted on the
artwork: **before — Location 1 carries 4 + 5 + 5 = 14 units** and Location 2 carries 5;
**after — Location 1 carries 10 units and Location 2 carries 9**.
- **FIND (a countable measure)**: the figure quantifies sign load in units of information and shows
  the remedy — moving a sign to the next structure. This is the picture behind 2E.43's limit of
  three guide signs at one overhead location.

### Figure 2E-49 — Next Exit Plaques (PDF 405)
E2-1P (wide) and E2-1aP (tall) NEXT EXIT XX MILES plaques.
- Related Guidance/Standard: **not used unless the distance between successive interchanges is more
  than 5 miles**; the wide version where the advance guide sign is at least as wide as the plaque,
  the tall version where the plaque would be wider; mounted **below the Interchange Advance guide
  sign nearest the interchange**, without affecting the breakaway support.

### Figures 2E-50 and 2E-51 — Post-Interchange Distance and Travel Time Signs (PDF 406, Rev. 1)
E7-3 three-line distance sign (junction, community of general interest, control city) and the
**E7-4 travel time sign with changeable message elements displaying MINS**.
- Related Standards: the **bottom line carries the control city**; distances to the same destination
  **not shown more often than at 5-mile intervals** and given as **actual distances to the
  destination, not to the exit**; the travel time sign **replaces** the distance sign in the
  post-interchange series; **travel times shall not be used on Interchange guide signs**.

### Figure 2E-52 — Travel Time Signs (PDF 407, Rev. 1)
**A Distance and Travel Time signs (E7-5)** — destination, distance in miles, and travel time in a
changeable element followed by MINS, limited to **one destination or junction**. **B Comparative
Travel Time sign (E7-6)** — one destination reached **two ways**, each route on its own line with its
own changeable travel time, one line carrying a **yellow TOLL panel**.
- Related Standard: comparative travel times **shall not be used to promote different modes of
  travel** (e.g. highway versus transit, or different forms of transit).

### Figures 2E-53 and 2E-54 — Supplemental Guide Sign for a Multi-Exit Interchange; Supplemental
Guide Signs for a Park-and-Ride Facility (PDF 408, Rev. 1)
A two-destination supplemental sign (each name with its own EXIT number), and PARK-RIDE signs in two
forms — **A with an exit number**, **B "NEXT RIGHT"** where the route is not exit-numbered — each
carrying the carpool pictograph.
- Related Standards/Guidance: **no more than two supplemental traffic generator destinations signed
  from a single interchange approach and four from a single interchange** along the roadway; **no more
  than one supplemental guide sign per approach**, showing **no more than two destinations and three
  lines**; placed **midway between two advance guide signs** or at least **800 ft** after a single
  one; a **transit pictograph on the same line as the carpool symbol**, its height **no more than
  twice the upper-case letter height**; park-and-ride and recreational/cultural signs count as
  supplemental guide signs.

### Figures 2E-55 and 2E-56 — Community Interchanges Identification Sign and its Use
(PDF 409–410, Rev. 1)
The E9-4/E9-5 sign lists a community name followed by **EXITS**, then each street or destination with
its distance to the nearest ¼ mile. The use figure shows it placed **in advance of the first
interchange serving the community**, with the **community name then omitted** from each interchange's
own advance and exit direction signs.
- **FIND**: the sign exists to stop the same community name repeating on every interchange sign — the
  figure shows the before/after division of information.

### Figures 2E-57 and 2E-58 — Next Exits Sign and its Use (PDF 411–412, Rev. 1)
The E9-3 sign ("Lanford NEXT 4 EXITS") placed ahead of the first interchange, with the region or area
name then **omitted from the individual interchange signs**; used where interchanges are not
conveniently identifiable or **more than three** are to be identified.

### Figure 2E-59 — Weigh Station Signing on Freeways (PDF 413)
The freeway sequence: **D8-1 WEIGH STATION 1 MILE**, the regulatory **R13-1 "use only if required by
law"**, **D8-1 ½ MILE "OR" D8-2 NEXT RIGHT**, **D8-3 at the ramp** (twice), and an optional
**W13-2 advisory exit speed**; **800 ft Min.** marked between signs.
- Figure notes: the D8-1 or D8-2 sign should include a **changeable message element displaying OPEN or
  CLOSED — within the sign border below the legend, or mounted below the sign, as a white legend on a
  black background**; and **"COMMERCIAL VEHICLE INSPECTION AREA" may be substituted for "WEIGH
  STATION" on all D8 series signs**.

### Figure 2E-60 — Interstate, Off-Interstate and U.S. Route Signs (PDF 414)
**A for guide sign and independent use** — Interstate M1-1 (two and three digit) and the green
Business Loop/Spur shields. **B for guide sign use** — the U.S. Route shield as a **cutout**.
**C for independent use** — the same shield **on a black square background**.
- **FIND**: the U.S. Route marker has **two forms**, cutout on a guide sign and black-background when
  standing alone. Related Guidance: route signs along a freeway enlarged to **36 × 36 in** (one or two
  digits) and **45 × 36 in** (three digits).

### Figure 2E-61 — Eisenhower Interstate System Signs (PDF 415)
M1-10 and M1-10a.
- Related Standards: **M1-10a only in rest areas or similar facilities** where it can be seen by
  people in parked vehicles or on foot, and **never on mainlines, ramps or roadways where vehicular
  traffic can view it**; neither sign is ever part of a Junction, Advance Route Turn, Directional or
  Trailblazer assembly, or of a guide sign giving direction.

### Figure 2E-62 — Signing for Route Diversion by Vehicle Class (PDF 417)
A network diagram routing hazardous-materials traffic around a tunnel. Legend distinguishes the
**direct through route** from the **route for diverted vehicles**. Signing uses **white "NO HAZMATS"
and "ALL HAZMATS" panels inside green guide signs**, standalone white regulatory signs ("ALL HAZMATS
MUST EXIT NEXT RIGHT", "…MUST EXIT 2 MILES"), and a diversion sign with a **yellow "TUNNEL 11 MILES"
header band** over a white panel.

## Part 2 — Chapter 2F (toll roads)

### Figure 2F-1 — ETC Account Pictographs and Use of Purple Backgrounds and Underlay Panels
(PDF 423)
**A** a pictograph that already has a **purple background with a white contrasting border** — used
directly, on purple or on a contrasting background. **B** a pictograph with **any other background
colour** — it must sit in a **purple underlay panel with a white contrasting border**, whether the
sign behind it is purple, another colour, or white.
- The "HOV 2+ ONLY" legend again appears on a **white panel**, consistent with Ruling 4.

### Figure 2F-2 — Toll Plaza Regulatory Signs and Plaques (PDF 424, Rev. 1)
**R3-28 Toll Rate** sign (toll by axle count) and the **R3-29P PAY TOLL / R3-30P TAKE TICKET** plaques.
- Related Standards/Guidance: **a STOP sign shall not be installed for an ETC-Only lane designed for
  tolls collected while moving**; a Speed Limit sign **not** used where a STOP sign controls the lane;
  the toll rate sign **no more than three lines**, each showing a single toll amount, placed between
  the plaza and the first advance sign; mounting heights and the **1-ft minimum lateral offset**
  allowed within a toll island.

### Figure 2F-3 — ETC Account-Only Auxiliary Signs for Use in Route Sign Assemblies (PDF 425)
**R3-31** — the ETC pictograph with **ONLY in black on a white panel set on the sign's purple
background, with a white border**; **R3-32P NO CASH** plaque (black on white); and an example route
assembly stacking **W16-17P TOLL (yellow) / M3-2P EAST / M1-4 shield / R3-31 / M5-1P arrow**.
- Related Standard: in any route sign assembly directing traffic to a toll facility where **ETC is the
  only payment method**, the R3-31 sign **shall** be mounted directly below the route sign.
- Figure note: **the ETC pictograph shown is an example only — the toll facility's own adopted
  pictograph shall be used.**

### Figure 2F-4 — Toll Plaza Warning Signs and Plaques (PDF 427, Rev. 1)
W9-6 series (PAY TOLL / STOP AHEAD PAY TOLL / TAKE TICKET, with distances and toll amounts) and
**W16-16P / W16-16aP LAST EXIT BEFORE TOLL** — all black on yellow.

### Figures 2F-5 to 2F-7 — Crossroad Signing for Approaches to a Toll Highway (PDF 429–431)
Minor interchange, one-lane approach and multi-lane diamond cases. Every route assembly and guide
sign leading to the toll facility carries the **yellow TOLL plaque or a black-on-yellow TOLL panel
incorporated into the green sign**; alternatives are shown "OR" (shield assemblies vs combined guide
signs, post-mounted vs "mounted overhead").
- Related Standard: a **TOLL (W16-17P) plaque above the route sign** in any route assembly directing
  traffic to a numbered toll facility; **a rectangular black-on-yellow TOLL panel incorporated into
  guide signs** leading to a tolled highway, except where a State Toll Route sign is used and except
  on Exit Gore and D1 destination signs; toll guide signs otherwise **white on green**.

### Figure 2F-8 — Guide Signs for Entrances to Toll Highways or Ramps (PDF 432)
**A** entrance where registration is not required — green sign with a **yellow TOLL panel**.
**B** entrance to an **ETC Account-Only** highway — a **purple header panel carrying the pictograph
and a white ONLY panel**, above the green sign with its yellow TOLL panel.
**C** entrance to a **non-toll highway via an ETC-only ramp**, shown two ways: where the toll entrance
is the only connection, and where an alternate non-toll entrance exists — the latter a **split sign
with a yellow NO TOLL panel beside a purple ETC-only panel**.
- **CHECK (this states the panel principle in the text)**: 2F.12 ¶10 — "regulatory and/or warning
  messages may be combined with guide signs … using plaques, header panels, or rectangular regulatory
  or warning panels incorporated within the guide signs, **as long as the proper legend and background
  colors are preserved**", and **¶11: regulatory messages within a guide sign go on a rectangular
  panel with a black legend on white; warning messages on a black legend on yellow.** This is the
  general rule behind Ruling 4 (occupancy on a regulatory panel, never on the green field).
- Related Standard: **Interstate, Off-Interstate and U.S. Route signs shall not be modified for tolled
  facilities**; a State Toll Route sign must carry the word TOLL in the W16-17P plaque's letter
  height, colours and dimensions.

### Figure 2F-9 — Conventional Toll Plaza Advance Signs (PDF 433)
A purple ETC-only lane sign with pictograph, white ONLY panel and a down arrow; and a green advance
sign with a **yellow "PAY TOLL 1 MILE" header band** over lane-specific panels — **EXACT CHANGE 75¢
with the M4-18 symbol panel and a white "CARS ONLY / NO TRAILERS" panel**, and **CASH-CHANGE RECEIPTS
with the M4-17 Toll Collector symbol panel**, each labelled by lane group.
- Related Standards: attended lanes **shall** carry the **M4-17 Toll Collector symbol panel**; exact
  change lanes **shall** carry the **M4-18 symbol panel and the passenger-vehicle toll amount**; these
  symbol panels are **only panels within guide signs, never independent signs**; ETC-only lanes carry
  the facility's pictograph and the regulatory ONLY message; an **Overhead Arrow-per-Lane guide sign
  is used in advance of a split into open-road ETC lanes and toll plaza lanes only where an option
  lane exists at the split**.

### Figure 2F-10 — Overhead Arrow-per-Lane Guide Sign and Arrow for a Split with an Option Lane
(PDF 434)
One sign combining every convention: a **purple ETC panel with the pictograph and white ONLY panel**
on the left, a **yellow "PAY TOLL ½ MILE" header** over the FULL SERVICE side with the **M4-17 and
M4-18 symbol panels**, per-lane arrows, and the **Y-shaped option-lane arrow**, shown enlarged beside
the sign ("see the Standard Highway Signs publication for details").
- Related Option: the ETC pictograph **without** a purple underlay or header panel may be used on
  Exact Change or attended lane signs to show that registered ETC vehicles may also use those lanes.

### Figure 2F-11 — Split with an Option Lane for a Mainline Toll Plaza on a Diverging Alignment from
Open-Road ETC Lanes (PDF 435)
Match-lined strips: the Arrow-per-Lane sign at the **beginning of the lane diverge**, separate ETC and
toll plaza signs at the **theoretical gore** (the plaza side carrying a **yellow "STOP AHEAD PAY TOLL"
header**), **800 ft MIN** between them, and a **W12-1 double-arrow warning sign** at the splitter.

### Figure 2F-12 — Guide Signs for the Entrance to a Toll Highway Collected Electronically Only
(PDF 436–438, 3 sheets)
**A all tolls billed by licence plate recognition** — no account needed; signs carry the yellow TOLL
panel, a **toll rates sign with changeable message elements** showing the price to each destination,
and white **"BILLED BY MAIL ONLY"** and **"NO CASH"** panels; spacings **800 ft MIN**.
**B registration in an ETC account required** — every sign carries the **purple ETC panel with ONLY**
above the green legend, including the exit gore sign ("EXIT 76" shown "OR" the same with the purple
panel above).
**C billed by either method** — plain toll signing, with the rates sign footnoted "**show only
non-discounted rates**" and the "BILLED BY MAIL **OR** [pictograph]" panel.
- **FIND**: the sign set changes with the **payment model**, not the geometry — three different
  approaches to the same interchange.

### Figure 2F-13 — Alternative Toll and Non-Toll Ramp Connections to a Non-Toll Highway (PDF 439)
Two ramps to the same destination, one tolled and one not: exit signs distinguished by the **purple
ETC panel** (Exit 79 A) versus a **yellow NO TOLL panel** (Exit 79 B), a **"TO 10 VIA Southdale Rd /
NO TOLL / EXIT 79 B"** sign, and a combined **"10 EXITS"** sign listing both routes with their
distances — the tolled line with the purple panel, the free line with the yellow NO TOLL panel.

### Figure 2F-14 — Mainline Toll Plaza Approach and Canopy Signing (PDF 441, Rev. 1)
**A all lanes attended** — yellow W9-6 series advance signs and R3-28 toll rate signs only.
**B exact change and attended lanes** — the same advance sequence plus **green canopy signs with the
M4-18 and M4-17 symbol panels, a white "CARS ONLY / NO TRAILERS" panel and down arrows**, under a
**yellow header band** ("STOP AHEAD-PAY TOLL", "PAY TOLL ½ MILE", "PAY TOLL 1 MILE").

### Figure 2F-15 — Mainline Toll Plaza on a Diverging Alignment from Open-Road ETC Lanes (PDF 442, Rev. 1)
The **open-road electronic toll collection point** is labelled on the artwork; purple ETC signs with
down arrows sit over the ORT lanes while the plaza side carries the symbol-panel signs with a yellow
header; lane-group legends ("LEFT LANES", "RIGHT LANES") appear beneath the canopy signs.

### Figure 2F-16 — Toll Plaza Canopy Signs (PDF 443)
Three canopy signs: **attended lane (green, M4-17 symbol, CASH-CHANGE RECEIPTS)**, **exact change or
ETC lane (green, M4-18 symbol, "EXACT CHANGE 75¢ OR [pictograph]", white NO TRUCKS panel)**, and
**ETC Account-Only lane (purple, pictograph and white ONLY panel)** with **optional flashing yellow
beacons above**.
- Related Standards: a canopy sign **above the approximate centre of each lane that is not an
  open-road ETC lane**; **purple background for an ETC Account-Only lane**; beacons mounted directly
  above or alongside, **separated from the lane-use control signals**; lane-use control signals give
  **open/closed status only and shall not be used to call attention to a payment type**.

## Part 2 — Chapter 2G (preferential and managed lanes)

### Figure 2G-1 — Preferential Lane Regulatory Signs and Plaque (PDF 451–452, 2 sheets; sheet 2 Rev. 1)
**A post-mounted** — white legend on black, each with the **white diamond at the top** (R3-10 series
occupancy signs, R3-11 series lane designations including BUSES ONLY and SHOULDER variants, R3-12
series lane-ends signs, and the R3-11hP MOTORCYCLES ALLOWED plaque).
**B overhead** — black legend on white with a **black diamond panel at the left**, plus BUSES-TAXIS
ONLY, lane-ahead and lane-ends versions.
- **FIND (a signal inside a sign)**: sheet 2 shows that **a lane-use control signal may be
  incorporated into an overhead preferential lane regulatory sign** to show reversible-lane status —
  a **green down arrow for lane open, a red X for lane closed**, set into the sign face.
- Notes on both sheets: the occupancy requirement **varies by facility (2+, 3+, 4+)**, may be **added
  to the first line** of the lane-ends signs, and the legends shown are **examples only**, to be set
  by local ordinance or State statute.
- **CHECK (supports Ruling 4)**: the occupancy legend lives on these **regulatory** signs — white on
  black or black on white — not on green guide signs.

### Figure 2G-2 — Signing for an Added Continuous-Access Contiguous or Buffer-Separated HOV Lane
(PDF 454, Rev. 1)
The full sequence: advance R3-15 signs at 1 mile and ½ mile, the overhead R3-14 at the lane's start,
then **R3-10 and R3-11a sets repeated at ½-mile intervals along the lane** (and after entrance ramps),
and the R3-12b / R3-15b lane-ends signs. Spacings marked ½ mile, ¼ mile and **800 ft MIN**; the HOV
diamond marking is drawn in the lane.
- Figure notes: occupancy and hours **vary by facility**; the signing applies to **part-time or
  full-time** HOV restrictions; where the median is too narrow, the **post-mounted designs may be
  used** instead of overhead.

### Figure 2G-3 — General-Purpose Lane that Becomes a Continuous-Access HOV Lane (PDF 455)
The mirror of 2G-2: "HOV 2+ ONLY BEGINS 1 MILE" in advance, the overhead R3-14 where the restriction
starts, R3-10/R3-11a sets at ½-mile intervals, and "HOV RESTRICTION ENDS" at the far end.
- Figure note: **the same scheme may be used for an HOV lane on the right-hand side** of the roadway.

### Figure 2G-4 — Warning Signs and Plaques Applicable Only to Preferential Lanes (PDF 459)
**A barrier-mounted rectangular warning signs** — a **vertical rectangle with a black top carrying the
white diamond and a yellow bottom carrying the black warning legend** (modified W4-1L, W4-2L and
W13-2). **B the W16-11P HOV plaque** (black on yellow) for mounting above a standard diamond warning
sign.
- **FIND (two colour systems in one sign)**: the Standard allows this hybrid **only** where a warning
  sign applicable solely to a preferential lane is installed on a median barrier with limited lateral
  clearance; the note adds that for other preferential lane types the appropriate symbol or word
  message appears in white on the black upper portion.

### Figures 2G-6 and 2G-7 — Preferential Lane Entrance Direction Signs; Entrance Gore Signs
(PDF 462)
E8-2 (overhead) and E8-2a (post-mounted) HOV LANE ENTRANCE signs — **green with a black panel
carrying the white diamond**; E8-1 / E8-1a entrance gore signs, same construction, vertical format.
- **FIND (a changeable element inside a guide sign)**: "a changeable message sign may be incorporated
  into an overhead Preferential Lane guide sign to indicate the status of a reversible operation" —
  drawn as **"HOV LANE / ENTRANCE" when open and "HOV LANE / CLOSED" when shut**.
- **CHECK (the Standard behind Ruling 4, printed on this page)**: 2G.10 ¶11 — "The diamond symbol
  shall be displayed in the legend of each Preferential Lane guide sign at the designated entry and
  exit points … **Guide signs shall not display the occupancy requirement** for the preferential
  lane", and ¶12 — "**A combination of guide and regulatory signs shall be used** in advance of and at
  the initial entry point and all intermediate entry points".

### Figures 2G-8, 2G-9 and 2G-10 — Advance Guide and Entrance Direction Signs for Preferential Lanes
(PDF 465–467; 2G-8 Rev. 1)
**2G-8 a general-purpose lane that becomes a preferential lane**: advance guide signs at 2 miles,
1 mile, ½ mile and ¼ mile, each with a **yellow LEFT panel above and a yellow "⬇ ONLY" panel below
the green**, with the **occupancy on separate white regulatory signs (R3-13a, R3-14)**; an
**HOV EXITS** sign listing destinations served; **800 ft MIN** at the lane's start.
**2G-9 an entrance to access-restricted HOV lanes**: the same sequence at **¼-mile intervals**, but
**without the yellow ONLY panels** — no lane is being dropped.
**2G-10 an intermediate entry** to a barrier- or buffer-separated lane: entrance signs at 1 mile,
½ mile and the opening, with the regulatory occupancy sign between them.
- Figure notes across all three: for a right-hand preferential lane the **same sequence is used with
  adjusted wording**; a **CMS may be located where marked** for reversible or counter-flow operation;
  destinations may be augmented on Interchange Sequence signs; the **E8-1 gore sign is for
  barrier-separated facilities only**.

### Figures 2G-11 to 2G-13 — Intermediate Entry, Egress and End of Access-Restricted HOV Lanes
(PDF 468–471; 2G-11 Rev. 1)
**2G-11** carries a **proportional dimension**: the entrance sign is placed at **0.25 L to 0.5 L**
along the access opening, where L is the opening's length; the "barrier, buffer, or contiguous access
prohibition" is labelled on the artwork; E8-5 / E8-6 "TO route" signs appear within the lane.
**2G-12** the barrier-mounted egress signs E8-5 (arrow) and E8-6 (distance) — **vertical green signs
with a black panel carrying the white diamond on top**.
**2G-13** intermediate egress, with the legend shown two ways: **"TO 42 Runnemede" "OR" "TO EXITS 48
TO 52"** — a destination or the range of exits reachable.
- **CHECK (wording by movement)**: 2G.12 ¶6 — advance guide and entrance direction signs for
  intermediate entry points **shall not include the word "EXIT"**; 2G.13 ¶2 — egress signs **shall not
  refer to the egress as an exit**. Advance guide signs for intermediate entry **shall be overhead**.

### Figures 2G-14 to 2G-16 — Direct Entrance and Exit Ramps for Preferential Lanes (PDF 472–473)
**2G-14** a direct entrance ramp from a park-and-ride facility and a local street, for a **reversible**
HOV lane; notes require **additional signs on adjoining surface streets telling non-HOVs not to
enter**, and the word **ENTRANCE** on local-street guide signs where the ramp does not pass through a
park-and-ride facility. **2G-15** the **E8-4 EXIT gore sign for a direct exit from a preferential
lane**. **2G-16** direct entrance and exit ramps, with HOV EXIT guide signs at 1 mile, ½ mile and the
ramp, and an HOV EXITS sign listing destinations.
- **FIND (the "exit" rule is about direction, not the facility)**: the word EXIT **is** used for a
  **direct exit from the preferential lane to another facility** (E8-4), while it is **barred** for
  movements between the preferential lane and the general-purpose lanes.

### Figure 2G-17 — Direct Access Ramp between HOV Lanes on Separate Freeways (PDF 474)
**This is the figure behind Ruling 4.** Examined at high zoom, its guide signs carry a **white header
panel with a black legend ("HOV EXIT", "HOV LANE") and the black-and-white diamond square at its
left**, above a green body with the route shield, cardinal direction and arrow; a yellow LEFT panel
sits above. The "HOV EXITS" summary sign is shown two ways — **all direct exits to the left**, or
**not all to the left** (with a yellow LEFT panel beside the individual line).
- **CHECK (settles the mechanics of Ruling 4)**: note 3's instruction to add the occupancy level "to
  the guide signs" where levels vary between facilities is satisfied by placing it in that **white
  header panel** ("HOV 2+ EXIT") — the black-on-white regulatory panel required by 2F.12 ¶11 — leaving
  the green field free of any occupancy legend, as 2G.10 ¶11 requires.

### Figure 2G-18 — Regulatory Signs for Managed Lanes (PDF 477, Rev. 1)
R3-40 and R3-43 occupancy signs; R3-42 series EXPRESS LANE / EXPRESS RESTRICTION ENDS; **R3-44 (ETC
pictograph + ONLY), R3-44a (pictograph "OR HOV 2+ ONLY"), R3-44b (EXPRESS ONLY)**; and the toll rate
signs **R3-48 / R3-48a — a green "EXPRESS LANE" header over destination lines whose prices are
changeable message elements**, the R3-48a adding a white "HOV 2+ NO TOLL" line.
- **FIND (a changeable occupancy)**: the last example on the sheet is "an example of a regulatory sign
  with changeable message elements" — **the occupancy figure itself ("HOV **2+** / **2** OR MORE
  PERSONS PER VEHICLE") is changeable**, for facilities that vary the requirement.
- Figure note: **changeable message sign elements shall be used for the numerals displayed for the
  variable tolls.**

### Figure 2G-19 — Guide Signs for Entrances to Priced Managed Lanes (PDF 478)
**A** from a general-purpose lane, shown two ways — a **purple header (pictograph + ONLY)** over the
green EXPRESS LANE ENTRANCE sign, or a **white header reading "Toll Pass OR HOV 2+ ONLY"**.
**B** a direct entrance from a crossroad.
- **CHECK (this is the Standard cited in Ruling 4, printed with its figure)**: 2G.19 ¶3 — for a priced
  managed lane allowing **non-toll HOV travel without registration**, "the header panel **shall be
  modified to a regulatory format** to display both the pictograph … and **the minimum occupancy
  requirement** for non-toll travel **with a black legend on a white background**". The occupancy thus
  appears in a **white regulatory header**, never on the green field.

### Figures 2G-20 to 2G-23 — Entrances to Access-Restricted Priced Managed Lanes (PDF 479–482)
- **2G-20 registration not required**: the purple header is **replaced by a yellow TOLL header**
  (2G.19 ¶5); optional signs read "TOLL BILLED BY MAIL ONLY" or "TOLL BILLED BY MAIL OR
  [pictograph]"; a **comparative travel time sign for parallel lanes** shows "VIA EXPRESS LANE 32 MINS
  / LOCAL LANES 46 MINS" in changeable elements; spacings ¼ mile and **800 ft**.
- **2G-21 ETC account required**: the same sequence drawn for **two cases side by side** —
  **(1) all vehicles need a registered account → purple header with ONLY**; **(2) all except HOVs need
  an account → white header "Toll Pass OR HOV 2+ ONLY"** — with the note that **if registration is
  required even for non-toll HOV travel, case (1) signing shall be used**.
- **2G-22 a general-purpose lane that becomes the managed lane**: the same two cases plus a
  **third (yellow TOLL header) for licence-plate billing**, each guide sign also carrying a
  **yellow "⬇ ONLY" panel** because a lane is being taken.
- **2G-23 an intermediate entry** to a barrier- or buffer-separated priced lane: entrance signs at
  1 mile, ½ mile and the opening, toll rate signs, an EXPRESS LANE EXITS sign, and the R3-43 occupancy
  sign; spacings **800 ft MIN** and **800 ft to ¼ mile**.
- **FIND**: across these four figures the **header colour is decided by the payment and registration
  rules** — purple for account-only, white regulatory for "account or HOV", yellow TOLL for
  licence-plate billing — while the green body never changes.

### Figure 2G-24 — Intermediate Entry, Egress and End of Access-Restricted Priced Managed Lanes
(PDF 483)
The priced-lane counterpart of 2G-11, again with the **0.25 L to 0.5 L** placement within the access
opening, the R3-45 / R3-42a end signs, toll rate signs, and **"LOCAL EXITS 2" signs** directing
managed-lane traffic back to the general lanes for nearby exits.

### Figures 2G-25 and 2G-26 — Exit Destinations Sign; Comparative Travel Time Information Sign
(PDF 484)
**2G-25 "EXPRESS LANE EXITS"** — a white-on-green header over the destinations and distances reachable
from the managed lane. **2G-26** — a route shield with **VIA**, then two columns, **EXPRESS LANE** and
**LOCAL LANES**, each with its travel time in a changeable element followed by MINS.
- Related Standard (2G.19 ¶13): guide signs for intermediate egress and direct exits **shall display
  header messages of white legend on a green background**; advance guide signs for **intermediate
  egress shall carry the legend LOCAL EXITS in a header panel**, with destinations or exit numbers
  and the distance to the egress.
- Figure note: **CMS elements shall be used for the numerals displayed for the estimated travel
  times.**

### Figures 2G-27 to 2G-29 — Egress and Direct Ramps for Managed Lanes (PDF 485–487)
**2G-27 intermediate egress**: guide signs shown three ways — a green **"LOCAL EXITS"** header over a
destination, "OR" over a **range of exit numbers ("28 TO 34")**, beside a pull-through
**"EXPRESS LANE"** sign with a down arrow.
**2G-28 direct entrance and exit ramps**: **"EXPRESS EXIT"** header panels (white on green) with exit
numbers and destinations at 1 mile, ½ mile and the ramp, an **EXPRESS EXIT gore sign**, and an
**EXPRESS EXITS** summary sign.
**2G-29 a direct access ramp between managed lanes on separate freeways**: the same pattern between
two facilities, with the summary sign carrying a **yellow LEFT panel beside the line whose exit is on
the left**.
- **FIND (wording by movement, again)**: leaving the managed lane **to another facility** is signed
  **"EXPRESS EXIT"**, while returning to the adjacent general-purpose lanes is signed
  **"LOCAL EXITS"** — never "exit" for the lane-to-lane movement.

### Figures 2G-30 and 2G-31 — Direct Entrance Ramps to Priced Managed Lanes from a Crossroad
(PDF 489–490)
**2G-30** purple-headed EXPRESS LANE entrance signs on the crossroad, drawn rotated to face each
approach, beside **trailblazer assemblies with "EXPRESS LANE" plaques** guiding drivers who cannot
use the managed lane to the ordinary entrance.
**2G-31** separate ramps from the same crossroad: the managed-lane sign with its purple header and
toll rate panel shown **"OR"** a version with **"KEEP LEFT"**, the general-purpose sign reading
"NEXT RIGHT", and an optional **comparative travel time sign (EXPRESS 18 MINS / LOCAL 32 MINS)**;
**800 ft MIN** between successive signs.

### Figure 2G-32 — Signing for Part-Time Travel on a Shoulder (PDF 491–494, 4 sheets; sheet 1 Rev. 1)
**A variable operation** — **lane-use control signals every ½ mile or less** reaffirm that shoulder
travel is allowed (downward green arrow) or prohibited (red X); an optional R3-51e "TRAVEL ON
SHOULDER ON GREEN ARROW ONLY" sign; and a **post-mounted R3-51d "…WHEN FLASHING" sign with two
beacons may be used instead of the lane-use signals at the same intervals**.
**B fixed operation** — the R3-51 sign with its hours repeated **every ½ mile or less**, with an
"EMERGENCY STOPPING ONLY OTHER TIMES" plaque.
**C signing at interchange ramps** — a **YIELD with a "TO TRAFFIC ON SHOULDER" plaque** on the
entrance ramp, W4-1R merge warning, an optional **W3-9 "TRAFFIC USING SHOULDER 6AM-10AM MON-FRI"**
warning sign, and an R3-56 "BEGIN EXIT LANE" sign.
**D emergency turnout signing** — R8-7 and the D17-5 / D17-6 EMERGENCY TURN-OUT signs within the
shoulder-running section.
**E travel on shoulder ends at an exit ramp** — the exit guide signs carry a **blank-out section**:
**off (black) when the shoulder is closed**, and **on (yellow EXIT ↗ ONLY) when travel on the shoulder
is allowed**, so the same sign reads differently by time of day; plus R3-52b "SHOULDER MUST EXIT
½ MILE".
- **FIND (a sign whose panel appears and disappears)**: the EXIT ONLY panel on these guide signs is a
  **blank-out element**, dark when the shoulder is not open to travel. Note on every sheet:
  **"consideration should be given to using blank-out signs in place of the R3-51 and R3-52 series
  conventional signs for part-time operations."**

### Figure 2G-33 — Lane-Use Control Signals and Variable Speed Limit Signs for Active Lane Management
During an Incident (PDF 497)
Gantries about **every ½ mile** carry lane-use control signals and changeable Speed Limit signs. The
blocked lane shows a **red X at the incident**, a **yellow X one gantry upstream**, and green arrows
beyond; the **variable speed limit steps down 55 → 35** on the approach; a two-phase CMS further back
reads "LANE BLOCKED 5 MILES" then "REDUCED SPEED LIMIT".
- **CHECK**: the yellow-X-before-red-X sequence and the ½-mile spacing match 4T.04 and 2G.25.

## Part 2 — Chapter 2H (general information signs)

### Figure 2H-1 — General Information and Miscellaneous Information Signs and Plaques (PDF 500, Rev. 1)
I1-1 SIGNALS SET FOR XX MPH; I2-1 State line and I2-2 stream name signs; transportation symbol signs
I3-5 Airport, I3-6 Bus Station, I3-7 Train Station, I3-8 Light Rail Transit Station,
I3-9 Vehicle Ferry Terminal, **I3-10 Passengers Only Ferry Terminal with the I3-10P FERRY plaque**;
I4-1 Library; **I4-2 RECYCLING CENTER**; and the M5/M6 arrow plaques (white arrows on green) used to
build a General Information Directional Assembly.
- Related Guidance: the **Recycling Center sign should not be used on freeways or expressways**.

### Figure 2H-2 — Future Interstate Signs (PDF 504)
I2-4 FUTURE INTERSTATE CORRIDOR and I2-4a FUTURE I-XX CORRIDOR.
- Related Standards: the **Interstate route marker or any likeness shall not be displayed** on these
  signs; they **shall not provide directional or distance information**, and **no route assembly may
  be used to sign a future route**; the I2-4a form only where **FHWA has approved the route number**.
- On the same page, for **State Welcome signs**: they **may use legend and background colours other
  than the standard sign colours**, but **shall not** display changeable or electronic messages,
  promotional advertising, Acknowledgment signs, business logos, telephone numbers, internet or
  e-mail addresses, or scanning graphics.

### Figure 2H-3 — Project Information Signs (PDF 505)
Two examples, each with route shield, project title, completion season and agency name.
- Related Standards: the legend is **limited to the roadway name or route number, a brief title, the
  completion date as a month or season, and the agency name**; **not installed more than one month
  before work begins**; **removed at the conclusion of work**; **one per direction of travel**;
  **white on green**, with **no internet addresses, e-mail addresses or telephone numbers**.

### Figure 2H-4 — Grade Separation Identification Signs (PDF 506)
I2-3 (overhead) and I2-3a (post-mounted) name plates for the crossing route, shown for numbered
routes, secondary routes, numbered-and-named highways and named highways, with a **section drawing**
of an overcrossing: sign **mounted on the bridge fascia**, with an **alternate post-mounted location**
beside the abutment, plus plan views for **crossroad over** and **crossroad under** the highway.

### Figures 2H-5 and 2H-6 — Reference Location and Intermediate Reference Location Signs (PDF 507)
D10-1 to D10-3 (integer mile) and D10-1a to D10-3a (with a tenth-of-a-mile decimal).
- Related Standards: reference location signs **shall be placed on all freeways** and on expressways
  where there is continuity, to help estimate progress and locate incidents; where intermediate signs
  are used, the **integer sign shall display a decimal point and a zero**; **minimum mounting height
  4 ft**, and these signs are **not governed by 2A.15's heights**; **distance numbering continuous for
  each route**, and where routes overlap, continuity is kept for **only one** — **the Interstate route
  if one is involved** — and that same route also governs **interchange exit numbering**.

### Figure 2H-7 — Enhanced Reference Location Signs (PDF 508, Rev. 1)
D10-4 (cardinal direction, route shield, mile) and D10-5 (the same with a tenth-of-a-mile line).
- Related Standards: **vertical signs, white legend and border on green, except the route shield,
  which keeps its standard colour and shape**; **zero distance begins at the south and west State
  lines**; distance measured on the **northbound and eastbound** roadways with the opposite-direction
  signs placed **directly opposite**; signs may be shifted up to **50 ft** and **omitted** if they
  cannot be placed within that.

### Figure 2H-8 — Acknowledgment Sign Designs (PDF 509)
I20 series — **white legend on blue**, the sponsor's name inside a bordered box (PARKWAY SPONSORED BY,
ADOPT A STREET, ADOPT A HIGHWAY, REST AREA SPONSORED BY, WELCOME CENTER SPONSORED BY, the I20-5P
plaque), one example carrying a **business identification sign panel** (a coloured logo); the D12-5
"511 TRAVEL INFO" sign appears alongside.
- Related Guidance: an agency running a sponsorship programme **should have a policy**, requiring
  eligible sponsors to comply with State anti-discrimination laws.

### Figure 2H-9 — Signs for Alternative Fuels Corridors (PDF 512)
D9-17a "NEXT EV CHARGING XX MILES"; **D9-19 ALTERNATIVE FUELS CORRIDOR** with its fuel-type plaques
D9-19aP / D9-19bP; M4-6P END and M4-14P BEGIN plaques; and the **yellow W16-19P "LAST IN CORRIDOR"
plaque**.
- Related Standards: used **only for segments FHWA has designated "Corridor Ready"**; the appropriate
  **General Service signs or plaques identifying the available fuels shall be included in the
  assembly**, limited to **EV charging, CNG, LNG, LPG and hydrogen**; **post-mounted only, never
  overhead**; **no State or agency variations and no sponsor acknowledgments**; normally **one sign
  per direction at the beginning of the corridor**.

### Figures 2H-10 and 2H-11 — Signing for an Alternative Fuels Corridor; Typical Signing from a
Freeway Exit Ramp to a Service Facility (PDF 514–515)
**2H-10** the whole corridor: BEGIN and END assemblies, fuel symbol signs with directional arrows,
the "NEXT EV CHARGING 52 MILES" sign, and the **yellow LAST IN CORRIDOR plaque above the final fuel
sign**. Note: **exit numbering may be used in place of directional arrows on the mainline**.
**2H-11** the trail from the freeway: symbol signs with **distance plaques and arrows at the ramp**,
then a symbol sign with an arrow **on the crossroad**, leading to the site on a side street.

## Part 2 — Chapter 2I (general service signs)

### Figure 2I-1 — General Service Signs and Plaques (PDF 519, Rev. 1)
The full blue symbol set: D9-1 Telephone, D9-2 Hospital, D9-3 Camping, D9-4 Litter Container,
D9-6 International Symbol of Accessibility with the D9-6P VAN ACCESSIBLE plaque, D9-7 Gas, D9-8 Food,
D9-9 Lodging, D9-10 Tourist Information, D9-11 Diesel, **the alternative-fuel series D9-11a CNG,
D9-11b EV charging, D9-11bP ELECTRIC VEHICLE CHARGING, D9-11c Ethanol, D9-11d LNG, D9-11e LPG,
D9-11f Hydrogen, D9-11g Biofuel**, D9-12 RV Sanitary Station, D9-13 Emergency Medical Services with
its word plaques (HOSPITAL, AMBULANCE STATION, EMERGENCY MEDICAL CARE, TRAUMA CENTER), D9-14 Police,
D9-16 Truck Parking, D9-16aP Truck External Power, D9-20 Pharmacy with the D9-20aP 24-HOUR plaque,
D9-21 Telecommunications Device for the Deaf, D9-22 Wireless Internet, and the M5/M6 arrow plaques
with an example directional assembly.

### Figure 2I-3 — General Service Signs with and without Exit Numbering (PDF 521)
The D9-18 series in **symbol form** (six symbols over EXIT 38 or NEXT RIGHT) and **word form**
("FOOD-PHONE / GAS-LODGING / HOSPITAL / CAMPING"), plus the smaller D9-18dP / D9-18eP / D9-18fP
ramp plaques.
- Related Standard: white legend and border on blue; **approved symbols are permitted as alternatives
  to word messages, but symbols and word messages shall not be intermixed on the same sign**; where
  the services are **not visible from the ramp** at a single-exit interchange, the signing is
  **repeated in smaller size at the ramp/crossroad intersection with arrows**.

### Figure 2I-4 — Interstate Oasis Signs and Plaques (PDF 524)
D5-12 INTERSTATE OASIS with exit number, D5-12b with an arrow, and the **D5-12aP plaque mounted below
a D9-18 General Service sign** where spacing does not allow a separate sign.
- Related Guidance: a separate D5-12 needs **at least 800 ft** from other guide signs, placed
  **upstream of the advance guide sign or between it and the exit direction sign**; eligibility rests
  on **FHWA's Interstate Oasis policy of 18 October 2006**; where specific service signing exists, the
  designated business may use the **bottom of its logo panel for the word OASIS**.

### Figures 2I-5 and 2I-6 — Rest Area and Other Roadside Area Signs; Brake Check and Chain-Up Area
Signs (PDF 526)
D5-1 series REST AREA with distances and arrows, **D5-6 NEXT REST AREA XX MILES**, parking, picnic and
scenic area signs (D5-9 to D5-11 series), and D5-13 to D5-16 brake check and chain-up signs.
- Figure note: **alternate legends may be substituted** — ROADSIDE TABLE or ROADSIDE PARK for PICNIC
  AREA, SCENIC VIEW or SCENIC OVERLOOK for SCENIC AREA.

### Figure 2I-7 — Tourist Information and Welcome Center Signs (PDF 527)
D5-7 / D5-7a / D5-8, each combining REST AREA with TOURIST INFO CENTER.
- Related Standards: **white on blue**; **continuously staffed or unstaffed operation at least 8 hours
  a day, 7 days a week is required**; **seasonal facilities' signs are removed or covered off-season**;
  supplemental panels **limited to three**; and the **Exit Gore sign carries only REST AREA with the
  arrow**, never the tourist-centre legend.

### Figure 2I-8 — Radio, Telephone and Carpool Information Signs (PDF 529)
D12-1 weather and D12-1a travel information radio signs, the latter with the **yellow
"URGENT MESSAGE WHEN FLASHING" plaque (D12-1bP)**; D12-2 CAR POOL INFO CALL \*CAR; D12-3 Channel 9
monitored; D12-4 EMERGENCY CALL 911; D12-5 / D12-5a 511 travel information; D12-6 ROADSIDE ASSISTANCE
CALL #95.
- **CHECK**: another **WHEN FLASHING plaque**, consistent with Ruling 6 (activated by beacons, not by
  LEDs in the legend); and more of the **specific signs permitted to carry telephone numbers**
  (511, 911, #95, \*CAR), the named exceptions to 2A.04 ¶18.
- Related Standard: **only official public agencies or their designee** may be named as the monitoring
  agency on the Channel 9 sign.

### Figure 2I-9 — Truck Parking Availability Signs (PDF 531)
Six layouts (by exit number, by distance, rest areas only, and combined roadside and off-system
sites), each listing sites with the **number of spaces open in a changeable message element**.
- Related Option/Guidance: **the word FULL may be displayed** in white when availability reaches a
  predetermined lower threshold; signs located **3 to 5 miles in advance** of the nearest facility,
  and the facilities listed **no more than 60 miles** from the sign.

### Figure 2I-10 — Use of Truck Parking Availability Signs (PDF 532)
Three corridor cases (reference-location exit numbering, rest areas only, combined roadside and
off-system sites), each with the availability sign upstream and **800 ft MIN** from the interchange
advance guide and exit direction signs; note: **exit numbering may be used in place of directional
arrows on the mainline**.

## Part 2 — Chapter 2J (specific service / logo signs)

### Figure 2J-1 — Business Identification Panel Arrangements on Specific Service Signs (PDF 535)
Layouts for **one, two and three services at a single-exit interchange** (stacked or side by side),
for **double-exit interchanges** with A and B suffixes, for **intersections** ("NEXT RIGHT"), and for
**ramp signs, where each panel carries its own arrow and distance**; plus an example business
identification panel.

### Figure 2J-2 — Specific Service Sign Locations (PDF 536, Rev. 1)
- **FIND (three different measurement points, labelled only on the artwork)**: "**the travel distance
  to be shown on signs** should be measured from this point" (at the ramp terminal); "**travel
  distance for sign priority** should always be measured from this point" (on the mainline); and "if a
  **loop** is signed, the travel distance shown should be measured from this point". So the distance
  **displayed** and the distance used to rank **which businesses qualify** come from different places.
- Spacing: **800 ft MIN** between successive service signs; **ramp signs at least 100 ft** from the
  exit gore sign, from each other and from the ramp terminal.
- Service order on the approach, as drawn: **GAS, EV CHARGING, FOOD, LODGING**, each sign shown in a
  six-panel "OR" three-panel form.

### Figure 2J-3 — General Service Signs Used with Specific Service Signs (PDF 538)
Where a service has no logo panels, the **blue General Service symbol or word sign** is used in the
same sequence, again at **800 ft MIN** spacing, shown as symbols "OR" words.

### Figure 2J-4 — Supplemental Messages on Business Identification Sign Panels (PDF 538)
A **yellow supplemental strip beneath the logo panel** reading **24 HRS**, **EV CHARGING** or
**RV ACCESS**.
- Related Standards: **no message promoting the availability of panel space**; to qualify for the
  **EV CHARGING** strip the business must offer charging **to the public without purchasing the
  primary service**, and meet **23 CFR 680.106** DC fast-charger criteria (gas, food, attraction) or
  DCFC and/or AC Level 2 (camping, lodging).

### Figures 2J-5 and 2J-6 — Specific Services Signing within a Freeway-to-Freeway Interchange; Services
Accessed from a Collector-Distributor Road (PDF 541, 543)
**2J-5** shows the service signs on the crossroad and ramp where the services are reached via a
conventional road inside a large interchange, with **800 ft MIN** spacing and ramp signs carrying
arrows and distances.
**2J-6** puts the service signs **on the C-D roadway**, with a mainline sign reading
**"FOOD-GAS LODGING EXITS 38-39" "OR" "… NEXT RIGHT"**.
- Note on 2J-6: if service signs are on the **mainline** for services reached from the C-D roadway,
  the panels displayed on the C-D roadway **shall be only duplicates** of those on the mainline.
- Related Standards (2J.07): at **numbered** single-exit interchanges the service name is followed by
  the **exit number**; at **unnumbered** ones, by **NEXT RIGHT (LEFT)**; where traffic may turn either
  way from the ramp, **ramp signs with arrows** are required for facilities not readily visible from
  the ramp terminal.

## Part 2 — Chapter 2K (tourist-oriented directional signs)

### Figures 2K-1 and 2K-2 — Tourist-Oriented Directional Signs and their Placement (PDF 547–548;
2K-1 Rev. 1)
Blue sign panels, each with the **arrow and distance in a block at one side** and the business name
or logo alongside, stacked up to three per assembly under an optional **TOURIST ACTIVITIES** or
**NEXT LEFT** header. Placement: **intersection approach signs 200 ft MIN** from the intersection and
from each other, **advance signs 500 ft MIN** further back and only "in special circumstances";
left-turn and right-turn businesses on **separate assemblies**; the "RIGHT ½ MILE" form used **only
where there is an intervening intersection**.
- Related Guidance: legends **upper case, at least 6 in**, except on business identification panels,
  which use mixed case; a **logo must be proportional to its panel**.

## Part 2 — Chapter 2L (changeable message signs)

### Figure 2L-1 — CMS Capability to Display Sign Legends Based on Pixel Pitch (PDF 556)
Two pictures of the same message: a **full-colour matrix with a pixel pitch of 20 mm or less**
reproduces a conventional sign legend, **including route shields and symbols**; a sign with
**pitch greater than 20 mm**, colour or monochrome, "should only display monochrome word messages".
Notes: pixel pitch is centre-to-centre spacing, given in **metric because manufacturers use metric**.
- Beside it, **Table 2L-2** counts a message's units of information (what happened / where / who for /
  what is advised = 4 units) and shows them split into a **two-phase message**.

## Part 2 — Chapter 2M (recreational and cultural interest area signs)

### Figure 2M-1 — Use of Arrows, Educational Plaques, and Prohibitive Circles and Diagonals (PDF 563)
Brown symbol signs used as **directional signs** (symbol over an arrow panel), **directional
assemblies**, and **with educational word plaques** (FIRST AID). **D** shows prohibitions for
**non-road use**: the brown symbol drawn **on a white background with a black border and a red circle
and diagonal**, the diagonal running **upper left to lower right**, with word plaques (NO CAMPFIRES,
NO SMOKING).
- Related Standard: this treatment is used **only where Chapter 2B provides no standard regulatory
  sign**; standard regulatory signs are used where they exist.

### Figure 2M-2 — Recreational and Cultural Interest Area Guide Signs (PDF 565)
**A conventional roads**: brown destination signs with symbols and arrows, distances, and the
**optional trapezoid shape** (pointed toward the direction of travel). **B expressways and freeways**:
a brown **supplemental guide sign** with exit number, and a brown **Exit Direction sign** — but the
**Exit Gore sign is drawn green (E5-1a)**.
- **CHECK**: confirms the reading-log finding that **Exit Gore signs remain white on green** even for
  recreational destinations; and the Standard on the facing page adds that the **Advance guide and
  Exit Direction signs keep white-on-green where the crossroad also serves a non-recreational
  destination**.

### Figure 2M-3 — Arrangement, Height and Lateral Position of Signs within Recreational Areas
(PDF 566)
Four assemblies with dimensions: **A business/commercial/residential with curb — 2 ft MIN lateral,
7 ft MIN height**; **B rural — 6 ft MIN from the paved shoulder, 5 ft MIN height**; **C business area
without curb — 6 ft MIN, 7 ft MIN**; **D rural — 12 ft MIN from the edge of the traveled way, 5 ft MIN
height**; plus stacked symbol-and-arrow arrangements shown "OR" a single combined panel.
- Note: **2A.16 applies for reduced lateral offsets** where space is limited.

### Figure 2M-4 — Symbol and Destination Guide Signing Layout (PDF 567)
A whole park in plan — lake, beach, launch ramp, picnic area, amphitheatre, information centre,
campground — with the brown assemblies drawn **rotated to face each approach**, including **vertical
destination signs ("Cedar Springs") at the park entrances**.

### Figures 2M-5 to 2M-10 — Recreational and Cultural Interest Area Symbol Signs (PDF 568–570)
The full RS symbol set in six plates: **general applications**, **accommodations**, **services**,
**land recreation**, **water recreation** and **winter recreation**.
- **CHECK**: the starred symbols carry the footnote "**for use only within recreational and cultural
  interest areas where speed limits are 25 mph or less**" — the same restriction recorded from
  Table 2M-1 during the first pass.
- **FIND**: the set is brown except **RS-200 Recycling, which is green**.

## Part 2 — Chapter 2N (emergency management signs)

### Figure 2N-1 — Emergency Management Signs (PDF 572)
**EM1-1 Evacuation Route** and **EM1-1a** with an event name (starred: "HURRICANE is an example of one
type of evacuation route; legends for other types may also be used"), both **white on a blue disc**;
**EM1-2 tsunami evacuation route** with its graphic; and the operational signs in **black on white** —
EM2-1 AREA CLOSED, EM2-2 TRAFFIC CONTROL POINT, EM2-3 MAINTAIN TOP SAFE SPEED, EM2-4 ROAD USE PERMIT
REQUIRED, EM3 series (medical, welfare, registration, decontamination centres) and EM4 series
shelters, the fallout and chemical shelters carrying the **yellow-and-black trefoil symbols**.
- Related Guidance: during an emergency, **permanent regulatory and warning signs that conflict are
  removed or covered**, then **promptly restored** afterwards; emergency signs are **removed promptly
  when no longer needed — except Evacuation Route signs**.

# PART 3 — MARKINGS

### Figure 3B-1 — Yellow Center Lines for Two-Lane, Two-Way Applications (PDF 581, Rev. 1)
**A** a normal broken yellow line where **passing is permitted in both directions**; **B** a run of
road showing, in sequence, **two-direction passing zone**, **one-direction no-passing zone** (broken
and solid), **two-direction no-passing zone** (double solid), then the reverse.
- Related Standards on the page: centre lines are **yellow** and separate opposing directions;
  **a single solid yellow line shall not be used as a centre line** on a two-way roadway; on undivided
  two-way roadways with **four or more lanes**, the centre line **shall be double solid yellow**
  (except with a reversible or two-way left-turn lane).

### Figure 3B-2 — Yellow Center Lines for Four-or-More Lane, Two-Way Applications (PDF 582)
**A** plain multi-lane two-way marking (double solid yellow). **B** the same with a **single-lane
left-turn channelization**, showing the **optional yellow diagonal markings** in the median opening
and **optional dotted extensions** through the opening. Note: lane-use arrows per 3B.20 and 3B.23.

### Figure 3B-4 — Method of Locating and Determining the Limits of No-Passing Zones at Curves
(PDF 585)
**A vertical curve (profile view)** and **B horizontal curve (plan view)**, each showing the lines of
sight, the **minimum passing sight distance for the 85th-percentile speed or the speed limit**, and
the points a/a′ (begin) and b/b′ (end) of the no-passing zone.
- **FIND (measuring convention)**: sight distance is measured **between two points 3.5 ft above the
  pavement**; the zone **begins where sight distance becomes less than the minimum** and **ends where
  it again exceeds the minimum**; note: the zones for opposite directions **might or might not
  overlap**, depending on alignment.

### Figure 3B-5 — Three-Lane, Two-Way Markings for Changing the Direction of the Center Lane (PDF 586)
Shows the **zones of limited sight distance for the two opposing drivers (Car X and Car Y)** and the
**buffer zone as the gap between them**, with two-direction no-passing markings, optional yellow
diagonal markings and optional dotted lane line extensions. Notes: **3B.03** for the minimum buffer
length, **3B.12** for the taper length L, **3J.03** for the flush median island.

### Figure 3B-7 — Two-Way Left-Turn Lane Marking Applications (PDF 588)
**A intersecting cross streets** and **B intersecting driveways**, each showing the broken yellow
line inside a solid yellow line, **lane-use arrows in opposing pairs spaced 8 to 16 ft apart**, the
optional yellow diagonal markings at the lane's end, and optional dotted extensions.

### Figure 3B-8 — Double Solid White Line Used to Prohibit Lane Changing (PDF 589)
An exit ramp area where crossing is barred, with the **double solid white lane line** marked optional
in the legend, alongside chevrons in the neutral area.
- Related Standard: **where crossing a lane line is prohibited, the lane line shall be a double solid
  white line.**

### Figure 3B-9 — Dotted Line and Channelizing Line Applications for Exit Ramp Markings
(PDF 590–591, 2 sheets, Rev. 1)
**A parallel deceleration lane** and **B tapered deceleration lane**, each labelling the **physical
gore**, the **theoretical gore**, the **wide white channelizing lines**, the **optional white chevron
markings in the neutral area**, and the dotted white lane line running **from the upstream end of the
full-width deceleration lane to the upstream end of the solid white lane line**.
- Related Standards (3B.07): a **normal-width dotted white line** separates a through lane from an
  adjacent deceleration or acceleration lane; for a **tapered** deceleration lane the dotted extension
  runs from the theoretical gore **to meet the edge line at the upstream end of the taper**; for
  entrance ramps with a parallel acceleration lane, the dotted line runs from the theoretical gore to
  **at least half the distance** to the downstream end of the acceleration taper.

### Figure 3B-9 sheet 2 (PDF 591, Rev. 1)
**C a parallel deceleration lane at a multi-lane exit ramp with an optional exit lane that also
carries the through route** — the option lane is separated by a **normal-width dotted white lane
line**, with a wide or normal solid white lane line of variable length beyond the gore.

### Figure 3B-10 — Dotted Line and Channelizing Line Applications for Entrance Ramp Markings
(PDF 592–593, 2 sheets)
**A parallel acceleration lane**: the legend defines **A = the length of the acceleration lane plus
taper**, and the **normal-width dotted lane line must run at least 0.5 A** from the theoretical gore,
with an optional dotted line beyond that point. **B and C tapered acceleration lanes**: the legend
defines **B = the distance from the physical gore to the downstream end of the full-width acceleration
lane**, with the dotted line for **at least 0.5 B**.
- **FIND (computable rules with named variables)**: the required length of the dotted lane line is
  **half the acceleration length**, expressed as 0.5 A or 0.5 B depending on the ramp type — stated
  only in the figures' legends.

### Figure 3B-11 — Freeway and Expressway Lane-Drop Markings (PDF 595–600, 6 sheets)
**A lane drop at a single-lane exit ramp**, **B at a multi-lane exit ramp with an optional exit lane
carrying the through route**, **C a two-lane lane drop at an exit ramp**, and further sheets for
splits and left-hand drops. Every case shows the same device: a **wide dotted white lane line
extending at least ½ mile upstream of the theoretical gore**, changing to a wide solid white lane
line of variable length near the gore, with wide white channelizing lines and optional chevrons in
the neutral area.
- **FIND**: the **½-mile wide dotted lane line is the pavement-marking equivalent of the EXIT ONLY
  panel** — the marking that tells a driver the lane will leave the roadway.

### Figure 3B-11 sheets 4–6 (PDF 598–600)
**D a route split with dedicated lanes** and **E a route split with an option lane** — both with the
**wide dotted white lane line for ½ mile MIN** upstream of the theoretical gore. **F a continuous
auxiliary lane, as at a cloverleaf interchange** — here the **wide dotted white lane line runs the
full length of the auxiliary lane**, between the upstream and downstream wide solid white lane lines,
with a theoretical gore, neutral area and physical gore labelled at each end.

### Figure 3B-12 — Conventional Road Lane-Drop Markings (PDF 601–602, 2 sheets)
**A a lane drop at an intersection**: a **wide solid white lane line** beside the dropped lane, a
**wide dotted white lane line** upstream, and repeated **arrow + ONLY** messages in the lane, with
**8 ft TYP.** between the two elements of one message and varying gaps between message groups
(3B.20 for grouped-message spacing).
**B an auxiliary lane between intersections**, drawn as two cases:
- **1 mile or less** — the **wide dotted white lane line runs the whole length**;
- **more than 1 mile** — the middle reverts to a **normal-width broken white lane line**, with the
  wide dotted line retained near each end.
- **FIND (clean threshold)**: the auxiliary-lane marking changes at **1 mile**.

### Figure 3B-13 — Line Extensions through Intersections (PDF 605–606, 2 sheets)
**A offset lane lines continued through the intersection** as dotted extensions, so a driver crossing
a wide intersection stays in lane. **B line extensions into the intersection for double turns**, with
**optional dotted extensions** guiding each of the two turning paths and lane-use arrows repeated in
each lane.

### Figure 3B-13 sheet 2 (PDF 606)
**C dotted lines extending lane lines into the intersection** and **D dotted lines extending both the
centre line and lane lines**, with **yellow dotted extensions for the centre line** and white for the
lane lines.

### Figure 3B-14 — Lane-Reduction Transition Markings (PDF 608, Rev. 1)
**A a lane reduction** and **B a lane reduction with a lateral shift to the left**, each defining the
variables in a note: **L = length of taper, W = offset, AP = advance placement distance (2C.04)**.
The lane-reduction arrows are spaced at **AP/4** intervals ahead of the taper, with an optional dotted
lane line through the transition, delineators along the taper, and the W4-2R and optional W9-1R signs.
- **FIND (computable, from the artwork)**: arrow spacing **AP/4**, with AP taken from Table 2C-3.

### Figure 3B-15 — Markings for Obstructions in the Roadway (PDF 610–611, 2 sheets)
**A centre of a two-lane road**, **B centre of a four-lane road**, **C traffic passing on both sides
in the same direction** (white markings instead of yellow). Each sheet repeats the formula in a note:
- **L = W·S for speeds of 45 mph or more; L = W·S²/60 below 45 mph**, where **S is the 85th-percentile
  speed or the speed limit, whichever is higher**, and W is the offset in feet;
- **minimum L = 100 ft urban, 200 ft rural**, extended as sight distance requires;
- approach markings **2L MIN** on a two-lane road; the marking is offset **1 to 2 ft** from the
  obstruction.
- **CHECK (supports Ruling 1)**: another instance of the ranked "whichever is higher" speed basis.

### Figure 3B-16 — Yield Line Applications (PDF 615, Rev. 1)
**A a channelized intersection**, **B an unsignalized midblock crosswalk**, **C a crosswalk across a
ramp** — the yield line placed **20 to 50 ft in advance of the crosswalk**, with **R1-5 Yield Here To
Pedestrians signs at the line** and W11-2 with diagonal arrow plaques at the crossing.
- Related Guidance: yield (stop) lines and Yield Here To (Stop Here For) Pedestrians signs **should
  not be used in advance of crosswalks on an approach to or departure from a circular intersection**;
  stop and yield lines **may be staggered lane by lane** to improve the view of pedestrians and sight
  distance for turning vehicles.

### Figures 3B-17 and 3B-18 — Elongated Letters for Word Pavement Markings; Elongated Route Shields
Applied as Pavement Markings (PDF 617)
**3B-17** the word ONLY drawn **8 ft tall and 5.9 ft wide**, elongated for viewing at a shallow angle.
**3B-18** route shields as pavement markings, shown for **dark and light pavement** — the Interstate
shield in colour, the U.S. and State markers as **white on a dark patch** or **black on a light
patch**.
- Related Standards/Guidance: **the ONLY word marking shall not be used in a lane shared by more than
  one movement**; word markings **may be reduced by 25 %** where operating speed is under 25 mph;
  route sign markings should be provided **in option lanes if provided in any lanes**, and two such
  markings in an option lane are **placed in sequence, not divided around an arrow**.

### Figures 3B-19 and 3B-20 — Accessibility Parking Space Marking; Yield Ahead Triangle Symbols
(PDF 618)
**3B-19** the wheelchair symbol as a pavement marking, with a note that the **blue background with
white border is optional**. **3B-20** the yield-ahead triangle in two sizes:
**A speed limit 45 mph or greater — 20 ft long, 6 ft wide, 36 in head, 8 in stroke**;
**B below 45 mph — 13 ft long, 6 ft wide, 30 in head, 8 in stroke**.
- Related Standard: the yield-ahead triangle or YIELD AHEAD word marking **shall not be used unless a
  YIELD sign is in place** at the intersection.

### Figure 3B-21 — Standard Arrows for Pavement Markings (PDF 620, Rev. 1)
Through, turn, turn-and-through, **U-turn**, U-turn-and-turn, **curved-stem** lane-use arrows, the
**wrong-way arrow** (and its version formed from **retroreflective raised pavement markers**), and the
**lane-reduction arrow**.
- **OPEN (third appearance of the unnamed element)**: among the **curved-stem** arrows a small circle
  at the tail is again labelled "**Optional for left-most lane**", with "match arrow(s) with desired
  lane use configuration" — the same optional mark seen on R3-8zd–zg (Figure 2B-4) and in the
  roundabout arrow options (Figure 2B-5). It exists as a **pavement marking as well as a sign
  element**, and the Manual still never states what it represents.

### Figure 3B-22 — Lane-Use Control Word and Arrow Pavement Markings (PDF 621, Rev. 1)
A full intersection with lane-use arrows, ONLY words, optional dotted extensions (white for lane
lines, yellow for the centre line) and yellow diagonal markings in the median openings.
- Related Option (3B.25 ¶2): chevron and diagonal markings may be used **A** at obstructions,
  **B** for channelized travel paths, **C** in buffer spaces between preferential and general-purpose
  lanes, **D** in neutral area gores, **E** in bifurcations at open-road tolling, **F** at managed-lane
  access and egress points, and **G** in the neutral areas of islands.

### Figure 3B-23 — Parking Space Markings (PDF 623)
Three layouts with the **Uniform Vehicle Code no-parking distances** drawn in: **30 ft MIN on
approaches controlled by STOP or YIELD signs**, **30 ft MIN on approaches controlled by traffic
signals**, **20 ft MIN from marked or unmarked crosswalks at intersections**, and **20 ft MIN** at the
departure side; stall lengths **22 to 26 ft** (about **20 ft typical for an end space**) and **8 ft**
depth; the T and cross markings drawn **12 in across with 4- to 6-in strokes**, with a note that the
**extension enables a driver to see the limits of the stall**.

### Figure 3B-24 — Do Not Block Intersection Markings (PDF 624)
Four permitted forms: **A outline only in wide solid white lines**; **B outline with a "DO NOT BLOCK"
or "KEEP CLEAR" text message**; **C outline with 4- to 6-inch solid white crosshatching** (two
patterns shown "OR"); **D the text message alone with no outline**. Note: **the outline does not have
to be rectangular** — its edges are aligned to define the specific area to be kept clear.

### Figure 3B-25 — Speed Reduction Markings (PDF 625)
**A recommended dimensions** — transverse white lines **no more than 12 in wide**, extending **no more
than 18 in into the lane**; **B placement** — lines on both sides of the lane with **progressively
reduced longitudinal spacing** toward the downstream end, to give the impression of increasing speed.
- Related Standards/Guidance: used **only in lanes that have a longitudinal line on both sides**;
  **not on long tangents or in areas used mainly by local drivers such as school zones**; they
  **supplement warning signs and never substitute for them**.

### Figures 3B-26 and 3B-27 — Pavement Markings for Speed Humps without Crosswalks; for Speed Tables
or Speed Humps with Crosswalks (PDF 626–627; 3B-27 Rev. 1)
Three options for a plain hump (chevrons pointing toward approaching traffic, **6 ft wide, 12-inch
white markings, 12 ft typical lane**; Option C at 9.5 ft with 10.4-inch elements) and two options
where the hump also serves as a crosswalk or speed table (**6 ft typical** bands either side of the
crossing area; note: crosswalk lines are not shown).
- Related Standards on the facing page, for a **diverging diamond (transposed alignment crossroad)**:
  **each direction is treated as a one-way roadway**, so **both yellow and white edge lines are
  used**; a **lane-use arrow is required in each approach lane at the crossover**; and **flush median
  islands shall not be used to divide the inverted flow**.

### Figure 3B-28 — Advance Warning Markings for Speed Humps or Speed Tables (PDF 628)
A fully dimensioned detail: **eight 12-inch white transverse markings within 100 ft** of the hump,
their **lengths decreasing 8, 7, 6, 5, 4, 3, 2, 1 ft** while the **gaps increase 2, 8, 10, 12, 14, 16,
18, 20 ft** toward the hump.
- **FIND (computable)**: the whole pattern is specified in the figure; Guidance adds that advance
  markings should be installed **in each approach lane**.

### Figure 3B-29 — Pavement Markings for a Diamond Interchange with a Transposed Alignment Crossroad
(PDF 629, Rev. 1)
The full diverging diamond in plan: **yellow edge lines on the left of each one-way direction and
white on the right**, dotted extensions through the crossovers, lane-use arrows in every approach
lane, crosswalks across the crossover throats, and raised islands (not flush) dividing the flows.

### Figure 3C-1 — Crosswalk Markings (PDF 631)
Already read on 22 September while settling Ruling 5 (bar-pair spacing): transverse, longitudinal
bar, ladder and bar pair designs with their widths, spacings and the 2.5× cap.

### Figure 3D-1 — Markings for Approach and Circulatory Roadways at a Roundabout (PDF 637)
Yield lines (shark's teeth) at each entry, **YIELD word markings** on the approaches, **wide dotted
white extension of the circulatory roadway edge line** across each entry, optional white diagonal
markings in the splitter islands, a **landscape buffer** labelled outside the circulatory roadway,
and crosswalks set back **20 ft MIN** from the circulatory roadway.
- **CHECK**: the 20-ft setback matches 3C.09 ¶3, 7B.03 ¶9 and 9E.05 ¶3 — the same distance recorded
  across three other Parts during the reading.

### Figures 3D-2 to 3D-6 — Roundabout Marking Examples (PDF 638–643)
**3D-2 one-lane roundabout**: yield lines at each entry, lane-use arrows on the approaches, dotted
white extensions of the circulatory edge line, optional white diagonal markings in the splitter
islands, landscape buffer outside the circulatory roadway.
**3D-3 two-lane roundabout with one-lane and two-lane approaches**, three cases —
**A an unextended central island**; **B the central island extended by pavement markings**, using an
**optional yellow edge line with yellow diagonal markings** (crossable); **C the central island
extended by a truck apron** (a physical surface).
**3D-4 two-lane roundabout with one-lane exits**, carrying a note: "**the marking configuration shown
on this figure requires U-turning drivers to change lanes within the circulatory roadway**".
**3D-5 two-lane roundabout with two-lane exits**, where the circulatory lane line continues through
each exit.
**3D-6 two-lane roundabout with a double left turn**, with paired lane-use arrows and ONLY words on
the approach.
- **FIND**: the same geometric problem (too much circulatory width for small vehicles) is solved
  either by **markings** or by a **truck apron**, and the figures show both as equivalents; and a
  figure note states a **behavioural consequence** of one marking choice, which is unusual.

### Figures 3D-7 and 3D-8 — Two-Lane Roundabout with a Double Right Turn; Diamond Interchange with
Two Circular-Shaped Roundabout Ramp Terminals (PDF 644–645)
**3D-7** paired right-turn arrows and ONLY words on the approach. **3D-8** a diverging-style diamond
with roundabout ramp terminals, optional white chevrons and yellow diagonals in the neutral areas, and
an **enlarged detail of an optional pavement marking** — the route shield with **WEST above and TO
below**, in elongated letters, in the lane serving that route.

## Part 3 — Chapter 3E (preferential lane markings)

### Table 3E-1 and Figure 3E-1 — Standard Edge and Lane Line Markings for Preferential Lanes;
Markings for Barrier-Separated Preferential Lanes (PDF 648)
The table (read from the page) sets the left- and right-hand lines for each lane type:
barrier-separated non-reversible (**yellow left, white right**), **barrier-separated reversible —
white on both sides**, buffer-separated left- and right-hand, and contiguous left- and right-hand,
with the line type chosen by whether crossing is **prohibited (wide solid double white)**,
**discouraged (wide solid single white)** or **permitted (wide broken single white)**.
Notes: with **two or more preferential lanes**, the lines between them are **normal broken white**;
the table is provided "in a tabular format for reference".
- **FIND**: a **reversible** lane is marked white on both sides because its direction changes — the
  yellow-left convention cannot apply.

### Figure 3E-2 — Markings for Buffer-Separated Preferential Lanes (PDF 649–650, 2 sheets)
**A enter/exit prohibited** (wide solid double white lines along both edges of the buffer, with
**white chevrons if the buffer is wider than 4 ft**), **B discouraged** (wide solid single white),
**C permitted** (wide broken single white, with an alternative "for use in weaving areas only" using
wider lanes), **D right-hand side preferential lanes**, where a **wide dotted single white line marks
where crossing is permitted to make a right turn**.
- Footnotes: where there is **no barrier or median and the left-hand side is the centre line of a
  two-way roadway, a double yellow centre line is used**; HOV symbols are spaced at **¼-mile
  intervals or by engineering judgment**.
- Related Standard (3E.03 ¶2): the **HOV diamond shall be at least 2.5 ft wide and 12 ft long with
  lines at least 6 in wide**; other preferential lanes carry their own word markings — the ETC
  system's name for account-only lanes, **EXPRESS / EXPRESS LANE(S)**, **BUS ONLY / BUS STOP**,
  **TAXI ONLY / TAXI STAND**, **LRT ONLY**.

### Table 3E-2 (PDF 650) — Counter-Flow Preferential Lanes on Divided Highways
Centre line on the left-hand side: **part-time contiguous — normal broken double yellow**;
**part-time buffer-separated — broken double yellow along both edges of the buffer**;
**full-time contiguous — solid double yellow**; **full-time buffer-separated — solid double yellow
along both buffer edges**; with a normal solid single white edge line where warranted.

### Figure 3E-3 — Markings for Contiguous Preferential Lanes (PDF 651)
The same four cases (prohibited, discouraged, permitted, right-hand side) without a buffer, the lane
line alone carrying the restriction, and the **wide dotted line again marking where a right turn may
cross**.

### Figure 3E-4 — Markings for Counter-Flow Preferential Lanes on Divided Highways (PDF 652, Rev. 1)
The four cases of Table 3E-2 drawn: part-time contiguous and buffer-separated (**broken double
yellow**, with "← OR →" showing the reversal), full-time contiguous and buffer-separated (**solid
double yellow**, with optional yellow diagonal markings filling the buffer).
- Related Standards: **motorcycle and Inherently Low Emission Vehicle markings shall not be used** to
  mark a preferential lane even where those vehicles may use it — that permission is conveyed by
  **regulatory signing**; and **static or changeable regulatory signs shall be used with preferential
  lane word or symbol markings**.

### Figures 3E-5 and 3E-6 — Markings for Part-Time Travel on a Shoulder (PDF 654–657)
**3E-5** six cases (A–F) of a right- or left-hand shoulder opened to **transit only** or to **HOVs**,
with **wide dotted white lane lines at ramps and openings** and **wide solid white lane lines**
between them; the transit cases carry **BUS ONLY word markings on optional red-coloured pavement**,
the HOV cases the **diamond symbol**; sheet 3 shows a **bus platform and shelter with a park-and-ride
lot** served from the shoulder.
**3E-6** part-time shoulder travel **through an intersection**, in two variants — **A priority to
turning traffic** and **B priority to the transit vehicle** — with SHOULDER / BUSES AND RIGHT TURNS
ONLY signs, R3-7 with the EXCEPT BUSES plaque, and R3-20 BEGIN RIGHT TURN LANE.
- **FIND**: **red-coloured pavement** appears here as an optional device for a **transit-only**
  shoulder — the colour carrying the restriction alongside the word marking.

### Figure 3G-1 — Delineator Placement (PDF 660)
A curve with delineators at **2 to 8 ft outside the roadway edge or face of curb** (and **2 to 8 ft
outside the shoulder edge** on the other side), with **Type 3 object markers** on the bridge rails and
delineators mounted **directly above, immediately behind, or on the innermost edge** of a bridge rail
or guardrail.
- Notes: delineators are normally at a **constant distance from the roadway edge**, but where an
  obstruction intrudes the line of delineators **makes a smooth transition to the inside of the
  obstruction**; **all delineators in this figure are white, including those on the outside of the
  curve facing oncoming drivers**; **Chevron Alignment signs may be used instead of or in addition
  to delineators**.

## Part 3 — Chapter 3H (coloured pavement)

### Figure 3H-1 — Aesthetic Treatments for Transverse Crosswalks (PDF 664, Rev. 1)
A brick-infilled crosswalk with a palette: **materials** (brick, stone, paver), **geometries**
(lattice, mesh, grid, polygon) and **colours** (red, brown, tan, clay).
- Related Standards: aesthetic treatments **shall not interfere with traffic control devices**, shall
  not confuse pedestrians with vision disabilities who rely on tactile cues, and their colours
  **shall be outside the chromaticity coordinates of traffic control colours**; the pattern shall be
  **devoid of advertising and contain no retroreflective elements**, shall **not encourage road users
  to remain in the crosswalk**, and **should contain no pictographs, illusions or symbols**; a **gap
  of at least half the white transverse line's width, never less than 6 in**, separates the treatment
  from the crosswalk lines.

### Figures 3H-2 and 3H-3 — Yellow- and White-Coloured Pavement Applications (PDF 665–666)
**Yellow** — limited to **flush or raised median islands separating opposing flows, left-hand
shoulders of divided highways, and left-hand shoulders of one-way streets or ramps**; **never** in
reversible lanes or two-way left-turn lanes, and **never on channelizing islands where traffic passes
the same way on both sides**. **White** — limited to **flush or raised channelizing islands where
traffic passes on both sides in the same general direction, right-hand shoulders, exit gore areas and
entrance gore areas**, and **may be used instead of chevron markings** in neutral areas.

### Figure 3H-4 — Green-Coloured Pavement Applications (PDF 668)
Four cases: **A the entire corridor**, **B limited to the bicycle symbol and arrow**, **C approaching
and departing an intersection**, **D supplementing the dotted line approaching intersections and the
dotted extensions through them** (green applied only to the dashes).
- Related Standard (3H.06 ¶2): green is limited to **bicycle lanes; extensions through intersections;
  extensions through weaving areas into mandatory turn lanes; two-stage turn boxes; bicycle boxes; and
  as a background for bicycle detector symbols**.

### Figure 3H-5 — Red-Coloured Pavement Applications (PDF 670, Rev. 1)
**A a bus only lane**, **B a bus only lane at terminals or station stops** (with a waiting area
alongside), **C a buffer-separated bus only lane**, each with **BUS ONLY** (and **BUS STOP**) word
markings reversed out of the red, and R3-11 series regulatory signs.

### Figure 3H-6 — Purple-Coloured Pavement Applications (PDF 671–672, 2 sheets)
**A an electronic toll collection only toll plaza lane** — the lane filled purple with the ETC word
markings reversed out, bounded by raised pavement markers, with the matching purple R3-44 sign.
- Notes: the word markings and pictograph shown are **examples only — the facility's adopted ETC
  system's markings shall be used**; the use of coloured pavement is **optional** throughout.
- **FIND (the colour system as a whole)**: **yellow** separates opposing traffic, **white** separates
  same-direction traffic, **green** marks bicycle operation, **red** marks transit-only lanes, and
  **purple** marks ETC-account-only lanes — each with its own closed list of permitted applications.

### Figure 3H-6 sheet 2 (PDF 672)
**B open-road ETC bypass with an upstream option lane** and **C with dedicated approach lanes** — the
purple lanes carry the ETC word markings, the **open-road electronic toll collection point** is
labelled with a dashed box, and the toll plaza is shown as a black band across the parallel lanes.

## Part 3 — Chapter 3I (channelizing devices as markings)

### Figure 3I-1 — Tubular Markers Supplementing Pavement Markings in Advance of an Unsignalized
Crosswalk (PDF 674–675, 2 sheets, Rev. 1)
Four cases: markers on the **centre line**; on the **centre line and lane lines**; on **lane lines
with an in-street pedestrian crossing sign (R1-6) on the centre line**; and on **edge and lane lines
with the in-street sign**. Each with W11-2 pedestrian signs and W16-7P diagonal arrow plaques on both
sides of the crossing.

## Part 3 — Chapter 3J (islands and sidewalk extensions)

### Figures 3J-1 to 3J-4 — Island Marking and Delineation (PDF 676–679)
**3J-1** an **approach-end treatment**: longitudinal markings and channelizing devices upstream,
diverging and concluding in the markings that outline the island; its length "varies".
**3J-2** islands designated by pavement markings — **A separating opposing flows in all directions**
and **B separating opposing flows in an intersecting street**, both outlined in **yellow**.
**3J-3** curb markings for raised islands — **A a median nose** and **B a channelizing island**, with
**optional marking on the face of the curb** and a note that a solid yellow edge line "might be
required, recommended, or optional".
**3J-4** pavement markings for raised islands — **A white channelizing lines around an island
separating same-direction flows**.
- Related Standards and Guidance: island channelizing lines are **white when separating traffic in the
  same general direction and yellow when separating opposing directions**; a continuous flush median
  island uses **two sets of double solid yellow lines**, and other markings inside it are **yellow
  except crosswalk markings, which are white**; **chevrons or diagonals inside the island take the
  same colour as the channelizing line**; **raised bars projecting more than 1 in** in the neutral
  area are marked **white or yellow according to the directions they separate**; **retroreflective
  solid yellow curb markings** on approach ends of raised medians in the line of traffic,
  **retroreflective solid white** where traffic may pass on either side; and where traffic passes on
  the **right** of an island separating same-direction flows, a **yellow edge line** is used beside
  the island instead of continuing the white channelizing line.

### Figure 3J-4 sheet 2 and Figure 3J-5 (PDF 679–680)
**3J-4 B** a **yellow edge line beside a raised island separating same-direction flows**, used where
traffic passes on the right of the island. **3J-5** optional **chevron and diagonal markings at a
raised island**, in the colour of the channelizing line.
- Related Standards: **delineators on islands take the colour of the related channelizing or edge
  line, except that when facing only wrong-way traffic they shall be red**; **each roadway through an
  intersection is considered separately** when positioning delineators.
- Support: yellow edge lines beside such islands act as a **countermeasure for wrong-way entry**.

### Figure 3J-6 — Sidewalk Extensions Designated by Pavement Markings and Channelization (PDF 681)
**A a sidewalk extension reducing the pedestrian crossing distance** and **B channelizing for speed
control and altered travel paths** (which is **not** a sidewalk extension).
- Related Standards: painted sidewalk extensions are formed with **double solid lines** connecting to
  the curb or the roadway edge, and the enclosed area **is not part of the roadway**; **crosswalk
  markings shall not be extended through** such an extension; Guidance adds **tubular markers adjacent
  to the double solid line, outside the travelled way**, for conspicuity.

## Part 3 — Chapter 3K (rumble strip markings)

### Figure 3K-1 — Longitudinal Rumble Strip Markings (PDF 683)
**A edge line beside the rumble strip**, **B edge line on the rumble strip** (a rumble stripe),
**C centre line on a rumble strip**.
- Related Standards: the colour of a line on a rumble stripe follows **3A.03**; **an edge line shall
  not be used in addition to a rumble stripe located along a shoulder**; a **transverse** rumble strip
  in a travel lane that is not the pavement colour **shall be black or white**, and white ones
  **should not be placed where they could be confused with stop lines or crosswalks**.

# PART 4 — HIGHWAY TRAFFIC SIGNALS

### Figures 4C-1 to 4C-4 — Warrant 2 (Four-Hour Volume) and Warrant 3 (Peak Hour) Curves
(PDF 696, 698)
Each figure plots the **minor-street higher-volume approach (vph)** against the **major-street total
of both approaches (vph)**, with four curves by lane configuration (1 & 1; 2+ major & 1 minor;
1 major & 2+ minor; 2+ & 2+).
- **FIND (floor values in the notes)**: the curves bottom out at fixed minimums —
  **Warrant 2: 115 vph (minor approach with 2+ lanes) and 80 vph (1 lane)**; **Warrant 2 at 70 %:
  80 and 60 vph**; **Warrant 3: 150 and 100 vph**; **Warrant 3 at 70 %: 100 and 75 vph**. The 70 %
  figures apply in a **community of less than 10,000 population or above 40 mph on the major street**.

### Figures 4C-5 to 4C-8 — Warrant 4 (Pedestrian Volume) Curves (PDF 699–700; 4C-7 and 4C-8 Rev. 1)
Each plots **total pedestrians crossing the major street (pph)** against major-street vehicles, with
**two curves**: the lower applies where the **15th-percentile crossing speed is less than 3.5 ft per
second**. Floors from the notes: **four-hour 107 / 53 pph; peak hour 133 / 66 pph**; at 70 % —
**75 / 37** and **93 / 46 pph**.
- **CHECK (confirms a reading-log finding)**: the 70 % pedestrian figures apply in a community under
  10,000 **or above 35 mph on the major street** — **35 mph, not the 40 mph** used for the vehicular
  warrants (Figures 4C-2, 4C-4).

### Figures 4C-9 and 4C-10 — Warrant 9, Intersection Near a Grade Crossing (PDF 705)
Separate figures for **one approach lane** and **two or more approach lanes** at the crossing, each
with a **family of curves for D = 30, 50, 70, 90, 110 and 130 ft**, an **inset drawing defining D**
(from the track to the intersection, with 6 ft shown from the track), a floor of **25 vph**, and an
axis note that the volumes are those **after applying the adjustment factors of Tables 4C-6, 4C-7
and 4C-8**.

### Figure 4D-1 and Table 4D-1 — Recommended Vehicular Signal Faces for Approaches at 45 mph or
Higher (PDF 710)
A plan view with the legend distinguishing the **recommended overhead R-Y-G primary face for the
through or through/right lane**, the **overhead primary left-turn face as determined by the left-turn
mode**, and **possible locations for supplemental R-Y-G faces**.
- Notes: **any primary left- or right-turn faces should be overhead for each mandatory turn lane**;
  supplemental pole-mounted or overhead faces should be considered to maximise visibility; and
  **all signal faces should have backplates**.
- Starred note: with a **protected/permissive left turn using a shared face**, that face carries
  left-turn arrows in addition to the circular indications and is located **over the projection of the
  lane line** between the left-turn and through lanes.

### Figure 4D-2 — Lateral and Longitudinal Location of Primary Signal Faces (PDF 713)
The cone of vision drawn: faces must lie within **20° either side of the centre of the approach**,
measured from a point **10 ft beyond the stop line**, at least **40 ft** from the stop line and no
more than **120 ft for 8-inch faces** or **180 ft for 12-inch faces** (the latter unless a near-side
supplemental face is used); the hatching distinguishes where **12-inch indications are required** from
where **8-inch may be used**; lateral positioning shown as **X and X/2** about the approach centre.

### Figure 4E-2 — Typical Arrangements of Signal Sections in Faces That Do Not Control Turning
Movements (PDF 719)
**A vertical faces** (three-section R-Y-G, three-section with a green arrow for a continuous movement,
four-section with two reds), **B horizontal faces** (the same arrangements laid out left to right),
**C a single-section green arrow for a continuous movement**.
- Related Standards (4E.04): in a vertical face **all red sections are above all yellow and green
  sections**; a **yellow arrow sits above the green arrow to which it applies**; and the full
  top-to-bottom order is fixed: CIRCULAR RED, left-turn RED ARROW, right-turn RED ARROW, CIRCULAR
  YELLOW, CIRCULAR GREEN, straight-through GREEN ARROW, left-turn YELLOW ARROW (steady then
  flashing), left-turn GREEN ARROW, right-turn YELLOW ARROW (steady then flashing), right-turn GREEN
  ARROW.

### Figures 4F-1 to 4F-6 — Left-Turn Signal Face Arrangements (PDF 726–731)
**4F-1 permissive only, shared face** — a three-section R-Y-G face positioned **over the lane line
between the left-turn and through lanes**; the shared face **always displays the same colour circular
indication as the adjacent through face**.
**4F-2 permissive only, separate face with a flashing yellow arrow** — **red arrow, steady yellow
arrow, flashing yellow arrow**; the flashing yellow arrow may run **while the adjacent through faces
show steady circular red and the opposing left-turn faces show a green arrow** for a protected turn.
**4F-3 permissive only / protected-permissive, separate face with a flashing red arrow** — including
a **vertical face with a horizontal cluster of two red arrows** (steady left, flashing right); the
note restricts the device to cases where a study shows **every vehicle must come to a full stop**, and
names the optional R10-27 sign.
**4F-4 protected only, shared face** — a four-section face (or a face with a horizontal green cluster);
the note: shared faces are used for a protected-only left **only if the circular green and the green
left arrow always begin and terminate together**.
**4F-5 protected only, separate face** — **red arrow, yellow arrow, green arrow**.
**4F-6 protected/permissive, shared face** — shown **with** and **without** a mandatory left-turn
lane, with the optional **LEFT TURN YIELD ON GREEN (R10-12)** sign, and a bracket marking the
arrangements that may be **"used only if the green arrow and circular green are always terminated
together"**.
- Related Standards worth carrying: a **separate left-turn face shall not be used on an approach
  without a mandatory left-turn lane**; a separate face in **permissive** mode **shall not display
  circular green**; a separate face in **protected/permissive** mode **shall not display circular
  green**; and a protected/permissive shared face **always displays the same circular colour as the
  adjacent through faces**.

### Figure 4F-7 — Separate Faces with Flashing Yellow Arrow for Protected/Permissive and Variable
Mode Left Turns (PDF 732)
The **four-section face** (red arrow, steady yellow arrow, flashing yellow arrow, green arrow) with
footnotes marking which sections are suppressed in each mode — **flashing yellow not displayed in
protected-only mode; green arrow not displayed in permissive-only mode** — plus the **three-section
version using a bimodal steady/flashing yellow section**.
- Related Standard: when a permissive left becomes protected, the **green arrow appears immediately on
  termination of the flashing yellow**, with **no steady yellow in between**.

### Figures 4F-8 to 4F-14 — Right-Turn Signal Face Arrangements (PDF 736–742)
The right-turn mirror of the left-turn series: **4F-8 permissive only, shared face** (including an
optional third face serving as a shared face); **4F-9 permissive only, separate face with flashing
yellow arrow**; **4F-10 flashing red arrow** (again permitting a **horizontal cluster of two red
arrows**, steady and flashing, in a vertical face); **4F-11 protected only, shared face** (only where
the circular green and green arrow always begin and terminate together); **4F-12 protected only,
separate face**; **4F-13 protected/permissive, shared face** (with the bracket marking arrangements
that depend on the green arrow and circular green terminating together); **4F-14 separate
protected/permissive face**.
- **FIND (the red-arrow / circular-red choice carries a signing consequence)**: a separate right-turn
  face may use a **steady red arrow** where right turn on red is **not** to be permitted, or a
  **steady circular red** where it **is**; and where that circular red is sometimes displayed while
  the adjacent through faces are not red, a **RIGHT TURN SIGNAL (R10-10R) sign is required** unless
  the red is **shielded, hooded, louvered or positioned so it is not readily visible** to through
  drivers.
- Related Standards: a **separate right-turn face shall not be used on an approach without a mandatory
  right-turn lane**; a separate face in **protected/permissive** mode **shall not display circular
  green**; a protected/permissive shared face **always displays the same circular colour as the
  adjacent through faces**.

### Figure 4F-15 — Signal Indications for Approaches with a Combined Left-Turn/Right-Turn Lane and No
Through Movement (PDF 746–748, 3 sheets)
Three cases — **A no conflicting vehicular or pedestrian movements**, **B conflicts with one turn
movement**, **C conflicts with both turn movements** — each drawn for single-lane, two-lane and
three-lane approaches, with arrow-section clusters shown "OR" plain circular faces.
- Footnote: a **left-turn GREEN ARROW section is included only where there is an opposing one-way
  approach and the phasing eliminates conflicts**.
- Notes: horizontally aligned faces may be used, and **shared faces may be five sections in a vertical
  line instead of a cluster**.
- Related Option: where lane use varies by time of day, a shared face may use a **bimodal section**
  carrying both the steady and flashing yellow arrow, **so as not to exceed the five-section maximum**
  (4E.03).

## Part 4 — Chapter 4I (pedestrian control features)

### Figure 4I-1 — Typical Pedestrian Signal Indications (PDF 759)
**A with countdown display** and **B without** — the WALKING PERSON and UPRAISED HAND shown as a
combined two-symbol unit, as separate sections, and with the countdown numerals beside or below.
- Related Standards: all new indications are **symbols within a rectangular background**, each
  **independently displayed and emitting a single colour**; in a two-section head the **UPRAISED HAND
  is directly above the WALKING PERSON**; in a one-section head the symbols may be overlaid or placed
  **side by side with the HAND to the left**; the **WALKING PERSON is white** and the **UPRAISED HAND
  Portland orange**.

### Figure 4I-2 — Preferred Push Button Location Area (PDF 762)
A corner drawn with three zones — **A preferred, B acceptable, C acceptable but less desirable** —
and the governing dimensions: **10 ft MAX from the edge of the associated curb ramp**, **5 ft MAX from
the outside edge of the farthest marked crosswalk**, **1.5 ft MIN (and 1.5–6 ft) from the face of the
curb**, **4 ft MIN unobstructed pedestrian access route**, **10 ft MIN separation between two push
buttons on the same corner**, mounting **about 3.5 ft, no more than 4 ft above the sidewalk**, the
**face parallel to the crosswalk served**, no farther from the crosswalk than the stop line, and
**outside the flared side of the curb ramp**.
- Notes: the MAX and MIN dimensions **are recommendations**, and the figure **is not drawn to scale**.

### Figure 4I-3 — Typical Push Button Locations (PDF 764)
Four corner types — **perpendicular ramps with crosswalks close together**, **parallel ramps**,
**perpendicular ramps with a shared landing**, **perpendicular ramps with a continuous surface
between them** — each keeping the **4 ft MIN** clear route, with the legend marking downward slope,
detectable warnings and landing areas. Notes: **not to scale**, and the drawings show **push button
locations only, not curb ramp design**.

### Figure 4I-4 — Pedestrian Intervals (PDF 765, Rev. 1)
The master timing diagram: **walk interval (7 seconds MIN)**, **pedestrian change interval (the
calculated clearance time)**, **buffer interval (2 seconds MIN)**, with the **"zero" point of the
countdown display at the end of the pedestrian change interval**, and **five possible relationships to
the vehicular phase** — the buffer equal to the yellow change interval; to the yellow plus red
clearance; to part of the yellow plus red clearance; to the red clearance alone; or the green
extending beyond the buffer.
- Footnotes: the **countdown display is optional for change intervals of 7 seconds or less**; the
  **walk interval may be reduced under some conditions**; the **buffer is always provided and
  displayed**, and may help satisfy the clearance time or begin after it ends.
- Related Guidance/Option: clearance time based on **3.5 ft/s**, or up to **4 ft/s** where an
  **extended push button press** gives slower pedestrians more time.
- **CHECK**: confirms the pedestrian timing items computed during the reading (4I.06).

### Figure 4L-1 — RRFBs at Uncontrolled, Marked Crosswalks at an Intersection (PDF 778, Rev. 1)
An intersection with two uncontrolled approaches (beacon-equipped crossing signs with diagonal arrow
plaques) and two stop-controlled approaches.
- Note (a Standard): when activated, the **RRFBs on both approaches shall commence and cease
  operation simultaneously**.

# PART 6 — TEMPORARY TRAFFIC CONTROL

### Figure 6B-1 — Component Parts of a Temporary Traffic Control Zone (PDF 813)
The zone anatomy, labelled: **advance warning area** (tells traffic what to expect), **transition
area** (moves traffic out of its normal path), **activity area** (containing the **work space**, the
**traffic space** and the **lateral and longitudinal buffer spaces**), and the **termination area**
with its **downstream taper**.

### Figure 6B-2 — Types of Tapers and Buffer Spaces (PDF 815)
**Merging taper = L**, **shifting taper = ½L**, **shoulder taper = ⅓L**, plus an optional
**downstream taper** and optional **lateral and longitudinal buffer spaces**; one segment is
dimensioned **4S ft** (S = speed in mph). Table 6B-4 gives the formulas for L.
- **FIND**: the taper family is defined as **fractions of L**, and one dimension is a **multiple of
  the speed** rather than a fixed length.

### Figure 6B-3 — One-Lane, Two-Way Traffic Taper (PDF 818)
A curve with one-way alternating operation: the **one-lane, two-way traffic taper 50 to 100 ft**, the
**downstream taper 50 to 100 ft**, flaggers at both ends, and a callout explaining that the
**longitudinal buffer space is used to position the taper in advance of the curve**.

### Figure 6D-1 — Use of Hand-Signaling Devices by Flaggers (PDF 825, Rev. 1)
Two columns — **the STOP/SLOW paddle as the preferred method (18 in MIN)** and **the flag for
emergency situations only (a 24 × 24 in red flag on a 36-in staff)** — across three actions: **to stop
traffic**, **to let traffic proceed**, and **to alert and slow traffic**.

### Figures 6F-1 and 6F-2 — Height and Lateral Location of TTC Signs; Methods of Mounting Signs Other
Than on Posts (PDF 831, 833)
**6F-1**: rural **5 ft MIN** height with **6 to 12 ft** lateral offset; rural with an advisory speed
plaque, **4 ft MIN** to the bottom of the plaque and **6 ft MIN** from the paved shoulder; business,
commercial or residential **7 ft MIN** with **2 ft MIN** lateral; the same without a curb at 6 to 12 ft.
**6F-2**: the **high-level warning device (flag tree) at 8 ft MIN**, portable sign stands and
vehicle-mounted signs with **1 ft MIN above the travelled way**, orange flags optional above signs,
and **barricade-mounted signs with an optional flasher**.
- Related Standards/Guidance: a sign on a barricade or portable support has its bottom **at least 1 ft
  above the travelled way**; supports that do not meet the Part 2 heights **should not be used for
  more than 3 days**; sign supports should not be placed on sidewalks or bicycle facilities.

### Figure 6G-1 — Regulatory Signs and Plaques in TTC Zones (PDF 835–836, 2 sheets, Rev. 1)
The work-zone regulatory set, including signs peculiar to work zones: **R1-7 / R1-7a WAIT ON STOP,
R1-8 GO ON SLOW**, **R4-9a STAY IN LANE TO MERGE POINT**, **R2-12 END WORK ZONE SPEED LIMIT**, the
**orange G20-5aP WORK ZONE plaque above a Speed Limit sign**, higher-fines signs, sidewalk and path
closure signs (**R9-8 to R9-12, R11-2c PATH CLOSED**), **R9-20 ALLOWED USE OF FULL LANE**, weight
limit signs and **R22-2 TURN OFF 2-WAY RADIO AND CELL PHONE**.
- Related Guidance: **STAY IN LANE TO MERGE POINT** is for **late merge operations**, directing
  traffic to use all lanes until the merge point; a marked detour must be provided for vehicles over
  a posted weight limit imposed by the work.

### Figure 6H-1 — Warning Signs and Plaques in TTC Zones (PDF 840–843, 4 sheets)
The work-zone warning set in orange, mirroring the Part 2 yellow signs (alignment, advance traffic
control, merge, lane and road width, two-way traffic, hill, bump) plus work-zone-only messages.
- Note on each sheet: **see Chapter 2C for the application of these signs** — the same signs, in
  orange, governed by the Part 2 rules.

### Figure 6H-1 sheets 2–4 (PDF 841–843)
The rest of the orange warning set, including **W22 blasting signs**, **W23-1 SLOW TRAFFIC AHEAD**,
**W23-2 NEW TRAFFIC PATTERN AHEAD**, the **W24-1 series lane-shift signs with an "ALL LANES" plaque**,
and the guide signs **G20-1 ROAD WORK NEXT XX MILES**, **G20-2 END ROAD WORK** and **G20-4 PILOT CAR
FOLLOW ME**.

### Figure 6I-1 — Exit Open and Closed and Detour Signs and Plaques (PDF 853)
**E5-2 EXIT OPEN**, **E5-2a EXIT CLOSED**, **E5-3 EXIT ONLY**, the **M4-8P DETOUR plaque**,
**M4-8a END DETOUR**, **M4-9 DETOUR with arrow**, and **separate pedestrian, bicyclist and combined
pedestrian/bicyclist detour signs (M4-9a, M4-9b, M4-9c)**, plus the **black-on-orange M4-10 detour
arrow**.
- Related Standards/Guidance: the pedestrian/bicyclist detour sign **shall have an arrow pointing in
  the appropriate direction** (on the face or on a plaque); the detour arrow is mounted **just below
  the ROAD CLOSED sign**; and when an exit ramp is closed, an **EXIT CLOSED panel is placed
  diagonally across the interchange guide signs**.

### Figure 6K-1 — Channelizing Devices (PDF 857, Rev. 1)
Every device dimensioned, with a **speed-based split**: **cones and tubular markers 18 in minimum for
day and low-speed roadways (≤ 40 mph) and 28 in minimum for night or high-speed roadways (≥ 45 mph)**;
**drums 36 in minimum, 18 in wide, 4- to 6-in stripes**; **vertical panels 24 in minimum with 45°
stripes**; **Type 1 and Type 2 barricades 36 in minimum**, **Type 3 barricades 5 ft minimum height and
4 ft minimum width**, and the **Direction Indicator Barricade with a 24 × 12 in arrow**.
- Footnotes: **warning lights are optional**; **rail stripes are 6 in wide, except 4 in where the rail
  is less than 36 in long**; and **the sides of barricades facing traffic shall have retroreflective
  rail faces**.

### Figure 6K-2 — Pedestrian Channelizing Device (PDF 858)
A cross-section and a perspective view, dimensioned: a **continuous hand-trailing edge 32 in MIN to
38 in MAX above the walkway**, with a **2 in MIN gap between it and its support**; a **continuous
detection plate 8 in MIN tall** with **no more than a 2 in gap at the bottom** (a gap permitted for
drainage); striping either vertical or at 45°.
- Related Standards: pedestrian channelizing devices shall be **crashworthy when exposed to vehicular
  traffic**, **detectable to users of long canes and visible to pedestrians with vision
  disabilities**, and when used as a sidewalk closure **shall cover the entire width of the sidewalk**.

### Figures 6L-1 and 6L-2 — Automated Flagger Assistance Devices (PDF 868, 870; 6L-2 Rev. 1)
**6L-1 the STOP/SLOW AFAD**: a remotely operated paddle with a **flashing beacon** above and a **gate
arm**, with the **R1-7 / R1-7a WAIT ON STOP** and **R1-8 GO ON SLOW** signs mounted beneath — the
explanation for those work-zone-only regulatory signs. Shown as **Method 1 with two AFADs**.
**6L-2 the red/yellow lens AFAD**: a **two-section signal face (red over yellow) with a required
gate**, the **R10-6 STOP HERE ON RED** sign, and a **W20-7 flagger symbol sign with an XX FEET
plaque**; shown as **Method 2 with one AFAD and a flagger**. Advance spacings use the **A, B, C**
letter codes of Table 6B-1.

### Figure 6L-3 — Advance Warning Arrow Board Display Specifications (PDF 875)
The mode requirements: **at least one of flashing arrow, sequential arrow or sequential chevron**;
**the flashing double arrow always**; and **at least one of flashing caution or alternating diamond
caution**. The type table (read earlier) gives sizes, legibility distances and element counts, with
**Type D having no minimum panel size** but a **48-in arrow with a 24-in arrowhead**.
- Related Standard: **a separate arrow board for each closed lane** where multiple lanes are closed,
  with Guidance on staggering the second board at the second merging taper.

### Figure 6N-1 — Late Merge (PDF 894, Rev. 1)
The zipper-merge sequence: **R4-9a STAY IN LANE TO MERGE POINT** far upstream, then ROAD WORK XX MILE,
RIGHT LANE CLOSED XX MILE, the W4-2 lane-ends warning, and at the taper **W9-2a MERGE HERE TAKE
TURNS** beside the arrow board, with **END ROAD WORK 500 ft** beyond; advance spacings by the A, B, C
letter codes.

### Figure 6O-1 — Traffic Incident Management Area Signs (PDF 896, Rev. 1)
The same shapes as the orange work-zone signs but on **fluorescent pink** — W3-4, W4-2, W9-3,
E5-2a EXIT CLOSED, M4-8a END DETOUR, M4-9 and M4-10 detour arrows.
- Related definitions on the page: a **major traffic incident** closes all or part of a roadway for
  **more than 2 hours**; anything expected to last **more than 24 hours** uses the ordinary Part 6
  procedures and devices.

## Part 6 — Chapter 6P (Typical Applications)

### Figure 6P-1 — Work Beyond the Shoulder (TA-1) (PDF 902)
The simplest application: a single **W20-1 ROAD WORK AHEAD** sign at distance **A** ahead of a work
space entirely beyond the shoulder. Note on the sheet: **Table 6P-2 for the symbols** and
**Table 6B-1 for the letter codes** — the two keys that unlock every Typical Application drawing.

### Figures 6P-2 to 6P-7 — Typical Applications 2 to 7 (PDF 904–914)
**TA-2 Blasting Zone**: the **blasting zone extends 1,000 ft MIN** each side of the blasting area,
with **BLASTING ZONE AHEAD**, then **TURN OFF 2-WAY RADIO AND CELL PHONE 300 to 500 ft** inside it,
and **END BLASTING ZONE** at each end, repeated both directions; the legend marks **blasting caps**.
**TA-3 Work on the Shoulders**: SHOULDER WORK signs on each approach at spacing **A**, a **⅓L shoulder
taper**, ROAD WORK NEXT XX MILES ahead and optional END ROAD WORK beyond; signs repeated on the
crossroad approaches.
**TA-4 Short-Duration or Mobile Operation on a Shoulder**: a **work vehicle with a shadow vehicle**
carrying an **optional truck-mounted attenuator** and an **arrow board in four-corner caution mode**,
plus vehicle-mounted signs — no cones or taper.
**TA-5 Shoulder Closure on a Freeway (Rev. 1)**: **RIGHT SHOULDER CLOSED** with NEXT XX MILES and
XX FT plaques at spacings A, B, C, a **⅓L taper**, a **crash cushion at the upstream end of the
barrier**, and optional barrier and lights.
**TA-6 Shoulder Work with Minor Encroachment**: the work may intrude into the lane only while **at
least 10 ft of lane width remains**, with a ⅓L taper and an optional buffer space.
**TA-7 Road Closure with a Diversion (Rev. 1)**: a temporary roadway around the closure, with
**temporary double yellow centre line and temporary white edge lines**, callouts marking where
**temporary pavement starts and ends**, **W24-1L lane-shift signs with an advisory speed plaque**,
large arrow signs, **crash cushions at the barrier ends**, and **END ROAD WORK 500 ft** beyond.
- **FIND (across the early TAs)**: each drawing carries its own **dimensions (1,000 ft, 10 ft, 500 ft,
  300–500 ft)** alongside the **letter codes A, B, C** and the **taper fractions (⅓L)** — the fixed
  numbers are in the drawings, the variable ones in Tables 6B-1 and 6B-4.

### Figures 6P-8 to 6P-13 — Typical Applications 8 to 13 (PDF 916–926)
**TA-8 Road Closure with an Off-Site Detour (Rev. 1)**: ROAD CLOSED **1000 FT** then **500 FT**, the
R11-2 barricade at the closure, **"ROAD CLOSED XX MILES AHEAD — LOCAL TRAFFIC ONLY"** with the detour
arrow at the junction, route assemblies with **DETOUR plaques and turn arrows** about **200 ft** from
the intersection, and the crossroad sequence at **1,000 ft / 500 ft** with **DETOUR 1500 FT**.
**TA-9 Overlapping Routes with a Detour (Rev. 1)**: a whole detour network for two overlapping routes.
- **FIND (a reading key)**: its note says **route assemblies shown without a DETOUR plaque are the
  existing permanent assemblies** — so the orange plaques mark exactly what the closure adds, and the
  **END DETOUR** plaques mark where the temporary routing stops.
**TA-10 Lane Closure on a Two-Lane Road Using Flaggers (Rev. 1)**: flagger stations with **W20-7
flagger symbol signs and XX FEET plaques**, the one-lane two-way taper and downstream taper each
**50 to 100 ft**, and the ROAD WORK / ONE LANE ROAD advance signs at A, B, C.
**TA-11 Lane Closure on a Two-Lane Road with Low Traffic Volumes**: the one-lane operation **without
flaggers** — a **YIELD sign with the "TO ONCOMING TRAFFIC" plaque**, an optional **yield line 15 ft**
ahead of it, a **W3-2 Yield Ahead** sign, **optional beacons above the advance signs**, and optional
buffer spaces either side of the work.
**TA-12 Lane Closure on a Two-Lane Road Using Temporary Traffic Control Signals (Rev. 1)**: temporary
signals with **W3-3 Signal Ahead** and **R10-6 STOP HERE ON RED**, **temporary markings 500 to 600 ft**
either side, stop lines **40 to 180 ft** from the one-lane section, tapers **50 to 100 ft**, and
**optional lighting** at both ends of the work space.
**TA-13 Temporary Road Closure**: a short full closure held by **flaggers at both ends** with optional
buffer spaces, BE PREPARED TO STOP and flagger symbol signs at A, B, C.

### Figures 6P-14 to 6P-19 — Typical Applications 14 to 19 (PDF 928–938)
**TA-14 Haul Road Crossing**: two variants — **A temporary signals** (stop lines **40 to 180 ft**
back, optional beacon above the Signal Ahead sign) and **B flaggers stationed 30 ft from the
crossing**, with **DO NOT PASS** and the pennant **NO PASSING ZONE** signs; optional temporary
markings; flagger or haul-road warning devices on the haul road itself.
**TA-15 Work in the Centre of a Road with Low Traffic Volumes**: channelizing devices around the work
with **R4-7 Keep Right signs facing each direction**, **½L tapers**, optional **high-level warning
devices (flag trees)**, and the requirement that **at least 10 ft remain to the edge of pavement or
outside edge of paved shoulder** on each side.
**TA-16 Surveying Along the Centre Line**: **SURVEY CREW** and flagger symbol signs, a flagger each
side, buffer spaces, and the same **10 ft MIN to the edge of pavement** rule.
**TA-17 Mobile Operations on a Two-Lane Road**: a **work vehicle and a shadow vehicle**, each with an
optional **truck-mounted attenuator**, the shadow vehicle carrying an optional arrow board in caution
mode and a sign whose **shape and legend suit the type of work**.
**TA-18 Lane Closure on a Minor Street**: a short taper **50 to 100 ft**, optional work vehicle with
attenuator, optional buffer space, and **W21-1 worker symbol signs** at spacing A each way.
**TA-19 Detour for One Travel Direction**: a one-way detour through a street grid, using **modified
street-name DETOUR signs (M4-9L/M4-9R with the street name)**, **ROAD CLOSED / ROAD CLOSED TO THRU
TRAFFIC** barricades, **DO NOT ENTER**, **ONE WAY**, **No Left/Right Turn** signs, and **DETOUR arrow
signs paired with ONE WAY signs**, with **END DETOUR** at the far end and a sign **100 ft** from the
final turn.

### Figures 6P-20 to 6P-25 — Typical Applications 20 to 25 (PDF 940–950; TA-22 to TA-25 Rev. 1)
**TA-20 Detour for a Closed Street**: a two-way detour around a closed block, using **modified
street-name DETOUR signs**, ROAD CLOSED and ROAD CLOSED TO THRU TRAFFIC barricades, turn prohibitions
and **END DETOUR** plaques at both ends.
**TA-21 Lane Closure on the Near Side of an Intersection**: a **merging taper L**, W9-3L and W20-1 at
spacings A and B, a **W12-1 double arrow at the work**, and optional work vehicle, buffer space and
high-level warning device.
**TA-22 Right-Hand Lane Closure on the Far Side of an Intersection (Rev. 1)**: the closure begins
beyond the intersection, with **R3-7R RIGHT LANE MUST TURN RIGHT** on the near side, an **arrow
board**, a **taper L**, and the advance sequence RIGHT LANE CLOSED AHEAD / W4-2R / ROAD WORK AHEAD at
A, B, C; the far-side work is coned off with its own arrow board.
**TA-23 Left-Hand Lane Closure on the Far Side of an Intersection (Rev. 1)**: the mirror case, with
**R3-7L 100 ft from the intersection**, a channelizing run of **2L** through the intersection, and a
taper **L** beyond.
**TA-24 Half Road Closure on the Far Side of an Intersection (Rev. 1)**: both directions affected — a
**taper L with a buffer space and a ½L shifting taper**, turn prohibitions (R3-1, R3-2), an optional
**R4-7c narrow Keep Right sign**, and mirrored advance signing on every approach.
**TA-25 Multiple Lane Closures at an Intersection (Rev. 1)**: a run of tapers in series — **⅓L, L,
2L and ½L** — with **R3-7L**, an arrow board, an optional high-level warning device, and R4-7 Keep
Right at the far side.
- **FIND**: the intersection applications express nearly every longitudinal dimension as a
  **multiple or fraction of L** (⅓L, ½L, L, 2L), with only a few fixed distances (100 ft), so the
  whole layout scales with the design speed through Table 6B-4.

### Figures 6P-26 to 6P-31 — Typical Applications 26 to 31 (PDF 952–962; TA-28 Rev. 1)
**TA-26 Closure in the Centre of an Intersection**: the work boxed in the middle with **½L tapers on
every approach**, **R4-7 Keep Right signs facing each direction**, and **10 ft MIN** left between the
work and each kerb line.
**TA-27 Closure at the Side of an Intersection**: one-lane two-way operation past the work with
**flaggers on all four approaches**, tapers **50 to 100 ft**, and ONE LANE ROAD AHEAD / flagger signs
at A, B, C on each leg.
**TA-28 Sidewalk Detour or Diversion (Rev. 1)**: the two options side by side — a **detour** sending
pedestrians across the street with SIDEWALK CLOSED / CROSS HERE signs, and a **diversion** building a
**temporary walkway in the parking lane with ramps at each end** and a **temporary walkway surface
covering rough, soft or uneven ground**.
**TA-29 Crosswalk Closures and Pedestrian Detours**: pedestrians routed to a **temporary crosswalk**
with temporary markings (high-visibility optional), pedestrian warning signs with arrow and AHEAD
plaques, and R9-9 / R9-11 / R9-11a closure signs.
- Note: for **long-term stationary work the double yellow centre line and lane lines should be removed
  between the crosswalk lines**.
**TA-30 Interior Lane Closure on a Multi-Lane Street**: an inside lane closed from both directions,
each with a **taper L**, an **arrow board**, optional buffer spaces, and a work vehicle with
attenuator.
**TA-31 Lane Closure on a Street with Uneven Directional Volumes**: traffic borrowed from the lighter
direction — a **taper L**, a **½L shifting taper**, a **temporary solid white lane line**, reverse
curve signs with advisory speed plaques, **100 ft** between the crossover and the work, and a tangent
of **4S ft** (S = speed in mph) between the shifting tapers.

### Figures 6P-32 to 6P-37 — Typical Applications 32 to 37 (PDF 964–974)
**TA-32 Half Road Closure on a Multi-Lane, High-Speed Highway**: traffic crossed onto the opposite
carriageway, with **temporary yellow lines** where the directions share pavement, a **temporary white
edge line**, **½L MIN** shifting tapers and reverse-curve signs with advisory speed plaques.
**TA-33 Stationary Lane Closure on a Divided Highway**: drawn twice to show that **duration changes
the layout** — **A long-term and intermediate** with a **temporary white edge line** and an optional
**100 ft downstream taper**; **B short-term** with a **work vehicle and attenuator** at the head and
no downstream taper. Both end **500 ft** before END ROAD WORK.
**TA-34 Lane Closure with a Temporary Traffic Barrier**: a barrier run with a **crash cushion at its
upstream end**, a shoulder taper, temporary white edge line, and **W20-1 1,500 ft** in advance on the
opposite carriageway.
**TA-35 Mobile Operation on a Multi-Lane Road**: a work vehicle and **two shadow vehicles**, each with
an attenuator and arrow board, and a **W20-5L LEFT LANE CLOSED AHEAD** sign carried on the last one.
**TA-36 Lane Shift on a Freeway**: the whole shift in fractions of L — a **⅓L shoulder taper** and
**½L shifting tapers** — with **temporary yellow edge line**, **temporary solid white lane lines**,
**temporary white edge line**, reverse-curve signs with advisory speeds, a crash cushion and optional
lighting.
**TA-37 Double Lane Closure on a Freeway**: two closures in series — **taper L, a 2L run, then a
second taper L** — each with its own **arrow board**, and a **"2 RIGHT LANES CLOSED ½ MILE"** advance
sign, matching the Standard that each closed lane gets its own arrow board.

### Figures 6P-38 to 6P-43 — Typical Applications 38 to 43 (PDF 976–986)
**TA-38 Interior Lane Closure on a Freeway**: an inside lane closed and the remaining traffic shifted,
with a **temporary solid double white lane line** forbidding lane changes, an optional **STAY IN
LANE** sign, a **16 ft MIN** combined width for the shifted lanes, and tapers of **L, 2L and ½L**.
**TA-39 Median Crossover on a Freeway**: one carriageway carrying both directions, with a **temporary
double yellow centre line**, **two-way traffic warning signs**, **DO NOT PASS**, and at the closed
carriageway **DO NOT ENTER, ROAD CLOSED and Keep Right**; crash cushions at the barrier ends and a
tangent of **2S ft** between shifting tapers.
**TA-40 Median Crossover for an Entrance Ramp**: the ramp fed into the two-way section, with a
**YIELD sign and Yield Ahead**, **DO NOT ENTER and ONE WAY** facing the wrong direction, channelizing
devices at **25-ft spacing**, **250 ft** of tapered separation, temporary yellow and white edge lines
and optional lighting.
**TA-41 Median Crossover for an Exit Ramp**: the mirror case, with the **EXIT gore sign retained**,
devices at **25-ft spacing**, **250 ft** and **150 ft** dimensions, and optional lighting both sides.
**TA-42 Work in the Vicinity of an Exit Ramp**: drawn twice — work **beyond** and work **before** the
ramp — each with **temporary yellow and white edge lines**, a taper **L**, **100 ft** and **1,000 ft**
dimensions, and an optional **EXIT OPEN** sign to confirm the ramp is still usable.
**TA-43 Partial Exit Ramp Closure**: the ramp narrowed rather than closed, needing **10 ft MIN**
remaining width, a **RAMP NARROWS** sign with an advisory speed plaque, **ROAD WORK XX FT with an ON
RAMP plaque**, and END ROAD WORK **500 ft** beyond.

### Figures 6P-44 to 6P-49 — Typical Applications 44 to 49 (PDF 988–998; TA-47 to TA-49 Rev. 1)
**TA-44 Work in the Vicinity of an Entrance Ramp**: drawn twice — **A added lane** (large arrow and
added-lane warning) and **B merge required** (**YIELD with Yield Ahead**) — carrying the Part 2
merge/added-lane distinction into the work zone; temporary yellow and white edge lines, taper L,
**500 ft** spacings.
**TA-45 Temporary Reversible Lane Using Movable Barriers**: the same road in **Phase A** and in
**transition to Phase B**, with the **barrier transfer vehicle**, its **parking location for each
phase**, a **movable attenuator**, and signing that changes with the phase.
**TA-46 Work in the Vicinity of a Grade Crossing**: one-lane operation near a railway crossing with an
**extended buffer space so queues never stop on the tracks**, **R8-8 DO NOT STOP ON TRACKS** signs and
crossbucks both approaches, and flaggers with tapers **50 to 100 ft**.
**TA-47 Bicycle Lane Closure without a Detour (Rev. 1)**: cyclists merge into the traffic lane, with a
**width threshold deciding the sign** — **lane narrower than 14 ft → R9-20 ALLOWED USE OF FULL LANE**;
**14 ft or wider → W11-1 bicycle warning with the W16-1P IN ROAD plaque**; **W9-5a bicycle MERGE** and
**BIKE LANE CLOSED AHEAD** upstream, **R9-12 BIKE LANE CLOSED** at the closure.
- Note: **the speeds used for the spacings shall be motor vehicle speeds.**
**TA-48 Bicycle Lane Closure with an On-Road Detour (Rev. 1)**: the same width threshold, plus a
signed on-road bicycle detour around the block using **M4-9c bicycle DETOUR signs with street names and
arrows** and **END DETOUR** at the far end.
**TA-49 Shared-Use Path Closure with a Diversion (Rev. 1)**: a **temporary path** built alongside, with
**PATH CLOSED (R11-2c)** signs and detour arrows at each end, **PATH WORK AHEAD** and lane-shift
warning signs at **100 ft** intervals on both approaches.

### Figures 6P-50 to 6P-54 — Typical Applications 50 to 54 (PDF 1000–1008; TA-50, TA-51 Rev. 1)
**TA-50 On-Road Detour for a Shared-Use Path (Rev. 1)**: path users sent onto the street network with
**bicycle DETOUR signs carrying the path's name and arrows**, **PATH CLOSED** signs at each end, the
**same 14-ft width threshold** deciding between ALLOWED USE OF FULL LANE and the bicycle warning with
IN ROAD plaque, and advance signs at **100 ft** intervals.
**TA-51 Paved Shoulder Closure with a Bicycle Diversion onto a Temporary Path (Rev. 1)**: a
**temporary path** built beside the closed shoulder with **⅓L tapers**, bicycle DETOUR signs at each
end, and RIGHT SHOULDER CLOSED with an XX FT plaque; a note refers to **Figures 6P-5 or 6P-34 for
additional devices or barriers**, depending on site conditions and work duration.
**TA-52 Short-Term or Short-Duration Work in a Circular Intersection**: work in one quadrant of a
roundabout, with **flaggers on every approach**, tapers **50 to 100 ft**, and ONE LANE ROAD / flagger
signs at A, B, C on each leg.
**TA-53 Flagging Operation on a Single-Lane Circular Intersection**: the circulatory roadway itself
reduced to one lane, with **flaggers and W12-1 double-arrow signs on every approach**, **ROAD CLOSED**
signs blocking the closed segment, channelizing devices at **50 to 100 ft** intervals, and the note
"**use the same sign sequence that is used on the northbound approach**" on each leg.
**TA-54 Inside Lane Closure on a Multi-Lane Circular Intersection**: the inner circulatory lane closed
all the way round, with **tapers L and arrow boards on every approach**, optional buffer spaces, and
the same repeated-sequence note.
- **FIND**: the roundabout applications rely on a **"use the same sign sequence as the northbound
  approach"** note rather than repeating the signs on every leg — a drafting shorthand the graph must
  expand when reading these drawings.

**All 54 Typical Applications read.**

# PART 7 — TRAFFIC CONTROL FOR SCHOOL AREAS

### Figure 7A-1 — School Route Plan Map (PDF 1010)
A whole-neighbourhood plan whose legend defines what such a plan must show: **the school, marked
crosswalks, crossing guard locations, signalized intersections, STOP or YIELD sign approaches, and
the established pedestrian routes**.

### Figure 7B-1 — Signs in School Areas and at School Crossings (PDF 1014–1015, 2 sheets, Rev. 1)
The school sign set in **fluorescent yellow-green**: the **School Advance Crossing Assembly** and
**School Crossing Assembly** (S1-1 with distance, AHEAD or arrow plaques), the **School Zone sign**
(S1-1 with ALL YEAR / SCHOOL / arrow plaques), the **School Speed Limit Assembly** (R2-1 with SCHOOL,
time-of-day, WHEN CHILDREN ARE PRESENT or WHEN FLASHING plaques), the **S5-1 School Speed Limit When
Flashing sign** with higher-fines plaques, and S3-1, S3-2, S4-5, S4-5a, S5-2, S5-3, R2-10, R2-11.
- **CHECK (third confirmation of Ruling 6)**: the plate's footnote — "**If used, the assembly or sign
  with WHEN FLASHING legend shall be accompanied by a flashing yellow Speed Limit Sign Beacon (see
  Section 4S.04)**" — joining Figure 2D-37 (beacons above the rerouting sign) and Figure 2I-8 (the
  URGENT MESSAGE WHEN FLASHING plaque). Recorded in the reading log.

### Figures 7B-2 to 7B-4 — School Zone and School Crossing Signing (PDF 1016, 1018, 1020;
7B-4 Rev. 1)
**7B-2** a school zone with a school speed limit and a school crossing — the speed limit assembly at
each end of the zone, **END SCHOOL SPEED LIMIT "OR" END SCHOOL ZONE** with an optional speed limit
sign beyond, crossing assemblies with diagonal arrow plaques at the crossing, and advance assemblies
with **200 FT / AHEAD** plaques; note: **the School Advance Crossing Assembly is optional within a
signed school zone**.
**7B-3** a school crossing **outside** a school zone, where the advance assembly is used with
**300 FT / AHEAD** plaques and an optional **W16-6PR** arrow plaque.
**7B-4** the same zone with **higher fines only for speeding**, using the **FINES HIGHER / FINES
DOUBLE / $150 FINE** plaques beneath the school speed limit assembly rather than the separate
higher-fines zone signs.

### Figure 7B-5 — School Zone with Higher Fines for All Traffic Violations (PDF 1022–1023, 2 sheets,
Rev. 1)
Two cases — **A the higher fines zone begins at the beginning of the school zone** and **B it begins
elsewhere** — using **R2-10 BEGIN HIGHER FINES ZONE** and **R2-11 END HIGHER FINES ZONE** signs with
the **FINES HIGHER / FINES DOUBLE / $150 FINE** plaques, alongside END SCHOOL ZONE.

# PART 8 — TRAFFIC CONTROL FOR RAILROAD AND LIGHT RAIL TRANSIT GRADE CROSSINGS

### Figure 8B-1 — Regulatory Signs and Plaques for Grade Crossings (PDF 1037)
Includes devices unique to crossings: the **R3-1a / R3-2a activated blank-out No Turn signs (white on
black)**, the **R15-1 crossbuck**, the **R15-2P number-of-tracks plaque**, the **R15-3P EXEMPT
plaque**, **R8-8 DO NOT STOP ON TRACKS**, **R8-9 TRACKS OUT OF SERVICE**, **R8-10 / R8-10a STOP HERE
WHEN FLASHING**, **R10-6 / R10-6a STOP HERE ON RED**, the **R15-4 series light rail lane-only signs**,
**R15-5 / R15-5a DO NOT PASS (stopped train)**, **R15-6 / R15-6a DO NOT DRIVE ON TRACKS**,
**R15-7 / R15-7a divided highway track crossing signs**, and the **R15-8 LOOK sign with a
double-headed arrow**.

### Figures 8B-2 and 8B-3 — Crossbuck Assembly with a YIELD or STOP Sign (PDF 1038–1040)
**8B-2 on the crossbuck support**: crossbuck at **9 ft** (variable to accommodate signs below), a
**2-inch white retroreflective strip on the back of the support** and an **optional 2-inch red or
white strip on the front**, ending **2 ft MAX** above the near edge of the roadway.
**8B-3 on a separate support**, drawn for **rural areas (5 ft MIN)** and **areas with pedestrian
movements or parking (7 ft MIN)**, with the YIELD or STOP sign **placed closer to the travelled way,
in the same plane as the crossbuck, with a 2-inch minimum separation** between the two sign edges.
- Mounting heights by situation: **at least 4 ft** for YIELD or STOP signs added to existing crossbuck
  supports; **5 ft** for new rural installations; **7 ft** where parking or pedestrian movements are
  likely.
- Notes: **YIELD or STOP signs are used only at passive crossings**, and a **STOP sign only where an
  engineering study finds it appropriate**.
- Related Standard: a **STOP sign shall not be installed on a Crossbuck Assembly** where the crossing
  is at a highway-highway intersection controlled by a signal that is **not interconnected with the
  crossing and not preempted** by rail traffic.

### Figure 8B-4 — Warning Signs and Plaques for Grade Crossings (PDF 1043)
The yellow crossing warning set, including **two more activated blank-out signs** (W10-7 light rail
symbol and **W10-16 ANOTHER TRAIN COMING**, white or yellow on black), and signs peculiar to crossings:
**W10-8 TRAINS MAY EXCEED XX MPH**, **W10-9 NO TRAIN HORN** with its W10-9P plaque, **W10-11a / W10-11b
plaques stating the distance between the tracks and a parallel highway**, **W10-12 skewed crossing**,
**W10-13P NO GATES OR LIGHTS**, **W10-14P NEXT CROSSING**, **W10-14aP USE NEXT CROSSING**,
**W10-15P ROUGH CROSSING**, **W10-21 BUSWAY CROSSING** and **W10-21aP SIGNAL AHEAD**.
- Related Guidance: where the tracks are **100 ft or more** from a parallel highway, the plain W10-1
  crossing-ahead sign is used instead of the combined-geometry signs.

### Figure 8B-5 — Emergency Notification System Sign (PDF 1048)
**White on blue**, carrying the emergency telephone number and the **USDOT grade crossing inventory
number**.
- **CHECK**: this is the sign recorded during the reading as a named exception to the ban on telephone
  numbers. Its Standards: **required on each approach** at all highway-rail crossings and at
  highway-LRT crossings with automatic gates or flashing light signals; **minimum 12 in wide and 9 in
  tall**, lettering and numerals **at least 1 in high**, and the sign **retroreflective**.

### Figures 8C-1 to 8C-3 — Grade Crossing Markings (PDF 1051–1054)
**8C-1 placement**: transverse lines **24 in** wide, the stop line **15 ft MIN** from the nearest rail
or **about 8 ft upstream of a gate**, the **RXR pavement symbol** with a **50 ft** extent placed at
least **50 ft** from the stop or yield line, and the **dynamic envelope** marking shown as optional.
On multi-lane roads the transverse lines extend across all approach lanes with an **RXR symbol in each
lane**; yield lines may replace stop lines where YIELD signs are used.
**8C-2 the symbol itself**, dimensioned for the standard form (**8 ft wide, 20 ft X, 6 ft letters,
16-in strokes**) and the **alternative narrow form** (**6.6 ft wide, letters below the X**).
**8C-3 dynamic envelope markings**: a **solid white line not less than 4 in and not greater than 24 in
wide**, placed **completely outside** the envelope and **parallel to the nearest rail** (never
perpendicular at a skewed crossing), with optional white cross-hatching between the transverse lines,
and **contrasting pavement colour or texture** permitted alone or with the markings.
- Related Standard: raised or tubular markers at a crossing **take the colour of the line they
  supplement**, day and night.

### Figures 8C-4 and 8C-5 — Dynamic Envelope and Do Not Block Markings (PDF 1055–1056)
White cross-hatching may **supplement but never substitute for** the solid dynamic envelope lines, and
may also mark adjacent areas where vehicles are not to stop or stand; in **semi-exclusive LRT
alignments** the envelope markings may run along the trackway between intersections, and in
**mixed-use alignments** they may be continuous.

### Figure 8D-1 — Active Traffic Control Devices for Grade Crossings, Showing Clearances (PDF 1058)
The fully dimensioned composite: **flashing light units 8 or 12 in**, **30 in apart**, **15 in** below
the crossbuck, mounted **8 ft MIN to 9 ft MAX** above the crown; a **cantilever at 17 ft MIN
clearance**; the **gate arm 3.5 ft MIN to 4.5 ft MAX** above the crown with a **minimum of three red
lights**; retroreflective sheeting **4 in wide for the first 32 ft of arm and 2 in beyond**; the
signal foundation **no more than 4 in above ground**; the nearest edge of the device **2 ft** from the
face of the curb.

### Figure 8D-2 — Location Plan for Flashing-Light Signals and Four-Quadrant Gates (PDF 1063)
Three geometries — **obtuse angle, acute angle and right angle** — with entrance and exit gates
distinguished in the legend, and a note that **the gate locations and any medians or islands between
them are determined by the Diagnostic Team**.

# PART 8 — Chapter 8E (pathway and sidewalk grade crossings)

### Figure 8E-1 — Difference between a Pathway and a Sidewalk Grade Crossing (PDF 1076)
A **pathway** crossing lies on its **own alignment, independent of any roadway**, so the roadway's
crossing devices give its users no warning; a **sidewalk** crossing lies **within the highway
right-of-way**, close enough that those devices usually do serve it. Both drawn with **detectable
warnings** either side of the tracks.
- Related Support: the **flangeway gap is typically 2.5 in at LRT crossings and 3 in at railroad
  crossings** — the reason a skewed crossing endangers wheelchair casters and bicycle wheels.

### Figures 8E-2 to 8E-4 — Pathway and Sidewalk Crossing Devices, Signing and Detectable Warnings
(PDF 1077–1079)
**8E-2** defines the dimension **"a"** from the edge of the sidewalk crossing to the centre of the
roadway's warning devices: **if a ≤ 25 ft, the flashing-light signals may be omitted** at the pathway
or sidewalk crossing. Clearances: **8 ft above a pathway, 10 ft where equestrians use it, 7 ft above a
sidewalk**, post-mounted signs at **4 ft**, and a **2 ft lateral offset** where a device sits lower
than 8 ft.
**8E-3** the passive case: crossbuck with number-of-tracks plaque, **YIELD or STOP (passive crossings
only)**, the optional **LOOK sign on a separate post**, **W10-1 at 50 ft MIN**, a **2 ft MIN**
detectable warning, and a yield or stop line.
**8E-4** a **refuge area between two tracks**: detectable warnings at both ends of the refuge, used
where the distance **A between the nearest rails is 30 ft or more**.
- Related Standards/Guidance: detectable warnings **extend the full width** of the pathway or
  sidewalk, are **at least 2 ft deep**, and sit **at least 2 ft upstream of the gate, counterweight,
  flashing-light signals or crossbuck** and **at least 12 ft from the nearest rail** (6 ft at
  pathway-LRT and sidewalk-LRT crossings).

### Figures 8E-5 to 8E-12 — Pathway and Sidewalk Crossing Devices (PDF 1080–1087)
**8E-5 the crossbuck assembly**: required on each approach where the crossing's nearest edge is **more
than 25 ft** from the centre of the roadway's warning device, optional at **25 ft or less**; mounting
**7 ft where the sign is less than 2 ft from the sidewalk edge, 4 ft where 2 ft or more**, 4 ft for
pathways; minimum lateral offset **0 ft for sidewalks, 2 ft for pathways**.
**8E-7 the flashing-light assembly**: **4-inch minimum lights** about **16 in** apart (8 in minimum
spacing), with an **audible device such as a bell**, mounted **7 ft above a sidewalk** or **8 ft above
a pathway**.
- Related Standards: on a **semi-exclusive LRT alignment**, active control is required where operating
  speeds **exceed 25 mph**, and **automatic gates as well where they exceed 40 mph**; the signals may
  be omitted where the crossing is **within 25 ft** of an active roadway crossing device.
**8E-8 the automatic pedestrian gate**: arm **3 ft MIN to 4 ft MAX** above the path, with **at least
one continuously illuminated red light** whenever the system is active (additional lights in pairs,
flashed in unison with the crossing's other lights).
**8E-9 and 8E-10 emergency escape routes**: a **swing gate** lets anyone caught between closed gates
escape away from the tracks, carrying **"PUSH TO EXIT" (I13-2) on the track side** and **DO NOT ENTER
(R5-1) on the side facing away**; fences or pedestrian barriers connect to the existing right-of-way
fence, and **edge lines may designate the escape route**.
**8E-11 a separate automatic pedestrian gate**, on its own mechanism so that manually raising the
pedestrian arm **has no effect on the vehicular gate**.
**8E-12 a horizontal hanging bar** on the gate arm, **no more than 26 in above the path**, to inform
pedestrians with vision disabilities that the gate is down.
- Related Guidance: where tracks are immediately adjacent to other tracks, the devices should be
  designed **to avoid having pedestrians wait between sets of tracks**.

# PART 9 — TRAFFIC CONTROL FOR BICYCLE FACILITIES

### Figure 9B-1 — Regulatory Signs and Plaques for Bicycle Facilities (PDF 1093–1094, 2 sheets)
The bicycle regulatory set, including signs that carry a rule in their legend: **R4-19 "3 FT MIN
CLEARANCE TO PASS"**, **R4-4 "BEGIN RIGHT TURN LANE — YIELD TO BIKES"**, **R4-16 KEEP RIGHT EXCEPT TO
PASS**, **R9-20 ALLOWED USE OF FULL LANE**, **R9-21 USE SHOULDER ONLY**, **R9-22 BICYCLES MUST EXIT**,
the **R9-23 series turn-box signs** ("LEFT TURN MUST USE TURN BOX"), the red **R5-1b WRONG WAY**
bicycle sign with the **R9-3cP RIDE WITH TRAFFIC** plaque, **R3-17 BIKE LANE (white on black)** with
AHEAD and ENDS plaques, **R7-9 / R7-9a No Parking Bike Lane**, **R7-10 BACK-IN PARKING ONLY**, and the
**R3-7bP EXCEPT BICYCLES** plaque.
- Related Standard: a **STOP or YIELD sign shall not be installed in conjunction with a bicycle signal
  face**.

### Figure 9B-2 — Applications of EXCEPT BICYCLES Regulatory Plaques (PDF 1095, Rev. 1)
The plaque applied beneath **DO NOT ENTER**, **No Left/Right Turn** and **lane-control (R3-8)** signs,
so a restriction on drivers does not bind cyclists.
- Related Guidance: priority at a shared-use path/roadway intersection is set by **relative speeds,
  volumes and importance** — **speed alone is not decisive** — and the **least restrictive control
  that is appropriate** goes on the lower-priority approach, with **STOP signs not used where YIELD
  signs would give adequate control**.

### Figure 9B-3 — Bicycle Facilities Adjacent to Back-In Parking (PDF 1098)
Angled **back-in** parking beside a bicycle lane, with **R7-10 BACK-IN PARKING ONLY** signs and
optional **green-coloured pavement** in the bicycle lane.
- Support: back-in angle parking is used beside bicycle lanes because the driver's scanning behaviour
  when entering and leaving the space gives **a more direct view of a cyclist** than head-in parking.

### Figure 9B-4 — Termination of Bicycle Access on Freeways and Expressways (PDF 1101)
**R9-22 BICYCLES MUST EXIT** with an arrow in advance of the exit, the ordinary green exit signing,
and **R5-6 NO BICYCLES** at the point where the freeway proper begins.

### Figure 9B-5 — Two-Stage Bicycle Turn Box where Use is Mandatory (PDF 1102, Rev. 1)
A skewed intersection where cyclists must make a left turn in two stages: **R9-23a "LEFT TURN FROM
BIKE LANE"**, **R9-23b / R9-23c "LEFT TURN MUST USE TURN BOX"**, **R3-2 No Left Turn** for motor
traffic, **R10-11 NO TURN ON RED**, **R3-7R RIGHT LANE MUST TURN RIGHT** and **R4-4 BEGIN RIGHT TURN
LANE — YIELD TO BIKES**, with the green turn box marked in the receiving street.

### Figure 9C-1 — Warning Signs, Plaques and Object Markers for Bicycle Facilities
(PDF 1106–1107, 2 sheets)
The roadway warning set at path scale, plus bicycle-specific signs: **W7-5 steep downgrade with a
bicycle**, **W8-10 slippery-when-wet bicycle symbol with its W8-10P plaque**, **W5-4a PATH NARROWS**,
**W9-5 bicycle LANE ENDS**, **W9-5a bicycle MERGE**, and **W10-12 / W10-9P crossing plaques**.
- Footnote: **fluorescent yellow-green may be used** for the bicycle and pedestrian signs, and a
  plaque's background **should match the sign it supplements**.
- Related Guidance: turn and curve signs **at least 50 ft in advance** of the change of alignment.

### Figures 9D-1 and 9D-2 — Guide Signs and Plaques for Bicycle Facilities; Bicycle Guide Signing
(PDF 1111–1115)
Green bicycle destination, distance, street-name and parking signs, bike route markers and the
**D11-1bP BIKE ROUTE plaque**, with the **M4-14P BEGIN / M4-6P END** plaques.
- Related Standard: **where an arrow is at the extreme left of a line, the bicycle symbol goes to the
  right of the arrow**; Option: **one oversized bicycle symbol may serve as the top line** instead of
  a symbol on each destination line.
- **FIND (a deliberate contrast with motor vehicle signing)**: **travel times should not be used on
  Bike Route Guide signs**, because a cyclist's travel time varies greatly with rider, bicycle and
  facility — where motorway signs carry live travel times in changeable elements.

### Figures 9D-3 and 9D-4 — Bike Route Signing (PDF 1116–1117)
Route assemblies for numbered and named bicycle routes.
- **FIND (a precedence rule)**: where **multiple numbered bicycle route systems** overlap, preference
  runs **United States route, then State, then county or local**, with the **highest-priority legend
  on the top, or to the left**, of the assembly; **non-numbered interstate routes have no standard
  sign**, and States are asked to coordinate a common design.

### Figures 9D-5 and 9D-6 — Mode-Specific and Destination Guide Signing on a Shared-Use Path
(PDF 1123–1124)
A path forking by **mode**, with separate bicycle, pedestrian and skater symbol signs directing each
group, and destination guide signs on the path.
- **FIND (an opening in the typography rules)**: on shared-use path destination guide signs, **a
  lettering style other than the Standard Alphabets may be used** where an engineering study shows its
  **legibility and recognition at minimum letter heights meet or exceed** the Standard Alphabets for
  the same legend height and stroke width.
- Related Standards: destination names in **mixed case**, all other word messages in **upper case**;
  arrow location and destination priority follow 2D.08 and 2D.36.

### Figure 9D-7 — Two-Stage Bicycle Turn Box where Use is Optional (PDF 1126, Rev. 1)
The optional counterpart to Figure 9B-5: **D11-20 "LEFT TURN MAY USE TURN BOX"** and **D11-20a**
guide signs (green) rather than mandatory regulatory signs, with the green turn boxes marked in each
receiving street.
- Starred note: **the R10-11 series NO TURN ON RED signs are required** where a turn box is provided
  (9E.11).

# PART 9 — Chapter 9E (markings)

### Figure 9E-1 — Word, Symbol and Arrow Pavement Markings for Bicycle Lanes (PDF 1127)
**A the bike symbol** with a **72-inch** arrow above it and **72 inches** between elements; **B the
word legend** "BIKE LANE" — letters **44 inches** tall with **64 inches** between the two words and
**72 inches** to the arrow.
- Related Standards/Guidance: **longitudinal markings plus a bicycle lane symbol or word marking
  define a bicycle lane**; the **first marking at the beginning of the lane**, further ones **after
  major intersections** and at **periodic intervals** by engineering judgment; an **arrow may be added
  downstream** of the symbol or word.

### Figures 9E-2 to 9E-4 — Bicycle Lane Markings on Streets and Intersection Approaches
(PDF 1129–1133)
**9E-2 on a two-way street**: **50 to 200 ft of dotted line** where there is a bus stop or heavy
right-turn volume, the dotted pattern being a **2-ft line with a 6-ft gap**; dotted extensions through
the intersection and green pavement shown as optional; **R7-1 / R7-107 no-parking signs** and
**R8-3 / R3-17 BIKE LANE** signs.
**9E-3 approaches to an intersection**: the bicycle lane carried to the left of a right-turn-only
lane, with **R3-7R RIGHT LANE MUST TURN RIGHT** and **R4-4 BEGIN RIGHT TURN LANE — YIELD TO BIKES at
the upstream end of the right-turn lane**.
**9E-4 a transition from a shared lane**: the **shared lane marking (sharrow)** upstream giving way to
a bicycle lane, with **optional green dotted markings** through the weaving area.

### Figure 9E-5 — Pavement Markings for Mixing Zones (PDF 1135)
**A a mixing zone without a yielding area**, **B with a yielding area**, **C re-establishment of the
bicycle lane after crossing paths with right-turning vehicles**, each using **R3-7R with the EXCEPT
BICYCLES plaque** and **R4-4**.
- Related Standards: **shared-lane or chevron markings shall not be used in bicycle lanes or their
  extensions**; **extensions through intersections shall use dotted line patterns**; and where the
  extension is **contiguous to a crosswalk**, **two longitudinal dotted lines** establish its lateral
  limits — **the crosswalk's transverse line shall not be used to demarcate one side** of the
  extension.

### Figure 9E-6 — Markings for Buffer-Separated Bicycle Lanes (PDF 1137)
Four cases with the buffer rules dimensioned:
- **buffer greater than 3 ft wide → chevron or diagonal markings shall be applied**;
- **buffer 2 to 3 ft wide → chevron or diagonal markings should be applied**;
- **buffer less than 2 ft wide → no chevron or diagonal markings may be applied**;
- the **buffer should be at least three times the width of the longitudinal lines defining it**, and
  **chevron or diagonal spacing should be 10 ft or greater**.
Green pavement and dotted extensions are shown at intersections and driveways, and **D** shows a
**contiguous buffer on both sides** of the lane.

### Figures 9E-7 and 9E-8 — Markings for Separated Bicycle Lanes (PDF 1140–1142, Rev. 1)
One-way lanes on a two-way street, a one-way lane behind on-street parking, a two-way lane on a
one-way street, and lanes shifted toward or away from traffic at intersections.
- **FIND (a different buffer threshold)**: for **separated** bicycle lanes, **diagonal or chevron
  markings shall be used if the buffer is 2 ft or greater** — where a **buffer-separated** lane uses
  **3 ft** (Figure 9E-6). Note: **on-street parking can itself provide the vertical element** of the
  separation; **tubular markers** appear in the legend.

### Figure 9E-9 — Shared-Lane Marking Applications (PDF 1143)
**A with parking on one side**, **B on an approach to an intersection**, **C with optional black
background markings**.
- Dimensions: with on-street parking the marking's **centre at least 12 ft from the face of the
  kerb**; **without parking, where the outside lane is less than 14 ft wide, at least 4 ft**; spacing
  **not less than 50 ft or greater than 250 ft**; the **first marking beyond an intersection no more
  than 50 ft** past it; where the **R9-20 Allowed Use of Full Lane** sign is added, the marking goes
  in the **approximate centre of the travel lane**.

### Figures 9E-10 to 9E-13 — Turn Boxes, Bicycle Boxes and Shared-Use Path Markings
(PDF 1145–1148, 1150)
Two-stage turn boxes, **intersection bicycle boxes** with an **advance stop line 10 ft MIN** ahead of
the intersection stop line, and shared-use path markings.
- Related Standards/Guidance: if used, **green-coloured pavement shall fill the full limits of the
  bicycle box**; the **EXCEPT BICYCLES plaque** under STOP HERE ON RED exempts cyclists from the
  advance stop line; on shared-use paths a **solid yellow centre line where passing is not
  permitted**, **broken yellow where it is** (**3-ft segments with 9-ft gaps**), a **solid white line
  to separate different user types travelling the same way**, **half-size arrows** and smaller word
  markings; and **crosswalk markings shall be used where a shared-use path crosses a roadway**.

### Figures 9E-14 and 9E-15 — Detection and Route Markers for Shared-Use Paths (PDF 1150–1151, Rev. 1)
Bicycle detector symbol markings, and route marker assemblies on a path (M1-8 / M1-9 bicycle route
markers with cardinal direction and arrow plaques) shown at a path fork.
- Related Standard on the same page: **channelizing devices used with bicycle facilities shall not
  incorporate the colour green** into the device or its retroreflective element to supplement green
  pavement; Guidance adds they **should be tubular markers**, placed **in the buffer and at least 1 ft
  from the longitudinal bicycle lane marking**, and warns that **inflexible raised devices immediately
  adjacent to the travel path without a buffer create a collision potential for bicyclists**.

### Figures 9E-16 and 9E-17 — Obstruction Pavement Markings on Bicycle Facilities (PDF 1152–1153)
**A an obstruction within the path**: a **diamond of normal-width solid yellow line** around it,
**2L long** with **1 ft** of offset either side. **B an obstruction at the edge**: a **wide solid
white line** tapering past it.
- **FIND (the taper formula in bicycle terms)**: **L = W·S, where W is the offset in feet and S is the
  BICYCLE approach speed in mph** — the same formula as the roadway obstruction markings (Figure
  3B-15) but with the cyclist's speed. Footnote: **add a foot of offset for a raised obstruction and
  use L = (W+1)·S**.

---

## GAP FOUND AND CLOSED — 22 FIGURES MISSED BY THE PAGE LIST

**All 511 figure pages read as rendered images — approximately 485 distinct figures across Parts 1
to 9, including all 54 Typical Applications (Chapter 6P), which the first pass had covered only
through their notes.**

The pass produced: confirmations of all four engineer rulings; a data correction (the Forest Route
sign is M1-7, not M1-1); dozens of computable rules that exist only in figure legends, notes or
dimensions; and one item still open — the small filled dot or circle marked "optional for left-most
lane", which appears on the R3-8 lane-control signs (Figure 2B-4), among the roundabout arrow options
(Figure 2B-5), in the two-lane roundabout sign alternatives (Figure 2B-23) and as a **pavement
marking** on the curved-stem arrows (Figure 3B-21). Its shape and placement are now fully
characterised — an optional mark at the **tail** of the left-most lane's arrow, available in both
arrow styles and in both sign and marking form — but **the Manual never states what it represents**.
It remains unrecorded pending the Standard Highway Signs plate or a text passage that names it.


---

## ADDENDUM — the 22 figures the page list missed (read 23 Sep)

The graph merge exposed a gap: `figpages.json` (511 pages) omitted 21 figure pages, so the earlier
claim of complete coverage was wrong. They are now read.

### Figures 1B-1 and 1B-2 — Experimentation and Rulemaking Processes (PDF 48, 51)
Two flowcharts. **1B-1**: request → FHWA review → approved? (no → respond to questions, loop) →
install → evaluate + **semi-annual reports to FHWA** → final report. **1B-2**: change request →
FHWA review → accepted for rulemaking? → Notice of Proposed Amendments → docket comment → Final
Rule; the parallel **Interim Approval** branch lets jurisdictions deploy before rulemaking, and
**State manuals must be in substantial conformance within 2 years (23 CFR 655.603(a))**.

### Figure 2D-3 — Arrows for Use on Guide Signs (PDF 255)
A **typed arrow vocabulary**: **Type A**, **Type A-Extended** (extra emphasis), **Type B**,
**Type C** (sharp-turn exit, placed to the side of the legend), **Type D** (primarily non-guide
signs; post-mounted low-speed and two-name street-name signs), **Type E** (**circular
intersections** — the driver path around the central island), plus the **down arrow**.

### Figure 2E-43 — Partial-Width Overhead Arrow-per-Lane Guide Sign (PDF 397)
- **Standard**: **the through route and/or destination shall not be displayed** on a partial-width
  Arrow-per-Lane sign — it shows only the option lane and the exit-only lane(s).
- Related Standards: Diagrammatic Advance guide signs **shall not** be used at cloverleafs to depict
  separate downstream departures from a C-D roadway, and **shall not** depict a downstream split of
  an exit ramp when located on the main roadway.

### Figure 2G-5 — Overhead Advance Guide Sign for a Preferential Lane Entrance (PDF 461)
The E8-3 sign (black diamond panel, green field, "HOV LANE ENTRANCE 1 MILE").
- **Standard (2G.10 ¶9)**: the **diamond symbol shall appear on each Advance Guide (E8-3), Entrance
  Direction (E8-2/E8-2a) and Entrance Gore (E8-1/E8-1a) sign**, and **shall not be used for
  preferential lanes of other types such as bus or taxi lanes**.
- **CHECK (Ruling 4)**: ¶10 — signing for an HOV lane **managed by varying the occupancy requirement**
  must also comply with these provisions.
- Guidance: guide sign priority order is **Advance Guide → Entrance Direction → Exit Destination
  Supplemental**.

### Figures 2I-2 and 2J-7 — Next Services Plaque; Specific Service Trailblazer Signs (PDF 520, 544)
**2I-2** the D9-17P "NEXT SERVICES XX MILES" plaque, used where the next services are **10 miles or
more** away. **2J-7** blue trailblazer signs with **one to four business panels**, which **shall be
duplicates of those on the ramp signs**, placed **no more than 500 ft in advance of a required turn**.
- **FIND (a precedence rule)**: where there is not enough space for all proposed signs, **guide,
  warning and regulatory signs take priority**, and the tourist-oriented or specific service signs
  **shall not be used**.

### Figures 3B-3 and 3B-6 — Three-Lane Two-Way Centre Lines; Reversible Lane Markings (PDF 583, 587)
**3B-3**: **A passing permitted in the single-lane direction** (broken + solid) and **B prohibited**
(double solid). **3B-6**: reversible lanes bounded by **double-dashed yellow lines on both sides**.
- **FIND (computable warrants for centre lines)**: **shall** be placed on paved undivided two-way
  **urban arterials/collectors with a travelled way ≥ 20 ft and ADT ≥ 6,000**, and on **all undivided
  two-way roads with three or more lanes**; **should** be placed on **rural arterials/collectors with
  ≥ 18 ft and ADT ≥ 3,000**; **may** be placed on other two-way roads **≥ 16 ft** wide.
- Related Standard: a **single-direction lane-use arrow shall not be used in a lane bordered on both
  sides by two-way left-turn markings**.

### Figure 3C-2 — Crosswalk Markings for an Exclusive Pedestrian Phase (PDF 634)
Diagonal crosswalks across the intersection plus perimeter crosswalks.
- Guidance: the **diagonal segments should not use high-visibility markings**, though the perimeter
  crosswalks may.
- **CHECK (Ruling 5)**: the same page carries the bar-pair Standards — individual bar **8 to 12 in**
  wide, lateral spacing within a pair **equal to one bar's width**, and spacing between pairs **not
  less than 24 in and not greater than 60 in, or 2.5 times the total width of a bar pair** —
  confirming that both limits apply and the lesser governs.
- Related Standard: **longitudinal bar pair crosswalks shall not be installed with accompanying
  transverse lines**; and **crosswalk markings shall not be provided to or from the central island of
  a roundabout**.

### Figure 4D-3 — Maximum Mounting Height of Signal Faces 40 to 53 ft from the Stop Line (PDF 715)
A **straight-line graph**: the maximum height to the top of the signal housing rises linearly from
**21 ft at 40 ft** to **25.6 ft at 53 ft** from the stop line (≈ 21 + 0.354·(d − 40)).
- Related Guidance: a vertically-arranged face not over the roadway, **bottom ≤ 19 ft** above the
  sidewalk or pavement; horizontally-arranged, **≤ 22 ft**; side-mounted faces lower than 15 ft need
  **≥ 2 ft lateral offset** from the kerb face.

### Figure 4E-1 — Typical Arrangements of U-Turn Signal Faces (PDF 717)
Vertical and horizontal three-section faces with **U-turn arrows** in red, yellow and green.
- Related Standards: arrows point **vertically upward for through**, **horizontally for a turn at or
  beyond a right angle**, **upward at a slope matching a shallower turn**, and **in a manner that
  directs the driver through the turn for a U-turn arrow**; a **bimodal section alternating a green
  and a yellow arrow in the same direction** is permitted provided both colours are never shown
  together; **letters and numbers shall not be displayed as part of a vehicular signal indication**,
  and **strobes shall not be used within or adjacent to any signal indication**.

### Figure 4H-1 — Typical Arrangements of Bicycle Signal Faces (PDF 756)
Vertical and horizontal faces of **all-bicycle-symbol indications**.
- **Standard**: a bicycle signal face **shall consist of all bicycle symbol indications — circular or
  arrow indications shall not be used** in it; a **Bicycle Signal sign shall be installed immediately
  adjacent** to every bicycle signal face (**24 × 36 in** overhead, **12 × 21 in** post-mounted);
  bicycle faces **operate in the same mode as the other faces** at the location and **shall not be
  placed in dark mode** while other vehicular faces are operating.

### Figures 4J-1, 4J-2 and 4J-3 — Pedestrian Hybrid Beacons (PDF 768–770; 4J-3 Rev. 1)
**4J-1 (speeds ≤ 35 mph)** and **4J-2 (> 35 mph)** are guideline curve families plotted by
**crosswalk length L = 34, 50, 72 and 100 ft**, both with a **floor of 20 pedestrians per hour**.
- **FIND**: the speed split for hybrid beacons is **35 mph**, matching Warrant 4 rather than the
  40 mph of Warrants 2 and 3; values for other crosswalk lengths are **interpolated between the
  curves**; the criteria **may be reduced by up to 50 %** where the **15th-percentile crossing speed
  is less than 3.5 ft/s**; and on a divided street with a wide enough median the criteria **may be
  applied separately to each direction**.
**4J-3 the sequence**, six intervals: **1 dark until activated → 2 flashing yellow → 3 steady yellow
→ 4 steady red during the pedestrian walk interval → 5 alternating flashing red during the pedestrian
change interval → 6 dark again**. Note: an **optional steady red clearance interval may follow
interval 3**, and an **optional short buffer interval (alternating flashing red while the pedestrian
signals show a steady UPRAISED HAND) may follow interval 5**.
- Related Standard: **bicycle signal faces shall not be used at a pedestrian hybrid beacon**.

### Figure 4N-1 — Sequence for an Emergency-Vehicle Hybrid Beacon (PDF 783)
**Five** intervals: **1 dark → 2 flashing yellow → 3 steady yellow → 4 alternating flashing red during
egress of the emergency vehicle(s) → 5 dark again**.
- **FIND (the contrast with 4J-3)**: the emergency-vehicle beacon has **no steady red interval** — it
  goes from steady yellow straight to alternating flashing red, because there is no pedestrian walk
  interval to protect. An optional steady red clearance may be inserted **after interval 3 and before
  interval 4**.
- Related Standards: actuated **only by authorized emergency or maintenance personnel**; **not within
  100 ft** of an intersection or driveway controlled by a STOP or YIELD sign; **at least two faces per
  approach** of the major street; **EMERGENCY SIGNAL—STOP ON FLASHING RED signs and stop lines
  required** on each major-street approach.

### Figure 4T-1 — Lane-Use Control Signal Indications (PDF 796)
Five indications on **rectangular faces with opaque backgrounds**: **downward green arrow**,
**yellow X**, **red X**, **white two-way left-turn arrows**, **white one-way left-turn arrow**.
- Dimensions and order: **18 in minimum** for the arrow and X faces, **30 in** for the white
  left-turn arrow faces; left-to-right order **RED X, YELLOW X, DOWNWARD GREEN ARROW, WHITE TWO-WAY
  LEFT-TURN ARROW, WHITE ONE-WAY LEFT-TURN ARROW**; visible for **2,300 ft**; housing bottom
  **15 ft minimum to 19 ft maximum** above the pavement; every lane that can be reversed or closed
  needs at least a **downward green arrow and a red X**.

### Figure 7C-1 — Two-Lane Pavement Marking of "SCHOOL" (PDF 1025, Rev. 1)
The word spanning two approach lanes, **letters 10 ft high and the whole marking 19.3 ft wide**.

### Figure 8D-3 — Light Rail Transit Signal Indications (PDF 1075)
A **separate signal vocabulary**: **horizontal bar = stop**, **vertical bar = go (straight)**,
**diagonal bars = go (left) and go (right)**, all **white on black**.
- Notes/Standards: **all rectangular bar indications shall be white**; **go indications may be flashed**
  to tell LRT operators to prepare to stop; where standard R-Y-G indications control LRT movements they
  **shall be positioned so they are not visible to motorists, pedestrians and bicyclists**; LRT faces
  **at least 3 ft from the nearest highway signal face** for the same approach.

### Figure 9A-1 — Sign Placement on Shared-Use Paths (PDF 1089)
**Overhead signs 8 ft MIN clearance**; **post-mounted signs 4 ft MIN height**; **2 ft MIN lateral
offset** on both sides.
- Related Standards: signs applying to both motorists and bicyclists take the **conventional road
  sizes**; bicycle-only sizes come from **Table 9A-1**; a diamond warning sign applying only to
  bicyclists or pedestrians on a path or separated lane **may be 18 × 18 in**.

### Figure 9B-6 — Application of a Bicycle Jughandle Sign (PDF 1103)
A jughandle letting cyclists use the crossroad's traffic control to make a left, right or U-turn,
with **R9-25 "U AND LEFT TURNS"** and bicycle destination signs; **green pavement optional**.

---

## FIGURE PASS COMPLETE (corrected)

**485 of 485 figures read** — 463 in the main pass and **22 more found missing when the graph merge
cross-checked the figure inventory against the log**. The gap existed because the page list built at
the start of the pass omitted 21 pages; it was caught only because the merge compared captions
extracted from the PDF against the figures actually logged.


---

## ADDENDUM 2 — the eight tables that had no figure-pass reading (read 23 Sep)

### Table 1D-1 — Acceptable Abbreviations (PDF 76)
General abbreviations plus days of the week, in two columns of word-message → standard abbreviation.
- **FIND (validity depends on context, not just spelling)**: three footnote classes govern *where*
  each abbreviation may be used — **\*** = "shall not be used for any application other than the name
  of a roadway" (Ave, Blvd, Ct, Dr, Expwy, Fwy, Hwy, Pkwy, Pl, Rd, St, Ter, Thwy, Tpk, Tr);
  **\*\*** = "shall not be used for any application other than as a descriptor or title within a
  proper name" (Ctr, Mt, Mtn, Natl, St for Saint); **\*\*\*** = **TUES and THURS may be shortened to
  TUE and THU on a CMS** only when the character count would otherwise force rewording.
- Note: abbreviations shown in mixed case **may be all upper case**, and **must** be where a
  low-resolution changeable sign cannot display lower case.
- Several entries are cross-references rather than abbreviations (Bridge, Interstate, Lane, US
  Numbered Route → "see Table 1D-2").

### Table 1D-2 — Abbreviations Only for Temporary Messages on Portable CMS (PDF 77–78, 2 sheets)
- **FIND (a prompt-word grammar)**: each abbreviation carries two extra columns — **prompt word
  preceding** and **prompt word following** — and is valid only in that construction. Examples:
  **AHD** needs a preceding word ("FOG AHD"); **EAST** needs a preceding route number or road name
  ("I-4 EAST"); **ACCS** needs a following word ("ACCS ROAD"); **CHEM** needs a following word
  ("CHEM SPILL"). A dash in both columns means the abbreviation stands alone (CANT, DONT, ITS, NORM,
  PKING, SLIP, TRAF, TRVLRS, CYCLES, VEH, WARN, WONT).
- Some words have **two abbreviations with different grammars** — EAST/E-BND, NORTH/N-BND,
  SOUTH/S-BND, WEST/W-BND, and LFT/RT each appear twice with different prompt words.
- Footnotes: **\*** with its prompt word the abbreviation **may be used on traffic control devices
  other than portable message signs** (see Table 1D-1); **\*\*** a **space and no hyphen** goes
  between the abbreviation and the route number ("NY 7", "US 202").

### Table 1D-3 — Unacceptable Abbreviations (PDF 78)
- **FIND (a blacklist that states its reason)**: each row gives the **intended word** and the
  **common misinterpretation** that disqualifies it — ACC (Accident → Access Road), CLRS (Clears →
  Colors), DLY (Delay → Daily), FDR (Feeder → Federal), L (Left → Lane/Merge), LT (Light → Left),
  PARK (Parking → Park), POLL (Pollution → Poll), RED (Reduce → Red), STAD (Stadium → Standard),
  WRNG (Warning → Wrong).

### Table 2L-2 — Example of Units of Information (PDF 556)
Four questions, one information unit each — **what happened** (MAJOR CRASH), **where** (AT EXIT 12),
**who the advisory is for** (drivers heading TO NEW YORK), **what is advised** (USE ROUTE 46) —
combined into a **two-phase message**.
- Related Standard (2L.05 ¶4): a message is **no more than two phases**, a phase **no more than three
  lines**, **each phase must be understandable by itself**, the **meaning must be the same regardless
  of the order the phases are read**, and each line is **centred**. Where more than one CMS is visible
  to road users, **only one may display a sequential message at a time** — except at toll plazas and
  similar booth-lane arrangements.

### Tables 2L-3 and 2L-4 — Message Construction for CMS and for Portable CMS (PDF 558–559;
2L-4 Rev. 1)
Nine and eight worked examples respectively, each giving a **potential message, an improved message,
and the reason**. The recurring rules: each phase conveys a complete thought; a general CAUTION is
not specific enough to act on; a message is **not repeated to fill the sign**; a second phase that is
not a complete message should be dropped; **changing only one line between phases compromises
recognition**; **slogan-type safety messages do not convey the legal requirement** and should be
replaced by the requirement plus the penalty.
- **FIND (the same word, opposite advice, resolved by sign width)**: **2L-3 example 2** says
  condensing ROAD WORK into "ROADWORK" is **unnecessary** because the sign will accommodate the
  two-word phrase; **2L-4 example 6** says condensing it **is** the right choice because it makes a
  single-phase message fit. The footnote supplies the reason — a **portable CMS is generally limited
  to 8 characters per line**.
- Same conditional applies to abbreviations: the less common Table 1D-2 abbreviations are **not
  warranted when the sign can accommodate the full message**, and should be **limited to portable CMS
  where characters per line are limited**.
- Note to 2L-3: the examples assume a **single-colour CMS with pixel spacing greater than 20 mm, all
  upper case**; a **multi-colour full-matrix CMS at 20 mm or less should use mixed case and proper
  legend and background colours** — the same 20 mm threshold as Figure 2L-1.

### Table 5A-1 — Automation Levels (PDF 801)
Levels 0 to 5, each with a description, an **automation category** and an **automation type**:
**Level 0** — human performs the whole dynamic driving task; category **None\***; type **None**.
**Levels 1–2** — sustained driver assistance for steering and/or acceleration, human performs the
rest; category **ADAS**. **Levels 3–4** — an ADS performs the whole task, Level 3 expecting the human
to respond to a request to intervene, Level 4 not; category **ADS**. **Level 5** — full-time ADS
performance under all conditions a human could manage; category **ADS**. Levels 1–5 share the type
**Driving Automation System**.
- Footnote: **Level 0 may include some ADAS features**, but at that level they count as **warning or
  momentary intervention systems** only.

### Tables 6B-2, 6B-3 and 6B-4 — Work Zone Sight Distance and Taper Lengths (PDF 816)
All three sit on one page. **6B-2** stopping sight distance by speed: **20 mph → 115 ft**, rising to
**75 mph → 820 ft**. **6B-3** taper length criteria: **merging ≥ L**, **shifting ≥ 0.5 L**,
**shoulder ≥ 0.33 L**, **one-lane two-way 50 ft min / 100 ft max**, **downstream 50 ft min / 100 ft
max**. **6B-4** the formulas: **speed 40 mph or less → L = W·S²/60**; **speed 45 mph or more →
L = W·S**, where L is taper length in feet, W the offset in feet, and S the speed in mph.
- **CHECK (confirms Ruling 2)**: Table 6B-4 has **no row covering 41–44 mph** — the two rows are
  "40 mph or less" and "45 mph or more". Ruling 2 fills exactly that gap by using the **"40 mph or
  less" row for anything below 45 mph**, with the formula still taking the **actual S**.
- **CHECK (confirms Figure 6B-2)**: the taper fractions read off the artwork — L, ½L, ⅓L and the
  50–100 ft tapers — match this table exactly.
- **FIND (an unranked speed definition, unlike Part 3)**: 6B-2 and 6B-4 define **S** as "**posted
  speed limit, or off-peak 85th-percentile speed prior to work starting, or the anticipated operating
  speed**" — three alternatives with **no ranking**, where Figure 3B-15 says "the 85th-percentile
  speed **or** the speed limit, **whichever is higher**". **Ruling 1 resolves it**: take the maximum
  of the speeds the provision names.

---

## TABLE COVERAGE COMPLETE — 68 of 68
