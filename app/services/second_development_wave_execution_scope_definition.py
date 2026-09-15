"""Immutable definition of the second-wave implementation scope."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    DEFINED = "SECOND_WAVE_SCOPE_DEFINED"
    DEFINED_WITH_WARNINGS = "SECOND_WAVE_SCOPE_DEFINED_WITH_WARNINGS"
    INCOMPLETE = "SECOND_WAVE_SCOPE_INCOMPLETE"
    BLOCKED = "SECOND_WAVE_SCOPE_BLOCKED"


@dataclass(frozen=True)
class SecondDevelopmentWaveExecutionScope:
    capability: str = ""
    purpose: str = ""
    user_system_behavior: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ()
    restricted_files: tuple[str, ...] = ()
    forbidden_files: tuple[str, ...] = ()
    input_contract: tuple[str, ...] = ()
    output_contract: tuple[str, ...] = ()
    error_contract: tuple[str, ...] = ()
    compatibility_requirements: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    required_tests: tuple[str, ...] = ()
    regression_tests: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    trace_reference: str = ""
    scope_definition_only: bool = True
    implementation_permission: bool = False
    feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.scope_definition_only or any((self.implementation_permission, self.feature_execution, self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required=(self.capability,self.purpose,self.user_system_behavior,self.non_goals,self.allowed_files,self.input_contract,self.output_contract,self.error_contract,self.compatibility_requirements,self.acceptance_criteria,self.required_tests,self.regression_tests,self.out_of_scope)
        if any(not x for x in required):
            return Outcome.INCOMPLETE
        return Outcome.DEFINED_WITH_WARNINGS if self.warnings else Outcome.DEFINED
