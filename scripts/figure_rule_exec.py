"""Execute the figure-derived rules and return a checkable certificate.

Each answer carries: the rule, the figure or table it was read from, the inputs,
the steps taken, and any engineer ruling that had to be applied. An answer with
no certificate is not an answer.
"""
from __future__ import annotations
import argparse, ast, json, os, sys, operator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# The repo root — the folder holding mrag/, scripts/, tests/ — worked out from
# this file's own location, so this runs from any checkout with no editing.
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def default_rules_path() -> Path:
    """MUTCD_FIGURE_RULES if set, else data/mutcd/figure_rules.json in the repo.

    `figure_rules.json` is committed data, not a build artefact, so it sits in
    the repo beside the reading logs it was derived from.
    """
    env = os.environ.get("MUTCD_FIGURE_RULES")
    if env:
        return Path(env)
    return REPO / "data" / "mutcd" / "figure_rules.json"

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _eval(node, env):
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise KeyError(f"no value supplied for {node.id}")
        return env[node.id]
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left, env), _eval(node.right, env))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand, env))
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


def evaluate(expr: str, env: Dict[str, float]) -> float:
    return _eval(ast.parse(expr, mode='eval'), env)


@dataclass
class Certificate:
    question: str
    rule: str
    source: List[str]
    inputs: Dict[str, Any]
    steps: List[str] = field(default_factory=list)
    rulings_applied: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    unit: str = ""
    abstained: bool = False
    reason: str = ""

    def render(self) -> str:
        out = [f"Q: {self.question}"]
        if self.abstained:
            out.append(f"ABSTAIN — {self.reason}")
        else:
            out.append(f"A: {self.result} {self.unit}".rstrip())
        out.append(f"   rule   : {self.rule}")
        out.append(f"   source : {', '.join(self.source)}")
        out.append(f"   inputs : {self.inputs}")
        for s in self.steps:
            out.append(f"   step   : {s}")
        for r in self.rulings_applied:
            out.append(f"   ruling : {r}")
        return "\n".join(out)


class RuleBook:
    def __init__(self, path: Optional[Path] = None):
        path = Path(path) if path else default_rules_path()
        if not path.exists():
            raise SystemExit(
                f"figure_rules.json not found at {path}\n"
                "Pass --rules, or set MUTCD_FIGURE_RULES, or put the file at "
                "data/mutcd/figure_rules.json in the repo.")
        self.path = path
        self.rules = {r['id']: r for r in json.loads(path.read_text())}

    # ---- Ruling 1: which speed to use when a provision names several -------
    @staticmethod
    def resolve_speed(named: Dict[str, float], cert: Certificate) -> float:
        if not named:
            raise KeyError("no speed supplied")
        if len(named) == 1:
            return next(iter(named.values()))
        chosen = max(named.values())
        which = [k for k, v in named.items() if v == chosen][0]
        cert.steps.append(
            f"provision names {len(named)} speeds {named}; taking the maximum ({which}={chosen})")
        cert.rulings_applied.append("Ruling 1 — take the maximum of the speeds the provision names")
        return chosen

    # ---- taper length -----------------------------------------------------
    def taper_length(self, W: float, speeds: Dict[str, float],
                     taper_type: str = 'merging') -> Certificate:
        r = self.rules['TAPER_LENGTH']
        c = Certificate(question=f"taper length, {taper_type} taper, offset {W} ft, speeds {speeds}",
                        rule='TAPER_LENGTH', source=r['source'],
                        inputs={'W': W, 'speeds': speeds, 'taper_type': taper_type}, unit='ft')
        S = self.resolve_speed(speeds, c)
        if S <= 40:
            expr, why = r['cases'][0]['expr'], "S <= 40 -> L = W*S^2/60"
        elif S >= 45:
            expr, why = r['cases'][1]['expr'], "S >= 45 -> L = W*S"
        else:
            expr, why = r['cases'][0]['expr'], f"S={S} falls in the 41-44 gap; {r['resolver']}"
            c.rulings_applied.append("Ruling 2 — below 45 use the '40 or less' row, with actual S")
        c.steps.append(why)
        L = evaluate(expr, {'W': W, 'S': S})
        c.steps.append(f"L = {L:.1f} ft")
        tt = self.rules['TAPER_TYPE_LENGTH']
        row = next((x for x in tt['rows'] if x['type'] == taper_type), None)
        if row is None:
            c.abstained = True
            c.reason = f"no taper type '{taper_type}' in Table 6B-3"
            return c
        c.source = list(dict.fromkeys(r['source'] + tt['source']))
        if row['rel'] == 'min..max':
            lo, hi = row['value'].split('..')
            c.result = f"{lo}-{hi}"
            c.steps.append(f"{taper_type} taper is a fixed {lo}-{hi} ft, independent of L")
        else:
            need = evaluate(row['value'], {'L': L})
            c.result = round(need, 1)
            c.steps.append(f"{taper_type} taper = {row['value']} = {need:.1f} ft ({row['rel']})")
        return c

    # ---- bicycle buffer chevrons -----------------------------------------
    def buffer_chevrons(self, width_ft: float, facility: str) -> Certificate:
        r = self.rules['BIKE_BUFFER_MARKING_THRESHOLD']
        c = Certificate(question=f"chevron markings for a {width_ft} ft buffer on a {facility} bicycle lane",
                        rule='BIKE_BUFFER_MARKING_THRESHOLD', source=r['source'],
                        inputs={'buffer_ft': width_ft, 'facility': facility})
        for row in r['rows']:
            if row['facility'] != facility:
                continue
            cond = row['when']
            ok = ((cond.startswith('>') and not cond.startswith('>=') and width_ft > float(cond[1:]))
                  or (cond.startswith('>=') and width_ft >= float(cond[2:]))
                  or (cond.startswith('<') and width_ft < float(cond[1:]))
                  or ('to' in cond and float(cond.split('to')[0]) <= width_ft <= float(cond.split('to')[1])))
            if ok:
                c.result = row['rule']
                c.steps.append(f"{facility} lane, buffer {width_ft} ft satisfies '{cond}'")
                return c
        c.abstained = True
        c.reason = f"no row in Figure 9E-6/9E-7 covers a {width_ft} ft buffer on a {facility} lane"
        return c

    # ---- signal mounting height ------------------------------------------
    def signal_height(self, d_ft: float) -> Certificate:
        r = self.rules['SIGNAL_MOUNTING_HEIGHT_40_TO_53']
        c = Certificate(question=f"maximum signal mounting height at {d_ft} ft from the stop line",
                        rule='SIGNAL_MOUNTING_HEIGHT_40_TO_53', source=r['source'],
                        inputs={'d': d_ft}, unit='ft')
        lo, hi = r['domain']
        if not (lo <= d_ft <= hi):
            c.abstained = True
            c.reason = f"Figure 4D-3 only covers {lo}-{hi} ft from the stop line"
            return c
        h = evaluate(r['expr'], {'d': d_ft})
        c.steps.append(f"{r['expr']} with d={d_ft}")
        c.result = round(h, 2)
        return c

    # ---- warrant floor ----------------------------------------------------
    def warrant_floor(self, warrant: str, lanes: str = 'minor_1_lane') -> Certificate:
        r = self.rules['WARRANT_FLOORS']
        c = Certificate(question=f"lower threshold volume for Warrant {warrant} ({lanes})",
                        rule='WARRANT_FLOORS', source=r['source'],
                        inputs={'warrant': warrant, 'lanes': lanes})
        for row in r['rows']:
            if row['warrant'].startswith(warrant):
                if lanes in row:
                    c.result = row[lanes]
                    c.unit = row['unit']
                    c.steps.append(f"floor read from the curve note on {row['warrant']}")
                    return c
                c.abstained = True
                c.reason = f"'{lanes}' is not a column of the {row['warrant']} curve"
                return c
        c.abstained = True
        c.reason = f"no warrant matching '{warrant}'"
        return c


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--rules', type=Path, default=None,
                    help='figure_rules.json (default: data/mutcd/figure_rules.json)')
    args = ap.parse_args()
    rb = RuleBook(args.rules)
    tests = [
        rb.taper_length(12, {'posted': 45, '85th': 50}, 'merging'),
        rb.taper_length(12, {'posted': 42}, 'merging'),
        rb.taper_length(11, {'posted': 35}, 'shifting'),
        rb.taper_length(11, {'posted': 60}, 'one-lane two-way'),
        rb.buffer_chevrons(2.5, 'buffer-separated'),
        rb.buffer_chevrons(2.5, 'separated'),
        rb.buffer_chevrons(1.5, 'buffer-separated'),
        rb.signal_height(47),
        rb.signal_height(60),
        rb.warrant_floor('4 pedestrian four-hour', 'slow_crossing'),
    ]
    for t in tests:
        print(t.render()); print()
