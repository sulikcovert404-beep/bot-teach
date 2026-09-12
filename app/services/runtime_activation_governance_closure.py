"""Immutable, advisory closure record for the pre-runtime governance chain."""
from __future__ import annotations
import hashlib, json, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets

class GovernanceClosureOutcome(StrEnum):
    GOVERNANCE_CLOSED = "GOVERNANCE_CLOSED"
    GOVERNANCE_CLOSED_WITH_WARNINGS = "GOVERNANCE_CLOSED_WITH_WARNINGS"
    GOVERNANCE_OPEN = "GOVERNANCE_OPEN"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    UNKNOWN = "UNKNOWN"

def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k, x in sorted(v.items(), key=lambda i: str(i[0]))}
    if isinstance(v, (list, tuple, set, frozenset)): return [_clean(x) for x in v]
    return v

@dataclass(frozen=True, slots=True)
class RuntimeActivationGovernanceClosure:
    closure_id: str
    activation_control_plane_reference: ReferenceToken
    activation_decision_reference: ReferenceToken
    activation_review_reference: ReferenceToken
    runtime_entry_consolidation_reference: ReferenceToken
    governance_freeze_reference: ReferenceToken
    baseline_manifest_reference: ReferenceToken
    consistency_findings: tuple[dict[str, Any], ...] = ()
    boundary_assertions: tuple[str, ...] = ()
    trace_reference: ReferenceToken | None = None
    closure_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.closure_id: raise ValueError("closure_id is required")
        if self.trace_reference is None: raise ValueError("trace_reference is required")
        _reject_secrets(self.payload())
        if self.closure_digest and self.closure_digest != self.compute_digest(): raise ValueError("closure digest mismatch")
        if not self.closure_digest: object.__setattr__(self, "closure_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        names = ("activation_control_plane_reference", "activation_decision_reference", "activation_review_reference", "runtime_entry_consolidation_reference", "governance_freeze_reference", "baseline_manifest_reference", "trace_reference")
        out = {"closure_id": self.closure_id, "consistency_findings": list(self.consistency_findings), "boundary_assertions": list(self.boundary_assertions), "runtime_activation": "PROHIBITED", "runtime_admission": "PROHIBITED", "execution": False}
        for n in names: out[n] = getattr(self, n).to_dict()
        return out

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.closure_digest == self.compute_digest()

def evaluate_runtime_activation_governance_closure(c: RuntimeActivationGovernanceClosure) -> GovernanceClosureOutcome:
    refs = [c.activation_control_plane_reference, c.activation_decision_reference, c.activation_review_reference, c.runtime_entry_consolidation_reference, c.governance_freeze_reference, c.baseline_manifest_reference, c.trace_reference]
    if not c.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return GovernanceClosureOutcome.GOVERNANCE_BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return GovernanceClosureOutcome.GOVERNANCE_OPEN
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return GovernanceClosureOutcome.UNKNOWN
    if c.consistency_findings: return GovernanceClosureOutcome.GOVERNANCE_OPEN
    if c.boundary_assertions != ("runtime_activation=PROHIBITED", "runtime_admission=PROHIBITED", "execution=false"): return GovernanceClosureOutcome.GOVERNANCE_OPEN
    return GovernanceClosureOutcome.GOVERNANCE_CLOSED
