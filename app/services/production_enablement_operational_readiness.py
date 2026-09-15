"""Immutable operational-readiness contract; it grants no runtime permission."""
from dataclasses import dataclass
from enum import StrEnum


class OperationalOutcome(StrEnum):
    READY = "OPERATIONAL_READY"
    READY_WITH_WARNINGS = "OPERATIONAL_READY_WITH_WARNINGS"
    DEFERRED = "OPERATIONAL_DEFERRED"
    BLOCKED = "OPERATIONAL_BLOCKED"


@dataclass(frozen=True)
class OperationalReadinessPackage:
    activation_boundary: tuple[str, ...] = ()
    runtime_ownership: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    identity_provider_path: tuple[str, ...] = ()
    credential_lifecycle: tuple[str, ...] = ()
    secret_boundaries: tuple[str, ...] = ()
    health_signals: tuple[str, ...] = ()
    audit_visibility: tuple[str, ...] = ()
    failure_detection: tuple[str, ...] = ()
    incident_ownership: tuple[str, ...] = ()
    recovery_flow: tuple[str, ...] = ()
    rollback_triggers: tuple[str, ...] = ()
    activation_sequence: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    operational_readiness_only: bool = True
    runtime_activation: bool = False
    deployment: bool = False
    credential_change: bool = False
    identity_provider_change: bool = False
    database_change: bool = False
    migration_execution: bool = False

    def outcome(self) -> OperationalOutcome:
        if not self.operational_readiness_only or not self.trace_reference:
            return OperationalOutcome.BLOCKED
        if any((self.runtime_activation, self.deployment, self.credential_change,
                self.identity_provider_change, self.database_change,
                self.migration_execution)):
            return OperationalOutcome.BLOCKED
        required = (
            self.activation_boundary, self.runtime_ownership, self.stop_conditions,
            self.identity_provider_path, self.credential_lifecycle,
            self.secret_boundaries, self.health_signals, self.audit_visibility,
            self.failure_detection, self.incident_ownership, self.recovery_flow,
            self.rollback_triggers, self.activation_sequence, self.decision,
        )
        if any(not value for value in required):
            return OperationalOutcome.DEFERRED
        return (OperationalOutcome.READY_WITH_WARNINGS
                if self.warnings else OperationalOutcome.READY)
