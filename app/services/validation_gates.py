"""Pure validation gate contracts for the admin pipeline."""
from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

GATE_ORDER: tuple[str, ...] = (
    "configuration_valid",
    "metadata_valid",
    "authorization_valid",
    "lifecycle_valid",
    "policy_valid",
    "digest_valid",
)


class GateStatus(str, Enum):
    PASSED = "Passed"
    FAILED = "Failed"
    BLOCKED = "Blocked"
    SKIPPED = "Skipped"


class GateReasonCode(str, Enum):
    OK = "ok"
    NOT_APPLICABLE = "not_applicable"
    MISSING_PREREQUISITE = "missing_prerequisite"
    INVALID_GATE = "invalid_gate"
    GATE_FAILED = "gate_failed"
    GATE_EXCEPTION = "gate_exception"
    INVALID_RESULT = "invalid_result"


def _safe_text(value: str) -> str:
    """Normalize human text while retaining Persian ZWNJ and safe RTL content."""
    return unicodedata.normalize("NFC", value)


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_name: str
    status: GateStatus
    reason_code: GateReasonCode
    safe_message: str
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.gate_name not in GATE_ORDER and self.gate_name != "unknown":
            raise ValueError("unknown gate name")
        object.__setattr__(self, "safe_message", _safe_text(self.safe_message))
        object.__setattr__(self, "details", tuple((str(k), _safe_text(str(v))) for k, v in self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "reason_code": self.reason_code.value,
            "safe_message": self.safe_message,
            "details": {k: v for k, v in self.details},
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    results: tuple[GateResult, ...]
    stopped_at: str | None = None

    @property
    def valid(self) -> bool:
        return bool(self.results) and all(r.status in (GateStatus.PASSED, GateStatus.SKIPPED) for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {"results": [r.to_dict() for r in self.results], "stopped_at": self.stopped_at, "valid": self.valid}

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ValidationGate(Protocol):
    gate_name: str

    def evaluate(self, context: Mapping[str, Any]) -> GateResult:
        """Evaluate without mutation, I/O, clocks, or external calls."""


def _blocked(name: str, code: GateReasonCode, message: str) -> GateResult:
    return GateResult(name, GateStatus.BLOCKED, code, message)


def run_validation_gates(
    context: Mapping[str, Any],
    gates: Sequence[ValidationGate] | None = None,
) -> ValidationReport:
    """Run gates in the fixed order, stopping at the first Failed/Blocked result."""
    supplied = tuple(gates if gates is not None else context.get("gates", ()))
    by_name: dict[str, ValidationGate] = {}
    results: list[GateResult] = []
    for gate in supplied:
        name = getattr(gate, "gate_name", None)
        if not isinstance(name, str) or name not in GATE_ORDER or name in by_name:
            _bad_name = name if isinstance(name, str) else "unknown"
            result = GateResult("unknown", GateStatus.BLOCKED, GateReasonCode.INVALID_GATE, "Unknown validation gate")
            return ValidationReport(tuple((*results, result)), "unknown")  # noqa: C409
        by_name[name] = gate

    for name in GATE_ORDER:
        gate = by_name.get(name)
        if gate is None:
            result = _blocked(name, GateReasonCode.MISSING_PREREQUISITE, "Validation gate is unavailable")
        else:
            try:
                result = gate.evaluate(context)
                if not isinstance(result, GateResult) or result.gate_name != name:
                    result = _blocked(name, GateReasonCode.INVALID_RESULT, "Validation gate returned an invalid result")
            except Exception:  # noqa: BLE001
                result = _blocked(name, GateReasonCode.GATE_EXCEPTION, "Validation gate could not be evaluated")
        results.append(result)
        if result.status in (GateStatus.FAILED, GateStatus.BLOCKED):
            return ValidationReport(tuple(results), name)
    return ValidationReport(tuple(results))
