"""Score the graph parser on queries whose governing section is known.

Gold sections were taken from the reading log, not from the parser's own
output. `accept` lists sections that answer the question properly; the first
is the best one.
"""
import argparse
from pathlib import Path

from mrag.vine.graph_parser import GraphParser

GOLD = [
    ("What size must a STOP sign be on a conventional road?",            ["2B.03"]),
    ("When is a Speed Limit sign required to be retroreflective?",       ["2B.21", "2A.09"]),
    ("taper length for a merging taper in a work zone",                  ["6B.08"]),
    ("crosswalk markings at a circular intersection",                    ["3C.09", "3C.03"]),
    ("R3-8 lane control sign placement",                                 ["2B.30"]),
    ("minimum mounting height for a sign in a business district",        ["2A.15"]),
    ("when may a YIELD sign be used instead of a STOP sign",             ["2B.07", "2B.06", "2B.05"]),
    ("what colour shall a pedestrian signal WALKING PERSON be",          ["4I.02"]),
    ("how long is the pedestrian walk interval",                         ["4I.06"]),
    ("dimensions of the bicycle lane symbol marking",                    ["9E.01", "9E.02"]),
    ("no-passing zone markings on a two-lane road",                      ["3B.03", "3B.01"]),
    ("when is a flashing yellow arrow used for a permissive left turn",  ["4F.04", "4F.08", "4F.03"]),
    ("spacing of channelizing devices in a taper",                       ["6K.02", "6B.08"]),
    ("what does the EXCEPT BICYCLES plaque do",                          ["9B.02"]),
    ("emergency notification system sign at a grade crossing",           ["8B.27"]),
    ("purple pavement for toll lanes",                                   ["3H.08", "3H.06"]),
    ("warrant for a pedestrian traffic signal",                          ["4C.05", "4C.06"]),
    ("advance warning sign spacing in a temporary traffic control zone", ["6B.03", "6C.04"]),
    ("height of a crossbuck assembly at a passive crossing",             ["8B.04"]),
    ("when shall a school speed limit assembly be used",                 ["7B.05", "7B.06"]),
]


def main(graph: Path | None = None, k: int = 5):
    gp = GraphParser(graph)
    top1 = acc = fail = 0
    ink = acck = 0
    rows = []
    for q, gold in GOLD:
        # parse_ranked compiles the best k sections instead of stopping at the
        # first that works. Top-1 is still the headline; the top-k columns say
        # whether a routing error is recoverable -- whether the right section
        # was in the candidate set at all and just lost the ranking.
        ranked, rep = gp.parse_ranked(q, k=k)
        spec = ranked[0].spec if ranked else None
        picked = ranked[0].section if ranked else ""
        secs = [c.section for c in ranked]
        ink += gold[0] in secs
        acck += any(s in gold for s in secs)
        if spec is None:
            fail += 1
            rows.append(("FAIL", q, "-", gold[0]))
            continue
        if picked == gold[0]:
            top1 += 1
            acc += 1
            rows.append(("BEST", q, picked, gold[0]))
        elif picked in gold:
            acc += 1
            rows.append(("OK  ", q, picked, gold[0]))
        else:
            rows.append(("MISS", q, picked, "/".join(gold)))

    n = len(GOLD)
    for tag, q, got, want in rows:
        print(f"  [{tag}] {q[:58]:58s} got {got:7s} want {want}")
    print()
    print(f"  best section  : {top1}/{n}  ({100*top1/n:.0f}%)")
    print(f"  acceptable    : {acc}/{n}  ({100*acc/n:.0f}%)")
    print(f"  no spec at all: {fail}/{n}")
    print()
    print(f"  best in top {k}   : {ink}/{n}  ({100*ink/n:.0f}%)")
    print(f"  acceptable top {k}: {acck}/{n}  ({100*acck/n:.0f}%)")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='score the graph parser')
    ap.add_argument('--graph', type=Path, default=None)
    ap.add_argument('--k', type=int, default=5,
                    help='how many sections to compile per query')
    a = ap.parse_args()
    main(a.graph, a.k)
