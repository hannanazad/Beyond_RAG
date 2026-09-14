"""Machine-readable table content — what the calculator and symbolic verifiers read.

WHY A SCHEMA RATHER THAN JUST TEXT
----------------------------------
A deterministic calculator (S3.3) cannot work from a picture or from a
sentence. It needs the value, what the value MEANS (which column, which row),
its unit, and every condition attached to it. The last part is the one that
bites: Table 6B-4's formulas are unusable without the key defining L, W and S,
and Table 2C-3's "N/A" means "no distance is provided, see note 5", which is a
different fact from "—" meaning the combination does not arise.

TEXT TABLES ARE INCLUDED TOO
----------------------------
A table of words carries no arithmetic, but it routes to one that does: a
classification in a word table decides which row of a numeric table applies.
Skipping them would break the chain before the calculator is ever reached.

PROVENANCE
----------
Every table carries its id, sheet, page and crop file, and links to the note
chunks already in the knowledge graph, so a certificate's evidence points at
the same objects retrieval returns. `verified` records whether a human has
checked the transcription against the crop: a model reading numbers off an
image is exactly the step VINE is built to distrust, so the flag is false
until someone says otherwise, and the calculator can be told to refuse
unverified tables.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = 1

# How a cell that is not a plain value should be read.
MISSING_KINDS = {
    "not_applicable",   # "N/A" — the combination exists but no value is given
    "none",             # "—" / "-" — the combination does not arise
    "blank",            # genuinely empty cell
}


COMPARATORS = {"=", ">=", "<=", ">", "<"}


@dataclass
class Quantity:
    """One named, comparable quantity inside a cell.

    Needed because MUTCD cells routinely carry MORE THAN ONE number:
    Table 2A-5 gives "W >= 250; G >= 25" (legend and background
    retroreflectivity in one cell) and Table 2B-1 gives "30 x 30" (width and
    height). Flattening those to a single number loses half the requirement,
    and flattening them to text loses all of it.
    """
    name: str                      # "W", "G", "width", "height"
    value: float
    unit: Optional[str] = None
    comparator: str = "="          # = | >= | <= | > | <

    def satisfied_by(self, measured: float) -> bool:
        c, v = self.comparator, self.value
        return {"=": measured == v, ">=": measured >= v, "<=": measured <= v,
                ">": measured > v, "<": measured < v}[c]


@dataclass
class Value:
    """A cell's machine-readable content. `text` is always the verbatim cell.

    Exactly one of the interpretations is normally set:
      number   a quantity, with its unit
      range    a band, as used by row keys ("40 mph or less", "45-55 mph")
      formula  an expression over the table's variables
      missing  one of MISSING_KINDS
      (none)   a plain word or phrase; `text` is the whole content
    """
    text: str
    number: Optional[float] = None
    unit: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    min_inclusive: bool = True
    max_inclusive: bool = True
    formula: Optional[str] = None
    missing: Optional[str] = None
    quantities: List[Quantity] = field(default_factory=list)
    footnotes: List[str] = field(default_factory=list)   # markers, e.g. ["5"]

    def quantity(self, name: str) -> Optional[Quantity]:
        return next((q for q in self.quantities if q.name == name), None)

    def is_numeric(self) -> bool:
        return (self.number is not None or self.minimum is not None
                or self.maximum is not None or bool(self.quantities))

    def contains(self, x: float) -> bool:
        """Does a measured quantity fall in this cell's range?"""
        if self.number is not None:
            return float(x) == self.number
        lo, hi = self.minimum, self.maximum
        if lo is not None and (x < lo or (x == lo and not self.min_inclusive)):
            return False
        if hi is not None and (x > hi or (x == hi and not self.max_inclusive)):
            return False
        return lo is not None or hi is not None


@dataclass
class Footnote:
    marker: str                      # "1", "a", "*", "where"
    text: str
    chunk_id: Optional[str] = None   # the TBLNOTE chunk already in the graph
    applies_to: str = "table"        # table | column:<i> | row:<i> | cell


@dataclass
class Table:
    table_id: str                    # "Table 6B-4"
    page_pdf: int
    column_labels: List[str]
    rows: List[List[Value]]          # data rows only; headers live in column_labels
    sheet: Optional[int] = None
    sheet_of: Optional[int] = None
    page_printed: str = ""
    title: str = ""
    crop_file: str = ""
    kind: str = "numeric"            # numeric | text | mixed | formula
    row_key_columns: List[int] = field(default_factory=lambda: [0])
    footnotes: List[Footnote] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)   # {"L": "taper length in feet"}
    note_chunk_ids: List[str] = field(default_factory=list)
    verified: bool = False
    source: str = ""
    schema_version: int = SCHEMA_VERSION

    # ---- lookup -------------------------------------------------------
    def column(self, label_fragment: str) -> Optional[int]:
        frag = label_fragment.strip().lower()
        for i, lab in enumerate(self.column_labels):
            if frag in lab.lower():
                return i
        return None

    def lookup(self, key: float, column: int) -> Optional[Value]:
        """The cell in `column` of the row whose key range contains `key`.

        This is the calculator's entry point: "stopping sight distance at
        37 mph" is a row-key range lookup, not an exact match.
        """
        for row in self.rows:
            for kc in self.row_key_columns:
                if kc < len(row) and row[kc].contains(key):
                    return row[column] if column < len(row) else None
        return None

    def footnote(self, marker: str) -> Optional[Footnote]:
        return next((f for f in self.footnotes if f.marker == str(marker)), None)

    def conditions_on(self, value: Value) -> List[Footnote]:
        """Every note attached to a cell, plus every table-wide note.

        The calculator must surface these with the number. A taper length
        without the key defining L, W and S is a number with no meaning.
        """
        out = [f for f in self.footnotes if f.applies_to == "table"]
        for m in value.footnotes:
            f = self.footnote(m)
            if f and f not in out:
                out.append(f)
        return out

    # ---- serialisation -------------------------------------------------
    def formula_variables_missing(self) -> List[str]:
        """Variables used by a formula cell with no entry in `variables`.

        Table 6B-4 is the case: L = WS^2/60 is meaningless without the key,
        and the key lives in a footnote rather than in the grid.
        """
        used = set()
        for row in self.rows:
            for cell in row:
                if cell.formula:
                    used |= set(re.findall(r"\b([A-Z])\b", cell.formula))
        return sorted(used - set(self.variables))

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["rows"] = [[_trim(asdict(v)) for v in row] for row in self.rows]
        for ri, row in enumerate(self.rows):
            for ci, v in enumerate(row):
                if v.quantities:
                    d["rows"][ri][ci]["quantities"] = [asdict(q) for q in v.quantities]
        d["footnotes"] = [asdict(f) for f in self.footnotes]
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Table":
        rows = []
        for row in d.get("rows", []):
            cells = []
            for cell in row:
                kw = {k: v for k, v in cell.items()
                      if k in Value.__annotations__ and k != "quantities"}
                kw["quantities"] = [Quantity(**q) for q in cell.get("quantities", [])]
                cells.append(Value(**kw))
            rows.append(cells)
        fns = [Footnote(**{k: v for k, v in f.items() if k in Footnote.__annotations__})
               for f in d.get("footnotes", [])]
        kw = {k: v for k, v in d.items()
              if k in Table.__annotations__ and k not in ("rows", "footnotes")}
        return Table(rows=rows, footnotes=fns, **kw)


def _trim(d: Dict[str, Any]) -> Dict[str, Any]:
    """Drop fields left at their default, so a file stays readable."""
    defaults = {"number": None, "unit": None, "minimum": None, "maximum": None,
                "min_inclusive": True, "max_inclusive": True, "formula": None,
                "missing": None, "footnotes": [], "quantities": []}
    return {k: v for k, v in d.items() if k not in defaults or v != defaults[k]}


# --------------------------------------------------------------------------- #
# File I/O — one JSON object per line, same as chunks.jsonl and figures.jsonl
# --------------------------------------------------------------------------- #
def load(path: Path) -> List[Table]:
    return [Table.from_dict(json.loads(line))
            for line in Path(path).read_text().splitlines() if line.strip()]


def save(tables: Iterable[Table], path: Path) -> None:
    Path(path).write_text(
        "\n".join(json.dumps(t.as_dict(), ensure_ascii=False) for t in tables) + "\n")


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
_NUMBERISH = re.compile(r"^-?\d[\d,]*\.?\d*$")


def validate(tables: List[Table], crops: Optional[List[dict]] = None,
             kg=None) -> List[str]:
    """Structural problems, as a list of messages. Empty means it is usable.

    Does NOT check that a transcribed number matches the crop — no code can.
    That is what `verified` is for.
    """
    problems: List[str] = []
    seen = set()
    known = {}
    if crops:
        for c in crops:
            if c.get("kind") == "Table":
                known.setdefault(c["figure_id"], []).append(c.get("sheet"))

    for t in tables:
        where = f"{t.table_id}" + (f" sheet {t.sheet}" if t.sheet else "")
        key = (t.table_id, t.sheet)
        if key in seen:
            problems.append(f"{where}: duplicate entry")
        seen.add(key)

        if known and t.table_id not in known:
            problems.append(f"{where}: not a table in figures.jsonl")
        elif known and t.sheet not in known[t.table_id]:
            problems.append(f"{where}: sheet {t.sheet!r} not among "
                            f"{known[t.table_id]} in figures.jsonl")

        if not t.column_labels:
            problems.append(f"{where}: no column labels")
        if not t.rows:
            problems.append(f"{where}: no data rows")

        n = len(t.column_labels)
        for i, row in enumerate(t.rows):
            if len(row) != n:
                problems.append(f"{where}: row {i} has {len(row)} cells, "
                                f"{n} column labels")
        for kc in t.row_key_columns:
            if kc >= n:
                problems.append(f"{where}: row_key_column {kc} is beyond "
                                f"{n} columns")

        markers = {f.marker for f in t.footnotes}
        dupes = [m for m in markers if sum(1 for f in t.footnotes if f.marker == m) > 1]
        if dupes:
            problems.append(f"{where}: duplicate footnote markers {sorted(dupes)}")
        for i, row in enumerate(t.rows):
            for j, cell in enumerate(row):
                for m in cell.footnotes:
                    if m not in markers:
                        problems.append(f"{where}: row {i} col {j} cites "
                                        f"footnote {m!r} which is not defined")
                for q in cell.quantities:
                    if q.comparator not in COMPARATORS:
                        problems.append(f"{where}: row {i} col {j} quantity "
                                        f"{q.name!r} has comparator {q.comparator!r}")
                names = [q.name for q in cell.quantities]
                if len(names) != len(set(names)):
                    problems.append(f"{where}: row {i} col {j} repeats a quantity name")
                if cell.missing and cell.missing not in MISSING_KINDS:
                    problems.append(f"{where}: row {i} col {j} missing="
                                    f"{cell.missing!r} not in {sorted(MISSING_KINDS)}")
                if cell.number is not None and cell.minimum is not None:
                    problems.append(f"{where}: row {i} col {j} is both a "
                                    f"number and a range")
                if (cell.minimum is not None and cell.maximum is not None
                        and cell.minimum > cell.maximum):
                    problems.append(f"{where}: row {i} col {j} has minimum "
                                    f"above maximum")
                # a bare number left as text is the commonest transcription slip
                if (cell.number is None and cell.minimum is None and not cell.missing
                        and not cell.formula and not cell.quantities
                        and _NUMBERISH.match(cell.text.strip())):
                    problems.append(f"{where}: row {i} col {j} text {cell.text!r} "
                                    f"looks numeric but has no number")

        # units should be consistent down a column
        for ci in range(n):
            units = {row[ci].unit for row in t.rows
                     if ci < len(row) and row[ci].unit}
            if len(units) > 1:
                problems.append(f"{where}: column {ci} "
                                f"({t.column_labels[ci][:30]!r}) mixes units {sorted(units)}")

        if t.formula_variables_missing():
            problems.append(f"{where}: formula uses {t.formula_variables_missing()} "
                            f"with no entry in `variables`")

        if kg is not None:
            for cid in t.note_chunk_ids:
                if not kg.g.has_node(f"chunk:{cid}"):
                    problems.append(f"{where}: note_chunk_id {cid} is not in the graph")
    return problems
