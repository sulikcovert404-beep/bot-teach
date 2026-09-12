"""Pure immutable historical snapshot for runtime-entry preparation."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class SnapshotOutcome(StrEnum):
    CAPTURED = "CAPTURED"
    CAPTURED_WITH_WARNINGS = "CAPTURED_WITH_WARNINGS"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_clean(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class RuntimeEntryPreparationBaselineSnapshot:
    snapshot_id: str
    preparation_review_reference: ReferenceToken
    reconciliation_reference: ReferenceToken
    freeze_reference: ReferenceToken
    baseline_reference: ReferenceToken
    captured_findings: tuple[dict[str, Any], ...] = ()
    trace_reference: ReferenceToken | None = None
    snapshot_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")
        if self.trace_reference is None:
            raise ValueError("trace_reference is required")
        _reject_secrets(self.payload())
        if self.snapshot_digest and self.snapshot_digest != self.compute_digest():
            raise ValueError("snapshot digest mismatch")
        if not self.snapshot_digest:
            object.__setattr__(self, "snapshot_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"snapshot_id": self.snapshot_id,
                "preparation_review_reference": self.preparation_review_reference.to_dict(),
                "reconciliation_reference": self.reconciliation_reference.to_dict(),
                "freeze_reference": self.freeze_reference.to_dict(),
                "baseline_reference": self.baseline_reference.to_dict(),
                "captured_findings": list(self.captured_findings),
                "trace_reference": self.trace_reference.to_dict()}

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.snapshot_digest == self.compute_digest()


def evaluate_runtime_entry_preparation_baseline_snapshot(
    snapshot: RuntimeEntryPreparationBaselineSnapshot,
) -> SnapshotOutcome:
    refs = (snapshot.preparation_review_reference, snapshot.reconciliation_reference,
            snapshot.freeze_reference, snapshot.baseline_reference, snapshot.trace_reference)
    if not snapshot.digest_matches() or any(ref.status is ReferenceStatus.INVALID for ref in refs):
        return SnapshotOutcome.INVALID
    if any(ref.status is ReferenceStatus.BLOCKED for ref in refs):
        return SnapshotOutcome.BLOCKED
    if any(ref.status is ReferenceStatus.REQUIRES_REVIEW for ref in refs):
        return SnapshotOutcome.UNKNOWN
    if snapshot.captured_findings:
        return SnapshotOutcome.CAPTURED_WITH_WARNINGS
    return SnapshotOutcome.CAPTURED
