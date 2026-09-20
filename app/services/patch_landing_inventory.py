"""Evidence-bound patch landing inventory and persistence delta contracts."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class InventoryClassification(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class InventoryEntry:
    identifier: str
    owner_module: str
    version: str
    dependencies: tuple[str, ...] = ()
    state_vocabulary: tuple[str, ...] = ()
    serialization_rules: tuple[str, ...] = ()
    persistence_requirement: str = "NONE"
    runtime_dependency_status: str = "NONE"
    presence: bool | None = None
    conformance: bool | None = None
    dependency_closure: bool | None = None
    classification: InventoryClassification = InventoryClassification.UNKNOWN
    digest: str = ""

    def with_digest(self) -> InventoryEntry:
        payload = {k: v for k, v in canonical_entry(self).items() if k != "digest"}
        digest = hashlib.sha256(_encode(payload)).hexdigest()
        return InventoryEntry(**{**self.__dict__, "digest": digest})


@dataclass(frozen=True)
class DeltaRow:
    identifier: str
    current_contract: str
    required_persistence: str
    delta_kind: str
    missing_boundary: str | None = None
    transaction_ownership: str | None = None
    migration_requirement: str | None = None
    concurrency_evidence: str | None = None
    recovery_evidence: str | None = None


@dataclass(frozen=True)
class EvidenceGate:
    name: str
    evidence_reference: str | None
    status: str = "UNKNOWN"


def classify(*, presence: bool | None, conformance: bool | None,
             dependency_closure: bool | None, blocked: bool = False) -> InventoryClassification:
    if blocked:
        return InventoryClassification.BLOCKED
    if None in (presence, conformance, dependency_closure):
        return InventoryClassification.UNKNOWN
    if not presence:
        return InventoryClassification.MISSING
    if presence and conformance and dependency_closure:
        return InventoryClassification.READY
    return InventoryClassification.PARTIAL


def _encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_entry(entry: InventoryEntry) -> Mapping[str, Any]:
    return {"classification": entry.classification.value, "conformance": entry.conformance,
            "dependencies": sorted(entry.dependencies), "dependency_closure": entry.dependency_closure,
            "digest": entry.digest, "identifier": entry.identifier, "owner_module": entry.owner_module,
            "persistence_requirement": entry.persistence_requirement, "presence": entry.presence,
            "runtime_dependency_status": entry.runtime_dependency_status,
            "serialization_rules": sorted(entry.serialization_rules), "state_vocabulary": sorted(entry.state_vocabulary),
            "version": entry.version}


def canonical_matrix(entries: tuple[InventoryEntry, ...], deltas: tuple[DeltaRow, ...],
                    gates: tuple[EvidenceGate, ...]) -> Mapping[str, Any]:
    return {"deltas": [r.__dict__ for r in sorted(deltas, key=lambda x: x.identifier)],
            "entries": [canonical_entry(e) for e in sorted(entries, key=lambda x: x.identifier)],
            "evidence_gates": [g.__dict__ for g in sorted(gates, key=lambda x: x.name)]}


def matrix_digest(entries: tuple[InventoryEntry, ...], deltas: tuple[DeltaRow, ...],
                  gates: tuple[EvidenceGate, ...]) -> str:
    return hashlib.sha256(_encode(canonical_matrix(entries, deltas, gates))).hexdigest()
