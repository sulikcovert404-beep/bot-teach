"""Provider-neutral persistence readiness contracts; no runtime adapter."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PersistenceResult(str, Enum):
    STORED = "STORED"
    CONFLICT = "CONFLICT"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PersistenceEvidence:
    migration: str | None = None
    transaction: str | None = None
    recovery: str | None = None
    audit_durability: str | None = None

    @property
    def complete(self) -> bool:
        return all((self.migration, self.transaction, self.recovery, self.audit_durability))


@dataclass(frozen=True)
class PersistenceRecord:
    result: PersistenceResult
    contract_version: str
    schema_version: str
    digest: str | None = None
    reference: str | None = None
    detail: str | None = None


def map_persistence_result(value: str) -> PersistenceResult:
    try:
        return PersistenceResult(value.upper())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"unknown persistence result: {value!r}") from exc


def readiness_status(evidence: PersistenceEvidence) -> str:
    return "READY" if evidence.complete else "NOT_READY"


def canonical_record(record: PersistenceRecord) -> Mapping[str, Any]:
    return {
        "contract_version": record.contract_version,
        "digest": record.digest,
        "reference": record.reference,
        "result": record.result.value,
        "schema_version": record.schema_version,
        "detail": record.detail,
    }
