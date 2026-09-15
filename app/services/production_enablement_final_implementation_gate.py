"""Immutable final implementation gate for production enablement."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    APPROVED = "IMPLEMENTATION_APPROVED"
    APPROVED_WITH_CONDITIONS = "IMPLEMENTATION_APPROVED_WITH_CONDITIONS"
    DEFERRED = "IMPLEMENTATION_DEFERRED"
    BLOCKED = "IMPLEMENTATION_BLOCKED"


@dataclass(frozen=True)
class ProductionEnablementFinalImplementationGate:
    approved_changes: tuple[str, ...] = ()
    excluded_changes: tuple[str, ...] = ()
    readiness: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    data_risks: tuple[str, ...] = ()
    security_risks: tuple[str, ...] = ()
    operational_risks: tuple[str, ...] = ()
    rollback_ownership: str = ""
    recovery_readiness: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    conditions: tuple[str, ...] = ()
    final_implementation_gate_only: bool = True
    implementation_permission: bool = False
    migration_execution: bool = False
    database_change: bool = False
    deployment: bool = False
    runtime_activation: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.final_implementation_gate_only:
            return Outcome.BLOCKED
        if any((self.implementation_permission, self.migration_execution,
                self.database_change, self.deployment, self.runtime_activation,
                self.credential_change)):
            return Outcome.BLOCKED
        required = (self.approved_changes, self.excluded_changes, self.readiness,
                    self.data_risks, self.security_risks, self.operational_risks,
                    self.rollback_ownership, self.recovery_readiness, self.decision)
        if any(not item for item in required):
            return Outcome.DEFERRED
        if self.blockers:
            return Outcome.BLOCKED
        return Outcome.APPROVED_WITH_CONDITIONS if self.conditions else Outcome.APPROVED
