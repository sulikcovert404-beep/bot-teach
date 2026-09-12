"""Immutable scope definition for production authorization wiring."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DEFINED = "AUTHORIZATION_SCOPE_DEFINED"
    DEFINED_WITH_WARNINGS = "AUTHORIZATION_SCOPE_DEFINED_WITH_WARNINGS"
    INCOMPLETE = "AUTHORIZATION_SCOPE_INCOMPLETE"
    BLOCKED = "AUTHORIZATION_SCOPE_BLOCKED"


@dataclass(frozen=True)
class AuthorizationProductionWiringScopeDefinition:
    identity_source: Tuple[str, ...] = ()
    identity_contract: Tuple[str, ...] = ()
    ownership_mapping: Tuple[str, ...] = ()
    permission_checks: Tuple[str, ...] = ()
    access_rules: Tuple[str, ...] = ()
    role_ownership_enforcement: Tuple[str, ...] = ()
    credential_boundary: Tuple[str, ...] = ()
    secret_handling: Tuple[str, ...] = ()
    audit_requirements: Tuple[str, ...] = ()
    existing_authorization_behavior: Tuple[str, ...] = ()
    regression_risks: Tuple[str, ...] = ()
    success_conditions: Tuple[str, ...] = ()
    failure_conditions: Tuple[str, ...] = ()
    rollback_boundary: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    authorization_scope_definition_only: bool = True
    implementation_execution: bool = False
    credential_change: bool = False
    database_change: bool = False
    migration_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.authorization_scope_definition_only:
            return Outcome.BLOCKED
        if any((self.implementation_execution, self.credential_change, self.database_change,
                self.migration_execution, self.runtime_activation, self.deployment)):
            return Outcome.BLOCKED
        required = (self.identity_source, self.identity_contract, self.ownership_mapping,
                    self.permission_checks, self.access_rules,
                    self.role_ownership_enforcement, self.credential_boundary,
                    self.secret_handling, self.audit_requirements,
                    self.existing_authorization_behavior, self.regression_risks,
                    self.success_conditions, self.failure_conditions,
                    self.rollback_boundary, self.decision)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.DEFINED_WITH_WARNINGS if self.warnings else Outcome.DEFINED
