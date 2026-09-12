"""Pure immutable boundary contract between admission evidence and future runtime."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from .runtime_admission_bundle import (
    BundleOutcome,
    ReferenceToken,
    ReferenceStatus,
    RuntimeAdmissionBundle,
    validate_runtime_admission_bundle,
)


class ExecutionScope(StrEnum):
    READ_ONLY = "READ_ONLY"
    VALIDATION_ONLY = "VALIDATION_ONLY"
    CONTROLLED_EXECUTION = "CONTROLLED_EXECUTION"


class BoundaryOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


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
class ExecutionBoundaryContract:
    boundary_id: str
    admission_bundle_reference: ReferenceToken
    execution_scope: ExecutionScope
    allowed_operations: frozenset[str]
    denied_operations: frozenset[str]
    actor_reference: str
    trace_reference: ReferenceToken
    boundary_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.boundary_id or not self.actor_reference:
            raise ValueError("boundary_id and actor_reference are required")
        if not self.admission_bundle_reference or not self.trace_reference:
            raise ValueError("admission and trace references are required")
        if any(not isinstance(item, str) or not item for item in (*self.allowed_operations, *self.denied_operations)):
            raise ValueError("operation names must be non-empty strings")
        if self.allowed_operations & self.denied_operations:
            raise ValueError("operation cannot be both allowed and denied")
        _reject_secrets(self.payload())
        if self.boundary_digest and self.boundary_digest != self.compute_digest():
            raise ValueError("boundary digest mismatch")
        if not self.boundary_digest:
            object.__setattr__(self, "boundary_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "admission_bundle_reference": self.admission_bundle_reference.to_dict(),
            "execution_scope": self.execution_scope.value,
            "allowed_operations": sorted(self.allowed_operations),
            "denied_operations": sorted(self.denied_operations),
            "actor_reference": self.actor_reference,
            "trace_reference": self.trace_reference.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return _canonical(self.payload())

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.boundary_digest == self.compute_digest()


def evaluate_boundary(
    boundary: ExecutionBoundaryContract,
    admission_bundle: RuntimeAdmissionBundle,
    operation: str,
    *,
    actor_reference: str | None = None,
) -> BoundaryOutcome:
    """Evaluate one operation without I/O, mutation, execution, or clock access."""
    if not operation or not boundary.digest_matches():
        return BoundaryOutcome.BLOCKED
    if boundary.admission_bundle_reference.status is not ReferenceStatus.VALID or boundary.trace_reference.status is not ReferenceStatus.VALID:
        return BoundaryOutcome.BLOCKED
    if validate_runtime_admission_bundle(admission_bundle) is not BundleOutcome.VALID:
        return BoundaryOutcome.BLOCKED
    if boundary.admission_bundle_reference.digest != admission_bundle.bundle_digest:
        return BoundaryOutcome.BLOCKED
    if actor_reference is not None and actor_reference != boundary.actor_reference:
        return BoundaryOutcome.BLOCKED
    if operation in boundary.denied_operations or operation not in boundary.allowed_operations:
        return BoundaryOutcome.REJECTED
    return BoundaryOutcome.ACCEPTED


def build_execution_boundary(
    *,
    boundary_id: str,
    admission_bundle_reference: ReferenceToken,
    execution_scope: ExecutionScope,
    allowed_operations: Iterable[str],
    denied_operations: Iterable[str],
    actor_reference: str,
    trace_reference: ReferenceToken,
) -> ExecutionBoundaryContract:
    """Construct a boundary contract; no permission is inferred from scope."""
    return ExecutionBoundaryContract(
        boundary_id=boundary_id,
        admission_bundle_reference=admission_bundle_reference,
        execution_scope=execution_scope,
        allowed_operations=frozenset(allowed_operations),
        denied_operations=frozenset(denied_operations),
        actor_reference=actor_reference,
        trace_reference=trace_reference,
    )
