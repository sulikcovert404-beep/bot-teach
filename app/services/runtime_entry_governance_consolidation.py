"""Pure immutable consolidation of Runtime Entry governance evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ConsolidationOutcome(StrEnum):
    CONSOLIDATED = "CONSOLIDATED"
    CONSOLIDATED_WITH_WARNINGS = "CONSOLIDATED_WITH_WARNINGS"
    NOT_CONSOLIDATED = "NOT_CONSOLIDATED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_clean(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class RuntimeEntryGovernanceConsolidation:
    """Evidence bundle only; it grants no runtime admission or execution rights."""

    consolidation_id: str
    governance_freeze_reference: ReferenceToken
    baseline_manifest_reference: ReferenceToken
    change_control_reference: ReferenceToken
    consistency_audit_reference: ReferenceToken
    preparation_review_reference: ReferenceToken
    preparation_snapshot_reference: ReferenceToken
    preparation_handoff_reference: ReferenceToken
    readiness_reconciliation_reference: ReferenceToken
    runtime_entry_decision_reference: ReferenceToken
    validation_findings: tuple[dict[str, Any], ...] = ()
    trace_reference: ReferenceToken | None = None
    consolidation_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.consolidation_id:
            raise ValueError("consolidation_id is required")
        if self.trace_reference is None:
            raise ValueError("trace_reference is required")
        _reject_secrets(self.payload())
        if self.consolidation_digest and self.consolidation_digest != self.compute_digest():
            raise ValueError("consolidation digest mismatch")
        if not self.consolidation_digest:
            object.__setattr__(self, "consolidation_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        refs = ("governance_freeze_reference", "baseline_manifest_reference", "change_control_reference",
                "consistency_audit_reference", "preparation_review_reference", "preparation_snapshot_reference",
                "preparation_handoff_reference", "readiness_reconciliation_reference",
                "runtime_entry_decision_reference", "trace_reference")
        out: dict[str, Any] = {"consolidation_id": self.consolidation_id,
                               "validation_findings": list(self.validation_findings),
                               "runtime_admission": "PROHIBITED", "executable": False}
        for name in refs:
            out[name] = getattr(self, name).to_dict()
        return out

    def canonical_bytes(self) -> bytes:
        return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.consolidation_digest == self.compute_digest()


def evaluate_runtime_entry_governance_consolidation(c: RuntimeEntryGovernanceConsolidation) -> ConsolidationOutcome:
    refs = [getattr(c, name) for name in (
        "governance_freeze_reference", "baseline_manifest_reference", "change_control_reference",
        "consistency_audit_reference", "preparation_review_reference", "preparation_snapshot_reference",
        "preparation_handoff_reference", "readiness_reconciliation_reference",
        "runtime_entry_decision_reference", "trace_reference")]
    if not c.digest_matches():
        return ConsolidationOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs):
        return ConsolidationOutcome.NOT_CONSOLIDATED
    if any(r.status is ReferenceStatus.BLOCKED for r in refs):
        return ConsolidationOutcome.BLOCKED
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs):
        return ConsolidationOutcome.UNKNOWN
    if c.validation_findings:
        return ConsolidationOutcome.CONSOLIDATED_WITH_WARNINGS
    return ConsolidationOutcome.CONSOLIDATED
