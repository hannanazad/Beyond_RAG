"""Rulings on unnamed-exception candidates, made by READING each rule against the
candidate paragraph and against the paragraphs the rule's own list names.

Each ruling is keyed by section + the opening words of the rule sentence + the
opening words of the candidate sentence, so it survives renumbering.

  YES      the candidate relaxes this rule; it becomes an EXCEPTS edge
  NO       it does not; the flag is removed, and `why` says why
  ENGINEER the letter and the evident intent disagree; kept as a flag, with
           the question the engineer must answer
Also: candidates found WHILE reading, pinned to the rule they actually relax.
"""
RULINGS = [
 # ---------------- YES ------------------------------------------------------
 ("2A.13", "Except as provided in Paragraph 8", "Under some circumstances, such as on curves", "YES",
  "Lets the primary sign go on the left on curves to the right, where ¶5 says right-hand side. "
  "First sentence of ¶14 only."),
 ("2A.13", "Except as provided in Paragraph 8", "A supplementary sign located on the left", "NO",
  "A supplementary sign on the left is already allowed by ¶5's own second sentence."),
 ("2B.26", "Movement Prohibition signs (see Figure 2B-4) shall", "Movement Prohibition signs may be omitted at a ramp", "YES",
  "Directly removes the ¶1 requirement at ramp entrances. The 2009 edition listed it; "
  "renumbering left it out."),
 ("2C.06", "If the use of a device or devices is indicated", "Devices for changes in horizontal alignment may be omitted when", "YES",
  "Removes the device requirement at 20 mph or less. Runs in parallel with Chart A (engineer's ruling)."),
 ("2F.12", "Except where the State Toll Route sign (see Paragraph 8 of this Section) is used, the TOLL", "A State Toll Route sign (see Paragraph 8", "YES",
  "Already named in words: the list says 'except where the State Toll Route sign is used' and "
  "points at ¶8 (its design). ¶7 is the paragraph that permits using it."),
 ("2F.12", "Except where the State Toll Route sign (see Paragraph 8 of this Section) is used and", "A State Toll Route sign (see Paragraph 8", "YES",
  "Same as ¶4: the exception is named by the sign; ¶7 is what permits it."),
 # ---------------- ENGINEER -------------------------------------------------
 ("2D.29", "Except as provided in Paragraph 9", "If engineering judgment indicates that groups", "YES_DELEGATED",
  "ENGINEER'S RULING: an exception, but one that rests on engineering judgment, so the manual cannot "
  "verify it. The answer states: assemblies are required on all approaches, except that under ¶8 the "
  "agency may omit or combine route signs where overlapping routes or multiple turns would confuse, "
  "provided clear directions are given. Reason field: AGENCY_CHOICE."),
 ("4F.17", "Except as provided in Paragraph 10", "When an actuated signal sequence includes", "YES",
  "ENGINEER'S RULING: ¶11 is a legitimate, intended operation. In an actuated sequence with lagging "
  "left turns, the red clearance is shown when the lagging left phase is skipped and omitted when it "
  "is shown. Recorded as an exception to ¶9 so the Standard does not forbid it; ¶9's list names only ¶10."),
 ("8B.08", "Where tracks are out of service", "The TRACKS OUT OF SERVICE (R8-9) sign", "NO",
  "ENGINEER'S RULING: no gap. ¶2's list names ¶3, and ¶3 says 'even if a TRACKS OUT OF SERVICE sign "
  "has been installed', so the manual already connects the optional R8-9 (¶1) to the rule through ¶3."),
 # ---------------- NO -------------------------------------------------------
 ("2B.26", "Except as provided in Item C", "The diamond symbol may be used", "NO",
  "About an HOV word message, not the NO TURNS two-sign rule. Also misfiled: stored as ¶1."),
 ("2B.26", "Except as provided in Item C", "Where ONE WAY signs are used", "NO",
  "Omits No Left/No Right Turn signs; ¶6 governs the NO TURNS sign. Different signs. "
  "¶13 is correctly an exception to ¶1."),
 ("2B.26", "Except as provided in Item C", "Movement Prohibition signs may be omitted at a ramp", "NO",
  "¶6 applies only IF a NO TURNS sign is used. Omitting the sign means the rule never applies; "
  "nothing to except."),
 ("2B.53", "If the metered parking", "A Tow-Away Zone", "NO", "About the tow-away plaque, not the time-limit display."),
 ("2B.53", "If the metered parking", "The word legend TOW-AWAY ZONE", "NO", "About the tow-away plaque, not the time-limit display."),
 ("2E.28", "Except as provided in Paragraph 14", "Where an existing sign structure", "NO",
  "About where the arrow sits on the EXIT ONLY panel, not overhead mounting. It varies the panel's "
  "layout so the arrow can sit over the lane centre, which 2E.18 ¶5 requires: it serves that rule, it does not relax it."),
 ("2E.28", "Except as provided in Paragraph 14", "Where the width of the Exit Direction sign", "NO",
  "About where the arrow sits on the EXIT ONLY panel, not overhead mounting. It varies the panel's "
  "layout so the arrow can sit over the lane centre, which 2E.18 ¶5 requires: it serves that rule, it does not relax it."),
 ("2E.28", "Except as provided in Paragraph 9", "Where an existing sign structure", "NO", "Arrow position, not the distance message."),
 ("2E.28", "Except as provided in Paragraph 9", "Where the width of the Exit Direction sign", "NO", "Arrow position, not the distance message."),
 ("2G.05", "For preferential lane restrictions", "On conventional roads where preferential", "NO",
  "Post-mounted vs overhead, not the period-of-operation legend."),
 ("2G.05", "On conventional roads where preferential", "In lieu of removing the period", "NO",
  "Legend content, not post-mounted vs overhead."),
 ("2G.07", "Except as provided in Paragraph 7", "An overhead Preferential Lane Ends (R3-15c)", "NO",
  "¶2 covers where traffic must MERGE (R3-12a/g). ¶8 covers where the lane CONTINUES as general "
  "purpose (R3-12c). ¶2 never required R3-12c."),
 ("2H.14", "Except as provided in Paragraph 7", "Exit numbering may be used", "NO",
  "A figure note about arrows, not the one-sign limit. Also misfiled: stored as ¶1."),
 ("2N.09", "Except as provided in Paragraph 4", "The distance to the shelter", "NO", "Content of the legend, not its colour."),
 ("3B.12", "An edge line", "On low-speed urban roadways", "NO",
  "¶13 omits DELINEATORS; this rule is about the EDGE LINE. The manual's lists pair them correctly."),
 ("3B.12", "Except as provided in Paragraph 6", "On low-speed urban roadways", "NO",
  "¶13 omits DELINEATORS; this rule is about the EDGE LINE."),
 ("3B.12", "Delineators installed", "On roadways with operating speeds less than 25", "NO",
  "¶6 omits the EDGE LINE; this rule is about DELINEATORS."),
 ("4F.01", "Shall be displayed on a signal face that controls a left-turn", "If not otherwise prohibited, steady red", "NO",
  "Item H.2. ¶6 permits arrows instead of circular indications, the same direction as H.2, not a relaxation of it."),
 ("4F.01", "Shall be displayed only to allow vehicular movements", "If not otherwise prohibited, steady red", "NO",
  "Item H.1 (green arrow only for non-conflicting moves). ¶6 changes which indications are used, not when a move may conflict."),
 ("4F.01", "Shall not be displayed when any conflicting vehicular", "If not otherwise prohibited, steady red", "NO",
  "Item F.4 (no yellow arrow during a conflict). ¶6 does not permit a yellow arrow during a conflict."),
 ("6C.05", "Except as provided in Paragraph 6", "Emergency and incident responders", "NO",
  "¶5 requires apparel 'as described in this Section'; ¶4 is part of that description."),
 ("7B.03", "Except as provided in Paragraph 3", "The STATE LAW legend", "NO", "Legend on in-street signs; unrelated to the advance assembly."),
 ("7B.03", "Except as provided in Paragraph 3", "A 12-inch reduced size", "NO", "In-street sign size; unrelated to the advance assembly."),
 ("7B.03", "The School Crossing assembly shall not", "The School Advance Crossing assembly may be omitted", "NO",
  "A different assembly (advance, not crossing), and omitting it goes the same way as the prohibition."),
 ("7B.03", "The School Crossing assembly shall not", "The STATE LAW legend", "NO", "Legend on in-street signs; not the School Crossing assembly."),
 ("7B.03", "The School Crossing assembly shall not", "A 12-inch reduced size", "NO", "In-street sign size; not the School Crossing assembly."),
 ("8B.04", "A Crossbuck Assembly shall consist", "The vertical strip of retroreflective", "NO",
  "¶18 is already the named exception to ¶17 (the strip rule), not to ¶1."),
 ("8E.09", "Except as provided in Paragraph 11", "The red light on an automatic pedestrian gate", "NO",
  "About the red light, not the gate mechanism. It is already the named exception to ¶4, which lists it."),
 ("9D.01", "Except as provided in Paragraph 14", "Destination (D1-1 and D1-1a) signs", "NO",
  "A substitution: when a motorist sign is used instead, it is not a Bicycle Destination sign and "
  "¶13 does not reach it."),
 ("9D.01", "Except as provided in Paragraph 14", "Distance (D2-1 through D2-3) signs", "NO",
  "A substitution, as with ¶6."),
 ("9D.06", "Except as provided in Paragraph 2", "Where a bicycle route is named", "NO", "Permission to use the sign at all, not its design."),
 ("9D.06", "Except as provided in Paragraph 2", "A green background or white border", "NO",
  "Outside the rule's scope: ¶1 governs signs 'used on roadways'; ¶6 is about shared-use paths."),
 # ---- found once the introducing sentences were restored (4F.01)
 ("4F.01", "Shall not be displayed when any conflicting vehicular", "A steady straight-through GREEN ARROW", "NO",
  "Item F.4 governs when a YELLOW arrow may show; ¶5 is about a straight-through GREEN arrow."),
 ("4F.01", "Shall be displayed on a signal face that controls a left-turn", "A steady straight-through GREEN ARROW", "NO",
  "Item H.1 names ¶5 explicitly; H.2 (left-turn faces) deliberately does not."),
 ("4F.01", "Except as provided in Paragraph 13 of this Section, the above combinations", "If not otherwise prohibited", "NO",
  "¶6 opens 'If not otherwise prohibited': by its own words it yields to this prohibition."),
 ("4F.01", "Except as provided in Paragraph 13 of this Section, the above combinations", "A steady straight-through GREEN ARROW", "NO",
  "¶5 swaps one indication for another; it does not permit forbidden combinations. Its pre-signal case "
  "(item D) is covered by ¶13, which this rule already names."),
 ("4F.01", "Except as provided in Paragraph 13 of this Section, the following combinations", "If not otherwise prohibited", "NO",
  "¶6 opens 'If not otherwise prohibited': by its own words it yields to this prohibition."),
 ("4F.01", "Except as provided in Paragraph 13 of this Section, the following combinations", "A steady straight-through GREEN ARROW", "NO",
  "As for ¶11: the pre-signal combinations are ¶13's, which is named."),
]

# Checked by reading and withdrawn: 8E.09 ¶6 is already named by ¶4; 2E.28 ¶5 serves
# 2E.18 ¶5 rather than relaxing it. Nothing is added here that has not been read.
FOUND_WHILE_READING = []
