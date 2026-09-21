"""Pure provider-neutral admin control-plane decision contract."""
from __future__ import annotations

import json
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4


class Outcome(StrEnum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CONFLICT = "CONFLICT"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


def _nfc(value: Any) -> Any:
    return unicodedata.normalize("NFC", value) if isinstance(value, str) else value


@dataclass(frozen=True, slots=True)
class Projection:
    reference: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    execution_id: str
    trace_id: str
    correlation_id: str
    outcome: Outcome
    reason_code: str
    workflow_result_reference: str | None = None
    validation_evidence: tuple[str, ...] = ()
    policy_reference: str | None = None
    audit: Projection = field(default_factory=Projection)
    observability: Projection = field(default_factory=Projection)

    def canonical_json(self) -> str:
        payload = {
            "audit": {"error": self.audit.error, "reference": self.audit.reference},
            "correlation_id": self.correlation_id,
            "execution_id": self.execution_id,
            "observability": {"error": self.observability.error, "reference": self.observability.reference},
            "outcome": self.outcome.value,
            "policy_reference": self.policy_reference,
            "reason_code": self.reason_code,
            "trace_id": self.trace_id,
            "validation_evidence": list(self.validation_evidence),
            "workflow_result_reference": self.workflow_result_reference,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ControlPlaneContext(Protocol):
    execution_id: str
    trace_id: str
    correlation_id: str


def execute_control_plane(
    context: Mapping[str, Any],
    *,
    decide: Callable[[Mapping[str, Any]], Any],
    audit_projector: Callable[[ExecutionReport], str] | None = None,
    observability_projector: Callable[[ExecutionReport], str] | None = None,
) -> ExecutionReport:
    """Coordinate decisions only; projection failures never change the outcome."""
    execution_id = str(context.get("execution_id") or uuid4())
    trace_id = _nfc(str(context.get("trace_id") or ""))
    correlation_id = _nfc(str(context.get("correlation_id") or ""))
    try:
        raw = decide(context)
        outcome = raw if isinstance(raw, Outcome) else Outcome(str(getattr(raw, "outcome", raw)))
        reason = str(getattr(raw, "reason_code", "ok"))
        evidence = tuple(str(x) for x in getattr(raw, "validation_evidence", ()))[:32]
        report = ExecutionReport(execution_id, trace_id, correlation_id, outcome, reason, getattr(raw, "workflow_result_reference", None), evidence, getattr(raw, "policy_reference", None))
    except Exception:  # noqa: BLE001
        report = ExecutionReport(execution_id, trace_id, correlation_id, Outcome.INTERNAL_FAILURE, "CONTROL_PLANE_UNHANDLED_FAULT")
    audit = Projection()
    obs = Projection()
    if audit_projector:
        try: audit = Projection(reference=str(audit_projector(report)))
        except Exception: audit = Projection(error="AUDIT_PROJECTION_FAILED")  # noqa: BLE001
    if observability_projector:
        try: obs = Projection(reference=str(observability_projector(report)))
        except Exception: obs = Projection(error="OBSERVABILITY_PROJECTION_FAILED")  # noqa: BLE001
    return replace(report, audit=audit, observability=obs)
