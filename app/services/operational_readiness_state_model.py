"""Readiness state design only; it never manages runtime or permission state."""
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class StateOutcome(str, Enum):
    STATE_MODEL_DEFINED="STATE_MODEL_DEFINED"; STATE_MODEL_DEFINED_WITH_WARNINGS="STATE_MODEL_DEFINED_WITH_WARNINGS"; STATE_MODEL_INCOMPLETE="STATE_MODEL_INCOMPLETE"; STATE_MODEL_BLOCKED="STATE_MODEL_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessStateModel:
    state_model_id: str; decision_framework_reference: str; decision_review_reference: str; assessment_reference: str; state_definitions: Mapping[str,str]; state_transition_rules: tuple[str,...]; state_constraints: tuple[str,...]; scope_exclusions: tuple[str,...]; boundary_assertions: Mapping[str,object]; trace_reference: str; state_digest: str
    def outcome(self)->StateOutcome:
        if not all((self.state_model_id,self.decision_framework_reference,self.decision_review_reference,self.assessment_reference,self.trace_reference,self.state_digest)): return StateOutcome.STATE_MODEL_BLOCKED
        if not self.state_definitions or not self.state_transition_rules or not self.state_constraints: return StateOutcome.STATE_MODEL_INCOMPLETE
        if self.boundary_assertions.get('runtime_state') is not False or self.boundary_assertions.get('activation_state') is not False or self.boundary_assertions.get('permission_state') is not False: return StateOutcome.STATE_MODEL_INCOMPLETE
        return StateOutcome.STATE_MODEL_DEFINED
