"""Pure, advisory foundation for validation and observability semantics."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class Outcome(str, Enum):
    READY = "VALIDATION_OBSERVABILITY_READY"
    READY_WITH_WARNINGS = "VALIDATION_OBSERVABILITY_READY_WITH_WARNINGS"
    INCOMPLETE = "VALIDATION_OBSERVABILITY_INCOMPLETE"
    BLOCKED = "VALIDATION_OBSERVABILITY_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OperationalValidationObservabilityFoundationPackage:
    validation_layers: Tuple[str, ...] = ()
    validation_ownership: Tuple[str, ...] = ()
    validation_criteria: Tuple[str, ...] = ()
    metric_semantics: Tuple[str, ...] = ()
    signal_categories: Tuple[str, ...] = ()
    event_classification: Tuple[str, ...] = ()
    health_states: Tuple[str, ...] = ()
    degradation_semantics: Tuple[str, ...] = ()
    warning_model: Tuple[str, ...] = ()
    failure_classification: Tuple[str, ...] = ()
    finding_lifecycle: Tuple[str, ...] = ()
    improvement_tracking: Tuple[str, ...] = ()
    review_cycle: Tuple[str, ...] = ()
    escalation_model: Tuple[str, ...] = ()
    blockers: Tuple[str, ...] = ()
    trace_reference: str = ""
    validation_design_only: bool = True
    observability_design_only: bool = True
    runtime_monitoring: bool = False
    runtime_execution: bool = False
    runtime_activation: bool = False
    runtime_admission: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not (self.validation_design_only and self.observability_design_only):
            return Outcome.INCOMPLETE
        if any((self.runtime_monitoring, self.runtime_execution, self.runtime_activation,
                self.runtime_admission, self.deployment, self.database_change,
                self.infrastructure_change)):
            return Outcome.INCOMPLETE
        required = (self.validation_layers, self.validation_ownership,
                    self.validation_criteria, self.metric_semantics,
                    self.signal_categories, self.health_states,
                    self.finding_lifecycle)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return (Outcome.READY_WITH_WARNINGS if self.blockers else Outcome.READY)
