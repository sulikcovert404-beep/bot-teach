"""Pure, immutable foundation for post-governance operational readiness design."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum


class DesignOutcome(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    DESIGN_READY_WITH_WARNINGS = "DESIGN_READY_WITH_WARNINGS"
    DESIGN_NOT_READY = "DESIGN_NOT_READY"
    DESIGN_BLOCKED = "DESIGN_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OperationalReadinessDesignFoundation:
    foundation_id: str
    governance_phase_closure_reference: str
    operational_scope_definition: str
    future_capability_boundaries: tuple[str, ...]
    dependency_inventory: tuple[str, ...]
    risk_summary: tuple[str, ...]
    readiness_constraints: tuple[str, ...]
    boundary_assertions: Mapping[str, object]
    trace_reference: str
    foundation_digest: str

    @staticmethod
    def digest_payload(**values: object) -> str:
        body = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def outcome(self) -> DesignOutcome:
        if not self.foundation_id or not self.governance_phase_closure_reference or not self.trace_reference:
            return DesignOutcome.DESIGN_BLOCKED
        if self.boundary_assertions.get("runtime_activation") != "PROHIBITED" or self.boundary_assertions.get("execution") is not False:
            return DesignOutcome.DESIGN_NOT_READY
        if not self.foundation_digest:
            return DesignOutcome.DESIGN_NOT_READY
        return DesignOutcome.DESIGN_READY_WITH_WARNINGS if self.risk_summary else DesignOutcome.DESIGN_READY
