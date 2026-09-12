"""Pure immutable evidence package for future runtime activation review."""
from __future__ import annotations
import hashlib, json, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets

class ActivationReadinessOutcome(StrEnum):
    READY_FOR_ACTIVATION_REVIEW = "READY_FOR_ACTIVATION_REVIEW"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k, x in sorted(v.items(), key=lambda i: str(i[0]))}
    if isinstance(v, (list, tuple, set, frozenset)): return [_clean(x) for x in v]
    return v

@dataclass(frozen=True, slots=True)
class RuntimeEntryActivationReadinessPackage:
    package_id: str
    governance_consolidation_reference: ReferenceToken
    readiness_gate_reference: ReferenceToken
    runtime_entry_decision_reference: ReferenceToken
    preparation_handoff_reference: ReferenceToken
    preparation_snapshot_reference: ReferenceToken
    readiness_reconciliation_reference: ReferenceToken
    environment_readiness_reference: ReferenceToken
    evidence_references: tuple[ReferenceToken, ...]
    trace_reference: ReferenceToken
    activation_findings: tuple[dict[str, Any], ...] = ()
    package_digest: str = field(default="", repr=False)
    def __post_init__(self) -> None:
        if not self.package_id: raise ValueError("package_id is required")
        if not self.evidence_references: raise ValueError("evidence_references are required")
        _reject_secrets(self.payload())
        if self.package_digest and self.package_digest != self.compute_digest(): raise ValueError("package digest mismatch")
        if not self.package_digest: object.__setattr__(self, "package_digest", self.compute_digest())
    def payload(self) -> dict[str, Any]:
        names = ("governance_consolidation_reference", "readiness_gate_reference", "runtime_entry_decision_reference", "preparation_handoff_reference", "preparation_snapshot_reference", "readiness_reconciliation_reference", "environment_readiness_reference", "trace_reference")
        out = {"package_id": self.package_id, "evidence_references": [r.to_dict() for r in self.evidence_references], "activation_findings": list(self.activation_findings), "runtime_activation": "PROHIBITED", "runtime_admission": "PROHIBITED", "executable": False}
        for n in names: out[n] = getattr(self, n).to_dict()
        return out
    def canonical_bytes(self) -> bytes: return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.package_digest == self.compute_digest()

def evaluate_runtime_entry_activation_readiness(p: RuntimeEntryActivationReadinessPackage) -> ActivationReadinessOutcome:
    refs = [p.governance_consolidation_reference, p.readiness_gate_reference, p.runtime_entry_decision_reference, p.preparation_handoff_reference, p.preparation_snapshot_reference, p.readiness_reconciliation_reference, p.environment_readiness_reference, p.trace_reference, *p.evidence_references]
    if not p.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return ActivationReadinessOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return ActivationReadinessOutcome.NOT_READY
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return ActivationReadinessOutcome.UNKNOWN
    if p.activation_findings: return ActivationReadinessOutcome.READY_WITH_WARNINGS
    return ActivationReadinessOutcome.READY_FOR_ACTIVATION_REVIEW
