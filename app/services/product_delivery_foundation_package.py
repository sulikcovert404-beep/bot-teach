"""Immutable product-delivery planning contract; it grants no execution authority."""
from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    READY = "DELIVERY_FOUNDATION_READY"
    READY_WITH_WARNINGS = "DELIVERY_FOUNDATION_READY_WITH_WARNINGS"
    INCOMPLETE = "DELIVERY_FOUNDATION_INCOMPLETE"
    BLOCKED = "DELIVERY_FOUNDATION_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProductDeliveryFoundationPackage:
    capability_inventory: tuple[str, ...] = ()
    feature_boundaries: tuple[str, ...] = ()
    business_objectives: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    delivery_streams: tuple[str, ...] = ()
    component_ownership: tuple[str, ...] = ()
    integration_assumptions: tuple[str, ...] = ()
    implementation_roadmap: tuple[str, ...] = ()
    dependency_ordering: tuple[str, ...] = ()
    milestone_planning: tuple[str, ...] = ()
    technical_risks: tuple[str, ...] = ()
    testing_strategy: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    review_gates: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    next_execution_candidates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    trace_reference: str = ""
    product_delivery_planning_only: bool = True
    runtime_execution: bool = False
    runtime_activation: bool = False
    runtime_admission: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> Outcome:
        if not self.trace_reference:
            return Outcome.BLOCKED
        if not self.product_delivery_planning_only:
            return Outcome.INCOMPLETE
        if any((self.runtime_execution, self.runtime_activation, self.runtime_admission,
                self.deployment, self.database_change, self.infrastructure_change,
                self.credential_change)):
            return Outcome.INCOMPLETE
        required = (self.capability_inventory, self.feature_boundaries,
                    self.business_objectives, self.success_criteria,
                    self.delivery_streams, self.component_ownership,
                    self.implementation_roadmap, self.dependency_ordering,
                    self.testing_strategy, self.acceptance_criteria)
        if any(not item for item in required):
            return Outcome.INCOMPLETE
        return Outcome.READY_WITH_WARNINGS if self.warnings else Outcome.READY
