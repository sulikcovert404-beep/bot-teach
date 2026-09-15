"""Readiness decision design; decisions never generate permission or execute actions."""
from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping

class DecisionOutcome(str, Enum):
    DECISION_FRAMEWORK_DEFINED="DECISION_FRAMEWORK_DEFINED"; DECISION_FRAMEWORK_DEFINED_WITH_WARNINGS="DECISION_FRAMEWORK_DEFINED_WITH_WARNINGS"; DECISION_FRAMEWORK_INCOMPLETE="DECISION_FRAMEWORK_INCOMPLETE"; DECISION_FRAMEWORK_BLOCKED="DECISION_FRAMEWORK_BLOCKED"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class OperationalReadinessDecisionFramework:
    decision_framework_id: str; governance_model_reference: str; assessment_framework_reference: str; evidence_model_reference: str; traceability_contract_reference: str; decision_rules: tuple[str,...]; precedence_rules: tuple[str,...]; decision_constraints: tuple[str,...]; scope_exclusions: tuple[str,...]; boundary_assertions: Mapping[str,object]; trace_reference: str; decision_digest: str
    def outcome(self)->DecisionOutcome:
        if not all((self.decision_framework_id,self.governance_model_reference,self.assessment_framework_reference,self.evidence_model_reference,self.traceability_contract_reference,self.trace_reference,self.decision_digest)): return DecisionOutcome.DECISION_FRAMEWORK_BLOCKED
        if not self.decision_rules or not self.precedence_rules or not self.decision_constraints: return DecisionOutcome.DECISION_FRAMEWORK_INCOMPLETE
        if self.boundary_assertions.get('permission_generation') is not False or self.boundary_assertions.get('execution') is not False: return DecisionOutcome.DECISION_FRAMEWORK_INCOMPLETE
        return DecisionOutcome.DECISION_FRAMEWORK_DEFINED
