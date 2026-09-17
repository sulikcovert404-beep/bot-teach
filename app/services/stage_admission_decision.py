"""Pure stage admission composition over existing readiness evidence contracts."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .environment_readiness import CapabilityStatus, EnvironmentReadinessReport
from .readiness_evidence_gate import GateName, GateStatus, ReadinessDecision, ReadinessReport
from .runtime_entry_decision import AdmissionOutcome, RuntimeEntryDecision, RuntimeStage


class StageAdmissionOutcome(str, Enum):
    ADMITTED = "ADMITTED"
    NOT_ADMITTED = "NOT_ADMITTED"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


STAGE_CAPABILITIES: dict[RuntimeStage, tuple[str, ...]] = {
    RuntimeStage.CONTRACT_STAGE: (),
    RuntimeStage.PERSISTENCE_STAGE: ("database", "migration"),
    RuntimeStage.RUNTIME_STAGE: ("database", "migration", "vector", "runtime_service"),
    RuntimeStage.PRODUCTION_STAGE: ("database", "migration", "vector", "runtime_service"),
}


@dataclass(frozen=True, slots=True)
class StageAdmissionDecision:
    stage: RuntimeStage
    outcome: StageAdmissionOutcome
    required_evidence: tuple[str, ...]
    environment_capabilities: tuple[str, ...]
    readiness_digest: str
    decision_digest: str
    reason_codes: tuple[str, ...]
    version_references: tuple[tuple[str, str], ...] = ()

    def to_dict(self, *, include_decision_digest: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "stage": self.stage.value,
            "outcome": self.outcome.value,
            "required_evidence": list(self.required_evidence),
            "environment_capabilities": list(self.environment_capabilities),
            "readiness_digest": self.readiness_digest,
            "reason_codes": list(self.reason_codes),
            "version_references": [list(item) for item in self.version_references],
        }
        if include_decision_digest:
            value["decision_digest"] = self.decision_digest
        return value

    def canonical_bytes(self) -> bytes:
        payload = json.dumps(self.to_dict(include_decision_digest=False), ensure_ascii=False,
                             sort_keys=True, separators=(",", ":"))
        return unicodedata.normalize("NFC", payload).encode("utf-8")

    @property
    def computed_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.decision_digest == self.computed_digest


def resolve_stage_admission_decision(
    stage: RuntimeStage,
    readiness: ReadinessReport,
    environment: EnvironmentReadinessReport,
    runtime_entry: RuntimeEntryDecision,
    *,
    expected_readiness_digest: str | None = None,
    expected_versions: Mapping[str, str] | None = None,
) -> StageAdmissionDecision:
    """Compose snapshots only; performs no I/O, probing, mutation, or clock access."""
    required_gates = tuple(g.value for g in runtime_entry.evaluated_gates)
    required_caps = STAGE_CAPABILITIES[stage]
    reasons: list[str] = []
    outcome = StageAdmissionOutcome.ADMITTED
    if runtime_entry.stage is not stage:
        outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["STAGE_MISMATCH"]
    elif expected_readiness_digest is not None and expected_readiness_digest != readiness.digest:
        outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["READINESS_DIGEST_MISMATCH"]
    elif readiness.decision is ReadinessDecision.BLOCKED:
        outcome, reasons = StageAdmissionOutcome.BLOCKED, ["READINESS_BLOCKED"]
    elif readiness.decision is not ReadinessDecision.READY_FOR_NEXT_STAGE:
        outcome, reasons = StageAdmissionOutcome.REQUIRES_REVIEW, ["READINESS_NOT_READY"]
    elif not environment.digest_matches():
        outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["ENVIRONMENT_DIGEST_MISMATCH"]
    else:
        caps = {item.capability_name: item for item in environment.capabilities}
        missing = [name for name in required_caps if name not in caps]
        if missing:
            outcome, reasons = StageAdmissionOutcome.REQUIRES_REVIEW, ["ENVIRONMENT_EVIDENCE_MISSING"]
        elif any(caps[name].status is CapabilityStatus.BLOCKED for name in required_caps):
            outcome, reasons = StageAdmissionOutcome.BLOCKED, ["ENVIRONMENT_CAPABILITY_BLOCKED"]
        elif any(caps[name].status is CapabilityStatus.UNKNOWN for name in required_caps):
            outcome, reasons = StageAdmissionOutcome.REQUIRES_REVIEW, ["ENVIRONMENT_CAPABILITY_UNKNOWN"]
        elif any(caps[name].status is not CapabilityStatus.AVAILABLE for name in required_caps):
            outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["ENVIRONMENT_CAPABILITY_UNAVAILABLE"]
        elif runtime_entry.outcome is not AdmissionOutcome.ALLOWED:
            outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["RUNTIME_ENTRY_NOT_ALLOWED"]
    versions = tuple(sorted((str(k), str(v)) for k, v in (expected_versions or {}).items()))
    if outcome is StageAdmissionOutcome.ADMITTED and expected_versions:
        actual = dict(runtime_entry.contract_versions)
        if any(actual.get(k) != v for k, v in expected_versions.items()):
            outcome, reasons = StageAdmissionOutcome.NOT_ADMITTED, ["VERSION_MISMATCH"]
    base = StageAdmissionDecision(stage, outcome, required_gates, required_caps,
                                  readiness.digest, "", tuple(reasons), versions)
    digest = base.computed_digest
    return StageAdmissionDecision(stage, outcome, required_gates, required_caps,
                                  readiness.digest, digest, tuple(reasons), versions)
