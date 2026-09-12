"""Pure, immutable lineage control record for activation decisions.

This contract observes consistency only; it never activates, admits, or executes runtime work.
"""
from __future__ import annotations
import hashlib, json, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets

class ControlPlaneOutcome(StrEnum):
    CONTROL_READY = "CONTROL_READY"
    CONTROL_READY_WITH_WARNINGS = "CONTROL_READY_WITH_WARNINGS"
    CONTROL_NOT_READY = "CONTROL_NOT_READY"
    CONTROL_BLOCKED = "CONTROL_BLOCKED"
    UNKNOWN = "UNKNOWN"

def _clean(value: Any) -> Any:
    if isinstance(value, str): return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum): return value.value
    if isinstance(value, dict): return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (list, tuple, set, frozenset)): return [_clean(v) for v in value]
    return value

@dataclass(frozen=True, slots=True)
class RuntimeActivationControlPlane:
    control_plane_id: str
    activation_decision_reference: ReferenceToken
    activation_review_reference: ReferenceToken
    readiness_package_reference: ReferenceToken
    governance_freeze_reference: ReferenceToken
    baseline_manifest_reference: ReferenceToken
    change_control_reference: ReferenceToken
    control_findings: tuple[dict[str, Any], ...] = ()
    trace_reference: ReferenceToken | None = None
    control_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.control_plane_id: raise ValueError("control_plane_id is required")
        if self.trace_reference is None: raise ValueError("trace_reference is required")
        _reject_secrets(self.payload())
        if self.control_digest and self.control_digest != self.compute_digest(): raise ValueError("control digest mismatch")
        if not self.control_digest: object.__setattr__(self, "control_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        names = ("activation_decision_reference", "activation_review_reference", "readiness_package_reference", "governance_freeze_reference", "baseline_manifest_reference", "change_control_reference", "trace_reference")
        out = {"control_plane_id": self.control_plane_id, "control_findings": list(self.control_findings), "runtime_activation": "PROHIBITED", "runtime_admission": "PROHIBITED", "executable": False}
        for name in names: out[name] = getattr(self, name).to_dict()
        return out

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.control_digest == self.compute_digest()

def evaluate_runtime_activation_control_plane(c: RuntimeActivationControlPlane) -> ControlPlaneOutcome:
    refs = [c.activation_decision_reference, c.activation_review_reference, c.readiness_package_reference, c.governance_freeze_reference, c.baseline_manifest_reference, c.change_control_reference, c.trace_reference]
    if not c.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return ControlPlaneOutcome.CONTROL_BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return ControlPlaneOutcome.CONTROL_NOT_READY
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return ControlPlaneOutcome.UNKNOWN
    if c.control_findings: return ControlPlaneOutcome.CONTROL_READY_WITH_WARNINGS
    return ControlPlaneOutcome.CONTROL_READY
