"""Pure staging-validation planning contract; it performs no staging actions."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import hashlib, json, unicodedata

class StagingValidationOutcome(StrEnum):
    STAGING_VALIDATION_READY = "STAGING_VALIDATION_READY"
    STAGING_VALIDATION_READY_WITH_WARNINGS = "STAGING_VALIDATION_READY_WITH_WARNINGS"
    STAGING_VALIDATION_NOT_READY = "STAGING_VALIDATION_NOT_READY"
    STAGING_VALIDATION_BLOCKED = "STAGING_VALIDATION_BLOCKED"
    UNKNOWN = "UNKNOWN"

def _clean(v: str) -> str:
    return unicodedata.normalize("NFC", str(v)).strip()

@dataclass(frozen=True, slots=True)
class RuntimeActivationStagingValidationFramework:
    framework_id: str
    final_readiness_review_reference: str
    assurance_bundle_reference: str
    activation_decision_reference: str
    validation_plan_reference: str
    evidence_requirements: tuple[str, ...]
    rollback_requirements: tuple[str, ...]
    trace_reference: str
    framework_digest: str = ""

    def __post_init__(self) -> None:
        for name in ("framework_id", "final_readiness_review_reference", "assurance_bundle_reference", "activation_decision_reference", "validation_plan_reference", "trace_reference"):
            value = _clean(getattr(self, name))
            if not value or any(x in value.lower() for x in ("api_key", "password", "secret", "bearer ")):
                raise ValueError(f"invalid or secret-bearing {name}")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "evidence_requirements", tuple(_clean(x) for x in self.evidence_requirements))
        object.__setattr__(self, "rollback_requirements", tuple(_clean(x) for x in self.rollback_requirements))
        digest = self.canonical_digest()
        if self.framework_digest and self.framework_digest != digest:
            raise ValueError("framework digest mismatch")
        object.__setattr__(self, "framework_digest", digest)

    def payload(self) -> dict[str, object]:
        return {"framework_id": self.framework_id, "final_readiness_review_reference": self.final_readiness_review_reference, "assurance_bundle_reference": self.assurance_bundle_reference, "activation_decision_reference": self.activation_decision_reference, "validation_plan_reference": self.validation_plan_reference, "evidence_requirements": self.evidence_requirements, "rollback_requirements": self.rollback_requirements, "trace_reference": self.trace_reference, "actual_staging_deployment": "PROHIBITED", "runtime_activation": "PROHIBITED", "runtime_admission": "PROHIBITED", "database_migration": "PROHIBITED", "execution": False}

    def canonical_digest(self) -> str:
        body = json.dumps(self.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def evaluate(*, references: tuple[str, ...], evidence: tuple[str, ...] = (), rollback: tuple[str, ...] = ()) -> StagingValidationOutcome:
        refs = tuple(_clean(x) for x in references)
        if not refs or any(not x for x in refs) or any(any(k in x.upper() for k in ("BLOCKED", "DIGEST_MISMATCH", "TRACE_FAILURE")) for x in refs):
            return StagingValidationOutcome.STAGING_VALIDATION_BLOCKED
        if any(any(k in x.upper() for k in ("INVALID", "CONTRADICTION")) for x in refs):
            return StagingValidationOutcome.STAGING_VALIDATION_NOT_READY
        if any("UNKNOWN" in x.upper() for x in refs) or not evidence or not rollback:
            return StagingValidationOutcome.UNKNOWN
        if any("WARNING" in x.upper() for x in evidence + rollback):
            return StagingValidationOutcome.STAGING_VALIDATION_READY_WITH_WARNINGS
        return StagingValidationOutcome.STAGING_VALIDATION_READY
