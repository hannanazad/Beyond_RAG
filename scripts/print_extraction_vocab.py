"""Print the extraction vocabulary cell, read from the graph.

WHY THIS EXISTS
---------------
The Colab benchmark needs a list of quantity kinds, their MUTCD phrasing, and
the units they are measured in. The first version of that cell was typed by
hand. That is a silent trap: the moment the vocabulary changes -- as it just
did, 57 kinds down to 46 -- the cell is stale and the benchmark is scoring the
model against labels the graph no longer uses.

So nothing here is authored. Every kind, every phrasing and every unit is read
out of data/mutcd/graph_cache.pkl. Re-run after any vocabulary change and paste
the output over the cell.

    python scripts/print_extraction_vocab.py > vocab_cell.py

The phrasings have EVERY number stripped. A model shown "mounting height shall
be at least 4 feet" can answer 4 on a question that says 7; shown "mounting
height shall be at least ___" it has nothing to copy and must read the question.
"""
from __future__ import annotations

import argparse
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine.graph_parser import default_graph_path  # noqa: E402


# The manual writes the same unit several ways -- foot, feet, ft; inch, inches;
# mph, miles per hour. Offering all of them in the grammar lets the model pick a
# different spelling from the graph's and score as wrong for being right, which
# is exactly the failure the kind merge just fixed. One name per unit.
UNIT_CANON = {
    "foot": "feet", "ft": "feet", "feet": "feet",
    "inch": "inches", "inches": "inches", "in": "inches", "mm": "millimeters",
    "mile": "miles", "miles": "miles",
    "mph": "mph", "miles per hour": "mph",
    "second": "seconds", "seconds": "seconds",
    "minute": "minutes", "minutes": "minutes",
    "hour": "hours", "hours": "hours",
    "day": "days", "days": "days",
    "month": "months", "months": "months",
    "year": "years", "years": "years",
    "lane": "lanes", "lanes": "lanes",
    "degree": "degrees", "degrees": "degrees",
    "percent": "percent", "count": "count", "people": "people",
    "vph": "vehicles per hour", "vehicles per hour": "vehicles per hour",
    "vpd": "vehicles per day", "vehicles per day": "vehicles per day",
    "vehicle-hours": "vehicle-hours", "feet per second": "feet per second",
}


# Where 1C.02 DEFINES a kind, the definition beats a usage example: it says what
# the thing IS rather than showing one sentence that happens to mention it. It is
# also the manual's legal basis -- FHWA's own guidance calls the Part 1
# definitions "of particular significance ... they establish a legal basis".
#
# Four kinds had no usable usage example at all (SPEED_AVERAGE,
# SPEED_LIMIT_STATUTORY, SPEED_PACE, SPEED_PREVAILING) because they are rare in
# the body text. All four are defined in the glossary.
GLOSSARY_HEADWORD = {
    "SPEED_AVERAGE": "Average Speed",
    "SPEED_85TH": "85th-Percentile Speed",
    "SPEED_PACE": "Pace",
    "SPEED_DESIGN": "Design Speed",
    "SPEED_OPERATING": "Operating Speed",
    "SPEED_LIMIT": "Speed Limit",
    "SPEED_LIMIT_POSTED": "Posted Speed Limit",
    "SPEED_LIMIT_STATUTORY": "Statutory Speed Limit",
    "INTERVAL": "Interval",
    "SPEED_PEDESTRIAN": "Walking Speed",
}
# Not in 1C.02 at all. FHWA Official Interpretation 2(09)-2 supplies one, and
# that is recorded rather than left blank.
NOT_IN_GLOSSARY = {
    "SPEED_PREVAILING": "not defined in the MUTCD; FHWA 2(09)-2 gives the average "
                        "of the 85th-percentile speed and the upper limit of the pace",
    # These two are OURS, not the manual's, and the model cannot guess them from
    # the name. Measured: on the manual's own sentences it collapsed
    # SPEED_ALTERNATIVES into a specific speed 4 times and SPEED_UNRESOLVED 5
    # times -- 9 of 43 disagreements, and the most costly ones, because
    # SPEED_ALTERNATIVES is precisely the case Ruling 1 exists to settle.
    "SPEED_ALTERNATIVES":
        "the sentence names SEVERAL speeds as alternatives and ranks none of "
        "them -- 'the posted, statutory, or 85th-percentile speed'. Use this "
        "whenever two or more speed types are offered as alternatives, NEVER "
        "one of them individually",
    "SPEED_UNRESOLVED":
        "a speed the sentence does not say which kind of -- plain 'the speed' "
        "or 'speeds of 45 mph or higher' with no type named. Use this rather "
        "than guessing a specific speed type",
    "SPEED_CHANGE":
        "a change or reduction IN speed, not a speed itself -- 'a reduction of "
        "10 mph', 'speeds drop by 15 mph'",
    "SPEED_TRAIN":
        "the speed of a TRAIN or light-rail vehicle, never a highway speed "
        "limit. 1C.02 keeps these apart and they are never comparable",
    "SPEED_PEDESTRIAN":
        "a walking speed, normally in feet per second, never a vehicle speed",
    "SPEED_DIFFERENTIAL":
        "the difference between two speeds, such as the approach speed minus "
        "the advisory speed",
}


def glossary_definitions(N) -> dict:
    """Headword -> the manual's own definition, numbers left in.

    Numbers are NOT stripped here, unlike usage examples. A definition's numbers
    are part of what the term means -- Pace is "the 10 mph speed range" and that
    10 is the definition, not a threshold to be copied into an answer. A usage
    example's numbers are a threshold, which is why those are removed.
    """
    out = {}
    for v in N.values():
        if v.kind not in ("SENTENCE", "NOTE") or v.section != "1C.02":
            continue
        # The separator is a hyphen and so is "85th-Percentile". Require the
        # separator to be followed by a lowercase word, and allow an internal
        # hyphen before it, or that entry is lost.
        # "85th-Percentile Speed" begins with a digit, so a capital-letter-only
        # start silently lost it -- the one speed term the whole project turns on.
        m = re.match(r"\s*(?:\([a-z]\)\s*)?([A-Z0-9][A-Za-z0-9 ,/()']+(?:-[A-Z][A-Za-z]+)*"
                     r"(?:\s+[A-Za-z]+)*?)[-–—](?=[a-z])",
                     v.text)
        if m:
            out[m.group(1).strip().lower()] = re.sub(r"\s+", " ", v.text).strip()
    return out


def strip_numbers(s: str) -> str:
    """Remove anything the model could copy as an answer."""
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\b[A-Z]{1,3}\d{1,3}-\d+[a-zA-Z]?P?\b", " ", s)   # sign codes
    s = re.sub(r"\bSection\s+[\dA-Z.]+", " ", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", " ", s)                       # every number
    return re.sub(r"\s+", " ", s).strip(" ,.;:-")


def main(graph: Path | None, per_kind: int) -> None:
    path = Path(graph) if graph else default_graph_path()
    N, E, _C = pickle.load(open(path, "rb"))

    phrasing: dict[str, str] = {}
    units: Counter = Counter()
    cands: defaultdict[str, list] = defaultdict(list)

    for v in N.values():
        if v.kind not in ("SENTENCE", "NOTE"):
            continue
        for q in (v.quantities or []):
            k = q.get("kind")
            if not k or not q.get("number"):
                continue
            if q.get("unit"):
                units[UNIT_CANON.get(q["unit"].lower(), q["unit"].lower())] += 1
            i = v.text.find(str(q["number"]))
            if i < 0:
                continue
            frag = strip_numbers(v.text[max(0, i - 110):i])
            if len(frag) < 30:
                continue
            # prefer a fragment that names the thing it measures
            words = set(k.lower().replace("_", " ").split())
            cands[k].append((sum(w in frag.lower() for w in words), -len(frag), frag))

    for k, v in cands.items():
        v.sort(reverse=True)
        phrasing[k] = v[0][2][-120:]

    # the glossary wins wherever it speaks
    gloss = glossary_definitions(N)
    for kind, headword in GLOSSARY_HEADWORD.items():
        d = gloss.get(headword.lower())
        if d:
            phrasing[kind] = d[:190]
    # These override any usage example: a one-line fragment from the body text
    # cannot convey "several speeds, none ranked", and the measurement showed
    # the model guessing a specific speed instead.
    for kind, note in NOT_IN_GLOSSARY.items():
        phrasing[kind] = note

    kinds = sorted(k.split(":", 1)[1] for k, v in N.items() if v.kind == "QUANTITY")
    keep_units = sorted(u for u, n in units.most_common() if n >= 2)

    out = ['# GENERATED by scripts/print_extraction_vocab.py -- do not hand-edit.',
           f'# Source: {path.name}. {len(kinds)} kinds, {len(keep_units)} units.',
           '# Every phrasing is the MUTCD\'s own wording with all numbers removed,',
           '# so there is no threshold for the model to answer with.',
           'KIND_PHRASING = {']
    for k in kinds:
        p = phrasing.get(k, "").replace('"', "'")
        out.append(f'  {k!r}: {p!r},' if p else f'  {k!r}: "",   # no clean example in the manual')
    out += ['}', '',
            f'KINDS = sorted(KIND_PHRASING) + ["OTHER"]',
            f'UNITS = {keep_units!r}', '',
            'print(len(KINDS), "kinds,", len(UNITS), "units")']
    print("\n".join(out))

    print(f'\n# kinds with no usable phrasing: '
          f'{[k for k in kinds if not phrasing.get(k)]}', file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graph", type=Path, default=None)
    ap.add_argument("--per-kind", type=int, default=1)
    a = ap.parse_args()
    main(a.graph, a.per_kind)
