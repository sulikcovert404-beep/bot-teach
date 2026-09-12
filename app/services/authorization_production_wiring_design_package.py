"""Immutable design package for production authorization wiring."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DESIGNED = "AUTHORIZATION_WIRING_DESIGNED"
    DESIGNED_WITH_WARNINGS = "AUTHORIZATION_WIRING_DESIGNED_WITH_WARNINGS"
    INCOMPLETE = "AUTHORIZATION_WIRING_INCOMPLETE"
    BLOCKED = "AUTHORIZATION_WIRING_BLOCKED"


@dataclass(frozen=True)
class AuthorizationProductionWiringDesignPackage:
    identity_flow: Tuple[str, ...] = ()
    identity_contract: Tuple[str, ...] = ()
    ownership_resolution: Tuple[str, ...] = ()
    permission_evaluation: Tuple[str, ...] = ()
    access_matrix: Tuple[str, ...] = ()
    role_enforcement: Tuple[str, ...] = ()
    credential_boundary: Tuple[str, ...] = ()
    secret_handling: Tuple[str, ...] = ()
    audit_trail: Tuple[str, ...] = ()
    existing_behavior_preservation: Tuple[str, ...] = ()
    migration_risks: Tuple[str, ...] = ()
    security_validation: Tuple[str, ...] = ()
    failure_handling: Tuple[str, ...] = ()
    rollback_strategy: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    authorization_design_only: bool = True
    implementation_execution: bool = False
    credential_change: bool = False
    permission_change: bool = False
    database_change: bool = False
    migration_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.authorization_design_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.credential_change,
                self.permission_change, self.database_change,
                self.migration_execution, self.runtime_activation, self.deployment)):
            return Outcome.BLOCKED
        required = (self.identity_flow, self.identity_contract,
                    self.ownership_resolution, self.permission_evaluation,
                    self.access_matrix, self.role_enforcement,
                    self.credential_boundary, self.secret_handling,
                    self.audit_trail, self.existing_behavior_preservation,
                    self.migration_risks, self.security_validation,
                    self.failure_handling, self.rollback_strategy, self.decision)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.DESIGNED_WITH_WARNINGS if self.warnings else Outcome.DESIGNED
