"""Pure validation record for the third-wave content capability."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    VALIDATED = "CONTENT_VALIDATED"
    VALIDATED_WITH_WARNINGS = "CONTENT_VALIDATED_WITH_WARNINGS"
    FAILED = "CONTENT_VALIDATION_FAILED"
    BLOCKED = "CONTENT_BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveValidation:
    implementation_outcome: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    behavior_correctness: tuple[str, ...] = ()
    test_coverage: tuple[str, ...] = ()
    regression_status: str = ""
    compatibility: tuple[str, ...] = ()
    typed_result_consistency: tuple[str, ...] = ()
    deterministic_reasons: tuple[str, ...] = ()
    preserved_behavior: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    trace_reference: str = ""
    validation_only: bool = True
    new_feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.validation_only:
            return Outcome.BLOCKED
        if any((self.new_feature_execution, self.runtime_execution, self.deployment,
                self.database_change, self.infrastructure_change, self.credential_change)):
            return Outcome.BLOCKED
        if self.implementation_outcome not in {"ACCEPTED", "PASS"}:
            return Outcome.FAILED
        required = (self.acceptance_criteria, self.behavior_correctness,
                    self.test_coverage, self.regression_status, self.compatibility,
                    self.typed_result_consistency, self.deterministic_reasons,
                    self.preserved_behavior)
        if any(not value for value in required):
            return Outcome.FAILED
        return Outcome.VALIDATED_WITH_WARNINGS if self.warnings else Outcome.VALIDATED

