"""Pure, immutable reconciliation of runtime-entry readiness evidence."""
from __future__ import annotations

import hashlib, json, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class ReconciliationOutcome(StrEnum):
    ALIGNED = "ALIGNED"
    ALIGNED_WITH_WARNINGS = "ALIGNED_WITH_WARNINGS"
    CONFLICTED = "CONFLICTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k, x in sorted(v.items(), key=lambda i: str(i[0]))}
    if isinstance(v, (tuple, list, set, frozenset)): return [_clean(x) for x in v]
    return v


@dataclass(frozen=True, slots=True)
class RuntimeEntryReadinessReconciliation:
    reconciliation_id: str
    preparation_review_reference: ReferenceToken
    runtime_entry_decision_reference: ReferenceToken
    readiness_snapshot_reference: ReferenceToken
    environment_readiness_reference: ReferenceToken
    conflict_findings: tuple[dict[str, Any], ...] = ()
    trace_reference: ReferenceToken | None = None
    reconciliation_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.reconciliation_id: raise ValueError("reconciliation_id is required")
        if self.trace_reference is None: raise ValueError("trace_reference is required")
        if self.reconciliation_digest and self.reconciliation_digest != self.compute_digest():
            raise ValueError("reconciliation digest mismatch")
        if not self.reconciliation_digest: object.__setattr__(self, "reconciliation_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"reconciliation_id": self.reconciliation_id,
                "preparation_review_reference": self.preparation_review_reference.to_dict(),
                "runtime_entry_decision_reference": self.runtime_entry_decision_reference.to_dict(),
                "readiness_snapshot_reference": self.readiness_snapshot_reference.to_dict(),
                "environment_readiness_reference": self.environment_readiness_reference.to_dict(),
                "conflict_findings": list(self.conflict_findings),
                "trace_reference": self.trace_reference.to_dict()}

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.reconciliation_digest == self.compute_digest()


def evaluate_runtime_entry_readiness_reconciliation(r: RuntimeEntryReadinessReconciliation) -> ReconciliationOutcome:
    refs = (r.preparation_review_reference, r.runtime_entry_decision_reference,
            r.readiness_snapshot_reference, r.environment_readiness_reference, r.trace_reference)
    if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ReconciliationOutcome.BLOCKED
    if any(x.status is ReferenceStatus.INVALID for x in refs): return ReconciliationOutcome.CONFLICTED
    if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ReconciliationOutcome.UNKNOWN
    if r.conflict_findings: return ReconciliationOutcome.CONFLICTED
    return ReconciliationOutcome.ALIGNED
