"""Pure, provider-neutral readiness evaluation over an evidence ledger."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class GateName(str, Enum):
    CONTRACT_READY = "CONTRACT_READY"
    MIGRATION_READY = "MIGRATION_READY"
    TRANSACTION_READY = "TRANSACTION_READY"
    RECOVERY_READY = "RECOVERY_READY"
    AUDIT_READY = "AUDIT_READY"
    CONCURRENCY_READY = "CONCURRENCY_READY"


class GateStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ReadinessDecision(str, Enum):
    READY_FOR_NEXT_STAGE = "READY_FOR_NEXT_STAGE"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"


class EvidenceKind(str, Enum):
    STATIC = "STATIC"
    LIVE = "LIVE"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_id: str
    source_reference: str
    digest: str
    version: str
    timestamp_reference: str
    artifact_reference: str
    kind: EvidenceKind = EvidenceKind.STATIC
    status: GateStatus = GateStatus.PASSED


@dataclass(frozen=True, slots=True)
class GateDefinition:
    name: GateName
    evidence_ids: tuple[str, ...] = ()
    depends_on: tuple[GateName, ...] = ()
    required_kind: EvidenceKind | None = None


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    name: GateName
    status: GateStatus
    evidence_ids: tuple[str, ...] = ()
    reason_code: str = ""


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    decision: ReadinessDecision
    evaluations: tuple[GateEvaluation, ...]
    report_version: str = "V1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "evaluations": [
                {"name": e.name.value, "status": e.status.value,
                 "evidence_ids": list(e.evidence_ids), "reason_code": e.reason_code}
                for e in self.evaluations
            ],
            "report_version": self.report_version,
        }

    def canonical_bytes(self) -> bytes:
        # NFC applies to metadata text at the serialization boundary; ZWNJ is preserved.
        value = unicodedata.normalize("NFC", json.dumps(self.to_dict(), ensure_ascii=False,
                                                         sort_keys=True, separators=(",", ":")))
        return value.encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def evaluate_readiness(
    definitions: tuple[GateDefinition, ...],
    evidence: Mapping[str, EvidenceReference],
) -> ReadinessReport:
    """Evaluate gates deterministically. Missing/invalid evidence fails closed."""
    defs = tuple(sorted(definitions, key=lambda d: d.name.value))
    results: dict[GateName, GateEvaluation] = {}
    for definition in defs:
        dependency_failure = next((results[d].status for d in definition.depends_on
                                   if d in results and results[d].status is not GateStatus.PASSED), None)
        if dependency_failure is not None:
            results[definition.name] = GateEvaluation(definition.name, GateStatus.BLOCKED,
                                                       reason_code="DEPENDENCY_NOT_PASSED")
            continue
        refs = tuple(evidence.get(i) for i in sorted(definition.evidence_ids))
        if not definition.evidence_ids or any(r is None for r in refs):
            results[definition.name] = GateEvaluation(definition.name, GateStatus.UNKNOWN,
                                                       tuple(definition.evidence_ids), "EVIDENCE_MISSING")
            continue
        typed = tuple(r for r in refs if r is not None)
        if definition.required_kind and any(r.kind is not definition.required_kind for r in typed):
            results[definition.name] = GateEvaluation(definition.name, GateStatus.UNKNOWN,
                                                       tuple(definition.evidence_ids), "EVIDENCE_KIND_MISMATCH")
            continue
        status = next((r.status for r in typed if r.status is not GateStatus.PASSED), GateStatus.PASSED)
        results[definition.name] = GateEvaluation(definition.name, status,
                                                   tuple(definition.evidence_ids),
                                                   "" if status is GateStatus.PASSED else "EVIDENCE_NOT_PASSED")
    ordered = tuple(results[d.name] for d in defs)
    if any(e.status is GateStatus.BLOCKED for e in ordered):
        decision = ReadinessDecision.BLOCKED
    elif any(e.status in (GateStatus.FAILED, GateStatus.UNKNOWN) for e in ordered):
        decision = ReadinessDecision.NOT_READY
    else:
        decision = ReadinessDecision.READY_FOR_NEXT_STAGE
    return ReadinessReport(decision, ordered)
