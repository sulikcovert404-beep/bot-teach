"""Immutable, provider-neutral transition planning foundation."""
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class TransitionOutcome(str, Enum):
    TRANSITION_READY = "TRANSITION_READY"
    TRANSITION_READY_WITH_WARNINGS = "TRANSITION_READY_WITH_WARNINGS"
    TRANSITION_INCOMPLETE = "TRANSITION_INCOMPLETE"
    TRANSITION_BLOCKED = "TRANSITION_BLOCKED"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class TransitionPlanningFoundation:
    foundation_id: str
    current_phase_reference: str
    future_phase_boundary: str
    transition_objectives: tuple[str, ...]
    dependency_assumptions: tuple[str, ...]
    change_categories: tuple[str, ...]
    impact_classification: Mapping[str, str]
    risk_levels: Mapping[str, str]
    required_review_boundaries: tuple[str, ...]
    rollback_scenarios: tuple[str, ...]
    failure_categories: tuple[str, ...]
    recovery_constraints: tuple[str, ...]
    restore_boundaries: tuple[str, ...]
    ownership_boundary: str
    responsibility_transition: str
    handoff_evidence_requirements: tuple[str, ...]
    review_package_scope: tuple[str, ...]
    review_inputs: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    trace_reference: str
    foundation_digest: str
    execution: bool = False
    transition_design_only: bool = True

    def outcome(self) -> TransitionOutcome:
        required=(self.foundation_id,self.current_phase_reference,self.future_phase_boundary,
                  self.trace_reference,self.foundation_digest)
        if not all(required): return TransitionOutcome.TRANSITION_BLOCKED
        if not self.transition_objectives or not self.dependency_assumptions or not self.change_categories or not self.required_review_boundaries:
            return TransitionOutcome.TRANSITION_INCOMPLETE
        if not self.rollback_scenarios or not self.failure_categories or not self.recovery_constraints or not self.restore_boundaries:
            return TransitionOutcome.TRANSITION_INCOMPLETE
        if not self.ownership_boundary or not self.responsibility_transition or not self.handoff_evidence_requirements:
            return TransitionOutcome.TRANSITION_INCOMPLETE
        if not self.review_package_scope or not self.review_inputs: return TransitionOutcome.TRANSITION_INCOMPLETE
        if self.execution or not self.transition_design_only: return TransitionOutcome.TRANSITION_INCOMPLETE
        return (TransitionOutcome.TRANSITION_READY_WITH_WARNINGS if self.unresolved_items else TransitionOutcome.TRANSITION_READY)

    def canonical_payload(self) -> str:
        return json.dumps(self._payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _payload(self) -> dict:
        return {k: v for k,v in self.__dict__.items() if k != "foundation_digest"}

    @staticmethod
    def digest_for(payload: Mapping[str, object]) -> str:
        raw=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
