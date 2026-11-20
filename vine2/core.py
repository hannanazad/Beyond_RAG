"""vine2/core.py -- answer first, then check every statement (no model calls in this file).

Why this exists (the faults of the plan-first VINE, 18-20 Nov 2026):
  1. the plan step chose which provisions mattered, and the answer writer never saw
     the rest (79% of what retrieval found was set aside);
  2. the answer writer could only repeat check results, so it could not explain a rule,
     its condition or its exception;
  3. each check saw one claim and a few pieces of evidence, so it lost the links
     between rules;
  4. a plan that failed left the question with no answer;
  5. two code checkers gave a verdict without comparing anything.

So here the order is reversed:
  - the answer is written first, from ALL the evidence (the writer model; see check.py);
  - the answer is split into numbered statements (`split_statements`);
  - the checker model judges every statement with the whole question, all the evidence
    and the images in view (`checker_prompt`), and may add what the answer is missing;
  - code then checks the checker (`read_reply`): every quote must be found word for word
    in the evidence piece it names (`verify_quote`); written arithmetic is recomputed
    (`arithmetic_checks`); a correction may not bring in a number that no verified quote
    or the question contains, a requirement word (shall, should, may, ...) whose force
    no verified source has, or a provision type its sources are not; a correction that
    turns the main answer or a yes/no round needs two different pieces (over the reply's
    passing corrections that turn something round), and one that turns a requirement
    round needs a limiting word in its quote or two pieces; if a turn of the main answer
    is refused, no turn is applied anywhere, and no yes/no elsewhere may disagree with
    the main answer; an addition may not repeat what is already there, name a provision
    type its sources are not, or contradict the main answer as corrected; the answer's
    citation list is looked up in the evidence (`citation_checks`);
  - the final answer (`assemble`) applies only corrections and additions that pass
    those checks. Everything else is kept as written and marked. A correction that
    fails them is not applied: the statement is kept and marked "disputed".
What this does NOT prove: a quote that is really in the manual can still be the wrong
paragraph for the case. That is why the safeguards above exist, and why the draft and
the final answer should both be graded.
Nothing here knows any benchmark question or answer: the rules are about how the
manual is written (Standard / Guidance / Option / Support, conditions, exceptions,
tables, figures) and about checking text against text.
"""
from __future__ import annotations

import ast
import json
import math
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

GROUP_ORDER = ("Standard", "Guidance", "Option", "Support")
MIN_QUOTE_WORDS = 5            # a quote, all its parts together
MIN_PART_WORDS = 3             # each part of a quote cut with "..."
MAX_ADDITIONS = 6
ANSWER_SECTIONS = re.compile(r"^(direct answer|answer|conclusion|short answer)$", re.I)
CITATION_SECTIONS = re.compile(r"^(citations?|sources?|references?)$", re.I)
REQUIREMENT_WORDS = ("shall", "should", "may", "must", "required", "prohibited", "permitted",
                     "allowed", "mandatory", "recommended", "optional")


def blank(v: Any) -> bool:
    return v is None or str(v).strip() in ("", "None")


# --------------------------------------------------------------------------- #
# 1. The evidence, as the checker sees it, and an index to check quotes against
# --------------------------------------------------------------------------- #
def piece_text(c: Dict[str, Any]) -> str:
    """A piece's words as the writer saw them: a list item with its lead-in sentence."""
    text = str(c.get("text") or "")
    if not blank(c.get("lead_in")):
        text = f"{str(c['lead_in']).strip()} {text}".strip()
    return text


def fid_in_id(fid: str, piece_id: str) -> bool:
    """Is figure/table `fid` ("Table 2Z-1") named in a table-row or reading id
    ("vine:trow:Table 2Z-1#s1r3", "vine:reading:2Z-1#12:Table 2Z-1+Figure 2Z-2")?"""
    return re.search(rf"(?<![0-9A-Za-z-]){re.escape(fid)}(?![0-9A-Za-z])", piece_id) is not None


def evidence_index(entry: Dict[str, Any], attached: Sequence[str] = ()) -> Dict[str, Dict[str, Any]]:
    """id -> {"text", "kind", "section", "ordinal", "title", "figure", "image"} for every
    piece and every listed figure or table. A figure's text is its caption plus the words
    of its table rows and figure readings among the pieces, so a quote from a printed
    table can be found. "image" is True only for a figure whose image was attached
    (`attached`: figure ids), the only case where a value may be read from a picture."""
    idx: Dict[str, Dict[str, Any]] = {}
    for c in entry.get("chunks") or []:
        cid = str(c.get("chunk_id") or "")
        if not cid:
            continue
        idx[cid] = {"text": piece_text(c), "kind": str(c.get("content_type") or "Support"),
                    "section": str(c.get("section_id") or ""), "ordinal": c.get("ordinal"),
                    "title": str(c.get("section_title") or ""), "authority": c.get("authority"),
                    "figure": False, "image": False}
    shown = set(attached)
    for f in entry.get("figures") or []:
        fid = str(f.get("figure_id") or "")
        if not fid:
            continue
        related = [v["text"] for k, v in idx.items() if k.startswith("vine:") and fid_in_id(fid, k)]
        idx[fid] = {"text": "\n".join([str(f.get("caption") or "")] + related),
                    "kind": "Figure" if fid.lower().startswith("figure") else "Table",
                    "section": "", "ordinal": None, "title": str(f.get("caption") or ""),
                    "authority": None, "figure": True, "image": fid in shown}
    return idx


def evidence_block(entry: Dict[str, Any]) -> str:
    """All of the question's evidence, each piece whole and labelled with its id, grouped as
    the writer saw it (Standard, Guidance, Option, Support, then the rest), then the list
    of figures and tables."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for c in entry.get("chunks") or []:
        groups.setdefault(str(c.get("content_type") or "Support"), []).append(c)
    order = list(GROUP_ORDER) + [g for g in groups if g not in GROUP_ORDER]
    out: List[str] = []
    for g in order:
        if not groups.get(g):
            continue
        out.append(f"=== {g} ===")
        for c in groups[g]:
            label = f" ({c['authority']})" if not blank(c.get("authority")) else ""
            ordinal = "?" if blank(c.get("ordinal")) else c.get("ordinal")
            page = "?" if blank(c.get("page_printed")) else c.get("page_printed")
            out.append(f"[{c.get('chunk_id')}] Section {c.get('section_id')} paragraph {ordinal} - "
                       f"{c.get('section_title') or ''} (p.{page}){label}\n{piece_text(c)}")
        out.append("")
    figs = [f for f in entry.get("figures") or [] if f.get("figure_id")]
    if figs:
        out.append("=== Figures and tables in the evidence ===")
        out += [f"[{f['figure_id']}] {f.get('caption') or ''}" for f in figs]
    return "\n".join(out).strip()


_QUOTE_MAP = {"‘": "'", "’": "'", "‛": "'", "′": "'", "“": '"', "”": '"',
              "‟": '"', "″": '"', "–": "-", "—": "-", "−": "-", "‐": "-",
              "‑": "-", "­": "", " ": " ", " ": " ", " ": " ", "×": "x"}


def norm(s: str) -> str:
    """Text for comparing: one kind of quote mark and dash, no soft hyphens, one space,
    lower case."""
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = "".join(_QUOTE_MAP.get(ch, ch) for ch in s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def _parts(quote: str) -> List[str]:
    """A quote's parts: cut at "...", "…", "[...]" or "[…]", without quote marks or the
    punctuation at either end of a part."""
    q = norm(quote).strip(" \"'")
    cut = re.split(r"\s*\[?\s*(?:\.\.\.|…)\s*\]?\s*", q)
    return [x for x in (p.strip(" \"'.,;:") for p in cut) if x]


def _found_in(parts: Sequence[str], text: str) -> bool:
    """All parts in `text`, in order, each starting and ending at a word boundary."""
    t, pos = norm(text), 0
    for p in parts:
        m = re.compile(rf"(?<![a-z0-9])(?<!\d[.,]){re.escape(p)}(?![a-z0-9])(?![.,]\d)").search(t, pos)
        if not m:
            return False
        pos = m.end()
    return True


def verify_quote(quote: str, source_id: str, idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Is `quote` word for word in the evidence piece `source_id`?

    Returns {"verified": "text" | "image" | False, "id": the id it was found under, "why"}.
      "text"  the quote is in that piece's words (whole words, parts in order); if the id
              is wrong, in exactly one other piece, whose id is then used;
      "image" the id is a figure or table whose image was attached and the quote is not in
              its caption or rows: it may be read from the picture, which code cannot check;
      False   not found, too short, or an id missing from the evidence.
    A quote cut with "..." is checked part by part; each part needs at least
    MIN_PART_WORDS words, and the quote MIN_QUOTE_WORDS in all."""
    parts = _parts(quote)
    words = sum(len(p.split()) for p in parts)
    if not parts or words < MIN_QUOTE_WORDS or (len(parts) > 1 and min(len(p.split()) for p in parts) < MIN_PART_WORDS):
        return {"verified": False, "id": source_id, "why": "quote too short"}
    sid = str(source_id or "").strip().strip("[]")
    if sid in idx and _found_in(parts, idx[sid]["text"]):
        return {"verified": "text", "id": sid, "why": ""}
    others = [k for k, v in idx.items() if k != sid and not v.get("figure") and _found_in(parts, v["text"])]
    if len(others) == 1:
        return {"verified": "text", "id": others[0], "why": f"found under {others[0]}, not {sid or '(no id)'}"}
    if sid in idx and idx[sid].get("image"):
        return {"verified": "image", "id": sid, "why": "read from the attached image; code cannot check it"}
    if sid not in idx:
        return {"verified": False, "id": sid, "why": "this id is missing from the question's evidence"}
    return {"verified": False, "id": sid, "why": "the quote is not in this piece"}


# --------------------------------------------------------------------------- #
# 2. Statements: the answer split into numbered sentences, with their exact place
# --------------------------------------------------------------------------- #
_ABBREV = {"e.g", "i.e", "sec", "secs", "no", "nos", "fig", "figs", "p", "pp", "vs", "approx", "u.s",
           "st", "dr", "mr", "ms", "jr", "in", "ft", "para", "paras", "min", "max", "e", "ref"}
_BULLET = re.compile(r"^(\s*(?:(?:[-*•]|\d{1,2}[.)]|[A-Za-z][.)])\s+)+)")   # "- ", "1. ", "A) ", "- 1. "
_HEADING_COLON = re.compile(r"^\s*(?:#{1,6}\s*)?\**\s*([A-Z][^:\n]{0,70}?)\s*\**\s*:\s*\**\s*$")
_HEADING_MD = re.compile(r"^\s*#{1,6}\s+(.+?)\s*:?\s*$")
_HEADING_BOLD = re.compile(r"^\s*\*\*([^*\n]{1,80}?)\*\*\s*:?\s*$")
_LEAD = re.compile(r"^\s*\**\s*(Direct Answer|Answer|Conclusion|Short answer)\s*\**\s*:\s*\**\s*", re.I)
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _heading(body: str) -> Optional[str]:
    if _LEAD.match(body) and _LEAD.sub("", body).strip(" *"):
        return None                                   # "Direct Answer: text" is a lead, not a heading
    for rx in (_HEADING_MD, _HEADING_BOLD, _HEADING_COLON):
        m = rx.match(body)
        if m:
            return m.group(1).strip().strip("*:").strip()
    return None


def _sentence_spans(line: str, base: int) -> List[Tuple[int, int]]:
    """Sentence spans of one line, as (start, end) offsets into the whole answer. A piece
    of under 3 words ("Yes.") is joined to the sentence after it."""
    spans, start = [], 0
    for m in re.finditer(r"[.!?][\"'”’)\]]*\s+(?=[\"'“(\[]*[A-Z0-9])", line):
        end = m.start() + 1
        before = re.search(r"([A-Za-z.]+)\.$", line[start:end])
        if before and before.group(1).lower().rstrip(".") in _ABBREV:
            continue
        seg = line[start:m.end()].rstrip()
        if seg.strip():
            spans.append((base + start, base + start + len(seg)))
        start = m.end()
    seg = line[start:].rstrip()
    if seg.strip():
        spans.append((base + start, base + start + len(seg)))
    merged: List[Tuple[int, int]] = []
    i = 0
    while i < len(spans):
        s, e = spans[i]
        while len(line[s - base:e - base].split()) < 3 and i + 1 < len(spans):
            i += 1
            e = spans[i][1]
        merged.append((s, e))
        i += 1
    return merged


def split_statements(answer: str) -> List[Dict[str, Any]]:
    """The answer cut into statements, each with its exact place in the answer.

    Each item: {"n" (1, 2, ... for the statements the checker judges; 0 otherwise),
    "start", "end", "text", "kind" ("claim" | "heading" | "citation" | "other"), "row"
    (a table row), "section" (the heading it falls under)}. Headings ("Name:", "## Name",
    "**Name**") are not judged. Lines under a "Citations", "Sources" or "References"
    heading are citations: code checks them (`citation_checks`). A "Direct Answer: ..."
    line is a heading plus the claims after it, up to the end of its paragraph. A table row is one statement (its last
    "|" left out, so a mark goes inside the last cell); a table's separator row is
    "other"."""
    out: List[Dict[str, Any]] = []
    section, pos, n = "", 0, 0
    after_lead: Optional[str] = None          # the section to go back to when a lead's paragraph ends
    for line in answer.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        base, pos = pos, pos + len(line)
        if not body.strip():
            if after_lead is not None:
                section, after_lead = after_lead, None
            continue
        lead_sp = len(body) - len(body.lstrip())
        h = _heading(body)
        if h is not None:
            section, after_lead = h, None
            out.append({"n": 0, "start": base + lead_sp, "end": base + len(body.rstrip()), "text": body.strip(),
                        "kind": "heading", "row": False, "section": section})
            continue
        kind = "citation" if CITATION_SECTIONS.match(section or "") else "claim"
        if body.lstrip().startswith("|"):
            if _TABLE_SEP.match(body):
                out.append({"n": 0, "start": base + lead_sp, "end": base + len(body.rstrip()),
                            "text": body.strip(), "kind": "other", "row": True, "section": section})
                continue
            stripped = body.rstrip()
            end = len(stripped) - 1 if stripped.endswith("|") and len(stripped) > lead_sp + 1 else len(stripped)
            text = answer[base + lead_sp:base + end].rstrip()
            if kind == "claim":
                n += 1
            out.append({"n": n if kind == "claim" else 0, "start": base + lead_sp,
                        "end": base + lead_sp + len(text), "text": text, "kind": kind, "row": True,
                        "section": section})
            continue
        offset = 0
        lead = _LEAD.match(body)
        if lead:
            after_lead = section if after_lead is None else after_lead
            section = lead.group(1).strip()
            offset = lead.end()
            kind = "claim"
        else:
            b = _BULLET.match(body)
            if b:
                offset = b.end()
        for s, e in _sentence_spans(body[offset:], base + offset):
            text = answer[s:e]
            if kind == "claim":
                n += 1
            out.append({"n": n if kind == "claim" else 0, "start": s, "end": e, "text": text,
                        "kind": kind, "row": False, "section": section})
    return out


def numbered_answer(statements: Sequence[Dict[str, Any]]) -> str:
    """The answer as the checker sees it: every claim with its number, headings as they are."""
    lines = []
    for s in statements:
        if s["kind"] == "heading":
            lines.append(f"\n{s['text']}")
        elif s["kind"] == "claim":
            sec = f" ({s['section']})" if s["section"] else ""
            lines.append(f"[S{s['n']}]{sec} {s['text']}")
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------- #
# 3. Code checks that do not need a model
# --------------------------------------------------------------------------- #
_ARITH_CHARS = set("0123456789.,()+-*/^ ×÷−²³x")


def _to_python(expr: str) -> Optional[str]:
    e = expr.strip()
    if not e or not (e[0].isdigit() or e[0] in "(-−"):
        return None
    if re.search(r"\d-\d", e):                                  # "20-50": a range, not a subtraction
        return None
    if re.search(r"\d\+\d{2}(?![\d.])", e):                      # "10+50": a station, not a sum
        return None
    e = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", e)              # 1,000 -> 1000
    if "," in e:
        return None
    e = re.sub(r"(?<=[\d)\s])x(?=[\s\d(])", "*", e)            # "12 x 35": a times sign
    if re.search(r"[A-Za-z]", e):                               # any other letter: not arithmetic
        return None
    return (e.replace("×", "*").replace("÷", "/").replace("−", "-")
             .replace("²", "**2").replace("³", "**3").replace("^", "**"))


def _safe_eval(py: str) -> Optional[float]:
    try:
        tree = ast.parse(py, mode="eval")
    except SyntaxError:
        return None
    ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult,
          ast.Div, ast.Pow, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if not isinstance(node, ok):
            return None
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and abs(node.right.value) <= 4):
                return None
    try:
        v = eval(compile(tree, "<arith>", "eval"), {"__builtins__": {}}, {})  # noqa: S307 (checked AST)
    except (ArithmeticError, ValueError, OverflowError):
        return None
    return float(v) if isinstance(v, (int, float)) and math.isfinite(v) else None


_UNIT_MARKS = [                                     # unit words after a number, as one mark each
    (r"square\s+(?:feet|foot|ft)|sq\.?\s*(?:ft|feet)\.?", ""),
    (r"square\s+(?:inches|inch|in)|sq\.?\s*in\.?", ""),
    (r"inches|inch|in\.?(?=\s*[x×*/=])", ""),
    (r"feet|foot|ft\.?", ""),
    (r"miles|mile|mi\.?", ""),
    (r"mph|km/h", ""),
    (r"seconds|second|sec\.?|s", ""),
    (r"meters|metres|m", ""),
]
_UNIT_RX = re.compile(r"(?<=\d)(\s?)(" + "|".join(f"(?:{a})" for a, _ in _UNIT_MARKS) + r")(?![A-Za-z0-9])", re.I)
_UNIT_CHARS = "".join(m for _, m in _UNIT_MARKS)
_SQUARE = {"", ""}


def _unit_mark(m: "re.Match[str]") -> str:
    for rx, mark in _UNIT_MARKS:
        if re.fullmatch(re.sub(r"\(\?=[^)]*\)", "", rx), m.group(2), re.I):    # without its look-ahead
            return m.group(1) + mark
    return m.group(0)


def arithmetic_checks(text: str) -> List[Dict[str, Any]]:
    """Every "number-expression = number" written in `text`, recomputed.

    Checked only: an expression of numbers and + - x * / ^ and squares, with at least one
    operation. Skipped: anything with a letter ("Q = AB^2/7" is a formula), a range
    written "20-50", a station "10+50", a conversion (other units on the two sides of "=",
    or square units on the right only: "36 x 36 inches = 9 square feet"), and a result
    that is itself the start of more arithmetic ("= 5 + 1 = 6" is checked at its last "=").
    A result followed by "%" or "percent" may be the share or the share x 100. Unit words
    after a number ("100 ft x 0.5 = 50 ft") are ignored. The result may be rounded to the
    digits it shows (or by 0.5%)."""
    text = _UNIT_RX.sub(_unit_mark, str(text))
    chars = _ARITH_CHARS | set(_UNIT_CHARS)
    out = []
    for m in re.finditer(r"=\s*([-−]?\d[\d,]*(?:\.\d+)?)(?![\d.,]*\d)", text):
        rest = text[m.end():]
        if re.match(rf"\s*[{_UNIT_CHARS}]?\s*(?:[+*/^×÷]|x\s*\d|[-−]\s*\d)", rest):
            continue
        i = m.start()
        j = i
        while j > 0 and text[j - 1] in chars:
            j -= 1
        left = text[j:i]
        units_left = {c for c in left if c in _UNIT_CHARS}
        left = "".join(c for c in left if c not in _UNIT_CHARS).strip()
        u = re.match(rf"\s*([{_UNIT_CHARS}])", rest)
        unit_right = u.group(1) if u else ""
        squared = {"\ue001": "\ue008", "\ue002": "\ue003"}          # inches -> square inches, feet -> square feet
        if unit_right and unit_right not in {squared.get(c) for c in units_left} and (
                (units_left and unit_right not in units_left) or (unit_right in _SQUARE and not units_left & _SQUARE)):
            continue                                            # a conversion, not a product
        while left and left[0] in ")+*/^ ×÷":
            left = left[1:].strip()
        if left[:1] in ("-", "−") and not re.match(r"[-−]\s*\d", left):
            left = left[1:].strip()
        if not left or not re.search(r"\d\s*(?:[+*/^×÷−-]|\sx\s|²|³)", left):
            continue
        py = _to_python(left)
        if py is None or py.count("(") != py.count(")"):
            continue
        val = _safe_eval(py)
        if val is None:
            continue
        stated_txt = m.group(1).replace(",", "").replace("−", "-")
        try:
            stated = float(stated_txt)
        except ValueError:
            continue
        decimals = len(stated_txt.split(".")[1]) if "." in stated_txt else 0
        tol = max(0.5 * 10 ** (-decimals) + 1e-9, 0.005 * abs(val))
        holds = abs(val - stated) <= tol
        if not holds and re.match(r"\s*(?:%|percent\b|per cent\b)", rest, re.I):
            holds = abs(val - stated / 100.0) <= max(0.5 * 10 ** (-decimals - 2) + 1e-9, 0.005 * abs(val))
        out.append({"expression": left, "stated": stated, "stated_written": stated_txt,
                    "computed": round(val, 6), "holds": holds})
    return out


_CITE = re.compile(r"Section\s+([0-9A-Z]{1,3}\.?\d{0,2})\s+([A-Za-z]+)\s*(?:§|paragraph|para\.?)\s*(\d{1,3}|\?)", re.I)
_FIGCITE = re.compile(r"\b((?:Figure|Table)\s+\d{1,2}[A-Z]{1,2}\d?-\d+[A-Za-z]?)\b")


def _ordinal(v: Any) -> str:
    try:
        return str(int(str(v).strip()))
    except (TypeError, ValueError):
        return str(v).strip().lower()


def citation_checks(statements: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Each line of the answer's citation list, looked up in the evidence by the same
    (section, type, paragraph) the writer was given (a table note or a typical-application
    note counts by its own section and type), or, for a figure or table, by its id. Lines
    that name neither, or a paragraph written "?", are skipped."""
    triples: Set[Tuple[str, str, str]] = set()
    for v in idx.values():
        if v.get("section") and not blank(v.get("ordinal")):
            triples.add((v["section"].upper(), v["kind"].lower(), _ordinal(v["ordinal"])))
    out = []
    for s in statements:
        if s["kind"] != "citation":
            continue
        m = _CITE.search(s["text"])
        if m:
            if m.group(3) == "?":
                continue
            key = (m.group(1).upper(), m.group(2).lower(), _ordinal(m.group(3)))
            out.append({"start": s["start"], "end": s["end"], "cited": " ".join(key),
                        "in_evidence": key in triples})
            continue
        f = _FIGCITE.search(s["text"])
        if f:
            fid = re.sub(r"\s+", " ", f.group(1))
            hit = fid in idx or any(fid_in_id(fid, k) for k in idx)
            out.append({"start": s["start"], "end": s["end"], "cited": fid, "in_evidence": hit})
    return out


# --------------------------------------------------------------------------- #
# 4. The checker's instructions, and reading its reply
# --------------------------------------------------------------------------- #
CHECKER_RULES = """You check a draft answer to a question about the MUTCD (11th Edition). Another model wrote
the draft from the evidence below. Your job is to judge every numbered statement of the
draft against that evidence and the question, and to name what the draft is missing.
Use only the evidence and the facts stated in the question. Do not use outside knowledge.

How the manual is written:
- Standard: a required or prohibited practice ("shall", "shall not", "must"). Guidance: a
  recommended practice ("should", "should not"). Option: a permission ("may"). Support:
  information only, no requirement. A table row or note carries the type the evidence
  gives it; a reading of a figure marked NOT NORMATIVE is a description, not the manual.
- A provision applies only when its stated conditions hold. An exception ("except",
  "unless", "does not apply", "Except as provided in ...") or a narrower provision changes
  the result for the cases it covers.
- A statement about the case is right only if the facts it relies on are stated in the
  question (or follow from them by correct arithmetic). A fact the question never gives
  is unknown: neither absent nor present.

For each statement [S1], [S2], ... give one verdict:
- SUPPORTED: the evidence shows it is right, including any value, unit, provision type
  (Standard/Guidance/Option/Support), section, condition and exception it states, and its
  application to the facts of the question. A statement that is right but could say more
  is SUPPORTED; put the extra point in the additions.
- CONTRADICTED: the statement as written is wrong or misleading for this question's facts:
  a wrong value or unit, a wrong provision type, a requirement stated as a recommendation
  or the other way round, a condition or exception not applied, a fact assumed that the
  question never gives, a wrong result for the case, or a claim that the evidence leaves
  something open when the evidence decides it. Quote the text that shows it, and give
  the corrected statement: rewrite only this statement, keep its correct parts, one or two
  sentences, no new topics. If you correct the main answer, also correct every statement
  that supports the old answer: the whole answer must stay consistent. A correction of the
  main answer needs at least two sources from different pieces of evidence. A correction
  that brings in "shall", "should" or "may" (or "must", "required", "recommended",
  "permitted", ...) must quote the piece that has that force. Every number in a correction
  must appear in a quoted source or the question, or follow from them by arithmetic you
  write out.
- NOT_SHOWN: the evidence neither supports nor contradicts it (it depends on something
  missing from the evidence, or a fact the question never gives).
- NO_CLAIM: it states nothing to check (a heading, a transition, a remark about the answer
  itself), or it says the evidence leaves something open and you agree.
For SUPPORTED and CONTRADICTED give at least one source: the id in square brackets from
the evidence, and an exact quote of 5 to 40 words copied from that piece (or, for a value
read from an attached image, the figure or table id and what you read). Keep "reason" to
one short sentence. "[Image N]" or "[Picture N]" in the draft means the Nth attached image.

Then list what the draft is missing ("additions"), at most 6, most important first:
- any part of the question the draft does not answer, or says it cannot determine, when
  the evidence settles it; and
- any provision in the evidence that governs this question and that changes, limits or
  qualifies the answer (a condition, an exception, a Guidance or Option that applies, a
  value from a table, a required distinction between Standard, Guidance and Option),
  when the draft does not state it.
Each addition: one or two sentences that could be added to the answer as they stand,
naming the provision's type and section, with at least one source quote from that
provision. Additions must not repeat or contradict the draft or your corrections. If nothing
is missing, give an empty list.

Reply with one JSON object only, no other text:
{"statements": [{"n": 1, "verdict": "SUPPORTED", "sources": [{"id": "...", "quote": "..."}],
  "correction": "", "reason": "..."}, ...],
 "additions": [{"text": "...", "sources": [{"id": "...", "quote": "..."}], "reason": "..."}]}"""


def checker_prompt(question: str, entry: Dict[str, Any], statements: Sequence[Dict[str, Any]],
                   image_ids: Sequence[str] = (), only: Optional[Sequence[int]] = None,
                   additions: bool = True) -> str:
    """The checker's prompt. `only`: judge just these statement numbers (the others are shown
    for context); `additions=False`: give an empty additions list (another call gives them)."""
    imgs = (f"\nAttached images, in order: {', '.join(image_ids)}." if image_ids else "\nNo images are attached.")
    claims = [s["n"] for s in statements if s["kind"] == "claim"]
    nums = list(only) if only else claims
    if only:
        task = (f"Judge ONLY statements [S{nums[0]}] to [S{nums[-1]}] ({len(nums)} statements); the others are "
                f"shown for context and are judged separately.")
    else:
        task = f"Check all {len(nums)} statements."
    if not additions:
        task += ' Give "additions": [] in this reply (they are asked for separately).'
    return (f"{CHECKER_RULES}\n\n##### QUESTION\n{question.strip()}\n\n##### EVIDENCE{imgs}\n"
            f"{evidence_block(entry)}\n\n##### DRAFT ANSWER (numbered statements)\n"
            f"{numbered_answer(statements)}\n\n{task} Reply with the JSON object only.")


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """The first JSON object in a reply (code fences and text around it ignored)."""
    t = (text or "").strip()
    i = t.find("{")
    while i >= 0:
        try:
            v, _ = json.JSONDecoder().raw_decode(t[i:])
            if isinstance(v, dict):
                return v
        except ValueError:
            pass
        i = t.find("{", i + 1)
    return None


def _as_list(v: Any) -> List[Any]:
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [v]
    return []


def _sources(raw: Any, idx: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in _as_list(raw):
        if not isinstance(s, dict):
            continue
        sid, quote = str(s.get("id") or "").strip().strip("[]"), str(s.get("quote") or "")
        v = verify_quote(quote, sid, idx)
        out.append({"id": v["id"], "quote": quote, "verified": v["verified"], "why": v["why"]})
    return out


# a reference is not a quantity: "Section 2Z.01", "paragraphs 3 and 5", "Part 6", "p.12"
_NOT_UNIT = r"(?!\s*(?:inch|inches|in\b|ft\b|feet|foot|mph|percent|%|miles?|mi\b|seconds?|sec\b|square|sq\b))"
_REFERENCE = re.compile(
    r"(?:§§?|\bparagraphs?|\bparas?\.?)\s*\d+[a-z]?\b(?:\s*(?:,|and|or|&|to|through|-)\s*\d+[a-z]?\b" + _NOT_UNIT + r")*"
    r"|(?:\bsections?|\bfigures?|\btables?|\bparts?|\bchapters?|\bpp?\.|\bpages?)\s*[\w.\-]+")
FORCE = {"shall": "standard", "must": "standard", "required": "standard", "mandatory": "standard",
         "prohibited": "standard", "should": "guidance", "recommended": "guidance", "may": "option",
         "permitted": "option", "allowed": "option", "optional": "option"}
_MODALS = {"shall", "should", "may", "must"}
NEGATIONS = ("not", "no", "never", "cannot")
_NEG_BEFORE = {"not", "no", "never", "neither", "nor", "without"}
LIMITING = NEGATIONS + ("except", "unless", "only", "prohibited")
TYPE_NAMES = ("standard", "guidance", "option", "support")
_TYPE = re.compile(r"\b(Standard|Guidance|Option|Support)s?\b")       # the manual's own capitalised names
# a requirement turned round: "shall not", "is not required", "never". A plain "no" or
# "cannot" ("the evidence gives no value", "cannot be determined") is not one: correcting
# a claim that the evidence leaves something open is the checker's job.
_FORCE_NEG = re.compile(r"\b(?:shall|should|may|must|need)\s+not\b|\bnever\b|"
                        r"\bnot\s+(?:be\s+)?(?:required|permitted|allowed|mandatory|recommended|prohibited|needed)\b|"
                        r"\bno\b(?:\s+[a-z]+){1,4}?\s+(?:shall|should|may|must)\b|"
                        r"\bno\b(?:\s+[a-z]+){1,3}?\s+(?:is|are)\s+(?:required|mandatory|needed|permitted|allowed)\b")
_NUMWORDS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
             "nine": "9", "ten": "10", "eleven": "11", "twelve": "12"}


def _nnorm(text: str) -> str:
    """`norm`, with short forms written out ("doesn't" -> "does not", "can't" -> "cannot")."""
    t = norm(text)
    t = re.sub(r"\bcan'?t\b", "cannot", t)
    t = re.sub(r"\bwon'?t\b", "will not", t)
    return re.sub(r"n't\b", " not", t)


def _negs(text: str) -> int:
    """How many requirement negations `text` has: "shall not", "not required", "no sign
    shall", "no permit is required", and "never" in a sentence with a requirement word."""
    t = _nnorm(text)
    found = [m.group(0) for m in _FORCE_NEG.finditer(t)]
    if "never" in found and not (set(re.findall(r"[a-z]+", t)) & set(FORCE)):
        found = [f for f in found if f != "never"]          # "the evidence never gives ...": no requirement
    return len(found)


def _num(x: str) -> str:
    x = x.replace(",", "")
    x = "0" + x if x.startswith(".") else x
    return x.rstrip("0").rstrip(".") if "." in x else x


def _numbers(text: str) -> Set[str]:
    """The quantities in `text`: numbers, also in "12-inch", "36x36", "48-by-60-inch", ".5"
    and the words two to twelve, and numbers stuck to a unit ("40in", "9ft"); not the
    numbers inside references (`_REFERENCE`) or codes
    where a letter touches a digit ("9Z.01", "R3-2"). "4.50" and "4.5" are the same."""
    t = _REFERENCE.sub(" ", norm(text))
    t = re.sub(r"(?<=\d)[\"']", " ", t)                     # 48"x48": inch and foot marks
    t = re.sub(r"(?<=\d)(?=(?:in|ft|mph|mi|sec|lbs?|cm|mm|km)\b)", " ", t)   # "40in", "9ft", "45mph"
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " x ", t)            # "36x36": a size, not a code
    out = set()
    for tok in t.split():
        tok = tok.strip("()[],;:\"'")
        words = [w for w in tok.split("-") if w in _NUMWORDS]
        if words:                                          # "two", "two-lane"
            out |= {_NUMWORDS[w] for w in words}
            continue
        if re.search(r"[a-z]\d|\d[a-z]", tok):
            continue                                       # "9z.01", "r3-2", "2b": a code, not a quantity
        out |= {_num(x) for x in re.findall(r"\d[\d,]*(?:\.\d+)?|(?<!\d)\.\d+", tok)}
    return out


def _words(text: str) -> Set[str]:
    return set(re.findall(r"[a-z]+", _nnorm(text)))


def _unnegated(words: Sequence[str], i: int) -> bool:
    return not (set(words[max(0, i - 2):i]) & _NEG_BEFORE)


def _stated_force(text: str) -> Set[str]:
    """The requirement words `text` states: "shall", "should", "may", "must" always (also
    "shall not"); "required", "permitted", ... only when no "not", "no", "never", ... stands in
    the two words before ("not required" states no requirement)."""
    w = re.findall(r"[a-z]+", _nnorm(text))
    return {x for i, x in enumerate(w) if x in FORCE and (x in _MODALS or _unnegated(w, i))}


def _types_named(text: str) -> Set[str]:
    """Provision types named in `text` ("Standard", "Guidance", "Option", "Support",
    capitalised as the manual writes them; not after "not" or "no")."""
    w = re.findall(r"[A-Za-z]+", text)
    return {x.lower().rstrip("s") for i, x in enumerate(w)
            if _TYPE.fullmatch(x) and _unnegated([y.lower() for y in w], i)}


_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be", "this", "that",
         "it", "its", "with", "as", "by", "at", "from", "which", "when", "if", "than", "there", "these"}


def _content(text: str) -> Set[str]:
    """Content words, without references ("Section 9Z.02") or provision type names."""
    return {w for w in re.findall(r"[a-z0-9]+", _REFERENCE.sub(" ", norm(text)))
            if w not in _STOP and w not in TYPE_NAMES}


def _repeats(text: str, seen: Sequence[str]) -> bool:
    """Does `text` repeat something already there: nearly the same words (Jaccard 0.8 or
    more), or fewer than 3 content words that the other lacks? Not when what it adds is a
    limiting word ("not", "except", "only", ...) or a number: that is an exception or a value."""
    x = _content(text)
    for t in seen:
        y = _content(t)
        if not x or not y:
            continue
        extra = x - y
        if extra & set(LIMITING) or _numbers(text) - _numbers(t):
            continue
        if len(x & y) / len(x | y) >= 0.8 or len(extra) < 3:
            return True
    return False


def _lead(t: str) -> str:
    """"yes" or "no" when `t` starts with one as an answer ("No.", "Yes, ..."), else "".
    "No sign is needed" does not start with an answer."""
    m = re.match(r"[^a-z]*(yes|no)\b[*_]*(?=\s*(?:[,.;:!-]|$))", norm(t))
    return m.group(1) if m else ""


def _turns(original: str, correction: str, answer: bool) -> bool:
    """Does the correction turn the statement round: its leading yes/no, a requirement
    negation, or (for the main answer) any "not / no / never / cannot"?"""
    if _lead(original) != _lead(correction) or _negs(original) != _negs(correction):
        return True
    return answer and _plain_negs(original) != _plain_negs(correction)


def _plain_negs(text: str) -> int:
    """How many times `text` says not / no / never / cannot, leaving out a leading yes/no and
    a contrast ("yellow, not blue")."""
    t = _nnorm(text)
    if _lead(text):
        t = re.sub(r"^[^a-z]*(?:yes|no)\b", "", t)
    t = re.sub(r",\s*(?:and\s+)?not\s+[a-z0-9]+", " ", t)
    return sum(1 for w in re.findall(r"[a-z]+", t) if w in NEGATIONS)


def _piece(i: str) -> str:
    """The piece a source id belongs to: a table row or a figure reading counts as its table
    or figure, so one table is never two pieces."""
    m = _FIGCITE.search(i) if i.startswith("vine:") else None
    return re.sub(r"\s+", " ", m.group(1)) if m else i


def _verified_text(srcs: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> str:
    """What a change may draw its numbers from: each text-verified piece whole, but for a
    figure or table id only the quote (a whole table holds other rows' values)."""
    parts = []
    for x in srcs:
        if x["verified"] == "text":
            v = idx.get(x["id"], {})
            parts.append(x["quote"] if v.get("figure") else v.get("text", ""))
    return " ".join(parts)


def _kinds(srcs: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> Set[str]:
    return {str(idx.get(x["id"], {}).get("kind", "")).lower() for x in srcs if x["verified"] == "text"}


def _force_problem(new: str, old: str, srcs: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> str:
    """A requirement word that `new` states and `old` does not must have its force backed by
    a text-verified source: "shall" by a Standard, "should" by a Guidance, "may" by an Option
    (a table, note or figure by a word of that force in its quote). A word `old` used only
    in a sentence with a negation (other than a leading "No.") does not count as already
    there. The question never backs a requirement word."""
    body = re.sub(r"^[^a-z]*(?:yes|no)\b", "", _nnorm(old)) if _lead(old) else _nnorm(old)   # "No." is an answer
    before = set() if _words(body) & _NEG_BEFORE else _stated_force(old)
    added = sorted(_stated_force(new) - before)
    if not added:
        return ""
    ok: Set[str] = set()
    for x in srcs:
        if x["verified"] != "text":
            continue
        kind = str(idx.get(x["id"], {}).get("kind", "")).lower()
        if kind in TYPE_NAMES:
            ok.add(kind)
        else:
            ok |= {FORCE[w] for w in _stated_force(x["quote"])}
    bad = [w for w in added if FORCE[w] not in ok]
    return f"brings in requirement words no verified source backs: {', '.join(bad)}" if bad else ""


def _type_problem(new: str, old: str, srcs: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> str:
    bad = sorted(_types_named(new) - _types_named(old) - _kinds(srcs, idx))
    return f"it names a provision type its sources are not: {', '.join(bad)}" if bad else ""


def _arith_results(text: str) -> Set[str]:
    return {n for a in arithmetic_checks(text) if a["holds"] for n in _numbers(a["stated_written"])}


def _correction_problem(original: str, correction: str, srcs: Sequence[Dict[str, Any]],
                        idx: Dict[str, Dict[str, Any]], question: str) -> str:
    """Why a correction must not be applied ("" if it may), apart from the two-piece rule
    for turning the answer round (in `read_reply`):
      - a number that no verified source, the question or the original contains (a correct
        arithmetic result in the correction itself is allowed);
      - a requirement word whose force no verified source backs (`_force_problem`);
      - a provision type (Standard, Guidance, ...) it newly names that its sources are not;
      - its own arithmetic does not hold;
      - a requirement negation ("shall not", "not required", "never") added or removed, when
        no verified quote has a limiting word ("not", "except", "unless", "only", ...) and
        it has fewer than two pieces ("not required" with an Option or Guidance source is
        allowed when that source's quote shares 3 or more content words with the correction
        and no source is a Standard: it shows the practice is no Standard)."""
    known = _numbers(_verified_text(srcs, idx)) | _numbers(question) | _numbers(original) | _arith_results(correction)
    new_nums = sorted(_numbers(correction) - known)
    if new_nums:
        return f"brings in numbers no verified source or the question contains: {', '.join(new_nums[:4])}"
    problem = _force_problem(correction, original, srcs, idx) or _type_problem(correction, original, srcs, idx)
    if problem:
        return problem
    if any(not a["holds"] for a in arithmetic_checks(correction)):
        return "its own arithmetic does not hold"
    own = {_piece(x["id"]) for x in srcs if x["verified"] == "text"}
    if _negs(correction) != _negs(original):
        quotes = " ".join(x["quote"] for x in srcs if x["verified"] == "text")
        added = [m.group(0) for m in _FORCE_NEG.finditer(norm(correction))]
        for m in _FORCE_NEG.finditer(norm(original)):
            if m.group(0) in added:
                added.remove(m.group(0))
        # "not required" backed by an Option or a Guidance: the evidence shows it is no Standard
        kinds = _kinds(srcs, idx)
        about = any(len(_content(x["quote"]) & _content(correction)) >= 3 for x in srcs if x["verified"] == "text"
                    and str(idx.get(x["id"], {}).get("kind", "")).lower() in ("option", "guidance"))
        not_required = (bool(added) and _negs(correction) > _negs(original)
                        and all(re.search(r"\b(?:required|mandatory|needed)$", a) for a in added)
                        and about and "standard" not in kinds)
        if not (_words(quotes) & set(LIMITING)) and len(own) < 2 and not not_required:
            return "it turns a requirement round (a negation) that no verified quote shows, with one source"
    return ""


def read_reply(reply: Optional[Dict[str, Any]], statements: Sequence[Dict[str, Any]],
               idx: Dict[str, Dict[str, Any]], question: str = "") -> Dict[str, Any]:
    """The checker's reply, with every quote verified by code, turned into one outcome per
    statement and a list of usable additions.

    outcome: "checked"       SUPPORTED, with a source verified in the text;
             "checked_image" SUPPORTED, with only a value read from an attached image;
             "corrected"     CONTRADICTED, with a text-verified source and a correction that
                             passes `_correction_problem` and the rules below;
             "disputed"      CONTRADICTED, with a text-verified source, but the correction
                             fails those checks: not applied;
             "unconfirmed"   NOT_SHOWN, no verdict, a CONTRADICTED with no usable correction,
                             or a verdict whose sources could not be verified;
             "no_claim"      NO_CLAIM.
    Turning the answer round:
      - a correction that turns the main answer round (`_turns`), or any leading yes/no,
        needs two different pieces, counted over the corrections in the reply that turn
        something round the same way (those in the main answer, and those with the same new
        yes/no) and pass their own checks (a table and its rows are one piece);
      - if a correction that would turn the main answer round is not applied, no other
        correction that turns something round is applied either (in the main answer or
        elsewhere), nor one that changes a value the main answer states: the main answer
        stays as written, whole;
      - a correction elsewhere is not applied if its leading yes/no disagrees with the main
        answer as it stands after the corrections.
    An addition is used only with a text-verified source, sound arithmetic, no number,
    requirement word or provision type that its sources do not back, no leading yes/no
    against the main answer (as corrected), and nothing it repeats."""
    claims = {s["n"]: s for s in statements if s["kind"] == "claim"}
    is_answer = {n: bool(ANSWER_SECTIONS.match(s["section"] or "")) for n, s in claims.items()}
    candidates: Dict[int, List[Dict[str, Any]]] = {}
    for r in _as_list((reply or {}).get("statements")):
        if not isinstance(r, dict):
            continue
        m = re.search(r"\d+", str(r.get("n")))
        if m and int(m.group(0)) in claims:
            candidates.setdefault(int(m.group(0)), []).append(r)
    chosen: Dict[int, Tuple[Dict[str, Any], List[Dict[str, Any]]]] = {}
    for n, rs in candidates.items():
        scored = [(sum(1 for x in srcs if x["verified"]), i, r, srcs)
                  for i, (r, srcs) in enumerate((r, _sources(r.get("sources"), idx)) for r in rs)]
        best = max(scored, key=lambda t: (t[0], -t[1]))
        chosen[n] = (best[2], best[3])

    # 1. each verdict on its own
    results: Dict[int, Dict[str, Any]] = {}
    for n, s in claims.items():
        if n not in chosen:
            results[n] = {"n": n, "verdict": None, "outcome": "unconfirmed", "sources": [],
                          "correction": "", "proposed_correction": "", "not_applied_because": "",
                          "reason": "the checker gave no verdict"}
            continue
        r, srcs = chosen[n]
        verdict = str(r.get("verdict") or "").upper().strip()
        correction = re.sub(r"\s+", " ", str(r.get("correction") or "")).strip()
        text_ok = any(x["verified"] == "text" for x in srcs)
        img_ok = any(x["verified"] == "image" for x in srcs)
        problem = ""
        if verdict == "SUPPORTED":
            outcome = "checked" if text_ok else ("checked_image" if img_ok else "unconfirmed")
        elif verdict == "CONTRADICTED" and text_ok and correction and norm(correction) != norm(s["text"]):
            problem = _correction_problem(s["text"], correction, srcs, idx, question)
            outcome = "disputed" if problem else "corrected"
        elif verdict == "NO_CLAIM":
            outcome = "no_claim"
        else:
            outcome = "unconfirmed"
            if verdict == "CONTRADICTED":
                problem = "the checker disagreed but gave no usable correction or verified source"
        results[n] = {"n": n, "verdict": verdict or None, "outcome": outcome, "sources": srcs,
                      "correction": correction if outcome == "corrected" else "",
                      "proposed_correction": correction, "not_applied_because": problem,
                      "reason": str(r.get("reason") or "")[:500]}

    def turning(n: int) -> bool:
        r = results[n]
        return bool(r["proposed_correction"]) and _turns(claims[n]["text"], r["proposed_correction"], is_answer[n])

    def hold(n: int, why: str) -> None:
        results[n].update(outcome="disputed", correction="", not_applied_because=why)

    main_lead = ""
    for _ in range(len(claims) + 1):          # again until nothing changes: a change held back
        before = [r["outcome"] for r in results.values()]   # takes its pieces out of the pool
        # 2. turning the answer round needs two pieces, over the passing corrections that turn
        #    it the same way: those in the main answer, and those whose new yes/no is the same
        passing = [n for n, r in results.items() if r["outcome"] == "corrected" and turning(n)]
        new_main = next((_lead(results[n]["proposed_correction"]) for n in sorted(passing)
                         if is_answer[n] and _lead(results[n]["proposed_correction"])), "")

        def pool_for(n: int) -> Set[str]:
            target = _lead(results[n]["proposed_correction"]) or new_main
            return {_piece(x["id"]) for m in passing + [n]
                    if m == n or is_answer[m] or (target and _lead(results[m]["proposed_correction"]) == target)
                    for x in results[m]["sources"] if x["verified"] == "text"}

        for n, r in results.items():
            o, c = claims[n]["text"], r["proposed_correction"]
            if (r["outcome"] == "corrected" and ((is_answer[n] and turning(n)) or _lead(o) != _lead(c))
                    and len(pool_for(n)) < 2):
                hold(n, "it turns the main answer or a yes/no round with fewer than two verified pieces")
        # 3. one answer, not two
        main_turn_refused = any(is_answer[n] and r["outcome"] == "disputed" and turning(n) for n, r in results.items())
        final = {n: (r["correction"] if r["outcome"] == "corrected" else claims[n]["text"]) for n, r in results.items()}
        main_lead = next((_lead(final[n]) for n in sorted(claims) if is_answer[n] and _lead(final[n])), "")
        for n, r in results.items():
            if r["outcome"] != "corrected" or not turning(n):
                continue
            if main_turn_refused:
                hold(n, "a correction of the main answer was not applied, so this change is held back to keep "
                        "the answer consistent")
            elif not is_answer[n] and main_lead and _lead(r["correction"]) and _lead(r["correction"]) != main_lead:
                hold(n, "its yes/no would disagree with the main answer")
        # a value the main answer still states, when a turn of it was refused, is not changed elsewhere
        if main_turn_refused:
            kept = set().union(*[_numbers(claims[m]["text"]) for m in claims if is_answer[m]])
            for n, r in results.items():
                if (not is_answer[n] and r["outcome"] == "corrected"
                        and (_numbers(claims[n]["text"]) & kept) - _numbers(r["correction"])):
                    hold(n, "it changes a value that the main answer, kept as written, still states")
        if [r["outcome"] for r in results.values()] == before:
            break

    seen = [s["text"] for s in claims.values()] + [r["correction"] for r in results.values() if r["correction"]]
    additions, rejected = [], []
    for a in _as_list((reply or {}).get("additions"))[:MAX_ADDITIONS]:
        if not isinstance(a, dict) or not str(a.get("text") or "").strip():
            continue
        text = re.sub(r"\s+", " ", str(a["text"])).strip()
        srcs = _sources(a.get("sources"), idx)
        backing = _verified_text(srcs, idx)
        item = {"text": text, "sources": srcs, "reason": str(a.get("reason") or "")[:500]}
        if not any(x["verified"] == "text" for x in srcs):
            item["rejected_because"] = "no source verified in the text"
        elif any(not x["holds"] for x in arithmetic_checks(text)):
            item["rejected_because"] = "its arithmetic does not hold"
        elif _numbers(text) - _numbers(backing) - _numbers(question) - _arith_results(text):
            item["rejected_because"] = "it brings in numbers no verified source or the question contains"
        elif _force_problem(text, "", srcs, idx) or _type_problem(text, "", srcs, idx):
            item["rejected_because"] = _force_problem(text, "", srcs, idx) or _type_problem(text, "", srcs, idx)
        elif main_lead and _lead(text) and _lead(text) != main_lead:
            item["rejected_because"] = "it contradicts the main answer"
        elif _repeats(text, seen):
            item["rejected_because"] = "it repeats a statement, a correction or another addition"
        if "rejected_because" in item:
            rejected.append(item)
        else:
            additions.append(item)
            seen.append(text)
    return {"statements": [results[n] for n in claims], "additions": additions, "additions_rejected": rejected}


# --------------------------------------------------------------------------- #
# 5. The final answer
# --------------------------------------------------------------------------- #
def _cite_label(src: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> str:
    v = idx.get(src["id"], {})
    if v.get("figure"):
        return src["id"]
    if src["id"].startswith("vine:"):                    # a table row or a figure reading
        m = _FIGCITE.search(src["id"])
        if m:
            return m.group(1)
    if v.get("section"):
        ordinal = v.get("ordinal")
        return f"Section {v['section']}" + (f" §{ordinal}" if not blank(ordinal) else "")
    return src["id"]


def _addition_lines(items: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> List[str]:
    """One line per addition, with the provisions it rests on in brackets (a provision the
    text already names is not named twice)."""
    lines = []
    for a in items:
        labels = sorted({_cite_label(x, idx) for x in a["sources"] if x["verified"] == "text"})
        t = norm(a["text"])
        labels = [lb for lb in labels if norm(re.sub(r"^Section\s+|\s*§.*$", "", lb)) not in t]
        lines.append(f"- {a['text'].rstrip()}" + (f" ({'; '.join(labels)})" if labels else ""))
    return lines


def _cells(row: str) -> List[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _table_after(answer: str, pos: int) -> int:
    """Where the line after the table that holds offset `pos` starts (or the answer's end)."""
    i = answer.find("\n", pos)
    while i >= 0 and answer[i + 1:].lstrip(" \t").startswith("|"):
        i = answer.find("\n", i + 1)
    return len(answer) if i < 0 else i + 1


def assemble(answer: str, statements: Sequence[Dict[str, Any]], checked: Dict[str, Any],
             citations: Sequence[Dict[str, Any]], idx: Dict[str, Dict[str, Any]], checker_name: str,
             unjudged: Sequence[int] = (), unjudged_why: str = "") -> Tuple[str, str, Dict[str, int], str]:
    """The final answers from the draft and the checks, and the counts.

    marked:  every outcome visible -- [corrected], [not confirmed], [not judged], [disputed by
             the checker] (its proposed correction listed at the end, not applied),
             [arithmetic not confirmed: ...], [citation not found in evidence]; the additions
             after the answer; one line saying what was checked.
    clean:   the same corrections and additions with no marks; the additions go just before
             the citation list (or at the end).
    corrections_only: the clean answer without the additions (to grade what the
             corrections alone do).
    A corrected table row is rewritten in place when the correction is a row with the same
    number of cells. Otherwise the marked answer keeps the row (marked) and lists the
    correction after the answer, and the clean answer drops the row and gives the
    correction as a sentence just after the table.
    `unjudged`: statement numbers the checker never judged (its call failed); they are
    marked [not judged] and counted apart from [not confirmed]."""
    by_n = {r["n"]: r for r in checked["statements"]}
    skipped = set(unjudged)
    marked_edits: List[Tuple[int, int, str]] = []
    clean_edits: List[Tuple[int, int, str]] = []
    counts = {"statements": 0, "checked": 0, "checked_image": 0, "corrected": 0, "row_corrections": 0,
              "disputed": 0, "unconfirmed": 0, "unjudged": 0, "no_claim": 0, "arithmetic_flags": 0,
              "citations_not_in_evidence": 0, "additions": len(checked["additions"])}
    row_notes, disputes = [], []
    after_table: Dict[int, List[str]] = {}
    for s in statements:
        if s["kind"] != "claim":
            continue
        counts["statements"] += 1
        r = by_n.get(s["n"], {"outcome": "unconfirmed"})
        not_judged = r["outcome"] == "unconfirmed" and s["n"] in skipped
        counts["unjudged" if not_judged else r["outcome"]] += 1
        text = s["text"]
        new, clean = text, text
        if r["outcome"] == "corrected":
            fix = r["correction"]
            if s.get("row"):
                if "|" in fix and len(_cells(fix)) == len(_cells(text)) >= 2:
                    row = "| " + " | ".join(_cells(fix))
                    new, clean = f"{row} [corrected]", row
                else:
                    counts["row_corrections"] += 1
                    new = f"{text.rstrip()} [corrected below]"
                    row_notes.append({"text": fix, "sources": r["sources"]})
                    line_start = answer.rfind("\n", 0, s["start"]) + 1
                    line_end = answer.find("\n", s["end"])
                    line_end = len(answer) if line_end < 0 else line_end + 1
                    clean_edits.append((line_start, line_end, ""))
                    after_table.setdefault(_table_after(answer, s["start"]), []).append(fix.rstrip())
            else:
                new, clean = f"{fix} [corrected]", fix
        elif not_judged:
            new = f"{text.rstrip()} [not judged]"
        elif r["outcome"] == "unconfirmed":
            new = f"{text.rstrip()} [not confirmed]"
        elif r["outcome"] == "disputed":
            new = f"{text.rstrip()} [disputed by the checker]"
            disputes.append(f"- [S{s['n']}] {r.get('proposed_correction', '')} (not applied: "
                            f"{r.get('not_applied_because', '')})")
        bad = [a for a in arithmetic_checks(text) if not a["holds"]]
        if bad and r["outcome"] != "corrected":
            counts["arithmetic_flags"] += 1
            new = f"{new.rstrip()} [arithmetic not confirmed: " + \
                  "; ".join(f"{a['expression']} = {a['computed']:g}" for a in bad) + "]"
        if new != text:
            marked_edits.append((s["start"], s["end"], new))
        if clean != text:
            clean_edits.append((s["start"], s["end"], clean))
    for at, fixes in after_table.items():
        # the text before `at` ends a line already if the draft's does, or if the table's last
        # row (the line before `at`) is removed
        ends_line = (at > 0 and answer[at - 1] == "\n") or any(
            e == at and b > 0 and answer[b - 1] == "\n" and new == "" for b, e, new in clean_edits)
        gap = "\n" if ends_line else "\n\n"
        tail = "" if at >= len(answer) else ("\n" if answer[at] in "\r\n" else "\n\n")
        clean_edits.append((at, at, gap + " ".join(fixes) + tail))
    for c in citations:
        if not c["in_evidence"]:
            counts["citations_not_in_evidence"] += 1
            marked_edits.append((c["end"], c["end"], " [citation not found in evidence]"))

    def apply(edits: List[Tuple[int, int, str]]) -> str:
        out = answer
        for start, end, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
            out = out[:start] + new + out[end:]
        return out.rstrip()

    marked = apply(marked_edits)
    if checked["additions"]:
        marked += "\n\nChecked additions (from the evidence; missing from the draft):\n" + \
                  "\n".join(_addition_lines(checked["additions"], idx))
    if row_notes:
        marked += "\n\nCorrections to table rows (applied in the clean answer):\n" + \
                  "\n".join(_addition_lines(row_notes, idx))
    if disputes:
        marked += "\n\nCorrections proposed by the checker but not applied:\n" + "\n".join(disputes)
    judged = counts["statements"] - counts["no_claim"]
    marked += (f"\n\nVerification: {counts['checked'] + counts['corrected']} of {judged} statements "
               f"checked against quoted manual text by {checker_name}"
               + (f" ({counts['checked_image']} more against an attached image)" if counts["checked_image"] else "")
               + f"; {counts['corrected']} corrected, {counts['disputed']} disputed (not applied), "
               f"{counts['unconfirmed']} not confirmed"
               + (f", {counts['unjudged']} not judged ({unjudged_why or 'the checker call failed'})"
                  if counts["unjudged"] else "")
               + (f", {counts['arithmetic_flags']} with arithmetic not confirmed" if counts["arithmetic_flags"] else "")
               + (f", {counts['citations_not_in_evidence']} citations not found in evidence"
                  if counts["citations_not_in_evidence"] else "")
               + (f"; {counts['additions']} addition{'s' if counts['additions'] != 1 else ''}"
                  if counts["additions"] else "") + ".")

    corrections_only = apply(clean_edits)
    clean = corrections_only
    if checked["additions"]:
        block = "Additional points from the evidence:\n" + "\n".join(_addition_lines(checked["additions"], idx))
        cite_heading = next((s for s in statements if s["kind"] == "heading"
                             and CITATION_SECTIONS.match(s["section"] or "")), None)
        if cite_heading is not None:
            # the clean edits before the heading change its offset by the same amount
            shift = sum(len(new) - (e - b) for b, e, new in clean_edits if e <= cite_heading["start"])
            at = cite_heading["start"] + shift
            clean = clean[:at].rstrip() + "\n\n" + block + "\n\n" + clean[at:]
        else:
            clean += "\n\n" + block
    if "\r\n" in answer:
        marked, clean, corrections_only = (t.replace("\r\n", "\n").replace("\n", "\r\n")
                                           for t in (marked, clean, corrections_only))
    return marked, clean.rstrip(), counts, corrections_only


def unchecked(answer: str, reason: str) -> str:
    """The draft as it is, when the checks could not run."""
    return f"{answer.rstrip()}\n\nVerification: not run ({reason}). This answer is unchecked."
