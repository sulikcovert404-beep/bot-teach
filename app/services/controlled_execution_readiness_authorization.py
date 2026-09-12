"""Immutable readiness authorization assessment; execution remains disabled."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    AUTHORIZED = "EXECUTION_AUTHORIZED"
    AUTHORIZED_WITH_CONDITIONS = "EXECUTION_AUTHORIZED_WITH_CONDITIONS"
    DEFERRED = "EXECUTION_DEFERRED"
    BLOCKED = "EXECUTION_BLOCKED"


@dataclass(frozen=True)
class ControlledExecutionReadinessAuthorization:
    allowed_execution_scope: Tuple[str, ...] = ()
    forbidden_actions: Tuple[str, ...] = ()
    rollback_authority: Tuple[str, ...] = ()
    required_environments: Tuple[str, ...] = ()
    configuration_readiness: Tuple[str, ...] = ()
    dependency_availability: Tuple[str, ...] = ()
    credential_requirements: Tuple[str, ...] = ()
    permission_ownership: Tuple[str, ...] = ()
    approval_chain: Tuple[str, ...] = ()
    monitoring_activation: Tuple[str, ...] = ()
    incident_path: Tuple[str, ...] = ()
    recovery_ownership: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    execution_readiness_review_only: bool = True
    execution_permission: bool = False
    production_execution: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False
    runtime_activation: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.execution_readiness_review_only:
            return Outcome.BLOCKED
        if any((self.execution_permission, self.production_execution, self.deployment,
                self.migration_execution, self.database_change, self.credential_change,
                self.runtime_activation)):
            return Outcome.BLOCKED
        required = (self.allowed_execution_scope, self.forbidden_actions,
                    self.rollback_authority, self.required_environments,
                    self.configuration_readiness, self.dependency_availability,
                    self.credential_requirements, self.permission_ownership,
                    self.approval_chain, self.monitoring_activation, self.incident_path,
                    self.recovery_ownership, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.AUTHORIZED_WITH_CONDITIONS if self.conditions else Outcome.AUTHORIZED
