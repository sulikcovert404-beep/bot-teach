"""Pure, immutable validation contract for persistence + authorization integration."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Tuple


class IntegrationOutcome(StrEnum):
    VALIDATED = "FOUNDATION_INTEGRATION_VALIDATED"
    VALIDATED_WITH_WARNINGS = "FOUNDATION_INTEGRATION_VALIDATED_WITH_WARNINGS"
    FAILED = "FOUNDATION_INTEGRATION_FAILED"
    BLOCKED = "FOUNDATION_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class FoundationIntegrationValidation:
    creator_ownership: Tuple[str, ...] = ()
    authorization_enforcement: Tuple[str, ...] = ()
    data_access_boundaries: Tuple[str, ...] = ()
    create_authorize_persist: Tuple[str, ...] = ()
    update_authorize_version_check: Tuple[str, ...] = ()
    deny_no_mutation: Tuple[str, ...] = ()
    unauthorized_access: Tuple[str, ...] = ()
    conflict_handling: Tuple[str, ...] = ()
    data_integrity: Tuple[str, ...] = ()
    content_regression: Tuple[str, ...] = ()
    commands_regression: Tuple[str, ...] = ()
    admin_authorization_regression: Tuple[str, ...] = ()
    curriculum_pipeline_regression: Tuple[str, ...] = ()
    identity_provider_gap: Tuple[str, ...] = ()
    credential_gap: Tuple[str, ...] = ()
    runtime_activation_gap: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
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
