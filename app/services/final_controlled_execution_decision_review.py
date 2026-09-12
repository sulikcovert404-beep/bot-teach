"""Immutable final decision record for controlled execution."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    APPROVED = "EXECUTION_APPROVED"
    APPROVED_WITH_CONDITIONS = "EXECUTION_APPROVED_WITH_CONDITIONS"
    DEFERRED = "EXECUTION_DEFERRED"
    BLOCKED = "EXECUTION_BLOCKED"


@dataclass(frozen=True)
class FinalControlledExecutionDecisionReview:
    preparation_artifacts: Tuple[str, ...] = ()
    runbook: Tuple[str, ...] = ()
    rollback: Tuple[str, ...] = ()
    evidence: Tuple[str, ...] = ()
    residual_risks: Tuple[str, ...] = ()
    deferred_items: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    execution_owner: str = ""
    approval_owner: str = ""
    incident_owner: str = ""
    rollback_safety: Tuple[str, ...] = ()
    recovery_safety: Tuple[str, ...] = ()
    monitoring_safety: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: Tuple[str, ...] = ()
    final_execution_decision_review_only: bool = True
    execution_permission: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.final_execution_decision_review_only:
            return Outcome.BLOCKED
        if any((self.execution_permission, self.production_execution, self.deployment,
                self.migration_execution, self.database_change, self.credential_change,
                self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.preparation_artifacts, self.runbook, self.rollback, self.evidence,
                    self.deferred_items, self.execution_owner, self.approval_owner,
                    self.incident_owner, self.rollback_safety, self.recovery_safety,
                    self.monitoring_safety, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.APPROVED_WITH_CONDITIONS if self.conditions or self.residual_risks else Outcome.APPROVED
