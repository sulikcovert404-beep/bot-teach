"""Immutable validation record for authorization wiring foundation."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    VALIDATED = "AUTHORIZATION_WIRING_VALIDATED"
    VALIDATED_WITH_WARNINGS = "AUTHORIZATION_WIRING_VALIDATED_WITH_WARNINGS"
    FAILED = "AUTHORIZATION_WIRING_FAILED"
    BLOCKED = "AUTHORIZATION_WIRING_BLOCKED"


@dataclass(frozen=True)
class AuthorizationWiringValidation:
    allowed_path: tuple[str, ...] = ()
    denied_path: tuple[str, ...] = ()
    reason_consistency: tuple[str, ...] = ()
    command_trace: tuple[str, ...] = ()
    actor_trace: tuple[str, ...] = ()
    policy_version: tuple[str, ...] = ()
    deterministic_output: tuple[str, ...] = ()
    existing_policy: tuple[str, ...] = ()
    content_integration: tuple[str, ...] = ()
    regression: tuple[str, ...] = ()
    ownership_boundary: tuple[str, ...] = ()
    access_enforcement: tuple[str, ...] = ()
    failure_handling: tuple[str, ...] = ()
    identity_provider_gap: tuple[str, ...] = ()
    credential_gap: tuple[str, ...] = ()
    production_permission_gap: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    validation_only: bool = True
    next_wave_execution: bool = False
    identity_provider_change: bool = False
    credential_change: bool = False
    permission_change: bool = False
    database_change: bool = False
    migration_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.validation_only:
            return Outcome.BLOCKED
        if any((self.next_wave_execution, self.identity_provider_change,
                self.credential_change, self.permission_change, self.database_change,
                self.migration_execution, self.runtime_activation, self.deployment)):
            return Outcome.BLOCKED
        required = (self.allowed_path, self.denied_path, self.reason_consistency,
                    self.command_trace, self.actor_trace, self.policy_version,
                    self.deterministic_output, self.existing_policy,
                    self.content_integration, self.regression,
                    self.ownership_boundary, self.access_enforcement,
                    self.failure_handling, self.identity_provider_gap,
                    self.credential_gap, self.production_permission_gap,
                    self.decision)
        if any(not item for item in required):
            return Outcome.FAILED
        return Outcome.VALIDATED_WITH_WARNINGS if self.warnings else Outcome.VALIDATED
