"""The deterministic calculator — S3.3, and Section 5 of the project handover.

    "generative models are used where interpretation is necessary, while
     deterministic or specialized operators are preferred whenever the
     obligation admits a more constrained verification mechanism."

WHAT THIS IS FOR
----------------
An obligation such as "the merging taper is at least the length required at
55 mph for a 12 foot offset" is arithmetic over a printed table. Asking a
model to read the number off a picture is the exact step VINE exists to
distrust. This verifier returns a number it did not invent: it came out of
`mutcd_tables.jsonl`, which a human checked against the crop.

THE RULE THAT MATTERS MOST
--------------------------
A value returned WITHOUT its conditions is worse than no value at all, because
it looks finished. Every footnote reaching a cell comes back attached, and
when a condition could change the answer and this verifier cannot settle it,
the status is UNKNOWN. The compiler then raises that condition as its own
obligation. That is the architecture working, not the calculator failing.

WHAT IT NEVER DOES
------------------
Guess a missing input. Apply a default. Trust an unverified table. Decide a
condition that is not arithmetic. Every one of those returns UNKNOWN.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .certificate import (Authority, Certificate, CertificateStore, Evidence,
                          Status)
from .network import Operation
from .table_data import Footnote, Table, Value

__all__ = ["make_calculator", "evaluate_formula", "extract_footnote_formulas",
           "classify_condition", "ConditionKind", "FormulaError"]


# --------------------------------------------------------------------------- #
# 1. A restricted expression evaluator
# --------------------------------------------------------------------------- #
class FormulaError(ValueError):
    """The expression could not be evaluated safely or at all."""


_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS: Dict[str, Callable[..., float]] = {
    "sqrt": math.sqrt, "abs": abs, "min": min, "max": max,
    "round": round, "floor": math.floor, "ceil": math.ceil,
}


def evaluate_formula(expr: str, values: Dict[str, float]) -> float:
    """Evaluate `expr` over `values`. No `eval`, no names but the ones given.

    The handover is explicit that free text must never reach `eval`. The
    expressions here come out of a transcription file, which is checked, but
    a file is still data and data is not code. Only arithmetic, a short list
    of functions, and the variables supplied are reachable.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"cannot parse {expr!r}: {e}") from e

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise FormulaError(f"{node.value!r} is not a number")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in values:
                raise FormulaError(f"no value for variable {node.id!r}")
            return float(values[node.id])
        if isinstance(node, ast.BinOp):
            fn = _BIN_OPS.get(type(node.op))
            if fn is None:
                raise FormulaError(f"operator {type(node.op).__name__} not allowed")
            return float(fn(walk(node.left), walk(node.right)))
        if isinstance(node, ast.UnaryOp):
            fn = _UNARY_OPS.get(type(node.op))
            if fn is None:
                raise FormulaError(f"operator {type(node.op).__name__} not allowed")
            return float(fn(walk(node.operand)))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
                raise FormulaError("only sqrt/abs/min/max/round/floor/ceil may be called")
            if node.keywords:
                raise FormulaError("keyword arguments are not allowed")
            return float(_FUNCS[node.func.id](*[walk(a) for a in node.args]))
        raise FormulaError(f"{type(node).__name__} is not allowed in a formula")

    result = walk(tree)
    if not math.isfinite(result):
        raise FormulaError(f"{expr!r} did not produce a finite number")
    return result


def formula_variables(expr: str) -> List[str]:
    """Names the expression reads, ignoring function names."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return []
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return sorted({n.id for n in ast.walk(tree)
                   if isinstance(n, ast.Name)} - called)


# --------------------------------------------------------------------------- #
# 2. Formulas that live in a footnote rather than in a cell
# --------------------------------------------------------------------------- #
# Table 3G-1 Note 5 prints "...computed from the formula S=3*sqrt(R-50)". The
# grid holds only rounded sample radii, so a request at R=450 finds no row.
# The manual supplies the exact rule and it is sitting in the note; a
# calculator that reads `cell.formula` only would abstain with the answer in
# front of it.
_FOOTNOTE_FORMULA_RE = re.compile(
    r"\b([A-Z])\s*=\s*([0-9A-Za-z_+\-*/^(). ]{2,80}?)(?=[.;,]\s|[.;,]?$)")


def extract_footnote_formulas(text: str) -> List[Tuple[str, str]]:
    """(variable, expression) pairs stated in a footnote, in reading order.

    A "where L = taper length in feet" key is NOT a formula and is rejected:
    the right-hand side has to be arithmetic, not prose.
    """
    out: List[Tuple[str, str]] = []
    for m in _FOOTNOTE_FORMULA_RE.finditer(text):
        var, rhs = m.group(1), m.group(2).strip()
        expr = rhs.replace("^", "**")
        if not re.search(r"[0-9]", expr):
            continue                       # "S = spacing" — a name, not a rule
        if re.search(r"[A-Za-z]{3,}", re.sub(r"\bsqrt\b", "", expr)):
            continue                       # prose: "L = taper length in feet"
        try:
            ast.parse(expr, mode="eval")
        except SyntaxError:
            continue
        out.append((var, expr))
    return out


# --------------------------------------------------------------------------- #
# 3. What a footnote DOES, which decides whether a value may be returned
# --------------------------------------------------------------------------- #
class ConditionKind(str, Enum):
    """Handover S5.3: many notes are not arithmetic, and the calculator must
    not decide them. It must still know which ones would change the answer."""
    KEY = "key"                    # defines the table's variables; discharged here
    FORMULA = "formula"            # states a computation; discharged here
    PRESENTATION = "presentation"  # units, rounding, layout; changes nothing
    BOUND = "bound"                # a min/max on the answer; checkable
    ROUTING = "routing"            # the answer is in ANOTHER table
    CONDITIONAL = "conditional"    # a scope or precondition, in words
    UNRECOGNISED = "unrecognised"  # unclassified, therefore treated as blocking


_TABLE_REF_RE = re.compile(
    r"\bTables?\s+((?:\d+[A-Z]-\d+[A-Za-z]?)"
    r"(?:\s*(?:,|,?\s*or|,?\s*and)\s*\d+[A-Z]-\d+[A-Za-z]?)*)", re.I)
_PRESENTATION_RE = re.compile(
    r"\b(are shown in|shown as|dimensions are|rounded to|expressed in|"
    r"in inches|in millimeters|width x height|see definition)\b", re.I)
# A note about HOW to read the table, not a condition on any value.
# "Spacing for specific radii may be interpolated from table" permits a
# method; it does not restrict when the printed numbers apply.
_METHOD_RE = re.compile(
    r"\b(may be interpolated|interpolated from|are adjusted for|"
    r"have been adjusted|were rounded|are based on|is determined by|"
    r"are determined by)\b", re.I)
_BOUND_RE = re.compile(
    r"\b(minimum|maximum|at least|no less than|not exceed|should not exceed)\b", re.I)
_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")
# NOTE: the numeric phrases are kept OUT of the \b...\b group. "less than 48"
# inside one fails to match, because \b after \d lands between "4" and "8",
# which is not a word boundary. That silently let Table 2A-5 note 3 ("For word
# legend and fine symbol signs measuring less than 48 inches") through as
# unclassified.
_CONDITIONAL_RE = re.compile(
    r"\b(if|when|unless|except|only|provided that|"
    r"may be used|used for|for use on|in an isolated community)\b"
    r"|\b(?:less|greater|more|fewer) than \d"
    r"|\b(?:above|below|exceeds|exceeding|at or above|up to) \d"
    r"|\bmeasuring \d", re.I)
# The manual's house phrasing for "this column applies in these situations":
# "Typical conditions are locations where...", "Applies to approaches with...",
# "Where a larger size is shown...". Checked against all 154 distinct
# footnotes in the data: it matches 7, and every one of the 7 is a real
# condition on when a column or a whole table may be read.
_APPLICABILITY_RE = re.compile(
    r"typical conditions? (are|is)|locations where|\bapplies? (to|when)\b|"
    r"\bis used (for|when)\b|\bwhere a \w+ (size|value)\b", re.I)


def referenced_tables(text: str, exclude: str = "") -> List[str]:
    """Table ids a footnote points at, including plural lists.

    Table 9A-1 Note 2 says "... in Tables 2B-1, 2C-1, 2D-1, or 8B-1". A
    pattern anchored on the singular word "Table" reads one target out of
    four, and the three it drops are the ones that route a bicycle sign to
    the conventional-road sizes.
    """
    out: List[str] = []
    for m in _TABLE_REF_RE.finditer(text):
        for tid in re.findall(r"\d+[A-Z]-\d+[A-Za-z]?", m.group(1)):
            label = f"Table {tid}"
            if label != exclude and label not in out:
                out.append(label)
    return out


def classify_condition(fn: Footnote, table: Table) -> ConditionKind:
    """What kind of thing this note is. Conservative on purpose.

    Anything not positively recognised is UNRECOGNISED and therefore blocks.
    An over-cautious UNKNOWN costs one extra obligation; a value released past
    a condition that governed it is a wrong answer wearing a certificate.
    """
    text = fn.text or ""
    if referenced_tables(text, exclude=table.table_id):
        return ConditionKind.ROUTING
    if extract_footnote_formulas(text):
        return ConditionKind.FORMULA
    # "where L = taper length in feet; W = width of offset in feet; S = ..."
    if table.variables and sum(
            1 for v in table.variables if re.search(rf"\b{re.escape(v)}\s*=", text)) >= 1:
        return ConditionKind.KEY
    # Conditional wording is tested BEFORE method wording, because a note
    # often does both and only one of the two matters. Table 2C-3 footnote 2
    # says what Condition A means -- "locations where the road user must use
    # extra time to adjust speed and change lanes in heavy traffic" -- and
    # then adds that the distances are determined by a formula. Matching the
    # second half first would classify the note as method, discharge it, and
    # release a Condition A distance without anyone having established that
    # Condition A is the applicable column. That judgement is the compiler's,
    # never this verifier's.
    if _CONDITIONAL_RE.search(text) or _APPLICABILITY_RE.search(text):
        return ConditionKind.CONDITIONAL
    # A BOUND is a rule this verifier can actually check, which means it has
    # to name ONE number: "the minimum spacing should be 20 feet". A note
    # carrying several numbers is explaining how a column was derived, not
    # setting a limit on the answer, and treating it as a limit would fail a
    # test that was never stated.
    if _BOUND_RE.search(text) and len(_NUM_RE.findall(text)) == 1:
        return ConditionKind.BOUND
    if _METHOD_RE.search(text) or _PRESENTATION_RE.search(text):
        return ConditionKind.PRESENTATION
    return ConditionKind.UNRECOGNISED


_DISCHARGED_BY_DEFAULT = {ConditionKind.KEY, ConditionKind.FORMULA,
                          ConditionKind.PRESENTATION}


# --------------------------------------------------------------------------- #
# 4. Inputs — from the obligation and from upstream certificates
# --------------------------------------------------------------------------- #
@dataclass
class Measurement:
    value: float
    unit: Optional[str] = None
    source: str = ""            # "claim" | "certificate:<obligation id>"


_UNIT_WORDS = {
    "mph": "mph", "miles per hour": "mph",
    "ft": "ft", "foot": "ft", "feet": "ft",
    "in": "in", "inch": "in", "inches": "in",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "vph": "vph", "veh/h": "vph", "vpd": "vpd", "aadt": "vpd",
    "%": "%", "percent": "%",
}
_NUMBER_UNIT_RE = re.compile(
    r"(-?\d[\d,]*\.?\d*)\s*[-\s]?\s*"
    r"(mph|miles per hour|feet|foot|ft|inches|inch|in|meters|metres|meter|metre|m|"
    r"vph|veh/h|vpd|aadt|percent|%)\b", re.I)
_NAMED_VALUE_RE = re.compile(r"\b([A-Z])\s*=\s*(-?\d[\d,]*\.?\d*)\b")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def measurements_from_claim(claim: str) -> Tuple[Dict[str, Measurement], List[Measurement]]:
    """Named values ("W = 12") and unit-tagged values ("55 mph") in the text."""
    named: Dict[str, Measurement] = {}
    for m in _NAMED_VALUE_RE.finditer(claim):
        named[m.group(1)] = Measurement(_to_float(m.group(2)), None, "claim")
    loose: List[Measurement] = []
    for m in _NUMBER_UNIT_RE.finditer(claim):
        start = m.start()
        # "W = 12 feet" was already captured by name; do not count it twice
        if any(claim[max(0, start - 6):start + 1].rstrip().endswith(str(int(v.value)))
               or re.search(rf"\b{re.escape(k)}\s*=\s*{re.escape(m.group(1))}\b", claim)
               for k, v in named.items()):
            unit = _UNIT_WORDS[m.group(2).lower()]
            for k, v in named.items():
                if v.unit is None and re.search(
                        rf"\b{re.escape(k)}\s*=\s*{re.escape(m.group(1))}\b", claim):
                    named[k] = Measurement(v.value, unit, "claim")
            continue
        loose.append(Measurement(_to_float(m.group(1)),
                                 _UNIT_WORDS[m.group(2).lower()], "claim"))
    return named, loose


def measurements_from_store(store: CertificateStore) -> Dict[str, Measurement]:
    """Values established upstream.

    A certificate may carry `provenance["measurements"]`, either as
    ``{"S": 55}`` or as ``{"S": {"value": 55, "unit": "mph"}}``. Only an
    ESTABLISHED certificate counts: S3.2 is explicit that an UNKNOWN
    establishes nothing, and a FALSE classification is not a measurement.
    """
    out: Dict[str, Measurement] = {}
    for cert in store.all():
        if cert.status is not Status.TRUE:
            continue
        raw = (cert.provenance or {}).get("measurements") or {}
        if not isinstance(raw, dict):
            continue
        for name, val in raw.items():
            try:
                if isinstance(val, dict):
                    out[str(name)] = Measurement(
                        float(val["value"]), val.get("unit"),
                        f"certificate:{cert.obligation_id or cert.verifier}")
                else:
                    out[str(name)] = Measurement(
                        float(val), None,
                        f"certificate:{cert.obligation_id or cert.verifier}")
            except (TypeError, ValueError, KeyError):
                continue
    return out


_UNIT_IN_DESCRIPTION = [
    ("mph", re.compile(r"\bmph\b|miles per hour", re.I)),
    ("ft", re.compile(r"\bfeet\b|\bfoot\b|\bft\b", re.I)),
    ("in", re.compile(r"\binches\b|\binch\b", re.I)),
    ("m", re.compile(r"\bmeters\b|\bmetres\b", re.I)),
    ("vpd", re.compile(r"\baadt\b|vehicles per day", re.I)),
    ("vph", re.compile(r"vehicles per hour|\bvph\b", re.I)),
]


def unit_of_variable(description: str) -> Optional[str]:
    for unit, rx in _UNIT_IN_DESCRIPTION:
        if rx.search(description or ""):
            return unit
    return None


def bind_variables(table: Table, named: Dict[str, Measurement],
                   loose: Sequence[Measurement],
                   wanted: Sequence[str]) -> Tuple[Dict[str, float], List[str], Dict[str, str]]:
    """Fill `wanted` from named values first, then by unique unit match.

    Returns (values, missing, how). A variable that two loose measurements
    could both fill is left MISSING, not guessed: "12 feet" and "10 feet" in
    one sentence do not say which is the offset width.
    """
    values: Dict[str, float] = {}
    how: Dict[str, str] = {}
    missing: List[str] = []
    used: set = set()
    for var in wanted:
        if var in named:
            values[var] = named[var].value
            how[var] = named[var].source
            continue
        unit = unit_of_variable(table.variables.get(var, ""))
        if unit is None:
            missing.append(var)
            continue
        hits = [i for i, m in enumerate(loose)
                if m.unit == unit and i not in used]
        if len(hits) == 1:
            i = hits[0]
            used.add(i)
            values[var] = loose[i].value
            how[var] = f"{loose[i].source} (matched on unit {unit})"
        else:
            missing.append(var)
    return values, missing, how


# --------------------------------------------------------------------------- #
# 5. The verifier
# --------------------------------------------------------------------------- #
def _unknown(op: Operation, reason: str, **extra: Any) -> Certificate:
    prov = {"reason": reason}
    prov.update(extra)
    return Certificate(claim=op.claim, status=Status.UNKNOWN,
                       normative_authority=op.normative_authority,
                       confidence=0.0, verifier="calculator",
                       obligation_id=op.id, provenance=prov)


def _table_ids_from(op: Operation) -> List[str]:
    """Tables the operation points at: the hint first, then the claim text."""
    hinted = [str(h.get("id", "")).strip()
              for h in (op.evidence_hint or [])
              if str(h.get("type", "")).lower() == "table" and h.get("id")]
    if hinted:
        return list(dict.fromkeys(hinted))
    return referenced_tables(op.claim)


def _hint(op: Operation, kind: str) -> Optional[str]:
    for h in (op.evidence_hint or []):
        if str(h.get("type", "")).lower() == kind and h.get("id") is not None:
            return str(h["id"])
    return None


def _discharged_markers(store: CertificateStore) -> set:
    """Conditions an upstream certificate says it settled.

    A certificate may carry `provenance["discharges"] = ["Table 4C-1:c"]`.
    This is how S5.3 closes: the calculator refuses to decide a worded
    condition, the compiler raises it as its own obligation, and the
    certificate that resolves it lets the value through on a later pass.
    """
    out = set()
    for cert in store.all():
        if cert.status is not Status.TRUE:
            continue
        for m in (cert.provenance or {}).get("discharges") or []:
            out.add(str(m))
    return out


def make_calculator(tables: Sequence[Table], kg=None) -> Callable[
        [Operation, CertificateStore], Certificate]:
    """Build the calculator verifier over a loaded table set.

    Plugs straight into ``execute(net, verifiers={"calculator": ...})``.
    """
    by_id: Dict[str, List[Table]] = {}
    for t in tables:
        by_id.setdefault(t.table_id, []).append(t)

    def calculate(op: Operation, store: CertificateStore) -> Certificate:
        # -- 1. which table ------------------------------------------------
        ids = _table_ids_from(op)
        if not ids:
            return _unknown(op, "no table is named by the obligation or its hint")
        if len(ids) > 1:
            return _unknown(op, "the obligation names more than one table; "
                                "the compiler must say which one applies",
                            tables_named=ids)
        table_id = ids[0]
        records = by_id.get(table_id)
        if not records:
            return _unknown(op, f"{table_id} is not in the table data",
                            table=table_id)

        # a table id may hold several records: sheets, or lettered parts
        part = _hint(op, "part")
        sheet = _hint(op, "sheet")
        if part is not None:
            records = [t for t in records if (t.part or "") == part] or records
        if sheet is not None:
            records = [t for t in records if str(t.sheet or "") == str(sheet)] or records

        # -- 2. refuse an unverified table ----------------------------------
        unverified = [t for t in records if not t.verified]
        if unverified:
            return _unknown(op, "the table transcription has not been checked "
                                "against the source; an unchecked number is not "
                                "evidence",
                            table=table_id, verified=False)

        # -- 3. inputs -------------------------------------------------------
        named = dict(measurements_from_store(store))
        claim_named, loose = measurements_from_claim(op.claim)
        named.update(claim_named)           # the obligation's own text wins

        # -- 4. the key ------------------------------------------------------
        attempts: List[str] = []
        for table in records:
            res = _lookup_in(op, table, named, loose, store, attempts)
            if res is not None:
                return res
        return _unknown(op, "no row of the table covers the requested key",
                        table=table_id, detail=attempts)

    # ---------------------------------------------------------------------- #
    def _lookup_in(op: Operation, table: Table, named: Dict[str, Measurement],
                   loose: Sequence[Measurement], store: CertificateStore,
                   attempts: List[str]) -> Optional[Certificate]:
        """Try one record. Returns None if the key does not land in it."""
        key_col = _resolve_key_column(op, table, named, loose)
        if key_col is None:
            attempts.append(f"{table.table_id}: cannot tell which key column "
                            f"{[table.column_labels[k] for k in table.row_key_columns]} "
                            f"the input refers to")
            return None
        col_idx, key = key_col
        target = _resolve_target_column(op, table)
        if target is None:
            attempts.append(f"{table.table_id}: the obligation does not say "
                            f"which column to read")
            return None

        value = table.lookup(key.value, target, key_column=col_idx)
        if value is None:
            alt = _out_of_range(op, table, key, target, named, loose, store)
            if alt is not None:
                return alt
            attempts.append(f"{table.table_id}: key {key.value} is outside "
                            f"every printed band of "
                            f"{table.column_labels[col_idx]!r}")
            return None
        return _certify(op, table, value, key, target, named, loose, store,
                        basis="printed value")

    # ---------------------------------------------------------------------- #
    def _resolve_key_column(op: Operation, table: Table,
                            named: Dict[str, Measurement],
                            loose: Sequence[Measurement]
                            ) -> Optional[Tuple[int, Measurement]]:
        """Which key column, and the measurement that goes into it.

        `Table.lookup` refuses an ambiguous call; this refuses it earlier and
        with the reason. 2C-5 is keyed by BOTH advisory speed and curve
        radius, and a bare number does not say which it is.
        """
        hint = _hint(op, "key_column")
        candidates = table.row_key_columns
        if hint is not None:
            idx = int(hint) if str(hint).isdigit() else table.column(str(hint))
            if idx is None or idx not in candidates:
                return None
            candidates = [idx]

        for idx in candidates:
            units = {row[idx].unit for row in table.rows
                     if idx < len(row) and row[idx].unit}
            unit = next(iter(units)) if len(units) == 1 else None
            # a named value whose letter matches the key column's variable
            for var, m in named.items():
                desc = table.variables.get(var, "")
                if desc and unit and unit_of_variable(desc) == unit:
                    return idx, m
            if unit is not None:
                hits = [m for m in loose if m.unit == unit]
                if len(hits) == 1:
                    return idx, hits[0]
        if len(candidates) == 1 and len(loose) == 1 and not named:
            return candidates[0], loose[0]
        # one key column, and a single named value is the only candidate
        if len(candidates) == 1 and len(named) == 1 and not loose:
            return candidates[0], next(iter(named.values()))
        return None

    def _resolve_target_column(op: Operation, table: Table) -> Optional[int]:
        hint = _hint(op, "column")
        if hint is not None:
            if str(hint).isdigit():
                idx = int(hint)
                return idx if idx < len(table.column_labels) else None
            return table.column(str(hint))
        non_key = [i for i in range(len(table.column_labels))
                   if i not in table.row_key_columns]
        return non_key[0] if len(non_key) == 1 else None

    # ---------------------------------------------------------------------- #
    def _out_of_range(op: Operation, table: Table, key: Measurement, target: int,
                      named: Dict[str, Measurement], loose: Sequence[Measurement],
                      store: CertificateStore) -> Optional[Certificate]:
        """A key outside every printed band.

        Order matters. If the manual states the formula the grid was built
        from, computing it is EXACT and beats interpolating between rounded
        samples. Only when there is no formula and a note permits it do we
        interpolate, and then the certificate says so and carries a lower
        confidence.
        """
        target_var = _column_variable(table, target)
        key_var = _column_variable(table, _index_of_key(table, key))

        for fn in table.footnotes:
            for var, expr in extract_footnote_formulas(fn.text):
                if target_var and var != target_var:
                    continue
                need = formula_variables(expr)
                values: Dict[str, float] = {}
                if key_var and key_var in need:
                    values[key_var] = key.value
                rest = [v for v in need if v not in values]
                more, missing, how = bind_variables(table, named, loose, rest)
                values.update(more)
                if missing:
                    continue
                try:
                    computed = evaluate_formula(expr, values)
                except FormulaError:
                    continue
                return _certify(op, table, None, key, target, named, loose, store,
                                basis=f"formula {var} = {expr} stated in "
                                      f"footnote {fn.marker!r}",
                                computed=computed, confidence=0.9,
                                extra_conditions=[fn])

        if any(re.search(r"interpolat", f.text, re.I) for f in table.footnotes):
            got = _interpolate(table, key, target)
            if got is not None:
                return _certify(op, table, None, key, target, named, loose, store,
                                basis="interpolated between printed rows, which "
                                      "a note permits",
                                computed=got, confidence=0.6)
        return None

    def _index_of_key(table: Table, key: Measurement) -> int:
        for idx in table.row_key_columns:
            units = {row[idx].unit for row in table.rows
                     if idx < len(row) and row[idx].unit}
            if key.unit and key.unit in units:
                return idx
        return table.row_key_columns[0]

    def _column_variable(table: Table, col: int) -> Optional[str]:
        """The single-letter variable a column stands for, e.g. "(S)" -> S."""
        if col is None or col >= len(table.column_labels):
            return None
        m = re.search(r"\(([A-Z])\)", table.column_labels[col])
        if m and m.group(1) in table.variables:
            return m.group(1)
        return None

    def _interpolate(table: Table, key: Measurement, target: int) -> Optional[float]:
        idx = _index_of_key(table, key)
        pts = []
        for row in table.rows:
            if idx >= len(row) or target >= len(row):
                continue
            x, y = row[idx].number, row[target].number
            if x is not None and y is not None:
                pts.append((x, y))
        pts.sort()
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= key.value <= x1 and x1 != x0:
                return y0 + (y1 - y0) * (key.value - x0) / (x1 - x0)
        return None

    # ---------------------------------------------------------------------- #
    def _certify(op: Operation, table: Table, value: Optional[Value],
                 key: Measurement, target: int, named: Dict[str, Measurement],
                 loose: Sequence[Measurement], store: CertificateStore,
                 basis: str, computed: Optional[float] = None,
                 confidence: float = 1.0,
                 extra_conditions: Sequence[Footnote] = ()) -> Certificate:
        """Build the certificate, with every condition attached."""
        provenance: Dict[str, Any] = {
            "table": table.table_id, "basis": basis,
            "key": {"value": key.value, "unit": key.unit, "source": key.source},
            "column": table.column_labels[target] if target < len(table.column_labels) else "",
        }
        if table.part:
            provenance["part"] = table.part
        if table.sheet:
            provenance["sheet"] = table.sheet

        # -- the cell that was found -----------------------------------------
        # A value COMPUTED from a footnote formula has no cell, so
        # `conditions_on` cannot be asked. It is still governed by every
        # table-wide note -- 3G-1's minimum of 20 feet and maximum of 300 feet
        # bind an interpolated spacing exactly as they bind a printed one.
        # Without this the off-grid answer would come back with FEWER
        # conditions than the printed one, which is backwards.
        conditions: List[Footnote] = [f for f in table.footnotes
                                      if f.applies_to == "table"]
        for f in extra_conditions:
            if f not in conditions:
                conditions.append(f)
        if value is not None:
            provenance["cell"] = value.text
            on_cell = table.conditions_on(value)
            conditions = on_cell + [f for f in conditions if f not in on_cell]
            if value.missing:
                # "N/A" and "—" are DIFFERENT facts and neither is a number
                return _unknown(
                    op, {"not_applicable": "the table gives no value for this "
                                           "combination",
                         "none": "this combination does not arise",
                         "blank": "the cell is empty"}[value.missing],
                    table=table.table_id, cell=value.text, missing=value.missing,
                    conditions=[_fn_dict(f) for f in conditions])

        # -- a formula cell needs its variables -------------------------------
        if computed is None and value is not None and value.formula:
            need = formula_variables(value.formula)
            key_var = _column_variable(table, _index_of_key(table, key))
            values: Dict[str, float] = {}
            if key_var and key_var in need:
                values[key_var] = key.value
            rest = [v for v in need if v not in values]
            more, missing, how = bind_variables(table, named, loose, rest)
            values.update(more)
            if missing:
                return _unknown(
                    op, f"the cell gives a formula and {missing} has no value; "
                        f"a missing input is never defaulted",
                    table=table.table_id, formula=value.formula,
                    cell=value.text, needs=need, have=values,
                    variables={v: table.variables.get(v, "") for v in need},
                    conditions=[_fn_dict(f) for f in conditions])
            try:
                computed = evaluate_formula(value.formula, values)
            except FormulaError as e:
                return _unknown(op, f"the formula could not be evaluated: {e}",
                                table=table.table_id, formula=value.formula)
            provenance["formula"] = value.formula
            provenance["inputs"] = {k: values[k] for k in sorted(values)}
            provenance["input_sources"] = how
            provenance["variables"] = {v: table.variables.get(v, "") for v in need}

        if computed is not None:
            provenance["computed"] = computed
        elif value is not None and value.number is not None:
            provenance["value"] = value.number
            provenance["unit"] = value.unit
        elif value is not None and value.quantities:
            provenance["quantities"] = [
                {"name": q.name, "comparator": q.comparator,
                 "value": q.value, "unit": q.unit} for q in value.quantities]
        elif value is not None:
            provenance["text"] = value.text

        # -- conditions -------------------------------------------------------
        discharged_upstream = _discharged_markers(store)
        answer = computed if computed is not None else (
            value.number if value is not None else None)
        blocking: List[Footnote] = []
        classified = []
        for f in conditions:
            kind = classify_condition(f, table)
            marker = f"{table.table_id}:{f.marker}"
            why = ""
            settled = False
            if kind in _DISCHARGED_BY_DEFAULT:
                settled, why = True, "the verifier used it"
            elif marker in discharged_upstream:
                settled, why = True, "settled by an upstream certificate"
            elif kind is ConditionKind.BOUND:
                settled = _bound_respected(f, answer)
                why = ("the answer satisfies it" if settled
                       else "the answer does not satisfy it")
            elif kind is ConditionKind.UNRECOGNISED and f.applies_to == "table":
                # Scope decides. A note on the CELL, its ROW KEY or its COLUMN
                # heading is a condition on THIS value, so an unreadable one
                # must block. A table-wide note applies to every value equally
                # and is usually context -- 107 of the 230 notes in the manual
                # are end-of-table remarks with no reference mark at all. If
                # those blocked, nothing would ever certify and the compiler
                # would be handed an obligation it could not act on. Such a
                # note is still ATTACHED and reported; it is not hidden.
                settled, why = True, ("table-wide context, reported but not "
                                      "treated as a condition on this value")
            classified.append({"marker": f.marker, "kind": kind.value,
                               "scope": f.applies_to, "text": f.text,
                               "chunk_id": f.chunk_id,
                               "discharged": bool(settled), "note": why})
            if not settled:
                blocking.append(f)

        provenance["conditions"] = classified

        evidence = [Evidence("table", table.table_id)]
        for cid in table.note_chunk_ids:
            evidence.append(Evidence("chunk", cid))
        for f in conditions:
            if f.chunk_id and not any(e.id == f.chunk_id for e in evidence):
                evidence.append(Evidence("chunk", f.chunk_id))
        for f in blocking:
            for other in referenced_tables(f.text, exclude=table.table_id):
                if not any(e.id == other for e in evidence):
                    evidence.append(Evidence("table", other))

        if blocking:
            # S5.3: the value is REPORTED but not certified. The condition
            # becomes the compiler's next obligation instead of a silent
            # assumption made here.
            provenance["undischarged"] = [
                {"marker": f.marker, "kind": classify_condition(f, table).value,
                 "text": f.text,
                 "routes_to": referenced_tables(f.text, exclude=table.table_id)}
                for f in blocking]
            return Certificate(
                claim=op.claim, status=Status.UNKNOWN, evidence=evidence,
                normative_authority=op.normative_authority, confidence=0.0,
                verifier="calculator", obligation_id=op.id,
                provenance={**provenance,
                            "reason": "a condition on this value is not "
                                      "arithmetic and was not settled upstream; "
                                      "it must be raised as its own obligation"})

        return Certificate(
            claim=op.claim, status=Status.TRUE, evidence=evidence,
            normative_authority=op.normative_authority,
            confidence=confidence, verifier="calculator", obligation_id=op.id,
            provenance=provenance)

    def _bound_respected(fn: Footnote, answer: Optional[float]) -> bool:
        """A min/max note is settled when the answer actually satisfies it."""
        if answer is None:
            return False
        nums = [float(n.replace(",", ""))
                for n in re.findall(r"-?\d[\d,]*\.?\d*", fn.text)]
        if len(nums) != 1:
            return False
        n = nums[0]
        if re.search(r"not exceed|maximum|no more than", fn.text, re.I):
            return answer <= n
        if re.search(r"minimum|at least|no less than", fn.text, re.I):
            return answer >= n
        return False

    def _fn_dict(f: Footnote) -> Dict[str, Any]:
        return {"marker": f.marker, "text": f.text, "chunk_id": f.chunk_id,
                "applies_to": f.applies_to}

    return calculate
