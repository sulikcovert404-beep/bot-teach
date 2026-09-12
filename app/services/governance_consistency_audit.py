"""Pure consistency audit across governance contract references."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken

class ConsistencyOutcome(StrEnum):
    CONSISTENT = "CONSISTENT"
    CONSISTENT_WITH_WARNINGS = "CONSISTENT_WITH_WARNINGS"
    INCONSISTENT = "INCONSISTENT"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")
def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k, x in sorted(v.items(), key=lambda x: str(x[0]))}
    if isinstance(v, (tuple, list, set, frozenset)): return [_clean(x) for x in v]
    return v
def _reject(v: Any) -> None:
    if isinstance(v, str) and _SECRET.search(v): raise ValueError("secret-like content is not permitted")
    if isinstance(v, dict):
        for k, x in v.items():
            if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
            _reject(x)
    elif isinstance(v, (tuple, list, set, frozenset)):
        for x in v: _reject(x)

@dataclass(frozen=True, slots=True)
class GovernanceConsistencyAudit:
    audit_id: str
    baseline_reference: ReferenceToken
    closure_reference: ReferenceToken
    handoff_reference: ReferenceToken
    readiness_reference: ReferenceToken
    change_control_reference: ReferenceToken
    consistency_findings: tuple[str, ...]
    trace_reference: ReferenceToken
    audit_digest: str = field(default="", repr=False)
    def __post_init__(self) -> None:
        if not self.audit_id: raise ValueError("audit_id is required")
        object.__setattr__(self, "consistency_findings", tuple(sorted(unicodedata.normalize("NFC", x) for x in self.consistency_findings)))
        _reject(self.payload())
        if self.audit_digest and self.audit_digest != self.compute_digest(): raise ValueError("audit digest mismatch")
        if not self.audit_digest: object.__setattr__(self, "audit_digest", self.compute_digest())
    def payload(self) -> dict[str, Any]:
        return {"audit_id": self.audit_id, "baseline_reference": self.baseline_reference.to_dict(), "closure_reference": self.closure_reference.to_dict(), "handoff_reference": self.handoff_reference.to_dict(), "readiness_reference": self.readiness_reference.to_dict(), "change_control_reference": self.change_control_reference.to_dict(), "consistency_findings": self.consistency_findings, "trace_reference": self.trace_reference.to_dict()}
    def canonical_bytes(self) -> bytes: return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.audit_digest == self.compute_digest()

def evaluate_consistency(audit: GovernanceConsistencyAudit) -> ConsistencyOutcome:
    refs = (audit.baseline_reference, audit.closure_reference, audit.handoff_reference, audit.readiness_reference, audit.change_control_reference)
    if not audit.digest_matches(): return ConsistencyOutcome.INCONSISTENT
    if any(r.status is ReferenceStatus.BLOCKED for r in refs): return ConsistencyOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return ConsistencyOutcome.INCONSISTENT
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return ConsistencyOutcome.UNKNOWN
    if audit.trace_reference.status is ReferenceStatus.INVALID: return ConsistencyOutcome.INCONSISTENT
    if audit.trace_reference.status is not ReferenceStatus.VALID: return ConsistencyOutcome.CONSISTENT_WITH_WARNINGS
    if any("VERSION" in r.reference_id.upper() and "MISMATCH" in r.reference_id.upper() for r in refs): return ConsistencyOutcome.INCONSISTENT
    return ConsistencyOutcome.CONSISTENT_WITH_WARNINGS if audit.consistency_findings else ConsistencyOutcome.CONSISTENT
