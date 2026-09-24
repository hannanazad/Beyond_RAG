"""Connecting tagged sentences into a graph.

semantics.py reads one sentence at a time. This module connects them:

  REFERS_TO        a sentence -> the section, table, figure, sign or
                   paragraph it names
  EXCEPTS          a rule -> a paragraph its own exception list names
  EXCEPTS_CANDIDATE a rule -> a paragraph in the same section that relaxes it
                   by what it DOES but is not in the list. Never attached
                   silently: it is a flag for the engineer. The list is a lower
                   bound (see MUTCD_structural_vocabulary.md, piece 12).
  DEFINES          a sentence -> the quantity it defines
  USES             a quantity in a sentence -> the sentence that defines it
  NOTE_OF          a table -> its notes, marked READ FIRST
  AXIS             a table -> the quantity each axis measures

and it gives every quantity a CANONICAL meaning, so that "20 mph" means one
thing and one thing only. Speeds are where this matters most, and where the
manual is most careful to distinguish -- so the distinctions below are the
manual's own, not invented ones.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .semantics import tag_sentence, sentences

# =========================================================================== #
# 1. Canonical quantities
# =========================================================================== #
# Every speed the manual names, kept apart. "Speed limit" with no qualifier is
# the legal limit, which may be posted OR statutory; the manual uses the words
# "posted" and "statutory" when it means one of them specifically.
# Each speed is anchored to the sentence that DEFINES it, and to its parent.
# source: where the definition lives -- 1C.02 (glossary), a local section, or
# an FHWA interpretation. Never mixed.
SPEEDS = {
    "SPEED_LIMIT":           dict(defined="1C.02 #250", parent=None,
                                  note="maximum OR MINIMUM, by law or regulation"),
    "SPEED_LIMIT_POSTED":    dict(defined="1C.02 #175", parent="SPEED_LIMIT",
                                  note="displayed on Speed Limit signs"),
    "SPEED_LIMIT_STATUTORY": dict(defined="1C.02 #254", parent="SPEED_LIMIT",
                                  note="by legislative action; not necessarily displayed"),
    "SPEED_ADVISORY":        dict(defined="1C.02 #8",   parent=None,
                                  note="recommended; set by engineering study (2C.59)"),
    "SPEED_AVERAGE":         dict(defined="1C.02 #249(a)", parent=None, note="measured"),
    "SPEED_DESIGN":          dict(defined="1C.02 #249(b)", parent=None, note="a design choice"),
    "SPEED_85TH":            dict(defined="1C.02 #249(c)", parent=None, note="measured"),
    "SPEED_OPERATING":       dict(defined="1C.02 #249(d)", parent=None,
                                  note="MAY BE realised as the average, pace or 85th-percentile speed"),
    "SPEED_PACE":            dict(defined="1C.02 #249(e)", parent=None,
                                  note="a 10 mph RANGE, not a single speed"),
    "SPEED_DIFFERENTIAL":    dict(defined="2C.06 ¶1 and 2C.59 ¶3 (local, not in 1C.02)",
                                  parent=None, note="approach speed minus advisory speed"),
    "SPEED_PREVAILING":      dict(defined="NOT defined in the MUTCD; FHWA 2(09)-2 gives one",
                                  parent=None, note="average of 85th-percentile and upper limit of pace"),
    "SPEED_PEDESTRIAN":      dict(defined="section-local (Part 4)", parent=None, note="walking or crossing"),
    "SPEED_TRAIN":           dict(defined=None, parent=None,
                                  note="a RAIL speed (train or LRT). Never comparable with a highway speed"),
    "SPEED_CHANGE":          dict(defined=None, parent=None,
                                  note="the SIZE of a change in speed -- not a speed. "
                                       "'a reduction of 10 mph' is not a limit of 10 mph"),
    "SPEED_UNRESOLVED":      dict(defined=None, parent=None, note="the manual does not say which speed"),
}
# operating speed and 85th-percentile speed are NOT disjoint (1C.02 #249(d))
MAY_BE_REALISED_AS = {"SPEED_OPERATING": ["SPEED_AVERAGE", "SPEED_PACE", "SPEED_85TH"]}

# What the manual says when it offers a CHOICE of speeds. Trap 3: these must
# stay a set, never collapse to one member.
_ALT_SPEED = re.compile(
    r"(?:posted|statutory)[^.;]{0,40}?(?:speed limit|speed)[^.;]{0,40}?"
    r"(?:or|and)[^.;]{0,30}?85th[- ]percentile", re.I)


def canonical_speed(sentence: str, start: int, end: Optional[int] = None,
                    lead_in: Optional[str] = None) -> Tuple[str, Optional[List[str]]]:
    """Which speed a number at `start` is measured on. Returns (kind, alternatives)."""
    near = sentence[max(0, start - 45):start].lower()
    after = sentence[end:end + 40].lower() if end else ""
    wide = sentence[max(0, start - 90):start].lower()
    # a rail speed is a different quantity altogether
    if re.search(r"\b(?:trains?|lrt|rail traffic|railroad)\b[^.;]{0,60}$", wide) or \
       re.match(r"\s*(?:mph\s+)?(?:signs?\b)", after) and "train" in wide:
        return "SPEED_TRAIN", None
    # a change in speed is not a speed
    if re.search(r"\b(?:reduction|increase|decrease|drop|change)s? of (?:more than |less than |at least )?$", near) or \
       re.search(r"\bexceed[^.]{0,70}\bby\s*(?:\d+\s*to\s*)?$", wide) or \
       re.search(r"\breduced by\s*$", near) or \
       re.match(r"\s*(?:mph\s+)?(?:in|to) the (?:posted )?speed limit", after) or \
       re.match(r"\s*(?:mph\s+)?(?:below|above) the (?:posted |statutory )?speed limit", after):
        return "SPEED_CHANGE", None
    # "a 35-mph advisory speed": the speed is named right after the number
    for phrase, kind in (("advisory speed", "SPEED_ADVISORY"), ("speed limit", "SPEED_LIMIT"),
                         ("design speed", "SPEED_DESIGN"), ("operating speed", "SPEED_OPERATING")):
        if re.match(rf"\s*(?:-\s*)?(?:mph\s+)?{phrase}", after):
            return kind, None
    # "the 10 mph speed range" -- the pace
    if re.match(r"\s*(?:mph\s+)?speed range", after):
        return "SPEED_PACE", None
    back = sentence[max(0, start - 160):start]
    # stay inside the clause
    cut = max(back.rfind(";"), back.rfind(". "))
    if cut >= 0:
        back = back[cut + 1:]
    low = back.lower()

    if re.search(r"\bdifference between\b[^.;]{0,120}\bspeed", low) or "speed differential" in low:
        return "SPEED_DIFFERENTIAL", None
    if re.search(r"\bposted or statutory\b(?![^.;]{0,50}85th)", back, re.I) and not _ALT_SPEED.search(back):
        return "SPEED_ALTERNATIVES", ["SPEED_LIMIT_POSTED", "SPEED_LIMIT_STATUTORY"]
    if _ALT_SPEED.search(back):
        alts = []
        if re.search(r"\bposted\b", low):     alts.append("SPEED_LIMIT_POSTED")
        if re.search(r"\bstatutory\b", low):  alts.append("SPEED_LIMIT_STATUTORY")
        if re.search(r"85th", low):           alts.append("SPEED_85TH")
        if re.search(r"anticipated operating", low): alts.append("SPEED_OPERATING")
        return "SPEED_ALTERNATIVES", alts
    # nearest named speed wins
    order = [("advisory speed", "SPEED_ADVISORY"), ("recommended speed", "SPEED_ADVISORY"),
             ("85th", "SPEED_85TH"),
             ("design speed", "SPEED_DESIGN"), ("average speed", "SPEED_AVERAGE"),
             ("pace", "SPEED_PACE"),
             ("statutory speed", "SPEED_LIMIT_STATUTORY"),
             ("posted speed", "SPEED_LIMIT_POSTED"),
             ("walking speed", "SPEED_PEDESTRIAN"), ("crossing speed", "SPEED_PEDESTRIAN"),
             ("operating speed", "SPEED_OPERATING"), ("prevailing speed", "SPEED_PREVAILING"),
             ("speed limit", "SPEED_LIMIT")]
    # the nearest named speed wins, but a longer phrase that CONTAINS a shorter
    # one wins over it: "posted speed limit" is POSTED, not merely a speed limit
    order = [("posted speed limit", "SPEED_LIMIT_POSTED"),
             ("statutory speed limit", "SPEED_LIMIT_STATUTORY")] + order
    best = None
    for phrase, kind in order:
        i = low.rfind(phrase)
        if i < 0:
            continue
        end = i + len(phrase)
        if best is None or end > best[0] or (end == best[0] and len(phrase) > best[2]):
            best = (end, kind, len(phrase))
    if best:
        return best[1], None
    # a list item inherits its speed from the sentence that introduces it:
    # "the determination of the recommended advisory speed ... including:"
    if lead_in:
        k, alts = canonical_speed(lead_in, len(lead_in))
        if k not in ("SPEED_UNRESOLVED", "SPEED_CHANGE"):
            return k, alts
    return "SPEED_UNRESOLVED", None


_OTHER = {"aadt": "VOLUME_DAILY", "adt": "VOLUME_DAILY", "average daily traffic": "VOLUME_DAILY",
          "volume": "VOLUME", "traffic volume": "VOLUME", "vehicles per hour": "VOLUME_HOURLY",
          "population": "POPULATION"}


def canonical(sentence: str, q, lead_in: Optional[str] = None) -> Tuple[Optional[str], Optional[List[str]]]:
    # the unit alone says it is a speed; the words around it say which
    if q.unit.lower() in ("mph", "miles per hour"):
        return canonical_speed(sentence, q.span[0], q.span[1], lead_in)
    u = q.unit.lower()
    if re.match(r"vehicles per hour|vph", u):
        return "VOLUME_HOURLY", None
    if re.match(r"vehicles per day|vpd", u):
        return "VOLUME_DAILY", None
    if u.startswith("vehicle") and "hour" in u:
        return "DELAY_VEHICLE_HOURS", None
    if u in ("schoolchildren", "students", "children", "people", "persons", "pedestrians"):
        return f"COUNT_{u.upper()}", None
    if q.head is None:
        return None, None
    if "speed" in q.head or q.head == "difference":
        return canonical_speed(sentence, q.span[0], q.span[1], lead_in)
    return _OTHER.get(q.head, q.head.upper().replace(" ", "_").replace("-", "_")), None


# =========================================================================== #
# 2. Graph records
# =========================================================================== #
@dataclass
class Node:
    id: str
    kind: str
    section: str
    text: str = ""
    authority: Optional[str] = None
    pieces: List[str] = field(default_factory=list)
    quantities: List[dict] = field(default_factory=list)
    ordinal: Optional[int] = None
    item: Optional[str] = None


@dataclass
class Edge:
    src: str
    rel: str
    dst: str
    why: str = ""


# =========================================================================== #
# 3. Building
# =========================================================================== #
_PARA_REF = re.compile(
    r"(?:Items?\s+(?P<item>[A-Z](?:\s*(?:,\s*and|,|and)\s*[A-Z])*)\s+(?:in|of)\s+)?"
    r"Paragraphs?\s+(?P<nums>\d+(?:\s*(?:,\s*and|,|and|through|to)\s*\d+)*)"
    r"\s+(?:of|in)\s+this\s+Section", re.I)
_EXC_LIST = re.compile(
    r"\b(?:except|unless)\b[^.;]{0,160}?" + _PARA_REF.pattern, re.I)
# what an unnamed exception sounds like: it removes, adds or replaces
_EFFECT = re.compile(r"\bmay be omitted\b|\bneed not\b|\badditional or supplemental\b|"
                     r"\bmay be used in place of\b|\binstead of\b|\bin lieu of\b|"
                     r"\bmay be placed on\b.{0,40}\bleft-hand side\b", re.I)


def _nums(spec: str) -> List[int]:
    out = []
    for a, b in re.findall(r"(\d+)\s*(?:through|to)\s*(\d+)", spec):
        out += list(range(int(a), int(b) + 1))
    spec = re.sub(r"\d+\s*(?:through|to)\s*\d+", "", spec)
    out += [int(x) for x in re.findall(r"\d+", spec)]
    return sorted(set(out))


def build(chunks: List[dict], tables_path: Optional[str] = None,
          interpretations: Optional[List[dict]] = None):
    nodes: Dict[str, Node] = {}
    edges: List[Edge] = []
    by_para = defaultdict(list)          # (section, ordinal) -> sentence ids
    by_para_item = defaultdict(list)     # (section, ordinal, item) -> ids

    norm = [c for c in chunks if c["content_type"] in ("Standard", "Guidance", "Option", "Support")]

    # ---- sentence nodes
    for c in norm:
        for k, s in enumerate(sentences(c["text"])):
            nid = f"sent:{c['chunk_id']}#{k}"
            t = tag_sentence(s)
            qs = []
            for q in t.quantities:
                kind, alts = canonical(s, q, c.get("lead_in"))
                qs.append(dict(number=q.number, unit=q.unit, op=q.op, kind=kind,
                               alternatives=alts, referent=q.referent))
            nodes[nid] = Node(nid, "SENTENCE", c["section_id"], s,
                              t.authority if c["content_type"] != "Support" else "SUPPORT",
                              sorted(t.pieces), qs, c.get("ordinal"), c.get("item"))
            by_para[(c["section_id"], c.get("ordinal"))].append(nid)
            if c.get("item"):
                by_para_item[(c["section_id"], c.get("ordinal"), c["item"])].append(nid)

            # ---- REFERS_TO: sections, tables, figures, signs (text-anchored)
            for sec in c.get("section_refs") or []:
                if re.search(rf"\bSection\s+{re.escape(sec)}\b", s):
                    edges.append(Edge(nid, "REFERS_TO", f"section:{sec}", "names the section"))
            for kind in ("Table", "Figure"):
                for grp in re.finditer(rf"\b{kind}s?\s+((?:[0-9A-Z]+-[0-9]+[a-z]?)(?:\s*(?:,|and|or|through|to)\s*(?:and\s+)?[0-9A-Z]+-[0-9]+[a-z]?)*)", s):
                    ids = re.findall(r"[0-9A-Z]+-[0-9]+[a-z]?", grp.group(1))
                    if re.search(r"\bthrough\b|\bto\b", grp.group(1)) and len(ids) == 2:
                        a, b = ids
                        pa, na = a.rsplit("-", 1); pb, nb = b.rsplit("-", 1)
                        if pa == pb and na.isdigit() and nb.isdigit():
                            ids = [f"{pa}-{k}" for k in range(int(na), int(nb) + 1)]
                    for t in ids:
                        edges.append(Edge(nid, "REFERS_TO", f"figure:{kind} {t}", f"names the {kind.lower()}"))
            # "Figure 4C-7 may be used in place of Figure 4C-5", "Tables 4C-4 and 4C-5 ... in place of Tables 4C-2 and 4C-3, respectively"
            for m in re.finditer(r"\b(Tables?|Figures?)\s+([0-9A-Z-]+(?:\s*(?:and|,)\s*[0-9A-Z-]+)*)\s+may be used in place of\s+(?:Tables?|Figures?)\s+([0-9A-Z-]+(?:\s*(?:and|,)\s*[0-9A-Z-]+)*)", s):
                kind = "Table" if m.group(1).startswith("Table") else "Figure"
                new = re.findall(r"[0-9A-Z]+-[0-9]+", m.group(2)); old = re.findall(r"[0-9A-Z]+-[0-9]+", m.group(3))
                if len(new) == len(old):
                    for a, b in zip(new, old):
                        edges.append(Edge(f"figure:{kind} {a}", "REPLACES", f"figure:{kind} {b}",
                                          f"under the conditions of {nid.split(':')[1]}"))
            for sc in c.get("sign_codes") or []:
                if sc in s:
                    edges.append(Edge(nid, "REFERS_TO", f"signcode:{sc}", "names the sign"))

    # ---- introducing sentences of lists. The data carries each item's lead-in;
    # without it an item has no rule, no authority and no way to know whether
    # the items combine as ANY or ALL. 281 lead-ins are rules in their own right.
    groups = defaultdict(list)
    _CAPTION = re.compile(r"^\s*(Table|Figure)\s+([0-9A-Z]+-[0-9]+[a-z]?)\.?\s*$")
    for c in norm:
        if not (c.get("item") and c.get("lead_in")):
            continue
        cap = _CAPTION.match(c["lead_in"])
        if cap:
            # a note printed under a table or figure, filed as a numbered item
            k = 0
            while f"sent:{c['chunk_id']}#{k}" in nodes:
                nid = f"sent:{c['chunk_id']}#{k}"
                nodes[nid].kind = "NOTE"
                edges.append(Edge(f"figure:{cap.group(1)} {cap.group(2)}", "NOTE_OF", nid,
                                  "a note printed under this " + cap.group(1).lower()))
                if nid in by_para.get((c["section_id"], c.get("ordinal")), []):
                    by_para[(c["section_id"], c.get("ordinal"))].remove(nid)
                if c.get("item"):
                    lst = by_para_item.get((c["section_id"], c.get("ordinal"), c["item"]), [])
                    if nid in lst:
                        lst.remove(nid)
                k += 1
            continue
        groups[(c["section_id"], c.get("ordinal"), c["lead_in"].strip())].append(c)
    _ANY = re.compile(r"\b(?:either of|any of|any one of|one or more of|at least one of|one of the following)\b", re.I)
    _ALL = re.compile(r"\b(?:all of|both of|each of|all the following|both the following)\b", re.I)
    _EXC = re.compile(r"\bexcept\b[^.]*\bfollowing\b", re.I)
    for (sec, o, lead), items in groups.items():
        lid = f"lead:{items[0]['chunk_id']}"
        t = tag_sentence(lead)
        auth = ("SUPPORT" if items[0]["content_type"] == "Support" else
                t.authority or {"Standard": "STANDARD", "Guidance": "GUIDANCE",
                                "Option": "OPTION"}.get(items[0]["content_type"]))
        qs = []
        for q in t.quantities:
            kind, alts = canonical(lead, q)
            qs.append(dict(number=q.number, unit=q.unit, op=q.op, kind=kind, alternatives=alts, referent=q.referent))
        nodes[lid] = Node(lid, "SENTENCE", sec, lead, auth, sorted(t.pieces), qs, o, None)
        by_para[(sec, o)].append(lid)
        tails = " ".join(i["text"].strip()[-8:].lower() for i in items[:-1])
        if _EXC.search(lead):
            comb = "EXCEPTION CASES: each item is a case in which the introducing rule does not apply"
        elif _ANY.search(lead) or re.search(r"\bor\s*[.;,]?\s*$", items[0]["text"].strip(), re.I) and len(items) > 1:
            comb = "ANY: one item is enough"
        elif _ALL.search(lead) or re.search(r"\band\s*[.;,]?\s*$", items[-2]["text"].strip(), re.I) if len(items) > 1 else False:
            comb = "ALL: every item applies"
        else:
            comb = "NOT STATED: the manual does not say whether these combine as any or all"
        for c in items:
            k = 0
            while f"sent:{c['chunk_id']}#{k}" in nodes:
                n = nodes[f"sent:{c['chunk_id']}#{k}"]
                edges.append(Edge(n.id, "ITEM_OF", lid, comb))
                if n.authority is None:
                    n.authority = auth          # "To this end the agency should: A. Keep ..."
                k += 1

    for n in nodes.values():
        if n.kind == "SENTENCE" and n.authority is None:
            ct = next((c["content_type"] for c in norm if n.id.startswith(f"sent:{c['chunk_id']}#")), None)
            n.authority = {"Standard": "STANDARD (by heading)", "Guidance": "GUIDANCE (by heading)",
                           "Option": "OPTION (by heading)"}.get(ct)

    nodes["external:stop-rules"] = Node("external:stop-rules", "EXTERNAL", "",
        "the rules for proceeding after a stop at a STOP sign: Uniform Vehicle Code and state law, not the MUTCD")
    nodes["external:other-devices"] = Node("external:other-devices", "EXTERNAL", "",
        "any other traffic control device at the location (lane-use signs, turn prohibitions, markings ...)")
    for nid, n in list(nodes.items()):
        if n.kind != "SENTENCE":
            continue
        if re.search(r"rules applicable after making a stop at a STOP sign", n.text, re.I):
            edges.append(Edge(nid, "REFERS_TO", "external:stop-rules", "outside the manual; cannot be checked here"))
        if re.search(r"\bexcept as such \w+ is modified by\b|\bunless otherwise directed by\b", n.text, re.I):
            edges.append(Edge(nid, "DEFEASIBLE_BY", "external:other-devices",
                              "open-ended: any other device present overrides this meaning"))

    for c in norm:
        k, parent = 0, None
        while f"sent:{c['chunk_id']}#{k}" in nodes:
            x = nodes[f"sent:{c['chunk_id']}#{k}"]
            if re.search(r"\bthe following\b[^.]*:\s*$", x.text):
                parent = x
            elif parent is not None and re.match(r"\s*\d{1,2}[.)]\s", x.text):
                t = parent.text.lower()
                comb = ("ANY: one sub-item is enough" if _ANY.search(t) or "at least one" in t else
                        "ALL: every sub-item applies" if _ALL.search(t) or re.search(r"\ball (?:two|three|four|five)\b", t) else
                        "NOT STATED: the manual does not say whether these combine as any or all")
                edges.append(Edge(x.id, "ITEM_OF", parent.id, comb))
            k += 1
    # "Warrants 1, 2, and 3" -> the warrant sections
    wsec = {}
    for c in chunks:
        m = re.match(r"Warrant (\d),", c.get("section_title") or "")
        if m:
            wsec[m.group(1)] = c["section_id"]
    for nid, x in list(nodes.items()):
        if x.kind != "SENTENCE":
            continue
        for m in re.finditer(r"\bWarrants?\s+(\d(?:\s*(?:,|and|or|through)\s*(?:and\s+|or\s+)?\d)*)", x.text):
            for w in re.findall(r"\d", m.group(1)):
                if w in wsec and wsec[w] != x.section:
                    edges.append(Edge(nid, "REFERS_TO", f"section:{wsec[w]}", f"names Warrant {w}"))

    # ---- paragraph references and named exceptions (need all nodes first)
    named_exc = defaultdict(set)         # rule sentence id -> named ordinals
    for nid, n in nodes.items():
        for m in _PARA_REF.finditer(n.text):
            for o in _nums(m.group("nums")):
                if m.group("item"):
                    targets = [t for it in re.findall(r"[A-Z]", m.group("item"))
                               for t in by_para_item.get((n.section, o, it), [])]
                else:
                    targets = by_para.get((n.section, o)) or []
                is_exc = bool(re.search(r"\b(?:except|unless)\b[^.;]{0,160}$",
                                        n.text[:m.start()], re.I))
                reverse = n.authority and n.authority.startswith("OPTION") and bool(re.search(
                    r"\b(?:are|is) not relevant\b|\bdo(?:es)? not apply\b|\bneed not\b|\bmay be (?:omitted|waived)\b",
                    n.text[m.end():m.end() + 160], re.I))
                if reverse:
                    for t in targets:
                        edges.append(Edge(t, "EXCEPTS", nid, "the exception names the rule it relaxes: "
                                          + n.text[m.end():m.end() + 90].strip()))
                    continue
                for t in targets:
                    edges.append(Edge(nid, "EXCEPTS" if is_exc else "REFERS_TO", t,
                                      f"names Paragraph {o}" + (f" Item {m.group('item')}" if m.group("item") else "")))
                if is_exc:
                    named_exc[nid].add(o)

    # ---- unnamed exceptions, found by effect, in sections that keep a list
    sec_nodes = defaultdict(list)
    for nid, n in nodes.items():
        sec_nodes[n.section].append(nid)
    candidates = []
    for rule_id, listed in named_exc.items():
        rule = nodes[rule_id]
        for nid in sec_nodes[rule.section]:
            n = nodes[nid]
            if n.ordinal in listed or n.ordinal == rule.ordinal or n.authority != "OPTION":
                continue
            if _EFFECT.search(n.text):
                edges.append(Edge(rule_id, "EXCEPTS_CANDIDATE", nid,
                                  f"Paragraph {n.ordinal} relaxes this rule by what it says, "
                                  f"but the rule's list names only {sorted(listed)}"))
                candidates.append((rule.section, rule.ordinal, n.ordinal, n.text))

    # ---- apply the rulings made by reading (rulings.py)
    from .rulings import RULINGS
    applied = defaultdict(int)
    kept = []
    for e in edges:
        if e.rel != "EXCEPTS_CANDIDATE":
            kept.append(e)
            continue
        r, c = nodes[e.src], nodes[e.dst]
        _strip = lambda t: re.sub(r"^\W*(?:[A-Za-z]|\d{1,2})[.)]\s+", "", t)
        hit = next((x for x in RULINGS if x[0] == r.section and _strip(r.text).startswith(x[1])
                    and _strip(c.text).startswith(x[2])), None)
        if hit is None:
            applied["UNRULED"] += 1
            kept.append(e)
        elif hit[3] == "YES":
            applied["YES"] += 1
            kept.append(Edge(e.src, "EXCEPTS", e.dst, "not in the rule's list; ruled by reading: " + hit[4]))
        elif hit[3] == "YES_DELEGATED":
            applied["YES_DELEGATED"] += 1
            kept.append(Edge(e.src, "EXCEPTS", e.dst,
                             "DELEGATED JUDGMENT, the agency's choice; ruled by reading: " + hit[4]))
        elif hit[3] == "ENGINEER":
            applied["ENGINEER"] += 1
            kept.append(Edge(e.src, "EXCEPTS_CANDIDATE", e.dst, "FOR THE ENGINEER. " + hit[4]))
        else:
            applied["NO"] += 1
    edges[:] = kept
    candidates = [cd for cd in candidates]   # the raw list stays for audit
    build.rulings_applied = dict(applied)

    # ---- quantity definitions and uses
    defines = defaultdict(list)          # (section, kind) -> defining sentence ids
    for nid, n in nodes.items():
        if not ({"DEFINITION", "COMPUTED"} & set(n.pieces)):
            continue
        low = n.text.lower()
        if re.search(r"\bspeed differential\b[^.]{0,80}\bshall be the difference\b", low) or \
           re.search(r"\bdifference between\b[^.]{0,40}\bspeed\b[^.]{0,80}\band\b", low) and "differential" in low:
            defines[(n.section, "SPEED_DIFFERENTIAL")].append(nid)
            edges.append(Edge(nid, "DEFINES", "quantity:SPEED_DIFFERENTIAL",
                              "states how the speed differential is computed"))
            if "advisory speed" in low:
                edges.append(Edge(nid, "COMPUTED_FROM", "quantity:SPEED_ADVISORY", "operand"))
            alts = [k for w, k in (("posted", "SPEED_LIMIT_POSTED"),
                                   ("statutory", "SPEED_LIMIT_STATUTORY"),
                                   ("85th", "SPEED_85TH")) if w in low]
            for k in alts:
                edges.append(Edge(nid, "COMPUTED_FROM", f"quantity:{k}",
                                  f"operand -- ONE OF {len(alts)} alternatives; the manual does not rank them"))
    for nid, n in nodes.items():
        for q in n.quantities:
            if q["kind"] == "SPEED_DIFFERENTIAL":
                for d in defines.get((n.section, "SPEED_DIFFERENTIAL"), []):
                    if d != nid:
                        edges.append(Edge(nid, "USES", d, "measures the differential defined here"))

    # ---- tables: axes and notes
    # A table number can hold SEPARATE charts (Table 2C-4: Chart A need /
    # Chart B selection; Table 4C-1: Condition A / Condition B). Those get one
    # node each, PART_OF the table. A table merely printed across several
    # pages (same title, sheet 1 of 2 ...) stays one node.
    def _sub_label(title: str) -> Optional[str]:
        if "\u2014" not in title:
            return None
        sub = title.split("\u2014", 1)[1].strip()
        m = re.match(r"(?:Chart\s+|Condition\s+)?([A-Z])\s*(?::|-|\u2013|\s)", sub)
        return m.group(1) if m else sub.split()[0]
    sub_nodes = defaultdict(set)          # table id -> sub-labels
    if tables_path:
        recs = [json.loads(l) for l in open(tables_path) if l.strip()]
        titles = defaultdict(set)
        for t in recs:
            titles[t["table_id"]].add(t["title"])
        for t in recs:
            tid = f"figure:{t['table_id']}"
            lab = _sub_label(t["title"]) if len(titles[t["table_id"]]) > 1 else None
            node = f"{tid}#{lab}" if lab else tid
            if lab and lab not in sub_nodes[t["table_id"]]:
                sub_nodes[t["table_id"]].add(lab)
                nodes[node] = Node(node, "SUBTABLE", "", t["title"])
                edges.append(Edge(node, "PART_OF", tid, "a separate chart under one table number"))
            for lab_c in t.get("column_labels") or []:
                low = lab_c.lower()
                kind = ("SPEED_DIFFERENTIAL" if "differential" in low else
                        "SPEED_ADVISORY" if "advisory speed" in low else
                        "VOLUME_DAILY" if "aadt" in low else
                        "VOLUME_HOURLY" if "vehicles per hour" in low else
                        "SPEED_UNRESOLVED" if "speed" in low else None)
                if kind:
                    edges.append(Edge(node, "AXIS", f"quantity:{kind}", f"column '{lab_c}'"))
            for f in t.get("footnotes") or []:
                if f.get("chunk_id"):
                    edges.append(Edge(node, "NOTE_OF", f"chunk:{f['chunk_id']}",
                                      f"READ FIRST; applies to {f.get('applies_to', 'table')}"))
    # route "Chart B of Table 2C-4" / "Condition A in Table 4C-1" to the chart it names
    for e in edges:
        if e.rel != "REFERS_TO" or not e.dst.startswith("figure:Table "):
            continue
        tb = e.dst.split("figure:", 1)[1]
        labs = sub_nodes.get(tb)
        if not labs:
            continue
        named = set(re.findall(r"\b(?:Chart|Condition)\s+([A-Z])\b", nodes[e.src].text)) & labs
        if len(named) == 1:
            e.dst = f"{e.dst}#{named.pop()}"
            e.why = "names this chart of the table"
        elif len(named) > 1:
            first, *rest = sorted(named)
            e.dst = f"{e.dst}#{first}"
            e.why = "names this chart of the table"
            for r in rest:
                edges.append(Edge(e.src, "REFERS_TO", f"figure:{tb}#{r}", "names this chart of the table"))

    # ---- quantity nodes, anchored to their definitions and to each other
    gl = glossary(chunks)
    gl_by_num = {n: t for t, (n, _) in gl.items()}
    for q, meta in SPEEDS.items():
        qid = f"quantity:{q}"
        nodes[qid] = Node(qid, "QUANTITY", "", f"{q}: {meta['note']}", None)
        if meta["parent"]:
            edges.append(Edge(qid, "IS_A", f"quantity:{meta['parent']}", "the manual's own hierarchy"))
        if meta["defined"] and meta["defined"].startswith("1C.02 #"):
            num = re.match(r"1C\.02 #(\d+)", meta["defined"]).group(1)
            edges.append(Edge(qid, "DEFINED_BY", f"term:{gl_by_num.get(num, num)}",
                              f"glossary {meta['defined']}"))
    for q, rs in MAY_BE_REALISED_AS.items():
        for r in rs:
            edges.append(Edge(f"quantity:{q}", "MAY_BE_REALISED_AS", f"quantity:{r}",
                              "1C.02 #249(d): not disjoint"))

    # ---- every number that measures a speed -> the quantity it measures
    for nid, n in list(nodes.items()):
        if n.kind != "SENTENCE":
            continue
        for q in n.quantities:
            if q["kind"] in SPEEDS:
                edges.append(Edge(nid, "MEASURES", f"quantity:{q['kind']}",
                                  f"{q['number']} {q['unit']} {q['op']}"))
            elif q["kind"] == "SPEED_ALTERNATIVES":
                for a in q["alternatives"] or []:
                    edges.append(Edge(nid, "MEASURES_ONE_OF", f"quantity:{a}",
                                      f"{q['number']} {q['unit']} {q['op']} -- the manual offers "
                                      f"{len(q['alternatives'])} and does not rank them"))

    # ---- terms -> their definitions (glossary + verified local definitions)
    edges.extend(link_terms(nodes, chunks))

    # ---- official interpretations: a separate authority, never mixed with the manual
    for it in interpretations or []:
        iid = f"interpretation:{it['id']}"
        nodes[iid] = Node(iid, "INTERPRETATION", it["section"], it["text"], it["authority"])
        for s in it["attaches_to_sections"]:
            for d in defines.get((s, it["quantity"]), []):
                edges.append(Edge(iid, "INTERPRETS", d, it["summary"]))

    return nodes, edges, candidates


# Local definitions outside 1C.02, verified by reading.
LOCAL_DEFINITIONS = [
    dict(term="short duration", section="6N.01", authority="STANDARD",
         meaning="work that occupies a location up to 1 hour"),
    dict(term="short-term stationary", section="6N.01", authority="STANDARD",
         meaning="daytime work more than 1 hour within a single daylight period"),
    dict(term="intermediate-term stationary", section="6N.01", authority="STANDARD",
         meaning="more than one daylight period up to 3 days, or night work over 1 hour"),
    dict(term="speed differential", section="2C.06", authority="STANDARD",
         meaning="difference between the approach speed and the advisory speed"),
]
# Words the manual uses and never defines -- anywhere. Checked against 1C.02
# and against section-local definitions. These are the true UNDETERMINED set.
UNDEFINED_TERMS = ["built-up area", "isolated community", "adequate trial",
                   "low-speed", "high-speed"]


def glossary(chunks: List[dict]) -> Dict[str, Tuple[str, str]]:
    """1C.02: term -> (number, full definition)."""
    out = {}
    for c in chunks:
        if c["section_id"] != "1C.02":
            continue
        m = re.match(r"\s*(\d+)\.\s*(.+?)\s*[-\u2014\u2013](?=[a-z])", c["text"])
        if m:
            out[m.group(2).strip().lower()] = (m.group(1), c["text"])
    return out


def link_terms(nodes: Dict[str, "Node"], chunks: List[dict]) -> List["Edge"]:
    """Every sentence that uses a defined multi-word term -> its definition.
    Single common words ('sign', 'lane') are skipped: they would link almost
    every sentence and mean nothing."""
    gl = glossary(chunks)
    terms = {t: f"1C.02 #{n}" for t, (n, _) in gl.items() if " " in t or "-" in t}
    for d in LOCAL_DEFINITIONS:
        terms[d["term"]] = f"{d['section']} (local)"
    pats = [(t, src, re.compile(r"\b" + re.escape(t) + r"s?\b", re.I))
            for t, src in sorted(terms.items(), key=lambda x: -len(x[0]))]
    out = []
    for nid, n in nodes.items():
        if n.kind != "SENTENCE" or n.section == "1C.02":
            continue
        taken = []
        for t, src, rx in pats:
            for m in rx.finditer(n.text):
                if any(a <= m.start() < b for a, b in taken):
                    continue              # a longer term already covers this span
                taken.append(m.span())
                out.append(Edge(nid, "USES_TERM", f"term:{t}", f"defined in {src}"))
                break
    return out


# The one interpretation verified against its source (FHWA, 2 June 2010).
FHWA_2_09_2 = dict(
    id="2(09)-2(I)", section="2C.06",
    authority="FHWA OFFICIAL INTERPRETATION (policy guidance; not a legal requirement)",
    quantity="SPEED_DIFFERENTIAL", attaches_to_sections=["2C.06", "2C.59"],
    summary="agency chooses which approach speed; the choice shall be documented",
    text=("Highway agencies have the flexibility to determine, based on engineering "
          "judgment, which speed value to use for the tangent approach (posted or "
          "statutory speed limit, 85th-percentile speed, or prevailing speed). The "
          "decision shall be documented in the engineering study. The provisions apply "
          "only where the advisory speed is less than the approach speed."))
