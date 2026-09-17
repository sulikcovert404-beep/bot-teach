"""Pure consistency validation for readiness design artifacts; no state enforcement."""
from dataclasses import dataclass
from enum import Enum


class ConsistencyOutcome(str, Enum):
    STATE_CONSISTENT="STATE_CONSISTENT"; STATE_CONSISTENT_WITH_WARNINGS="STATE_CONSISTENT_WITH_WARNINGS"; STATE_INCONSISTENT="STATE_INCONSISTENT"; STATE_BLOCKED="STATE_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessStateConsistencyValidation:
    validation_id: str; state_model_reference: str; decision_framework_reference: str; review_framework_reference: str; assessment_reference: str; consistency_rules: tuple[str,...]; transition_checks: tuple[str,...]; conflict_findings: tuple[str,...]; validation_constraints: tuple[str,...]; scope_exclusions: tuple[str,...]; boundary_assertions: dict[str,object]; trace_reference: str; validation_digest: str
    def outcome(self)->ConsistencyOutcome:
        if not all((self.validation_id,self.state_model_reference,self.decision_framework_reference,self.review_framework_reference,self.assessment_reference,self.trace_reference,self.validation_digest)): return ConsistencyOutcome.STATE_BLOCKED
        if not self.consistency_rules or not self.transition_checks: return ConsistencyOutcome.STATE_INCONSISTENT
        if self.conflict_findings: return ConsistencyOutcome.STATE_INCONSISTENT
        if self.boundary_assertions.get('execution') is not False or self.boundary_assertions.get('runtime_state') is not False: return ConsistencyOutcome.STATE_INCONSISTENT
        return ConsistencyOutcome.STATE_CONSISTENT
