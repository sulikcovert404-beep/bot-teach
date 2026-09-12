"""Evidence semantics for readiness governance; collection and storage are prohibited."""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class EvidenceOutcome(str, Enum):
    EVIDENCE_MODEL_DEFINED="EVIDENCE_MODEL_DEFINED"; EVIDENCE_MODEL_DEFINED_WITH_WARNINGS="EVIDENCE_MODEL_DEFINED_WITH_WARNINGS"; EVIDENCE_MODEL_INCOMPLETE="EVIDENCE_MODEL_INCOMPLETE"; EVIDENCE_MODEL_BLOCKED="EVIDENCE_MODEL_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessEvidenceModel:
    evidence_model_id: str
    governance_model_reference: str
    evidence_categories: tuple[str, ...]
    required_evidence_rules: Mapping[str, str]
    ownership_rules: Mapping[str, str]
    trace_requirements: tuple[str, ...]
    validation_constraints: tuple[str, ...]
    scope_exclusions: tuple[str, ...]
    boundary_assertions: Mapping[str, object]
    trace_reference: str
    evidence_digest: str

    def outcome(self) -> EvidenceOutcome:
        if not self.evidence_model_id or not self.governance_model_reference or not self.trace_reference or not self.evidence_digest:
            return EvidenceOutcome.EVIDENCE_MODEL_BLOCKED
        if not self.evidence_categories or not self.ownership_rules or not self.validation_constraints:
            return EvidenceOutcome.EVIDENCE_MODEL_INCOMPLETE
        if self.boundary_assertions.get("evidence_collection") is not False or self.boundary_assertions.get("evidence_storage") is not False:
            return EvidenceOutcome.EVIDENCE_MODEL_INCOMPLETE
        return EvidenceOutcome.EVIDENCE_MODEL_DEFINED_WITH_WARNINGS if not self.trace_requirements else EvidenceOutcome.EVIDENCE_MODEL_DEFINED
