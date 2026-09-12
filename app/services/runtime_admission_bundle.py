"""Pure immutable contract for assembling pre-runtime admission evidence."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class BundleOutcome(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class ReferenceStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
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
        return [_clean(item) for item in value]
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
class ReferenceToken:
    """Opaque, digest-bearing reference; payloads must never be embedded."""

    reference_id: str
    digest: str
    status: ReferenceStatus = ReferenceStatus.VALID

    def __post_init__(self) -> None:
        if not self.reference_id or not self.digest:
            raise ValueError("reference_id and digest are required")
        _reject_secrets(self.reference_id)
        _reject_secrets(self.digest)

    def to_dict(self) -> dict[str, str]:
        return {"reference_id": self.reference_id, "digest": self.digest, "status": self.status.value}


@dataclass(frozen=True, slots=True)
class RuntimeAdmissionBundle:
    bundle_id: str
    target_stage: str
    release_decision_reference: ReferenceToken
    stage_admission_reference: ReferenceToken
    runtime_entry_reference: ReferenceToken
    environment_reference: ReferenceToken
    evidence_references: tuple[ReferenceToken, ...]
    validation_references: tuple[ReferenceToken, ...]
    trace_reference: ReferenceToken
    bundle_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        _reject_secrets(self.payload())
        if not self.bundle_id or not self.target_stage:
            raise ValueError("bundle_id and target_stage are required")
        if not self.evidence_references or not self.validation_references:
            raise ValueError("evidence_references and validation_references are required")
        if self.bundle_digest and self.bundle_digest != self.compute_digest():
            raise ValueError("bundle digest mismatch")
        if not self.bundle_digest:
            object.__setattr__(self, "bundle_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "target_stage": self.target_stage,
            "release_decision_reference": self.release_decision_reference.to_dict(),
            "stage_admission_reference": self.stage_admission_reference.to_dict(),
            "runtime_entry_reference": self.runtime_entry_reference.to_dict(),
            "environment_reference": self.environment_reference.to_dict(),
            "evidence_references": [item.to_dict() for item in self.evidence_references],
            "validation_references": [item.to_dict() for item in self.validation_references],
            "trace_reference": self.trace_reference.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return _canonical(self.payload())

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.bundle_digest == self.compute_digest()


def validate_runtime_admission_bundle(bundle: RuntimeAdmissionBundle) -> BundleOutcome:
    """Classify a bundle without I/O, clock access, or mutation."""
    if not bundle.digest_matches():
        return BundleOutcome.INVALID
    refs = (
        bundle.release_decision_reference,
        bundle.stage_admission_reference,
        bundle.runtime_entry_reference,
        bundle.environment_reference,
        *bundle.evidence_references,
        *bundle.validation_references,
        bundle.trace_reference,
    )
    statuses = {ref.status for ref in refs}
    if ReferenceStatus.INVALID in statuses:
        return BundleOutcome.INVALID
    if ReferenceStatus.BLOCKED in statuses:
        return BundleOutcome.BLOCKED
    if ReferenceStatus.REQUIRES_REVIEW in statuses:
        return BundleOutcome.REQUIRES_REVIEW
    return BundleOutcome.VALID


def build_runtime_admission_bundle(
    *,
    bundle_id: str,
    target_stage: str,
    release_decision_reference: ReferenceToken,
    stage_admission_reference: ReferenceToken,
    runtime_entry_reference: ReferenceToken,
    environment_reference: ReferenceToken,
    evidence_references: Iterable[ReferenceToken],
    validation_references: Iterable[ReferenceToken],
    trace_reference: ReferenceToken,
) -> tuple[BundleOutcome, RuntimeAdmissionBundle | None]:
    """Build a bundle only when dependencies are admissible."""
    bundle = RuntimeAdmissionBundle(
        bundle_id, target_stage, release_decision_reference, stage_admission_reference,
        runtime_entry_reference, environment_reference, tuple(evidence_references),
        tuple(validation_references), trace_reference,
    )
    outcome = validate_runtime_admission_bundle(bundle)
    if outcome is not BundleOutcome.VALID:
        return outcome, None
    return outcome, bundle
