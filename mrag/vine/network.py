"""The compiled verification network Nq — Eq 2, and the checks of S3.1.

    Nq = (Sq, Oq, Fq, Gq, Gamma^0_q)

S3.1 is explicit that a compiled network is not trusted on sight: "Networks
containing unresolved references, missing producers for mandatory states,
invalid dependencies, or unreachable terminal states are rejected or returned
to the compiler for repair." `validate()` implements exactly those four
checks, plus acyclicity, which a partial order requires and which an LLM
compiler will eventually get wrong.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from .certificate import Authority, CertificateStore


class ObligationType(str, Enum):
    """S3.1: the kinds of check a provision decomposes into."""
    APPLICABILITY = "applicability"
    CLASSIFICATION = "classification"
    NUMERICAL = "numerical"
    VISUAL = "visual"
    DEFINITIONAL = "definitional"
    CROSS_REFERENCE = "cross_reference"
    EXCEPTION = "exception"


class MergeType(str, Enum):
    """S3.2: merges are typed, not a generic boolean."""
    CONJUNCTION = "conjunction"     # all branches must hold
    ALTERNATIVE = "alternative"     # any one suffices
    EXCEPTION = "exception"         # one branch relaxes or overrides another
    THRESHOLD = "threshold"         # a numeric comparison decides


@dataclass
class Operation:
    """An element of Oq. Produces a certificate into `produces`."""
    id: str
    claim: str
    produces: str                                  # the state it marks
    requires: List[str] = field(default_factory=list)   # Pre(o) — states
    verifier: str = "llm"
    obligation_type: Optional[ObligationType] = None
    normative_authority: Authority = Authority.STANDARD
    guard: Optional[Callable[[CertificateStore], bool]] = None   # g_o
    guard_desc: str = ""
    # The states the guard reads. Eq 4 evaluates g_o against the whole store,
    # so a guarded state need not be a prerequisite -- but it IS part of why
    # the branch ran, and S3.4 puts "the certificates that support the
    # terminal decision" in Pi_q. Without this the states were unrecoverable
    # from the compiled network (only `guard_desc` survived), so a check that
    # gated a whole branch was reported as dangling and left out of the audit
    # trail. Measured on a real run: Chart A of Table 2C-4, the test for
    # whether any device is needed at all, was certified and then discarded.
    guard_states: List[str] = field(default_factory=list)
    merge: Optional[MergeType] = None              # set on merge operations
    merge_inputs: List[str] = field(default_factory=list)  # states being merged
    evidence_hint: List[Dict[str, str]] = field(default_factory=list)
    mandatory: bool = True


@dataclass
class Network:
    """Sq, Oq, Fq, Gq and the initial store."""
    query: str
    states: Set[str] = field(default_factory=set)          # Sq
    operations: List[Operation] = field(default_factory=list)  # Oq
    terminal: str = ""                                      # the decision state
    initial: CertificateStore = field(default_factory=CertificateStore)

    # ---- structure -------------------------------------------------------
    def op(self, op_id: str) -> Optional[Operation]:
        return next((o for o in self.operations if o.id == op_id), None)

    def producers(self, state: str) -> List[Operation]:
        return [o for o in self.operations if o.produces == state]

    def flow(self) -> List[tuple]:
        """Fq as (state, operation) and (operation, state) arcs."""
        arcs = []
        for o in self.operations:
            arcs.extend((s, o.id) for s in o.requires)
            arcs.append((o.id, o.produces))
        return arcs

    # ---- S3.1 soundness --------------------------------------------------
    def validate(self) -> List[str]:
        """Return a list of problems. Empty means the network may execute."""
        problems: List[str] = []
        ids = [o.id for o in self.operations]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            problems.append(f"duplicate operation ids: {sorted(dupes)}")

        declared = set(self.states)
        produced = {o.produces for o in self.operations}
        pre_marked = set(self.initial.states())

        # 1. unresolved references: a required state nobody declares
        for o in self.operations:
            for s in o.requires:
                if s not in declared:
                    problems.append(f"{o.id} requires undeclared state '{s}'")
        if self.terminal and self.terminal not in declared:
            problems.append(f"terminal state '{self.terminal}' is not declared")

        # 2. missing producers for mandatory states
        for s in declared:
            if s in produced or s in pre_marked:
                continue
            needed_by = [o.id for o in self.operations if s in o.requires and o.mandatory]
            if needed_by or s == self.terminal:
                problems.append(
                    f"state '{s}' has no producer and is not pre-marked "
                    f"(needed by {needed_by or ['terminal']})")

        # 3. invalid dependencies: a cycle means no partial order exists
        cyc = self._first_cycle()
        if cyc:
            problems.append(f"dependency cycle: {' -> '.join(cyc)}")

        # 4. unreachable terminal state
        if self.terminal and not cyc and not self._reachable(self.terminal):
            problems.append(f"terminal state '{self.terminal}' is unreachable")

        # merge operations must actually merge declared states
        for o in self.operations:
            if o.merge is None:
                continue
            if len(o.merge_inputs) < 2:
                problems.append(f"{o.id} is a {o.merge.value} merge with "
                                f"{len(o.merge_inputs)} input(s); needs at least 2")
            for s in o.merge_inputs:
                if s not in declared:
                    problems.append(f"{o.id} merges undeclared state '{s}'")
                if s not in o.requires:
                    problems.append(f"{o.id} merges '{s}' but does not require it")

        # SUPPORT is never an obligation
        for o in self.operations:
            if o.normative_authority is Authority.SUPPORT:
                problems.append(f"{o.id} has authority SUPPORT; "
                                f"support material is not an obligation")
        return problems

    # ---- helpers ---------------------------------------------------------
    def _op_deps(self) -> Dict[str, Set[str]]:
        """operation -> operations that must run first."""
        by_state: Dict[str, Set[str]] = {}
        for o in self.operations:
            by_state.setdefault(o.produces, set()).add(o.id)
        return {o.id: {p for s in o.requires for p in by_state.get(s, set())}
                for o in self.operations}

    def _first_cycle(self) -> Optional[List[str]]:
        deps = self._op_deps()
        colour: Dict[str, int] = {}
        stack: List[str] = []

        def walk(node: str) -> Optional[List[str]]:
            colour[node] = 1
            stack.append(node)
            for nxt in sorted(deps.get(node, ())):
                if colour.get(nxt, 0) == 1:
                    return stack[stack.index(nxt):] + [nxt]
                if colour.get(nxt, 0) == 0:
                    found = walk(nxt)
                    if found:
                        return found
            colour[node] = 2
            stack.pop()
            return None

        for o in self.operations:
            if colour.get(o.id, 0) == 0:
                found = walk(o.id)
                if found:
                    return found
        return None

    def _reachable(self, state: str) -> bool:
        """Could `state` ever be marked, ignoring guards (guards are runtime)."""
        have = set(self.initial.states())
        changed = True
        while changed:
            changed = False
            for o in self.operations:
                if o.produces in have:
                    continue
                if all(s in have for s in o.requires):
                    have.add(o.produces)
                    changed = True
        return state in have
