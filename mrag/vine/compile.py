"""Compile — Kq -> Nq, Eq 1 and S3.1.

    Kq = Retrieve(q, K),   Nq = Compile(q, Kq)

WHAT THE PAPER ASKS FOR
-----------------------
S3.1: "an LLM-based semantic parser extracts atomic verification obligations
and their logical relations into a CONSTRAINED INTERMEDIATE REPRESENTATION,
which is then DETERMINISTICALLY compiled into a query-specific, Petri-net-
inspired verification network". And: "The resulting structured specification
is instantiated deterministically and checked before execution. Networks
containing unresolved references, missing producers for mandatory states,
invalid dependencies, or unreachable terminal states are rejected or returned
to the compiler for repair."

So compilation is in two halves, and only the first is allowed to be a model.

    text ---(parser: LLM, or the baseline below)---> NetworkSpec   <- the IR
    NetworkSpec ---(instantiate: deterministic)----> Network       <- Nq
    Network.validate() ---problems---> repair_request() -----------> back

THE IR IS DATA, NEVER CODE
--------------------------
A guard in Eq 4 is a function of the certificate store. If a model were
allowed to supply one, it would be supplying executable code, and every
guarantee in this file would rest on that code being benign. Guards are
therefore written in a fixed vocabulary -- a state, a status, and `all`/`any`
-- and turned into functions here. An unrecognised guard is a rejected spec,
not a fallback.

For the same reason the instantiator never invents. A dependency on an
obligation that does not exist is an error reported back to the parser; it is
not quietly dropped, because dropping it would turn "check A then B" into
"check B" and the network would still validate.

THE MODEL-FREE BASELINE
-----------------------
`compile_section` builds a spec from the printed structure of a section alone:
the Standard/Guidance/Option headings the manual prints, the exception
phrases, and the table, figure and section references already in the chunk
records. It is not a replacement for the semantic parser -- it cannot read a
sentence and see two independent conditions inside it -- but it produces real,
executable networks with no model, no API key and no annotations. That is
enough for the two experiments that compare execution STRUCTURE rather than
answer quality.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .certificate import Authority, CertificateStore, Status
from .network import MergeType, Network, ObligationType, Operation
from .symbolic import Comparison, Conjunction, Disjunction, Negation, parse_rule

__all__ = ["Obligation", "MergeSpec", "NetworkSpec", "GuardSpec",
           "instantiate", "assign_verifier", "repair_request",
           "compile_section", "CompileError"]


class CompileError(ValueError):
    """The spec could not be turned into a network."""


# --------------------------------------------------------------------------- #
# 1. The intermediate representation
# --------------------------------------------------------------------------- #
_GUARD_STATUSES = {"TRUE", "FALSE", "UNKNOWN", "RESOLVED"}


@dataclass(frozen=True)
class GuardSpec:
    """A guard, as data. One of:

        {"state": "o_class", "status": "TRUE"}
        {"state": "o_class", "status": "RESOLVED"}     TRUE or FALSE, not UNKNOWN
        {"all": [<guard>, ...]}
        {"any": [<guard>, ...]}
        {"not": <guard>}

    `state` names an OBLIGATION id; the instantiator maps it to the state that
    obligation produces, so the parser never has to know about state names.
    """
    kind: str                       # state | all | any | not
    state: str = ""
    status: str = "TRUE"
    parts: Tuple["GuardSpec", ...] = ()

    @staticmethod
    def from_dict(d: Any) -> "GuardSpec":
        if d is None:
            raise CompileError("empty guard")
        if not isinstance(d, dict):
            raise CompileError(f"a guard must be an object, got {type(d).__name__}")
        for key in ("all", "any"):
            if key in d:
                parts = d[key]
                if not isinstance(parts, list) or len(parts) < 2:
                    raise CompileError(f"{key!r} needs at least two guards")
                return GuardSpec(key, parts=tuple(GuardSpec.from_dict(p) for p in parts))
        if "not" in d:
            return GuardSpec("not", parts=(GuardSpec.from_dict(d["not"]),))
        if "state" in d:
            status = str(d.get("status", "TRUE")).upper()
            if status not in _GUARD_STATUSES:
                raise CompileError(f"guard status {status!r} is not one of "
                                   f"{sorted(_GUARD_STATUSES)}")
            return GuardSpec("state", state=str(d["state"]), status=status)
        raise CompileError(f"guard has no recognised key: {sorted(d)}")

    def states(self) -> List[str]:
        if self.kind == "state":
            return [self.state]
        return [s for p in self.parts for s in p.states()]

    def describe(self) -> str:
        if self.kind == "state":
            return f"{self.state} is {self.status}"
        if self.kind == "not":
            return f"not ({self.parts[0].describe()})"
        joiner = " and " if self.kind == "all" else " or "
        return "(" + joiner.join(p.describe() for p in self.parts) + ")"


_BARE_ID = re.compile(r"^\d+[A-Z]-\d+[A-Za-z]?$", re.I)


def _normalise_hint(h: Dict[str, Any]) -> Dict[str, str]:
    """Give an evidence hint the id the verifiers actually look up.

    A model writes what the manual prints inside a sentence -- "Table 2C-4"
    becomes `{"type": "table", "id": "2C-4"}` -- but `mutcd_tables.jsonl` is
    keyed on "Table 2C-4" and the graph on "Figure 2C-1". A bare id therefore
    resolves to nothing, and the calculator abstains with "2C-4 is not in the
    table data" on an obligation it could have answered. The baseline compiler
    already prefixed these; the parser path did not, so it is done here where
    both meet.
    """
    kind = str(h.get("type", "")).lower()
    ident = str(h.get("id", "")).strip()
    if _BARE_ID.match(ident):
        if kind == "table":
            ident = f"Table {ident}"
        elif kind == "figure":
            ident = f"Figure {ident}"
    return {**{k: str(v) for k, v in h.items()}, "type": kind, "id": ident}


@dataclass
class Obligation:
    """One atomic check. The parser emits these; it does not emit states."""
    id: str
    claim: str
    type: str = "applicability"            # an ObligationType value
    authority: str = "STANDARD"            # an Authority value
    requires: List[str] = field(default_factory=list)   # other obligation ids
    guard: Optional[GuardSpec] = None
    evidence_hint: List[Dict[str, str]] = field(default_factory=list)
    verifier: Optional[str] = None         # left None -> assigned by rule
    mandatory: bool = True
    source_chunk: str = ""                 # provenance back into Kq

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Obligation":
        if not d.get("id"):
            raise CompileError(f"an obligation has no id: {d}")
        if not str(d.get("claim", "")).strip():
            raise CompileError(f"obligation {d['id']!r} has no claim")
        guard = GuardSpec.from_dict(d["guard"]) if d.get("guard") else None
        return Obligation(
            id=str(d["id"]), claim=str(d["claim"]),
            type=str(d.get("type", "applicability")).lower(),
            authority=str(d.get("authority", "STANDARD")).upper(),
            requires=[str(r) for r in (d.get("requires") or [])],
            guard=guard,
            evidence_hint=[_normalise_hint(h)
                           for h in (d.get("evidence_hint") or [])],
            verifier=(str(d["verifier"]) if d.get("verifier") else None),
            mandatory=bool(d.get("mandatory", True)),
            source_chunk=str(d.get("source_chunk", "")))


@dataclass
class MergeSpec:
    """A typed synchronisation. S3.2 makes merges typed precisely so the
    composition is not a model's free choice, so `kind` is closed."""
    id: str
    claim: str
    kind: str                              # a MergeType value
    inputs: List[str] = field(default_factory=list)   # obligation ids
    authority: str = "STANDARD"
    guard: Optional[GuardSpec] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MergeSpec":
        if not d.get("id"):
            raise CompileError(f"a merge has no id: {d}")
        return MergeSpec(
            id=str(d["id"]), claim=str(d.get("claim", d["id"])),
            kind=str(d.get("kind", "conjunction")).lower(),
            inputs=[str(i) for i in (d.get("inputs") or [])],
            authority=str(d.get("authority", "STANDARD")).upper(),
            guard=GuardSpec.from_dict(d["guard"]) if d.get("guard") else None)


@dataclass
class NetworkSpec:
    """The constrained intermediate representation of S3.1."""
    query: str
    terminal: str                          # an obligation or merge id
    obligations: List[Obligation] = field(default_factory=list)
    merges: List[MergeSpec] = field(default_factory=list)
    source: str = ""                       # how this spec was produced

    # ---- structural checks on the IR itself --------------------------------
    def problems(self) -> List[str]:
        """What is wrong with the SPEC, before any network is built.

        Separate from `Network.validate()` on purpose. These are errors in the
        parser's output, phrased in the parser's own vocabulary, so the repair
        request can name an obligation id rather than a state name the parser
        never saw.
        """
        out: List[str] = []
        ids = [o.id for o in self.obligations] + [m.id for m in self.merges]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            out.append(f"duplicate ids: {dupes}")
        known = set(ids)

        for o in self.obligations:
            if o.type not in {t.value for t in ObligationType}:
                out.append(f"{o.id}: unknown obligation type {o.type!r}")
            if o.authority not in {a.value for a in Authority}:
                out.append(f"{o.id}: unknown authority {o.authority!r}")
            if o.authority == Authority.SUPPORT.value:
                out.append(f"{o.id}: authority SUPPORT; support material is "
                           f"not an obligation")
            for r in o.requires:
                if r not in known:
                    out.append(f"{o.id}: requires {r!r}, which no obligation "
                               f"or merge produces")
            if o.guard:
                for s in o.guard.states():
                    if s not in known:
                        out.append(f"{o.id}: guard names {s!r}, which no "
                                   f"obligation or merge produces")

        for m in self.merges:
            if m.kind not in {k.value for k in MergeType}:
                out.append(f"{m.id}: unknown merge kind {m.kind!r}")
            if len(m.inputs) < 2:
                out.append(f"{m.id}: a {m.kind} merge needs at least two "
                           f"inputs, got {len(m.inputs)}")
            for i in m.inputs:
                if i not in known:
                    out.append(f"{m.id}: merges {i!r}, which no obligation "
                               f"or merge produces")
            if m.kind == MergeType.EXCEPTION.value and len(m.inputs) >= 2:
                base = next((o for o in self.obligations if o.id == m.inputs[0]), None)
                if base is not None and base.type == ObligationType.EXCEPTION.value:
                    out.append(f"{m.id}: the FIRST input of an exception merge "
                               f"is the base rule, but {base.id!r} is itself "
                               f"an exception")

        if not self.terminal:
            out.append("no terminal proposition")
        elif self.terminal not in known:
            out.append(f"terminal {self.terminal!r} is not an obligation or merge")
        if not self.obligations:
            out.append("no obligations were extracted")
        return out

    # ---- serialisation -----------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        def guard(g):
            if g is None:
                return None
            if g.kind == "state":
                return {"state": g.state, "status": g.status}
            if g.kind == "not":
                return {"not": guard(g.parts[0])}
            return {g.kind: [guard(p) for p in g.parts]}
        return {
            "query": self.query, "terminal": self.terminal, "source": self.source,
            "obligations": [{**{k: v for k, v in asdict(o).items() if k != "guard"},
                             "guard": guard(o.guard)} for o in self.obligations],
            "merges": [{**{k: v for k, v in asdict(m).items() if k != "guard"},
                        "guard": guard(m.guard)} for m in self.merges],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "NetworkSpec":
        return NetworkSpec(
            query=str(d.get("query", "")), terminal=str(d.get("terminal", "")),
            obligations=[Obligation.from_dict(o) for o in (d.get("obligations") or [])],
            merges=[MergeSpec.from_dict(m) for m in (d.get("merges") or [])],
            source=str(d.get("source", "")))

    @staticmethod
    def from_json(text: str) -> "NetworkSpec":
        try:
            return NetworkSpec.from_dict(json.loads(text))
        except json.JSONDecodeError as e:
            raise CompileError(f"the parser did not return valid JSON: {e}") from e


# --------------------------------------------------------------------------- #
# 2. Assigning a verifier
# --------------------------------------------------------------------------- #
def assign_verifier(o: Obligation) -> str:
    """S3.1 step four, done by rule rather than by asking.

    "generative models are used where interpretation is necessary, while
     deterministic or specialized operators are preferred whenever the
     obligation admits a more constrained verification mechanism." (S3.3)

    Which mechanism an obligation admits is readable from the obligation
    itself: a table reference means a lookup, a section reference means the
    resolver, and a claim that reduces to a comparison means arithmetic. Only
    what is left over needs a model.
    """
    if o.verifier:
        return o.verifier
    kinds = {str(h.get("type", "")).lower() for h in o.evidence_hint}

    if o.type == ObligationType.CROSS_REFERENCE.value:
        return "cross_reference_resolver"
    # An explicitly visual obligation goes to the VLM whatever else it cites.
    if o.type == ObligationType.VISUAL.value:
        return "vlm"
    # Otherwise the MOST CONSTRAINED mechanism available wins, which is why a
    # table beats a figure: "If Table 2C-4 indicates that a sign (see Figure
    # 2C-1) is required" is decided by the table, and the figure only shows
    # what the sign looks like. Sending it to a model to look at a picture
    # would replace a lookup with a judgement.
    # A hint says WHERE the evidence is, not which tool can decide the claim.
    # Treating a table hint as "send it to the calculator" routed
    # "The sign installed in advance of the curve is a Curve (W1-2) sign" --
    # a classification that happens to cite Table 2C-4 -- to a deterministic
    # lookup, which can only abstain. So the TYPE decides the tool, and the
    # hint only chooses between tools that could serve that type.
    if o.type == ObligationType.NUMERICAL.value:
        if "table" in kinds:
            return "calculator"
        # A comparison with a RECOMMENDATION bolted onto it is not a
        # comparison. "The curve's advisory speed is 30 mph or less, so a Turn
        # (W1-1) sign should be used instead of a Curve (W1-2) sign" parses to
        # `speed <= 30`, and the symbolic evaluator would return TRUE -- for a
        # claim that also asserts which sign to install. The arithmetic
        # supports the first half and nothing else. Only a claim that stops at
        # the comparison may go to a verifier that can only compare.
        return "llm" if _CONSEQUENCE_RE.search(o.claim) else "symbolic"
    if ("figure" in kinds and "table" not in kinds
            and o.type in (ObligationType.CLASSIFICATION.value,
                           ObligationType.APPLICABILITY.value)):
        # A figure hint sends the check to a VLM only when the claim is about
        # what something IS or LOOKS LIKE. On an exception it usually is not:
        # "if the curve has a change of 135 degrees or more, a Hairpin Curve
        # sign may be used" is a geometric condition and a recommendation, and
        # Figure 2C-1 is cited because it pictures the signs, not because the
        # answer is in it. One run routed five such conditions to the VLM,
        # which would have been asked to read a threshold off a picture.
        #
        # A table cited alongside the figure also disqualifies it: the table
        # is the more constrained evidence, and a claim resting on both is
        # being decided by the table with the figure as illustration.
        return "vlm"
    # "the major-street speed exceeds 40 mph" is a comparison wearing the word
    # applicability, and a model should not be spent on it. But a whole
    # printed paragraph is never a bare comparison: "A Turn sign should be
    # used instead of a Curve sign in advance of a curve that has an advisory
    # speed of 30 mph or less" CONTAINS one. Routing that to the symbolic
    # evaluator would certify "a Turn sign should be used" on the strength of
    # 30 <= 30, which is a far stronger claim than the arithmetic supports.
    # The length test is what separates an atomic obligation from a paragraph.
    if (len(o.claim.split()) <= _ATOMIC_WORDS
            and not _CONSEQUENCE_RE.search(o.claim)
            and _reduces_to_comparison(parse_rule(o.claim))):
        return "symbolic"
    return "llm"


# A claim this short that parses cleanly to a comparison IS the comparison.
_ATOMIC_WORDS = 15

# The manual states a condition and its consequence in one sentence far more
# often than it states either alone. A verifier that can only decide the
# condition must not be handed the pair.
_CONSEQUENCE_RE = re.compile(
    r"\b(shall|should|may|must)\s+(not\s+)?(be\s+)?"
    r"(used|installed|placed|provided|applied|omitted|required|displayed)\b"
    r"|,\s*so\b|\binstead of\b|\bin lieu of\b", re.I)


def _reduces_to_comparison(expr) -> bool:
    if isinstance(expr, Comparison):
        return True
    if isinstance(expr, (Conjunction, Disjunction)):
        return all(_reduces_to_comparison(p) for p in expr.parts)
    if isinstance(expr, Negation):
        return _reduces_to_comparison(expr.part)
    return False


# --------------------------------------------------------------------------- #
# 3. Instantiating — deterministic
# --------------------------------------------------------------------------- #
def _state_of(node_id: str) -> str:
    return f"s_{node_id}"


def _build_guard(spec: GuardSpec) -> Callable[[CertificateStore], bool]:
    """Turn guard DATA into the function Eq 4 needs.

    Every branch here is written in this file. Nothing the parser sent is
    executed; it only selects among these.
    """
    if spec.kind == "state":
        state, want = _state_of(spec.state), spec.status

        def check(store: CertificateStore) -> bool:
            cert = store.latest(state)
            if cert is None:
                return False
            if want == "RESOLVED":
                return cert.status is not Status.UNKNOWN
            return cert.status.value == want
        return check
    parts = [_build_guard(p) for p in spec.parts]
    if spec.kind == "all":
        return lambda store: all(p(store) for p in parts)
    if spec.kind == "any":
        return lambda store: any(p(store) for p in parts)
    if spec.kind == "not":
        return lambda store: not parts[0](store)
    raise CompileError(f"unknown guard kind {spec.kind!r}")


def instantiate(spec: NetworkSpec) -> Tuple[Network, List[str]]:
    """Build Nq from the spec. Returns (network, problems).

    Problems from the SPEC are returned before a network is built, because a
    spec that names a missing obligation cannot be instantiated into anything
    meaningful. Problems from `Network.validate()` are returned alongside the
    network, since the executor refuses to run it anyway and the caller may
    want to inspect what was built.
    """
    problems = spec.problems()
    if problems:
        return Network(query=spec.query), problems

    net = Network(query=spec.query, terminal=_state_of(spec.terminal))
    states: Set[str] = set()
    operations: List[Operation] = []

    for o in spec.obligations:
        produces = _state_of(o.id)
        states.add(produces)
        # a guard's states are read, not consumed: Eq 4 evaluates g_o against
        # the whole store, so a guarded state need NOT be in Pre(o). It must
        # still be declared, or validate() will call it an unresolved reference
        states.update(_state_of(s) for s in o.requires)
        if o.guard:
            states.update(_state_of(s) for s in o.guard.states())
        operations.append(Operation(
            id=o.id, claim=o.claim, produces=produces,
            requires=[_state_of(r) for r in o.requires],
            verifier=assign_verifier(o),
            obligation_type=ObligationType(o.type),
            normative_authority=Authority(o.authority),
            guard=_build_guard(o.guard) if o.guard else None,
            guard_desc=o.guard.describe() if o.guard else "",
            evidence_hint=list(o.evidence_hint),
            mandatory=o.mandatory))

    for m in spec.merges:
        produces = _state_of(m.id)
        inputs = [_state_of(i) for i in m.inputs]
        states.add(produces)
        states.update(inputs)
        if m.guard:
            states.update(_state_of(s) for s in m.guard.states())
        operations.append(Operation(
            id=m.id, claim=m.claim, produces=produces,
            # a merge requires everything it merges; validate() insists on it,
            # and Eq 4 would otherwise let a merge run on a half-empty store
            requires=inputs, verifier="merge",
            normative_authority=Authority(m.authority),
            guard=_build_guard(m.guard) if m.guard else None,
            guard_desc=m.guard.describe() if m.guard else "",
            merge=MergeType(m.kind), merge_inputs=inputs))

    net.states = states
    net.operations = operations
    return net, net.validate()


# --------------------------------------------------------------------------- #
# 4. Repair
# --------------------------------------------------------------------------- #
# validate() speaks in state names; the parser wrote obligation ids. Handing
# back "state 's_o3' has no producer" to something that never wrote "s_o3"
# invites it to invent a state rather than fix the dependency.
_STATE_IN_TEXT = re.compile(r"'s_([A-Za-z0-9_.\-]+)'")


def repair_request(spec: NetworkSpec, problems: Sequence[str]) -> Dict[str, Any]:
    """The structured feedback S3.1 calls returning a network "for repair".

    Deliberately not prose. The parser gets the ids it used, the rules it
    broke, and nothing else, so a repair is a targeted edit rather than a
    second guess at the whole section.
    """
    translated = [_STATE_IN_TEXT.sub(lambda m: f"'{m.group(1)}'", p) for p in problems]
    ids = [o.id for o in spec.obligations] + [m.id for m in spec.merges]
    touched: List[str] = []
    for p in translated:
        touched += [i for i in ids if f"'{i}'" in p or p.startswith(f"{i}:")]
    return {
        "status": "rejected",
        "problems": translated,
        "obligation_ids": ids,
        "implicated": sorted(set(touched)),
        "rules": [
            "every id in `requires`, `inputs` and a guard must be an id "
            "declared in this same spec",
            "a merge needs at least two inputs",
            "the first input of an exception merge is the base rule, not the "
            "exception",
            "SUPPORT material is never an obligation",
            "the dependency graph must be acyclic",
            "the terminal must be reachable from obligations with no "
            "prerequisites",
        ],
        "spec": spec.as_dict(),
    }


# --------------------------------------------------------------------------- #
# 5. The model-free baseline parser
# --------------------------------------------------------------------------- #
_EXCEPTION_LEAD_RE = re.compile(r"^\s*(except|unless)\b", re.I)
_NOT_APPLY_RE = re.compile(r"\b(shall not apply|does not apply|do not apply|"
                           r"are not required|is not required)\b", re.I)
# How the manual opens a provision that scopes the rest of a section.
_GATE_RE = re.compile(r"^\s*(if|where|when|whenever)\b", re.I)
_CLASSIFICATION_RE = re.compile(r"\bis considered\b|\bclassified as\b|"
                                r"\bis defined as\b|\bshall be considered\b", re.I)
_AUTHORITY = {"Standard": "STANDARD", "Guidance": "GUIDANCE",
              "Option": "OPTION", "Support": "SUPPORT"}


def _is_exception_branch(text: str) -> bool:
    """Is this a provision that RELAXES another, or a rule with a caveat in it?

    Measured on the 4,814 normative paragraphs: 449 contain an exception word,
    but only 186 lead with one and 13 say a rule does not apply. The other 261
    have it mid-sentence -- "devices other than those adopted in this Manual
    shall be prohibited unless the FHWA approves" is one rule with its own
    scope, not a separate branch.

    Treating those as exception branches was the first thing that went wrong
    here: 2C.07's only Standard contains the word "unless", so it was moved
    out of the base and became the relaxing branch, leaving the base a
    conjunction of Guidance and Option material with no Standard in it at all.
    """
    return bool(_EXCEPTION_LEAD_RE.match(text) or _NOT_APPLY_RE.search(text))


def _obligation_type(chunk: Dict[str, Any]) -> str:
    text = chunk.get("text", "")
    if _is_exception_branch(text):
        return ObligationType.EXCEPTION.value
    if chunk.get("table_refs"):
        return ObligationType.NUMERICAL.value
    if chunk.get("figure_refs"):
        return ObligationType.VISUAL.value
    if chunk.get("section_refs"):
        return ObligationType.CROSS_REFERENCE.value
    if _CLASSIFICATION_RE.search(text):
        return ObligationType.CLASSIFICATION.value
    return ObligationType.APPLICABILITY.value


def _hints(chunk: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for t in chunk.get("table_refs") or []:
        out.append({"type": "table", "id": t if str(t).lower().startswith("table")
                    else f"Table {t}"})
    for f in chunk.get("figure_refs") or []:
        out.append({"type": "figure", "id": f if str(f).lower().startswith("figure")
                    else f"Figure {f}"})
    for s in chunk.get("section_refs") or []:
        out.append({"type": "section", "id": str(s)})
    return out


def compile_section(section_id: str, chunks: Iterable[Dict[str, Any]],
                    query: Optional[str] = None,
                    include_guidance: bool = True,
                    include_option: bool = True) -> NetworkSpec:
    """A spec built from the printed structure of one section. No model.

    The shape follows the paper's own worked example in S3.1 and Appendix B:
    a classification or applicability check upstream, the required checks as
    parallel branches, the exception as a separate branch, and the results
    synchronised before the terminal state.

    What it does NOT do, and what the semantic parser is for: split one
    sentence carrying two independent conditions into two obligations, or see
    a dependency that the manual states in words rather than in structure.
    Every obligation here is one printed paragraph.
    """
    rows = [c for c in chunks if c.get("section_id") == section_id]
    rows = [c for c in rows if c.get("source") != "table_note"]
    rows.sort(key=lambda c: (int(c.get("ordinal", 0)), str(c.get("chunk_id", ""))))

    wanted = {"Standard"}
    if include_guidance:
        wanted.add("Guidance")
    if include_option:
        wanted.add("Option")

    obligations: List[Obligation] = []
    kept: List[Tuple[Obligation, str]] = []      # (obligation, content_type)

    n = 0
    for c in rows:
        if c.get("content_type") not in wanted:
            continue                      # Support is never an obligation
        n += 1
        ob = Obligation(
            id=f"o{n}", claim=(c.get("text") or "").strip(),
            type=_obligation_type(c), authority=_AUTHORITY[c["content_type"]],
            evidence_hint=_hints(c), source_chunk=str(c.get("chunk_id", "")))
        obligations.append(ob)
        kept.append((ob, c["content_type"]))

    if not obligations:
        raise CompileError(f"section {section_id} has no Standard, Guidance or "
                           f"Option material to compile")

    exceptions = [o.id for o, _ in kept if o.type == ObligationType.EXCEPTION.value]
    # The base is what must HOLD: Standards, plus Guidance so that a
    # recommendation not followed is recorded as non-conformance by the
    # executor. Options are left out of it -- an option not taken is not a
    # failure, and putting it in the conjunction only to have the merge
    # neutralise it again says nothing.
    base_ids = [o.id for o, ct in kept
                if o.id not in exceptions and ct in ("Standard", "Guidance")]

    # Safeguard: a base with no Standard in it is not a base. If every
    # Standard was read as an exception branch, the reading was wrong -- put
    # them back and leave the exception branch to whatever is left.
    if not any(o.authority == "STANDARD" for o in obligations if o.id in base_ids):
        recovered = [o.id for o in obligations
                     if o.id in exceptions and o.authority == "STANDARD"]
        if recovered:
            base_ids = recovered + base_ids
            exceptions = [e for e in exceptions if e not in recovered]

    # The same failure one level down. 2D.06 is a single Guidance paragraph
    # that opens "Except where otherwise provided in this Manual" -- it is the
    # rule, with its scope stated first. With nothing else in the section
    # there was no base for it to relax, so it was made both the base and the
    # branch that relaxes it, and the network was rejected. An exception with
    # nothing to except FROM is simply a rule.
    if not base_ids:
        recovered = [o.id for o in obligations
                     if o.id in exceptions and o.authority in ("STANDARD", "GUIDANCE")]
        base_ids = recovered or [obligations[0].id]
        exceptions = [e for e in exceptions if e not in base_ids]

    # The gate: the first Standard that OPENS with a condition. It stays in
    # the base as well -- Eq 4 only requires a prerequisite to be MARKED, so a
    # gate that was not also a base input could be FALSE without refuting
    # anything, and a Standard that cannot refute is not a Standard.
    #
    # The test is on the wording, not on the obligation type. 2C.07 opens
    # "If Table 2C-4 indicates that a horizontal alignment sign is required",
    # which is plainly the gate for the rest of the section, but its type is
    # `numerical` because it is answered by a table lookup. Type says which
    # verifier; the leading condition says which role.
    upstream: Optional[str] = None
    if len(obligations) > 1:
        for o, _ct in kept:
            if o.authority != "STANDARD":
                continue
            if (_GATE_RE.match(o.claim)
                    or o.type == ObligationType.CLASSIFICATION.value):
                upstream = o.id
            break                         # only the FIRST Standard can gate
    if upstream is not None:
        for o in obligations:
            if o.id != upstream:
                o.requires = [upstream]

    merges: List[MergeSpec] = []
    if len(base_ids) >= 2:
        merges.append(MergeSpec("m_base", f"the requirements of {section_id} "
                                          f"are met", "conjunction", list(base_ids)))
        base = "m_base"
    elif base_ids:
        base = base_ids[0]
    else:
        base = obligations[0].id

    terminal = base
    exceptions = [e for e in dict.fromkeys(exceptions) if e != base]
    if exceptions:
        # S3.2: inputs[0] is the base rule, inputs[1:] relax it
        merges.append(MergeSpec("m_decision", f"the decision for {section_id}",
                                "exception", [base] + exceptions))
        terminal = "m_decision"

    return NetworkSpec(
        query=query or f"do the provisions of Section {section_id} hold?",
        terminal=terminal, obligations=obligations, merges=merges,
        source=f"compile_section({section_id})")
