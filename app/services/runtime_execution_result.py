"""Pure immutable contract for recording a future runtime execution result."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from collections.abc import Iterable

from .runtime_admission_bundle import BundleOutcome, ReferenceStatus, ReferenceToken, RuntimeAdmissionBundle, validate_runtime_admission_bundle
from .runtime_execution_boundary import ExecutionBoundaryContract


class ExecutionResultStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return sorted((_clean(item) for item in value), key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _reject_secrets(value: Any) -> None:
    if isinstance(value, str) and _SECRET.search(value):
        raise ValueError("secret-like content is not permitted")
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET.search(str(key)):
                raise ValueError("secret-like field is not permitted")
            _reject_secrets(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _reject_secrets(item)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    execution_id: str
    boundary_reference: ReferenceToken
    admission_bundle_reference: ReferenceToken
    status: ExecutionResultStatus
    output_reference: ReferenceToken | None
    evidence_references: tuple[ReferenceToken, ...]
    trace_reference: ReferenceToken
    result_digest: str = field(default="", repr=False)
    failure_reference: ReferenceToken | None = None
    recovery_reference: ReferenceToken | None = None

    def __post_init__(self) -> None:
        if not self.execution_id or not self.boundary_reference or not self.admission_bundle_reference or not self.trace_reference:
            raise ValueError("execution_id, boundary, admission, and trace references are required")
        if self.status in (ExecutionResultStatus.SUCCEEDED, ExecutionResultStatus.PARTIAL) and self.output_reference is None:
            raise ValueError("successful and partial results require an output reference")
        if self.status is ExecutionResultStatus.PARTIAL and not self.evidence_references:
            raise ValueError("partial result requires explicit evidence")
        _reject_secrets(self.payload())
        if self.result_digest and self.result_digest != self.compute_digest():
            raise ValueError("result digest mismatch")
        if not self.result_digest:
            object.__setattr__(self, "result_digest", self.compute_digest())

    @staticmethod
    def _ref(value: ReferenceToken | None) -> dict[str, str] | None:
        return value.to_dict() if value is not None else None

    def payload(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "boundary_reference": self.boundary_reference.to_dict(),
            "admission_bundle_reference": self.admission_bundle_reference.to_dict(),
            "status": self.status.value,
            "output_reference": self._ref(self.output_reference),
            "evidence_references": [item.to_dict() for item in self.evidence_references],
            "trace_reference": self.trace_reference.to_dict(),
            "failure_reference": self._ref(self.failure_reference),
            "recovery_reference": self._ref(self.recovery_reference),
        }

    def canonical_bytes(self) -> bytes:
        return _canonical(self.payload())

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.result_digest == self.compute_digest()


def validate_execution_result(
    result: ExecutionResult,
    boundary: ExecutionBoundaryContract | None = None,
    admission_bundle: RuntimeAdmissionBundle | None = None,
) -> bool:
    """Validate integrity and optional concrete upstream bindings without side effects."""
    if not result.digest_matches() or result.trace_reference.status is not ReferenceStatus.VALID:
        return False
    if result.status is ExecutionResultStatus.UNKNOWN and result.output_reference is not None:
        return False
    if result.status is ExecutionResultStatus.PARTIAL and not result.evidence_references:
        return False
    if boundary is not None and (not boundary.digest_matches() or result.boundary_reference.digest != boundary.boundary_digest):
        return False
    if admission_bundle is not None and (validate_runtime_admission_bundle(admission_bundle) is not BundleOutcome.VALID or result.admission_bundle_reference.digest != admission_bundle.bundle_digest):
        return False
    if boundary is not None and admission_bundle is not None and boundary.admission_bundle_reference.digest != admission_bundle.bundle_digest:
        return False
    return True


def build_execution_result(
    *,
    execution_id: str,
    boundary_reference: ReferenceToken,
    admission_bundle_reference: ReferenceToken,
    status: ExecutionResultStatus,
    output_reference: ReferenceToken | None,
    evidence_references: Iterable[ReferenceToken],
    trace_reference: ReferenceToken,
    failure_reference: ReferenceToken | None = None,
    recovery_reference: ReferenceToken | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        execution_id, boundary_reference, admission_bundle_reference, status, output_reference,
        tuple(evidence_references), trace_reference, failure_reference=failure_reference,
        recovery_reference=recovery_reference,
    )
