"""Provider-neutral immutable validation evidence contract."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
import re
import unicodedata
from typing import Optional


class EvidenceStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class EvidenceContractError(ValueError):
    pass


class DigestMismatchError(EvidenceContractError):
    pass


class LineageError(EvidenceContractError):
    pass


class SecretLikeValueError(EvidenceContractError):
    pass


_SECRET_PATTERNS = (
    re.compile(r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(?:postgres(?:ql)?|mysql)://[^\s]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
)


def _clean(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceContractError(f"{field} must be a non-empty string")
    return unicodedata.normalize("NFC", value)


def _reject_secrets(values: tuple[str, ...]) -> None:
    for value in values:
        if any(pattern.search(value) for pattern in _SECRET_PATTERNS):
            raise SecretLikeValueError("secret-like value is not permitted in evidence")


@dataclass(frozen=True, slots=True)
class ValidationEvidenceRecord:
    evidence_id: str
    validation_id: str
    plan_version: str
    result_status: EvidenceStatus
    artifact_reference: str
    digest: str
    timestamp_reference: str
    source_type: str
    validity_period: Optional[str] = None
    parent_evidence_reference: Optional[str] = None
    derived_evidence_reference: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("evidence_id", "validation_id", "plan_version", "artifact_reference", "digest", "timestamp_reference", "source_type"):
            object.__setattr__(self, name, _clean(getattr(self, name), field=name))
        if not isinstance(self.result_status, EvidenceStatus):
            try:
                object.__setattr__(self, "result_status", EvidenceStatus(self.result_status))
            except ValueError as exc:
                raise EvidenceContractError("unknown evidence status") from exc
        if self.validity_period is not None:
            object.__setattr__(self, "validity_period", _clean(self.validity_period, field="validity_period"))
        for name in ("parent_evidence_reference", "derived_evidence_reference"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _clean(value, field=name))
        _reject_secrets(tuple(v for v in (self.artifact_reference, self.timestamp_reference, self.source_type, self.validity_period or "") if v))

    def canonical_bytes(self) -> bytes:
        payload = {
            "artifact_reference": self.artifact_reference,
            "derived_evidence_reference": self.derived_evidence_reference,
            "evidence_id": self.evidence_id,
            "parent_evidence_reference": self.parent_evidence_reference,
            "plan_version": self.plan_version,
            "result_status": self.result_status.value,
            "source_type": self.source_type,
            "timestamp_reference": self.timestamp_reference,
            "validation_id": self.validation_id,
            "validity_period": self.validity_period,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def computed_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def verify_digest(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.digest) or self.computed_digest() != self.digest:
            raise DigestMismatchError("evidence digest does not match canonical record")

    def validate_lineage(self, *, known_ids: frozenset[str] = frozenset(), ancestors: frozenset[str] = frozenset()) -> None:
        for ref in (self.parent_evidence_reference, self.derived_evidence_reference):
            if ref is None:
                continue
            if ref == self.evidence_id or ref in ancestors:
                raise LineageError("circular evidence lineage")
            if known_ids and ref not in known_ids:
                raise LineageError("evidence lineage reference is unresolved")

    def as_dict(self) -> dict[str, object]:
        return json.loads(self.canonical_bytes().decode("utf-8"))

