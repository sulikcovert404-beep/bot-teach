"""Immutable execution plan for a development wave; it performs no execution."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "WAVE_PLAN_READY"
    READY_WITH_WARNINGS = "WAVE_PLAN_READY_WITH_WARNINGS"
    INCOMPLETE = "WAVE_PLAN_INCOMPLETE"
    BLOCKED = "WAVE_PLAN_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DevelopmentWaveExecutionPlan:
    selected_work_packages: Tuple[str, ...] = ()
    implementation_sequence: Tuple[str, ...] = ()
    milestones: Tuple[str, ...] = ()
    technical_tasks: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    expected_outputs: Tuple[str, ...] = ()
    unit_test_expectations: Tuple[str, ...] = ()
    review_checkpoints: Tuple[str, ...] = ()
    acceptance_flow: Tuple[str, ...] = ()
    implementation_risks: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    mitigation_actions: Tuple[str, ...] = ()
    completion_criteria: Tuple[str, ...] = ()
    handoff_requirements: Tuple[str, ...] = ()
    closure_conditions: Tuple[str, ...] = ()
    trace_reference: str = ""
    wave_execution_planning_only: bool = True
    implementation_execution: bool = False
    feature_execution: bool = False
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.wave_execution_planning_only or any((self.implementation_execution,
                self.feature_execution, self.runtime_execution, self.deployment,
                self.database_change, self.infrastructure_change, self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.selected_work_packages, self.implementation_sequence,
                    self.milestones, self.technical_tasks, self.dependencies,
                    self.expected_outputs, self.unit_test_expectations,
                    self.review_checkpoints, self.acceptance_flow,
                    self.completion_criteria, self.handoff_requirements,
                    self.closure_conditions)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY
