"""Pure, advisory foundation for validation and observability semantics."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "VALIDATION_OBSERVABILITY_READY"
    READY_WITH_WARNINGS = "VALIDATION_OBSERVABILITY_READY_WITH_WARNINGS"
    INCOMPLETE = "VALIDATION_OBSERVABILITY_INCOMPLETE"
    BLOCKED = "VALIDATION_OBSERVABILITY_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OperationalValidationObservabilityFoundationPackage:
    validation_layers: tuple[str, ...] = ()
    validation_ownership: tuple[str, ...] = ()
    validation_criteria: tuple[str, ...] = ()
    metric_semantics: tuple[str, ...] = ()
    signal_categories: tuple[str, ...] = ()
    event_classification: tuple[str, ...] = ()
    health_states: tuple[str, ...] = ()
    degradation_semantics: tuple[str, ...] = ()
    warning_model: tuple[str, ...] = ()
    failure_classification: tuple[str, ...] = ()
    finding_lifecycle: tuple[str, ...] = ()
    improvement_tracking: tuple[str, ...] = ()
    review_cycle: tuple[str, ...] = ()
    escalation_model: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
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
