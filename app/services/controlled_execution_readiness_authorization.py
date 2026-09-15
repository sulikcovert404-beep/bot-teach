"""Immutable readiness authorization assessment; execution remains disabled."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    AUTHORIZED = "EXECUTION_AUTHORIZED"
    AUTHORIZED_WITH_CONDITIONS = "EXECUTION_AUTHORIZED_WITH_CONDITIONS"
    DEFERRED = "EXECUTION_DEFERRED"
    BLOCKED = "EXECUTION_BLOCKED"


@dataclass(frozen=True)
class ControlledExecutionReadinessAuthorization:
    allowed_execution_scope: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    rollback_authority: tuple[str, ...] = ()
    required_environments: tuple[str, ...] = ()
    configuration_readiness: tuple[str, ...] = ()
    dependency_availability: tuple[str, ...] = ()
    credential_requirements: tuple[str, ...] = ()
    permission_ownership: tuple[str, ...] = ()
    approval_chain: tuple[str, ...] = ()
    monitoring_activation: tuple[str, ...] = ()
    incident_path: tuple[str, ...] = ()
    recovery_ownership: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
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
