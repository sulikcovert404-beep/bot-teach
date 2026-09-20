"""Provider-neutral declarative runtime validation plan contracts."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationOutcome(str, Enum):
    PASSED='PASSED'; FAILED='FAILED'; BLOCKED='BLOCKED'; UNKNOWN='UNKNOWN'; REQUIRES_REVALIDATION='REQUIRES_REVALIDATION'; NOT_RUN='NOT_RUN'

@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    evidence_id: str
    version: str
    digest: str
    validity_reference: str

@dataclass(frozen=True, slots=True)
class ValidationStep:
    validation_id: str
    order: int
    dependencies: tuple[str, ...]
    applicability: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    input_evidence: tuple[EvidenceRequirement, ...]
    expected_evidence: tuple[EvidenceRequirement, ...]
    digest: str
    validity_reference: str
    failure_policy: str
    timeout_budget_ms: int = 0
    cleanup_expectation: str = 'NONE'
    sandbox_requirement: str = 'NONE'

@dataclass(frozen=True, slots=True)
class RuntimeValidationPlan:
    plan_id: str
    version: str
    validation_steps: tuple[ValidationStep, ...]
    prerequisites: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    evidence_requirements: tuple[EvidenceRequirement, ...]
    failure_policy: str
    rollback_reference: str
    invalidation_graph: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def ordered_steps(self) -> tuple[ValidationStep, ...]:
        return tuple(sorted(self.validation_steps, key=lambda s: (s.order, s.validation_id)))

    def forward_dependencies(self) -> dict[str, tuple[str, ...]]:
        return {s.validation_id: s.dependencies for s in self.validation_steps}

    def reverse_invalidations(self) -> dict[str, tuple[str, ...]]:
        return dict(self.invalidation_graph)

    def canonical_bytes(self) -> bytes:
        def norm(v: Any) -> Any:
            if isinstance(v, Enum): return v.value
            if isinstance(v, str): return unicodedata.normalize('NFC', v)
            if isinstance(v, tuple): return [norm(x) for x in v]
            if hasattr(v, '__dataclass_fields__'): return {k: norm(getattr(v,k)) for k in v.__dataclass_fields__}
            if isinstance(v, dict): return {k: norm(v[k]) for k in sorted(v)}
            return v
        return json.dumps(norm(self), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

    def plan_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

def propagate_outcome(plan: RuntimeValidationPlan, outcomes: dict[str, ValidationOutcome]) -> dict[str, ValidationOutcome]:
    result = dict(outcomes)
    for step in plan.ordered_steps():
        if step.validation_id not in result:
            result[step.validation_id] = ValidationOutcome.NOT_RUN
        if any(result.get(dep) in {ValidationOutcome.FAILED, ValidationOutcome.BLOCKED, ValidationOutcome.NOT_RUN} for dep in step.dependencies):
            result[step.validation_id] = ValidationOutcome.NOT_RUN
        elif any(dep not in result for dep in step.dependencies):
            result[step.validation_id] = ValidationOutcome.NOT_RUN
    return result

