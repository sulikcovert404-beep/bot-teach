"""Pure, immutable change-impact contract; no persistence or runtime mutation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping


class ChangeType(str, Enum):
    CONTRACT_CHANGE = "CONTRACT_CHANGE"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    CAPABILITY_CHANGE = "CAPABILITY_CHANGE"
    EVIDENCE_CHANGE = "EVIDENCE_CHANGE"
    POLICY_CHANGE = "POLICY_CHANGE"


class ImpactOutcome(str, Enum):
    NO_IMPACT = "NO_IMPACT"
    REQUIRES_REVALIDATION = "REQUIRES_REVALIDATION"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ImpactReference:
    target_id: str
    target_type: str
    digest: str
    version: str

    def __post_init__(self) -> None:
        for value in (self.target_id, self.target_type, self.digest, self.version):
            if not value or "\x00" in value:
                raise ValueError("reference fields must be non-empty and secret-free")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.digest):
            raise ValueError("digest must use sha256:<64 lowercase hex>")


@dataclass(frozen=True, slots=True)
class ChangeImpactRecord:
    change_id: str
    change_type: ChangeType
    affected_contracts: tuple[ImpactReference, ...] = field(default_factory=tuple)
    affected_stages: tuple[ImpactReference, ...] = field(default_factory=tuple)
    dependency_changes: tuple[ImpactReference, ...] = field(default_factory=tuple)
    evidence_impact: tuple[ImpactReference, ...] = field(default_factory=tuple)
    trace_reference: ImpactReference | None = None
    requirement_reference: ImpactReference | None = None
    revision_reference: ImpactReference | None = None
    supersession_reference: ImpactReference | None = None
    outcome: ImpactOutcome = ImpactOutcome.UNKNOWN
    rationale: str = ""
    warrant: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.change_id or "\x00" in self.change_id:
            raise ValueError("change_id is required")
        text = unicodedata.normalize("NFC", self.rationale)
        if "password" in text.lower() or "secret" in text.lower() or "api_key" in text.lower():
            raise ValueError("secret values are forbidden")
        object.__setattr__(self, "rationale", text)
        if self.outcome is ImpactOutcome.NO_IMPACT and not self.warrant:
            raise ValueError("NO_IMPACT requires a deterministic warrant")
        if self.digest and self.digest != self.compute_digest():
            raise ValueError("digest mismatch")
        if not self.digest:
            object.__setattr__(self, "digest", self.compute_digest())

    def _payload(self) -> dict[str, Any]:
        def refs(items: tuple[ImpactReference, ...]) -> list[dict[str, str]]:
            return [ref.__dict__ if hasattr(ref, "__dict__") else {"target_id": ref.target_id, "target_type": ref.target_type, "digest": ref.digest, "version": ref.version} for ref in items]
        payload: dict[str, Any] = {"change_id": self.change_id, "change_type": self.change_type.value,
            "affected_contracts": refs(self.affected_contracts), "affected_stages": refs(self.affected_stages),
            "dependency_changes": refs(self.dependency_changes), "evidence_impact": refs(self.evidence_impact),
            "trace_reference": refs((self.trace_reference,)) if self.trace_reference else None,
            "requirement_reference": refs((self.requirement_reference,)) if self.requirement_reference else None,
            "revision_reference": refs((self.revision_reference,)) if self.revision_reference else None,
            "supersession_reference": refs((self.supersession_reference,)) if self.supersession_reference else None,
            "outcome": self.outcome.value, "rationale": self.rationale, "warrant": self.warrant}
        return payload

    def canonical_bytes(self) -> bytes:
        return json.dumps(self._payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def verify_digest(self) -> bool:
        return self.digest == self.compute_digest()


def evaluate_impact(*, complete_graph: bool, outcome: ImpactOutcome, rationale: str = "", warrant: str | None = None) -> ImpactOutcome:
    """Pure outcome guard: incomplete dependency graphs fail closed."""
    if not complete_graph:
        return ImpactOutcome.BLOCKED
    if outcome is ImpactOutcome.NO_IMPACT and not warrant:
        return ImpactOutcome.UNKNOWN
    return outcome
