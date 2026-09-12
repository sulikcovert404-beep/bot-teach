"""Immutable validation record for the content integration boundary."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    VALIDATED = "CONTENT_INTEGRATION_VALIDATED"
    VALIDATED_WITH_WARNINGS = "CONTENT_INTEGRATION_VALIDATED_WITH_WARNINGS"
    FAILED = "CONTENT_INTEGRATION_FAILED"
    BLOCKED = "CONTENT_INTEGRATION_BLOCKED"


@dataclass(frozen=True)
class ContentIntegrationValidation:
    create_flow: Tuple[str, ...] = ()
    update_flow: Tuple[str, ...] = ()
    ownership_enforcement: Tuple[str, ...] = ()
    conflict_handling: Tuple[str, ...] = ()
    persistence_adapter_contract: Tuple[str, ...] = ()
    authorization_contract: Tuple[str, ...] = ()
    typed_result_behavior: Tuple[str, ...] = ()
    existing_content_behavior: Tuple[str, ...] = ()
    command_compatibility: Tuple[str, ...] = ()
    api_compatibility: Tuple[str, ...] = ()
    in_memory_limitation: Tuple[str, ...] = ()
    migration_readiness: Tuple[str, ...] = ()
    production_gap: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    validation_only: bool = True
    new_integration_execution: bool = False
    database_change: bool = False
    migration_execution: bool = False
    deployment: bool = False
    runtime_activation: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.validation_only:
            return Outcome.BLOCKED
        if any((self.new_integration_execution, self.database_change,
                self.migration_execution, self.deployment, self.runtime_activation,
                self.credential_change)):
            return Outcome.BLOCKED
        required = (self.create_flow, self.update_flow, self.ownership_enforcement,
                    self.conflict_handling, self.persistence_adapter_contract,
                    self.authorization_contract, self.typed_result_behavior,
                    self.existing_content_behavior, self.command_compatibility,
                    self.api_compatibility, self.in_memory_limitation,
                    self.migration_readiness, self.production_gap, self.decision)
        if any(not item for item in required):
            return Outcome.FAILED
        return Outcome.VALIDATED_WITH_WARNINGS if self.warnings else Outcome.VALIDATED
