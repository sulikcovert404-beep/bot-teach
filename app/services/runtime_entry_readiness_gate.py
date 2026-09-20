"""Pure contract gate assessing readiness for a future Runtime Admission step."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ReadinessGateOutcome(StrEnum):
    READY = "READY"
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
class RuntimeEntryReadinessGate:
    gate_id: str
    governance_consolidation_reference: ReferenceToken
    runtime_entry_decision_reference: ReferenceToken
    readiness_reconciliation_reference: ReferenceToken
    environment_readiness_reference: ReferenceToken
    gate_findings: tuple[dict[str, Any], ...] = ()
    trace_reference: ReferenceToken | None = None
    gate_digest: str = field(default="", repr=False)
    def __post_init__(self) -> None:
        if not self.gate_id: raise ValueError("gate_id is required")
        if self.trace_reference is None: raise ValueError("trace_reference is required")
        _reject_secrets(self.payload())
        if self.gate_digest and self.gate_digest != self.compute_digest(): raise ValueError("gate digest mismatch")
        if not self.gate_digest: object.__setattr__(self, "gate_digest", self.compute_digest())
    def payload(self) -> dict[str, Any]:
        names = ("governance_consolidation_reference", "runtime_entry_decision_reference", "readiness_reconciliation_reference", "environment_readiness_reference", "trace_reference")
        out = {"gate_id": self.gate_id, "gate_findings": list(self.gate_findings), "runtime_admission": "PROHIBITED", "executable": False}
        for name in names: out[name] = getattr(self, name).to_dict()
        return out
    def canonical_bytes(self) -> bytes: return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.gate_digest == self.compute_digest()

def evaluate_runtime_entry_readiness_gate(g: RuntimeEntryReadinessGate) -> ReadinessGateOutcome:
    refs = [g.governance_consolidation_reference, g.runtime_entry_decision_reference, g.readiness_reconciliation_reference, g.environment_readiness_reference, g.trace_reference]
    if not g.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return ReadinessGateOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return ReadinessGateOutcome.NOT_READY
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return ReadinessGateOutcome.UNKNOWN
    if g.gate_findings: return ReadinessGateOutcome.READY_WITH_WARNINGS
    return ReadinessGateOutcome.READY
