"""Pure, immutable validation contract for persistence + authorization integration."""
from dataclasses import dataclass
from enum import StrEnum


class IntegrationOutcome(StrEnum):
    VALIDATED = "FOUNDATION_INTEGRATION_VALIDATED"
    VALIDATED_WITH_WARNINGS = "FOUNDATION_INTEGRATION_VALIDATED_WITH_WARNINGS"
    FAILED = "FOUNDATION_INTEGRATION_FAILED"
    BLOCKED = "FOUNDATION_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class FoundationIntegrationValidation:
    creator_ownership: tuple[str, ...] = ()
    authorization_enforcement: tuple[str, ...] = ()
    data_access_boundaries: tuple[str, ...] = ()
    create_authorize_persist: tuple[str, ...] = ()
    update_authorize_version_check: tuple[str, ...] = ()
    deny_no_mutation: tuple[str, ...] = ()
    unauthorized_access: tuple[str, ...] = ()
    conflict_handling: tuple[str, ...] = ()
    data_integrity: tuple[str, ...] = ()
    content_regression: tuple[str, ...] = ()
    commands_regression: tuple[str, ...] = ()
    admin_authorization_regression: tuple[str, ...] = ()
    curriculum_pipeline_regression: tuple[str, ...] = ()
    identity_provider_gap: tuple[str, ...] = ()
    credential_gap: tuple[str, ...] = ()
    runtime_activation_gap: tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: tuple[str, ...] = ()
    integration_validation_only: bool = True
    identity_provider_change: bool = False
    credential_change: bool = False
    permission_change: bool = False
    database_change: bool = False
    migration_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False

    def outcome(self) -> IntegrationOutcome:
        if not self.integration_validation_only or not self.trace_reference:
            return IntegrationOutcome.BLOCKED
        if any((self.identity_provider_change, self.credential_change,
                self.permission_change, self.database_change,
                self.migration_execution, self.runtime_activation, self.deployment)):
            return IntegrationOutcome.BLOCKED
        required = (
            self.creator_ownership, self.authorization_enforcement,
            self.data_access_boundaries, self.create_authorize_persist,
            self.update_authorize_version_check, self.deny_no_mutation,
            self.unauthorized_access, self.conflict_handling, self.data_integrity,
            self.content_regression, self.commands_regression,
            self.admin_authorization_regression, self.curriculum_pipeline_regression,
            self.identity_provider_gap, self.credential_gap,
            self.runtime_activation_gap, self.decision,
        )
        if any(not value for value in required):
            return IntegrationOutcome.FAILED
        return (IntegrationOutcome.VALIDATED_WITH_WARNINGS
                if self.warnings else IntegrationOutcome.VALIDATED)
