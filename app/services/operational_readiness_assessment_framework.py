"""Pure assessment artifact for future operational readiness; no execution authority."""
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class AssessmentOutcome(str, Enum):
    ASSESSMENT_READY="ASSESSMENT_READY"; ASSESSMENT_READY_WITH_WARNINGS="ASSESSMENT_READY_WITH_WARNINGS"; ASSESSMENT_NOT_READY="ASSESSMENT_NOT_READY"; ASSESSMENT_BLOCKED="ASSESSMENT_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessAssessmentFramework:
    assessment_id: str
    contract_matrix_reference: str
    capability_assessments: Mapping[str, str]
    dependency_findings: tuple[str, ...]
    readiness_gaps: tuple[str, ...]
    risk_summary: tuple[str, ...]
    assessment_constraints: tuple[str, ...]
    boundary_assertions: Mapping[str, object]
    trace_reference: str
    assessment_digest: str

    def outcome(self) -> AssessmentOutcome:
        if not self.assessment_id or not self.contract_matrix_reference or not self.trace_reference or not self.assessment_digest:
            return AssessmentOutcome.ASSESSMENT_BLOCKED
        if not self.capability_assessments or not self.dependency_findings:
            return AssessmentOutcome.ASSESSMENT_NOT_READY
        if self.readiness_gaps or self.boundary_assertions.get("execution") is not False or self.boundary_assertions.get("runtime_activation") != "PROHIBITED":
            return AssessmentOutcome.ASSESSMENT_NOT_READY
        return AssessmentOutcome.ASSESSMENT_READY_WITH_WARNINGS if self.risk_summary else AssessmentOutcome.ASSESSMENT_READY
