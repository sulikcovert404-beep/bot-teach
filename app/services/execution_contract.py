"""Pure execution seam between control-plane decisions and future adapters."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import Any
from uuid import uuid4


class ExecutionOutcome(StrEnum):
    NOT_EXECUTED = "NOT_EXECUTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    AMBIGUOUS = "AMBIGUOUS"


class ExecutionContractError(ValueError):
    """Raised when an execution request cannot be safely constructed."""


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    execution_id: str
    decision_reference: str
    command_reference: str
    actor_reference: str
    trace_context: tuple[tuple[str, str], ...]
    digest_reference: str

    @classmethod
    def from_context(cls, context: Mapping[str, Any]) -> "ExecutionRequest":
        trace = tuple(sorted((str(k), _nfc(str(v))) for k, v in (context.get("trace_context") or {}).items()))
        return cls(
            str(context.get("execution_id") or uuid4()),
            _nfc(str(context.get("decision_reference") or "")),
            _nfc(str(context.get("command_reference") or "")),
            _nfc(str(context.get("actor_reference") or "")),
            trace,
            _nfc(str(context.get("digest_reference") or "")),
        )

    def canonical_json(self) -> str:
        return _canonical({"actor_reference": self.actor_reference, "command_reference": self.command_reference,
                           "decision_reference": self.decision_reference, "digest_reference": self.digest_reference,
                           "execution_id": self.execution_id, "trace_context": dict(self.trace_context)})


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    outcome: ExecutionOutcome
    result_reference: str | None
    error_classification: str | None
    started_at: str
    completed_at: str | None
    execution_id: str
    request_fingerprint: str

    def canonical_json(self) -> str:
        return _canonical({"completed_at": self.completed_at, "error_classification": self.error_classification,
                           "execution_id": self.execution_id, "outcome": self.outcome.value,
                           "request_fingerprint": self.request_fingerprint, "result_reference": self.result_reference,
                           "started_at": self.started_at})


def execute(decision: Any, context: Mapping[str, Any]) -> ExecutionResult:
    """Validate and materialize an execution intent; never performs effects."""
    request = ExecutionRequest.from_context(context)
    fingerprint = hashlib.sha256(request.canonical_json().encode("utf-8")).hexdigest()
    started = _nfc(str(context.get("started_at") or ""))
    if bool(context.get("cancelled")):
        return ExecutionResult(ExecutionOutcome.CANCELLED, None, "CANCELLATION_REQUESTED", started, None, request.execution_id, fingerprint)
    status = str(getattr(decision, "outcome", decision)).upper()
    if status not in {"APPROVED", "Outcome.APPROVED"}:
        return ExecutionResult(ExecutionOutcome.NOT_EXECUTED, None, f"DECISION_{status or 'INVALID'}", started, None, request.execution_id, fingerprint)
    expected = str(context.get("expected_digest") or request.digest_reference)
    if expected != request.digest_reference:
        return ExecutionResult(ExecutionOutcome.FAILED, None, "DECISION_DIGEST_MISMATCH", started, None, request.execution_id, fingerprint)
    return ExecutionResult(ExecutionOutcome.COMPLETED, f"execution:{request.execution_id}", None, started, _nfc(str(context.get("completed_at") or started)), request.execution_id, fingerprint)
