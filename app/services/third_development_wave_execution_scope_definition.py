"""Immutable execution scope for the third development wave."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    DEFINED = "SCOPE_DEFINED"
    BLOCKED = "SCOPE_BLOCKED"


@dataclass(frozen=True)
class ThirdDevelopmentWaveExecutionScopeDefinition:
    capability: str = ""
    objective: str = ""
    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()
    expected_behavior: Tuple[str, ...] = ()
    allowed_files: Tuple[str, ...] = ()
    restricted_files: Tuple[str, ...] = ()
    forbidden_changes: Tuple[str, ...] = ()
    success_scenarios: Tuple[str, ...] = ()
    error_scenarios: Tuple[str, ...] = ()
    regression_scenarios: Tuple[str, ...] = ()
    edge_cases: Tuple[str, ...] = ()
    new_tests: Tuple[str, ...] = ()
    regression_tests: Tuple[str, ...] = ()
    out_of_scope: Tuple[str, ...] = ()
    implementation_changes: Tuple[str, ...] = ()
    preserved_behavior: Tuple[str, ...] = ()
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
