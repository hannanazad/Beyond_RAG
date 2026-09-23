"""Turn the sentence graph into the full graph, reproducibly.

`graph_links.build()` produces sentence and lead nodes only. Every reference it
emits -- figure, table, section, sign code, term -- is an edge pointing at a
node that does not exist, so 54% of the graph's edges dangle and a query naming
"Figure 2C-5" or "R3-8" lands on nothing.

This module adds the missing layer and the knowledge read off the artwork:

    1  captions          485 figures + 68 tables, read out of the PDF
    2  reference layer   FIGURE / TABLE / SECTION / SIGNCODE / TERM / CHUNK nodes
    3  readings          what each figure shows, parsed from the figure log
    4  rules             the computable rules, from figure_rules.json
    5  rulings           the engineer's rulings, from the reading log

Run it after build() and the result is the graph the parser expects. Nothing
here needs a network, an API key or a person.

    python -m mrag.vine.graph_enrich --pdf MUTCD.pdf --in raw.pkl --out full.pkl
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .graph_links import Node, Edge

# Data this module needs, shipped beside the code so a rebuild is self-contained.
DATA = Path(__file__).resolve().parent.parent.parent / "data" / "mutcd"
DEFAULT_FIGURE_LOG = DATA / "FIGURE_READING_LOG.md"
DEFAULT_RULES = DATA / "figure_rules.json"
DEFAULT_READING_LOG = DATA / "MANUAL_READING_LOG.md"


# --------------------------------------------------------------------------- #
# 1. captions                                                                 #
# --------------------------------------------------------------------------- #
def extract_captions(pdf_path: Path) -> Dict[str, Dict[str, list]]:
    """Every figure and table caption, read from the PDF itself.

    The inventory must come from the artefact, not from a page list made by
    hand: the hand-made list in the first pass missed 21 figures and the error
    was invisible until the captions were cross-checked against it.
    """
    import pymupdf                                   # lazy: only needed here

    doc = pymupdf.open(str(pdf_path))
    figs: Dict[str, list] = {}
    tbls: Dict[str, list] = {}
    fig_re = re.compile(r"^Figure\s+(\d+[A-Z]-\d+[a-z]?)\.\s+(.+)$")
    tbl_re = re.compile(r"^Table\s+([0-9]+[A-Z]?-[0-9]+[a-z]?)\.?\s+(.+)$")

    def absorb(lines: List[str], j: int, cap: str) -> str:
        k = j + 1
        while (k < len(lines) and lines[k]
               and not re.match(r"^(Figure|Table|Section|Note|Notes|[A-Z]\s?–)", lines[k])
               and len(cap) < 110 and not lines[k].startswith("(")):
            cap += " " + lines[k]
            k += 1
        return cap.strip()

    for i in range(len(doc)):
        lines = [l.strip() for l in doc[i].get_text().split("\n")]
        for j, line in enumerate(lines):
            m = fig_re.match(line)
            if m:
                figs.setdefault(m.group(1), [absorb(lines, j, m.group(2).strip()), i + 1])
            m = tbl_re.match(line)
            if m:
                tbls.setdefault(m.group(1), [absorb(lines, j, m.group(2).strip()), i + 1])

    # Some tables are drawn as images and their caption only appears in the
    # list of tables at the front; recover those.
    toc_re = re.compile(r"^Table\s+([0-9]+[A-Z]?-[0-9]+[a-z]?)\s*$")
    for p in range(min(50, len(doc))):
        lines = [l.strip() for l in doc[p].get_text().split("\n")]
        for j, line in enumerate(lines):
            m = toc_re.match(line)
            if not m or m.group(1) in tbls:
                continue
            cap, k = "", j + 1
            while k < len(lines) and len(cap) < 100:
                nxt = lines[k]
                if re.match(r"^Table\s+[0-9]", nxt) or not nxt:
                    break
                cap += (" " if cap else "") + nxt
                k += 1
            cap = re.sub(r"\.{2,}.*$", "", cap).strip()
            cap = re.sub(r"\s+\d+$", "", cap).strip()
            if cap:
                tbls[m.group(1)] = [cap, None]
    return {"figures": figs, "tables": tbls}


# --------------------------------------------------------------------------- #
# 2. the reference layer                                                      #
# --------------------------------------------------------------------------- #
def add_reference_layer(N: dict, E: list, C: list,
                        captions: Dict[str, Dict[str, list]]) -> Counter:
    """Create the nodes the edges already point at."""
    made: Counter = Counter()

    def chapter_of(ident: str) -> str:
        m = re.match(r"(\d+[A-Z]?)", ident)
        return m.group(1) if m else ""

    for ident, (cap, page) in captions["figures"].items():
        key = f"figure:Figure {ident}"
        if key not in N:
            N[key] = Node(id=key, kind="FIGURE", section=chapter_of(ident), text=cap,
                          pieces=[f"pdf_page={page}"] if page else [])
            made["FIGURE"] += 1
    for ident, (cap, page) in captions["tables"].items():
        key = f"figure:Table {ident}"
        if key not in N:
            N[key] = Node(id=key, kind="TABLE", section=chapter_of(ident), text=cap,
                          pieces=[f"pdf_page={page}"] if page else [])
            made["TABLE"] += 1

    def field(chunk, name):
        return getattr(chunk, name) if hasattr(chunk, name) else chunk.get(name)

    sections: Dict[str, str] = {}
    for ch in C:
        sid = field(ch, "section_id")
        if sid:
            sections.setdefault(sid, field(ch, "section_title") or "")
    for sid, title in sections.items():
        key = f"section:{sid}"
        if key not in N:
            N[key] = Node(id=key, kind="SECTION", section=sid, text=title)
            made["SECTION"] += 1

    by_chunk = {field(ch, "chunk_id"): ch for ch in C}
    for dst in {str(e.dst) for e in E if str(e.dst).startswith("chunk:")}:
        if dst in N:
            continue
        ch = by_chunk.get(dst.split(":", 1)[1])
        ctype = field(ch, "content_type") if ch else None
        N[dst] = Node(id=dst, kind="CHUNK",
                      section=(field(ch, "section_id") if ch else ""),
                      text=(field(ch, "text") if ch else ""),
                      authority=(ctype.upper() if ctype else None))
        made["CHUNK"] += 1

    cites: Counter = Counter()
    for ch in C:
        for code in (field(ch, "sign_codes") or []):
            cites[code] += 1
    referenced = {str(e.dst).split(":", 1)[1] for e in E
                  if str(e.dst).startswith("signcode:")}
    for code in sorted(set(cites) | referenced):
        key = f"signcode:{code}"
        if key not in N:
            N[key] = Node(id=key, kind="SIGNCODE", section="", text=code,
                          pieces=[f"citations={cites.get(code, 0)}"])
            made["SIGNCODE"] += 1

    defined = re.compile(r"^([A-Z][A-Za-z0-9 ,'\-/()]{2,60})\s*[—\-–]\s*")
    terms: Dict[str, str] = {}
    for ch in C:
        sid = field(ch, "section_id") or ""
        if not (sid.endswith(".02") or sid.endswith(".03")):
            continue
        m = defined.match((field(ch, "text") or "")[:120])
        if m:
            terms.setdefault(m.group(1).strip().lower(), field(ch, "chunk_id"))
    for term in {str(e.dst).split(":", 1)[1] for e in E
                 if str(e.dst).startswith("term:")}:
        key = f"term:{term}"
        if key not in N:
            src = terms.get(term)
            N[key] = Node(id=key, kind="TERM", section="", text=term,
                          pieces=[f"defined_in={src}"] if src else [])
            made["TERM"] += 1
    return made


# --------------------------------------------------------------------------- #
# 3. readings and findings                                                    #
# --------------------------------------------------------------------------- #
_TAG = re.compile(r"\*\*(FIND|CHECK|DATA|OPEN)")
_ID = re.compile(r"\b(\d+[A-Z]?-\d+[a-z]?)\b")


def parse_figure_log(path: Path) -> List[dict]:
    """The figure log as structured entries. Headings may be plural or a
    range: 'Figures 6P-2 to 6P-7' covers six figures, and dropping the plural
    form silently loses a third of the log."""
    text = Path(path).read_text()
    out: List[dict] = []
    for block in re.split(r"\n### ", text)[1:]:
        lines = block.split("\n")
        head, body = lines[0].strip(), "\n".join(lines[1:]).strip()
        if not re.match(r"(Figures?|Tables?)\b", head):
            continue
        ids = _ID.findall(head)
        m = re.search(r"(\d+[A-Z]?)-(\d+)\s*(?:to|through|–)\s*(?:\d+[A-Z]?-)?(\d+)", head)
        if m:
            pre, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
            if 0 <= hi - lo < 40:
                ids = sorted(set(ids) | {f"{pre}-{i}" for i in range(lo, hi + 1)})
        bullets = re.findall(r"^- (.+?)(?=\n- |\n\n|\Z)", body, flags=re.M | re.S)
        out.append({"head": head, "ids": sorted(set(ids)), "body": body,
                    "bullets": [b.strip() for b in bullets]})
    return out


def attach_readings(N: dict, E: list, entries: List[dict]) -> Counter:
    made: Counter = Counter()
    for i, ent in enumerate(entries):
        targets = [f"figure:{p} {fid}" for fid in ent["ids"] for p in ("Figure", "Table")
                   if f"figure:{p} {fid}" in N]
        if not targets:
            continue
        rid = f"reading:{ent['ids'][0]}#{i}"
        N[rid] = Node(id=rid, kind="FIGURE_READING", section="",
                      text=ent["body"][:4000], pieces=[f"heading={ent['head']}"])
        made["FIGURE_READING"] += 1
        for t in targets:
            E.append(Edge(src=t, rel="HAS_READING", dst=rid, why="visual reading"))
        for j, b in enumerate(ent["bullets"]):
            m = _TAG.search(b)
            tag = m.group(1) if m else "NOTE"
            fid = f"finding:{ent['ids'][0]}#{i}.{j}"
            N[fid] = Node(id=fid, kind=f"FIGURE_{tag}", section="",
                          text=b[:2000], authority=tag)
            made[f"FIGURE_{tag}"] += 1
            for t in targets:
                E.append(Edge(src=t, rel="HAS_FINDING", dst=fid,
                              why=f"{tag} from the figure pass"))
    return made


# --------------------------------------------------------------------------- #
# 4. computable rules and 5. rulings                                          #
# --------------------------------------------------------------------------- #
def attach_rules(N: dict, E: list, rules_path: Path) -> Counter:
    made: Counter = Counter()
    for r in json.loads(Path(rules_path).read_text()):
        rid = f"rule:{r['id']}"
        N[rid] = Node(id=rid, kind="COMPUTABLE_RULE", section="", authority="RULE",
                      text=json.dumps({k: v for k, v in r.items() if k != "source"},
                                      ensure_ascii=False),
                      pieces=[f"kind={r['kind']}"] + [f"source={s}" for s in r["source"]])
        made["COMPUTABLE_RULE"] += 1
        for s in r["source"]:
            if f"figure:{s}" in N:
                E.append(Edge(src=rid, rel="DERIVED_FROM", dst=f"figure:{s}",
                              why="read from the artwork or table"))
        for n in ("1", "2", "5"):
            if f"ruling:{n}" in r.get("resolver", "") and f"ruling:{n}" in N:
                E.append(Edge(src=rid, rel="RESOLVED_BY", dst=f"ruling:{n}",
                              why="engineer ruling closes the gap"))
    return made


def attach_rulings(N: dict, E: list, reading_log: Path) -> Counter:
    made: Counter = Counter()
    if not Path(reading_log).exists():
        return made
    text = Path(reading_log).read_text()
    confirmed = {
        "1": ["figure:Figure 3B-15", "figure:Table 6B-4", "figure:Table 6B-2"],
        "2": ["figure:Table 6B-4", "figure:Table 6B-3"],
        "4": ["figure:Figure 2G-17", "figure:Figure 2G-19", "figure:Figure 2G-6",
              "figure:Figure 2G-5", "figure:Figure 2F-8"],
        "5": ["figure:Figure 3C-1", "figure:Figure 3C-2"],
        "6": ["figure:Figure 2D-37", "figure:Figure 2I-8", "figure:Figure 7B-1",
              "figure:Figure 2E-14"],
    }
    for block in re.split(r"\n## (?=Ruling \d)", text):
        if not block.startswith("Ruling "):
            continue
        num = re.match(r"Ruling (\d+)", block).group(1)
        rid = f"ruling:{num}"
        N[rid] = Node(id=rid, kind="ENGINEER_RULING", section="", authority="RULING",
                      text=block.split("\n", 1)[1].strip()[:3000],
                      pieces=[f"title={block.splitlines()[0]}"])
        made["ENGINEER_RULING"] += 1
        for t in confirmed.get(num, []):
            if t in N:
                E.append(Edge(src=rid, rel="CONFIRMED_BY", dst=t,
                              why="figure or table evidence"))
    return made


# --------------------------------------------------------------------------- #
# driver                                                                      #
# --------------------------------------------------------------------------- #
def attach_notices(N: dict, E: list) -> Counter:
    """Corrections and open questions: things the pass established that are
    not rules. An open question is stored as a question, never as a fact."""
    made: Counter = Counter()
    cid = "correction:M1-7"
    N[cid] = Node(id=cid, kind="DATA_CORRECTION", section="2D.34",
                  authority="CORRECTION",
                  text="Forest Route sign is M1-7 (brown with yellow legend), not M1-1. "
                       "The text-layer extraction recorded M1-1, the Interstate shield. "
                       "Corrected from Figure 2D-4.")
    made["DATA_CORRECTION"] += 1
    if "figure:Figure 2D-4" in N:
        E.append(Edge(src=cid, rel="CORRECTS_FROM", dst="figure:Figure 2D-4",
                      why="read from the figure"))

    oid = "open:unnamed-lane-arrow-mark"
    N[oid] = Node(id=oid, kind="OPEN_ITEM", section="", authority="OPEN",
                  text="An optional small filled mark at the TAIL of the left-most lane "
                       "arrow, labelled 'optional for left-most lane'. Appears on the R3-8 "
                       "lane-control signs, the roundabout arrow options, the two-lane "
                       "roundabout alternatives, and as a PAVEMENT MARKING on the "
                       "curved-stem arrows. Shape and placement are characterised; the "
                       "Manual never states what it represents. Not recorded as a fact.")
    made["OPEN_ITEM"] += 1
    for t in ("figure:Figure 2B-4", "figure:Figure 2B-5",
              "figure:Figure 2B-23", "figure:Figure 3B-21"):
        if t in N:
            E.append(Edge(src=oid, rel="OBSERVED_IN", dst=t,
                          why="appearance of the unnamed mark"))
    return made


def enrich(N: dict, E: list, C: list, pdf: Path,
           figure_log: Path = DEFAULT_FIGURE_LOG,
           rules: Path = DEFAULT_RULES,
           reading_log: Path = DEFAULT_READING_LOG,
           verbose: bool = True) -> Counter:
    """Add every layer, in order. Safe to run twice: nodes are keyed."""
    made: Counter = Counter()
    caps = extract_captions(pdf)
    if verbose:
        print(f"  captions      : {len(caps['figures'])} figures, "
              f"{len(caps['tables'])} tables")
    made += add_reference_layer(N, E, C, caps)
    made += attach_rulings(N, E, reading_log)          # before rules, which link to them
    if Path(figure_log).exists():
        entries = parse_figure_log(figure_log)
        if verbose:
            print(f"  figure log    : {len(entries)} entries")
        made += attach_readings(N, E, entries)
    if Path(rules).exists():
        made += attach_rules(N, E, rules)
    made += attach_notices(N, E)
    return made


def resolution(N: dict, E: list) -> Tuple[int, int]:
    ok = sum(1 for e in E if str(e.dst) in N and str(e.src) in N)
    return ok, len(E)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", required=True, type=Path, help="the MUTCD PDF")
    ap.add_argument("--in", dest="src", required=True, type=Path,
                    help="graph from graph_links.build()")
    ap.add_argument("--out", required=True, type=Path, help="where to write the full graph")
    ap.add_argument("--figure-log", type=Path, default=DEFAULT_FIGURE_LOG)
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--reading-log", type=Path, default=DEFAULT_READING_LOG)
    a = ap.parse_args(argv)

    N, E, C = pickle.load(open(a.src, "rb"))
    before_n, before_e = len(N), len(E)
    ok0, tot0 = resolution(N, E)
    print(f"in  : {before_n} nodes, {before_e} edges, "
          f"{100 * ok0 / max(1, tot0):.1f}% of edges resolve")

    made = enrich(N, E, C, a.pdf, a.figure_log, a.rules, a.reading_log)
    for kind, n in made.most_common():
        print(f"  + {kind}: {n}")

    ok1, tot1 = resolution(N, E)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump((N, E, C), open(a.out, "wb"))
    print(f"out : {len(N)} nodes, {len(E)} edges, "
          f"{100 * ok1 / max(1, tot1):.1f}% of edges resolve")
    print(f"written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
