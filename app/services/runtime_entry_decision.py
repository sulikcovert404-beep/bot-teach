"""Pure runtime stage admission decisions derived from readiness evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from collections.abc import Mapping
from typing import Any
import unicodedata

from .readiness_evidence_gate import (
    EvidenceReference,
    GateName,
    GateStatus,
    ReadinessDecision,
    ReadinessReport,
)


class RuntimeStage(str, Enum):
    CONTRACT_STAGE = "CONTRACT_STAGE"
    PERSISTENCE_STAGE = "PERSISTENCE_STAGE"
    RUNTIME_STAGE = "RUNTIME_STAGE"
    PRODUCTION_STAGE = "PRODUCTION_STAGE"


class AdmissionOutcome(str, Enum):
    ALLOWED = "ALLOWED"
    NOT_ALLOWED = "NOT_ALLOWED"
    BLOCKED = "BLOCKED"
    REQUIRES_EVIDENCE = "REQUIRES_EVIDENCE"


# Ordered and explicit: stage admission never depends on mapping iteration order.
REQUIRED_GATES: dict[RuntimeStage, tuple[GateName, ...]] = {
    RuntimeStage.CONTRACT_STAGE: (GateName.CONTRACT_READY,),
    RuntimeStage.PERSISTENCE_STAGE: (
        GateName.CONTRACT_READY,
        GateName.MIGRATION_READY,
        GateName.TRANSACTION_READY,
    ),
    RuntimeStage.RUNTIME_STAGE: (
        GateName.CONTRACT_READY,
        GateName.MIGRATION_READY,
        GateName.TRANSACTION_READY,
        GateName.RECOVERY_READY,
        GateName.AUDIT_READY,
        GateName.CONCURRENCY_READY,
    ),
    RuntimeStage.PRODUCTION_STAGE: (
        GateName.CONTRACT_READY,
        GateName.MIGRATION_READY,
        GateName.TRANSACTION_READY,
        GateName.RECOVERY_READY,
        GateName.AUDIT_READY,
        GateName.CONCURRENCY_READY,
    ),
}


@dataclass(frozen=True, slots=True)
class RuntimeEntryDecision:
    outcome: AdmissionOutcome
    stage: RuntimeStage
    evaluated_gates: tuple[GateName, ...]
    evidence_references: tuple[EvidenceReference, ...]
    readiness_digest: str
    gate_versions: tuple[tuple[str, str], ...]
    contract_versions: tuple[tuple[str, str], ...]
    timestamp_reference: str
    reason_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "stage": self.stage.value,
            "evaluated_gates": [g.value for g in self.evaluated_gates],
            "evidence_references": [
                {
                    "evidence_id": e.evidence_id,
                    "source_reference": e.source_reference,
                    "digest": e.digest,
                    "version": e.version,
                    "timestamp_reference": e.timestamp_reference,
                    "artifact_reference": e.artifact_reference,
                    "kind": e.kind.value,
                    "status": e.status.value,
                }
                for e in self.evidence_references
            ],
            "readiness_digest": self.readiness_digest,
            "gate_versions": [list(v) for v in self.gate_versions],
            "contract_versions": [list(v) for v in self.contract_versions],
            "timestamp_reference": self.timestamp_reference,
            "reason_code": self.reason_code,
        }

    def canonical_bytes(self) -> bytes:
        value = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return unicodedata.normalize("NFC", value).encode("utf-8")

    @property
    def decision_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def resolve_stage_admission(
    stage: RuntimeStage,
    report: ReadinessReport,
    evidence: Mapping[str, EvidenceReference],
    *,
    expected_readiness_digest: str | None = None,
    expected_gate_versions: Mapping[str, str] | None = None,
    contract_versions: Mapping[str, str] | None = None,
    timestamp_reference: str = "",
) -> RuntimeEntryDecision:
    """Resolve admission without I/O, mutation, clock access, or cache state."""
    gates = REQUIRED_GATES[stage]
    refs: list[EvidenceReference] = []
    gate_versions: list[tuple[str, str]] = []
    statuses = {item.name: item.status for item in report.evaluations}
    for gate in gates:
        evaluation = next((item for item in report.evaluations if item.name is gate), None)
        if evaluation is None:
            status = GateStatus.UNKNOWN
            ids: tuple[str, ...] = ()
        else:
            status = evaluation.status
            ids = evaluation.evidence_ids
        refs.extend(evidence[item] for item in sorted(ids) if item in evidence)
        for item in sorted(ids):
            if item in evidence:
                gate_versions.append((gate.value, evidence[item].version))
        statuses[gate] = status

    unique_refs = tuple(sorted({ref.evidence_id: ref for ref in refs}.values(), key=lambda r: r.evidence_id))
    versions = tuple(sorted((str(k), str(v)) for k, v in (contract_versions or {}).items()))
    expected = tuple(sorted((str(k), str(v)) for k, v in (expected_gate_versions or {}).items()))
    actual = tuple(sorted(gate_versions))

    if expected_readiness_digest is not None and expected_readiness_digest != report.digest:
        outcome, reason = AdmissionOutcome.NOT_ALLOWED, "READINESS_DIGEST_MISMATCH"
    elif expected and any(pair not in actual for pair in expected):
        outcome, reason = AdmissionOutcome.NOT_ALLOWED, "GATE_VERSION_MISMATCH"
    elif any(status is GateStatus.BLOCKED for status in (statuses[g] for g in gates)):
        outcome, reason = AdmissionOutcome.BLOCKED, "REQUIRED_GATE_BLOCKED"
    elif any(status is GateStatus.UNKNOWN for status in (statuses[g] for g in gates)):
        outcome, reason = AdmissionOutcome.REQUIRES_EVIDENCE, "REQUIRED_EVIDENCE_MISSING_OR_UNKNOWN"
    elif any(status is GateStatus.FAILED for status in (statuses[g] for g in gates)):
        outcome, reason = AdmissionOutcome.NOT_ALLOWED, "REQUIRED_GATE_FAILED"
    elif report.decision is not ReadinessDecision.READY_FOR_NEXT_STAGE:
        outcome, reason = AdmissionOutcome.NOT_ALLOWED, "READINESS_NOT_READY_FOR_STAGE"
    else:
        outcome, reason = AdmissionOutcome.ALLOWED, "ALL_REQUIRED_GATES_PASSED"

    return RuntimeEntryDecision(
        outcome, stage, gates, unique_refs, report.digest, actual, versions,
        timestamp_reference, reason,
    )
