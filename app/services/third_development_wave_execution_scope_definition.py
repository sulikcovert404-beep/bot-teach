"""Immutable execution scope for the third development wave."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    DEFINED = "SCOPE_DEFINED"
    BLOCKED = "SCOPE_BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveExecutionScopeDefinition:
    capability: str = ""
    objective: str = ""
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    expected_behavior: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ()
    restricted_files: tuple[str, ...] = ()
    forbidden_changes: tuple[str, ...] = ()
    success_scenarios: tuple[str, ...] = ()
    error_scenarios: tuple[str, ...] = ()
    regression_scenarios: tuple[str, ...] = ()
    edge_cases: tuple[str, ...] = ()
    new_tests: tuple[str, ...] = ()
    regression_tests: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    implementation_changes: tuple[str, ...] = ()
    preserved_behavior: tuple[str, ...] = ()
    trace_reference: str = ""
    scope_definition_only: bool = True
    implementation_permission: bool = False
    feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference or not self.scope_definition_only:
            return Outcome.BLOCKED
        if any((self.implementation_permission, self.feature_execution, self.runtime_execution,
                self.deployment, self.database_change, self.infrastructure_change)):
            return Outcome.BLOCKED
        required = (self.capability, self.objective, self.inputs, self.outputs,
                    self.expected_behavior, self.allowed_files, self.forbidden_changes,
                    self.success_scenarios, self.error_scenarios,
                    self.regression_scenarios, self.edge_cases, self.new_tests,
                    self.regression_tests, self.out_of_scope, self.implementation_changes,
                    self.preserved_behavior)
        return Outcome.DEFINED if all(required) else Outcome.BLOCKED
