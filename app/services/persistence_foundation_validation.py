"""Immutable validation record for the persistence foundation wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    VALIDATED = "PERSISTENCE_FOUNDATION_VALIDATED"
    VALIDATED_WITH_WARNINGS = "PERSISTENCE_FOUNDATION_VALIDATED_WITH_WARNINGS"
    FAILED = "PERSISTENCE_FOUNDATION_FAILED"
    BLOCKED = "PERSISTENCE_FOUNDATION_BLOCKED"


@dataclass(frozen=True)
class PersistenceFoundationValidation:
    creator_isolation: Tuple[str, ...] = ()
    snapshot_stability: Tuple[str, ...] = ()
    ordering_guarantees: Tuple[str, ...] = ()
    backward_compatibility: Tuple[str, ...] = ()
    regression_tests: Tuple[str, ...] = ()
    contract_preservation: Tuple[str, ...] = ()
    deterministic_behavior: Tuple[str, ...] = ()
    in_memory_limitation: Tuple[str, ...] = ()
    production_storage_gap: Tuple[str, ...] = ()
    migration_readiness: Tuple[str, ...] = ()
    decision: str = ""
    trace_reference: str = ""
    warnings: Tuple[str, ...] = ()
    validation_only: bool = True
    next_wave_execution: bool = False
    runtime_activation: bool = False
    deployment: bool = False
    migration_execution: bool = False
    database_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.validation_only:
            return Outcome.BLOCKED
        if any((self.next_wave_execution, self.runtime_activation, self.deployment,
                self.migration_execution, self.database_change, self.credential_change)):
            return Outcome.BLOCKED
        required = (self.creator_isolation, self.snapshot_stability,
                    self.ordering_guarantees, self.backward_compatibility,
                    self.regression_tests, self.contract_preservation,
                    self.deterministic_behavior, self.in_memory_limitation,
                    self.production_storage_gap, self.migration_readiness,
                    self.decision)
        if any(not item for item in required):
            return Outcome.FAILED
        return Outcome.VALIDATED_WITH_WARNINGS if self.warnings else Outcome.VALIDATED
