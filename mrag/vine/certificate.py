"""Verification certificates — Eq 3 and Appendix A of the VINE draft.

    Ci = (phi_i, z_i, R_i, r_i, c_i, rho_i)

A certificate is the ONLY thing that flows between operations. Appendix A is
explicit that it "is not intended as unrestricted natural-language memory";
its fields are constrained so guards can inspect results programmatically.
That is why `status` is an enum rather than a string an LLM wrote, and why
`evidence` is a list of typed ids rather than prose.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    """z_i in Eq 3. UNKNOWN is a first-class outcome, not an error: S3.2 says
    missing evidence is propagated as unresolved verification rather than
    silently converted into a positive or negative conclusion."""
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class Authority(str, Enum):
    """r_i in Eq 3. Decides what a FALSE result MEANS, which is not the same
    question as whether the check passed:

        STANDARD  FALSE refutes the terminal claim
        GUIDANCE  FALSE does NOT refute — it records non-conformance
        OPTION    FALSE means the option was not taken; nothing fails
        SUPPORT   never an obligation at all
    """
    STANDARD = "STANDARD"
    GUIDANCE = "GUIDANCE"
    OPTION = "OPTION"
    SUPPORT = "SUPPORT"


REFUTING = (Authority.STANDARD,)


@dataclass(frozen=True)
class Evidence:
    """One item of R_i. `inferred` marks a normative type this project derived
    from the verb rather than read from a printed heading — true for every
    note printed inside a figure or table (see parsing.py). A certificate must
    never present a guess as if the manual had said it."""
    type: str            # section | figure | table | chunk | paragraph
    id: str
    inferred: bool = False

    def as_dict(self) -> Dict[str, Any]:
        d = {"type": self.type, "id": self.id}
        if self.inferred:
            d["inferred"] = True
        return d


@dataclass
class Certificate:
    claim: str                                   # phi_i
    status: Status                               # z_i
    evidence: List[Evidence] = field(default_factory=list)   # R_i
    normative_authority: Authority = Authority.STANDARD       # r_i
    confidence: float = 0.0                      # c_i
    verifier: str = ""                           # part of rho_i
    dependencies: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)  # rho_i
    obligation_id: str = ""

    def refutes(self) -> bool:
        """A FALSE result that actually kills the terminal claim."""
        return self.status is Status.FALSE and self.normative_authority in REFUTING

    def non_conformance(self) -> bool:
        """FALSE Guidance: recorded, but the claim is not refuted."""
        return self.status is Status.FALSE and self.normative_authority is Authority.GUIDANCE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status.value,
            "evidence": [e.as_dict() for e in self.evidence],
            "normative_authority": self.normative_authority.value,
            "confidence": round(float(self.confidence), 4),
            "verifier": self.verifier,
            "dependencies": list(self.dependencies),
            "provenance": self.provenance,
            "obligation_id": self.obligation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Certificate":
        ev = []
        for e in d.get("evidence") or []:
            if isinstance(e, str):
                ev.append(Evidence("section", e))
            else:
                ev.append(Evidence(str(e.get("type", "section")), str(e.get("id", "")),
                                   bool(e.get("inferred", False))))
        return Certificate(
            claim=str(d.get("claim", "")),
            status=Status(str(d.get("status", "UNKNOWN")).upper()),
            evidence=ev,
            normative_authority=Authority(str(d.get("normative_authority", "STANDARD")).upper()),
            confidence=float(d.get("confidence", 0.0)),
            verifier=str(d.get("verifier", "")),
            dependencies=list(d.get("dependencies") or []),
            provenance=dict(d.get("provenance") or {}),
            obligation_id=str(d.get("obligation_id", "")),
        )


class CertificateStore:
    """Gamma_t — the marking of the net. Maps a STATE to its certificates.

    Append-only by design: execution history is the audit trail (S3.4, "the
    execution trace [is] directly auditable"), so a certificate is never
    overwritten or deleted.
    """

    def __init__(self) -> None:
        self._by_state: Dict[str, List[Certificate]] = {}
        self._order: List[str] = []

    def add(self, state: str, cert: Certificate) -> None:
        self._by_state.setdefault(state, []).append(cert)
        self._order.append(state)

    def get(self, state: str) -> List[Certificate]:
        return list(self._by_state.get(state, []))

    def latest(self, state: str) -> Optional[Certificate]:
        c = self._by_state.get(state)
        return c[-1] if c else None

    def marked(self, state: str) -> bool:
        """Gamma_t(s) != empty — the left half of Eq 4."""
        return bool(self._by_state.get(state))

    def states(self) -> List[str]:
        return list(self._by_state.keys())

    def all(self) -> List[Certificate]:
        return [c for s in self._by_state for c in self._by_state[s]]

    def as_dict(self) -> Dict[str, Any]:
        return {s: [c.as_dict() for c in cs] for s, cs in self._by_state.items()}

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_state.values())
