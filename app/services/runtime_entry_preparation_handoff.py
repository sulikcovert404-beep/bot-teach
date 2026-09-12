"""Pure immutable transfer record for runtime-entry preparation evidence."""
from __future__ import annotations
import hashlib, json, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets

class HandoffOutcome(StrEnum):
    TRANSFERRED = "TRANSFERRED"
    TRANSFERRED_WITH_WARNINGS = "TRANSFERRED_WITH_WARNINGS"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

def _clean(value: Any) -> Any:
    if isinstance(value, str): return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum): return value.value
    if isinstance(value, dict): return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple, set, frozenset)): return [_clean(v) for v in value]
    return value

@dataclass(frozen=True, slots=True)
class RuntimeEntryPreparationHandoff:
    handoff_id: str
    preparation_snapshot_reference: ReferenceToken
    preparation_review_reference: ReferenceToken
    reconciliation_reference: ReferenceToken
    runtime_entry_decision_reference: ReferenceToken
    trace_reference: ReferenceToken
    handoff_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.handoff_id: raise ValueError("handoff_id is required")
        _reject_secrets(self.payload())
        if self.handoff_digest and self.handoff_digest != self.compute_digest(): raise ValueError("handoff digest mismatch")
        if not self.handoff_digest: object.__setattr__(self, "handoff_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"handoff_id": self.handoff_id,
                "preparation_snapshot_reference": self.preparation_snapshot_reference.to_dict(),
                "preparation_review_reference": self.preparation_review_reference.to_dict(),
                "reconciliation_reference": self.reconciliation_reference.to_dict(),
                "runtime_entry_decision_reference": self.runtime_entry_decision_reference.to_dict(),
                "trace_reference": self.trace_reference.to_dict()}
    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.handoff_digest == self.compute_digest()

def evaluate_runtime_entry_preparation_handoff(handoff: RuntimeEntryPreparationHandoff) -> HandoffOutcome:
    refs = (handoff.preparation_snapshot_reference, handoff.preparation_review_reference,
            handoff.reconciliation_reference, handoff.runtime_entry_decision_reference, handoff.trace_reference)
    if not handoff.digest_matches() or any(r.status is ReferenceStatus.INVALID for r in refs): return HandoffOutcome.REJECTED
    if any(r.status is ReferenceStatus.BLOCKED for r in refs): return HandoffOutcome.BLOCKED
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return HandoffOutcome.UNKNOWN
    return HandoffOutcome.TRANSFERRED
