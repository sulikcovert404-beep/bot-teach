"""Immutable operational-readiness contract; it grants no runtime permission."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple


class OperationalOutcome(StrEnum):
    READY = "OPERATIONAL_READY"
    READY_WITH_WARNINGS = "OPERATIONAL_READY_WITH_WARNINGS"
    DEFERRED = "OPERATIONAL_DEFERRED"
    BLOCKED = "OPERATIONAL_BLOCKED"


@dataclass(frozen=True)
class OperationalReadinessPackage:
    activation_boundary: Tuple[str, ...] = ()
    runtime_ownership: Tuple[str, ...] = ()
    stop_conditions: Tuple[str, ...] = ()
    identity_provider_path: Tuple[str, ...] = ()
    credential_lifecycle: Tuple[str, ...] = ()
    secret_boundaries: Tuple[str, ...] = ()
    health_signals: Tuple[str, ...] = ()
    audit_visibility: Tuple[str, ...] = ()
    failure_detection: Tuple[str, ...] = ()
    incident_ownership: Tuple[str, ...] = ()
    recovery_flow: Tuple[str, ...] = ()
    rollback_triggers: Tuple[str, ...] = ()
    activation_sequence: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
