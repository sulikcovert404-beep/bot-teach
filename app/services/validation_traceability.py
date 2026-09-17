"""Pure, provider-neutral traceability contract for validation pipelines."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class TraceEventType(str, Enum):
    CREATED = "CREATED"
    EVALUATED = "EVALUATED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class EdgeType(str, Enum):
    PARENT = "PARENT"
    CAUSATION = "CAUSATION"
    CORRELATION = "CORRELATION"


class TraceIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TraceReference:
    target_id: str
    target_type: str
    digest: str
    version: str

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.target_id, self.target_type, self.digest, self.version)):
            raise TraceIntegrityError("trace references require non-empty identity, type, digest, and version")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.digest):
            raise TraceIntegrityError("trace reference digest must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class ValidationTraceContext:
    trace_id: str
    request_reference: TraceReference
    decision_reference: TraceReference
    evidence_references: tuple[TraceReference, ...]
    plan_reference: TraceReference
    stage_reference: TraceReference
    correlation_reference: TraceReference | None = None

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise TraceIntegrityError("trace_id is required")
        if not isinstance(self.evidence_references, tuple):
            object.__setattr__(self, "evidence_references", tuple(self.evidence_references))

    def to_dict(self) -> dict[str, object]:
        def ref(r: TraceReference) -> dict[str, str]:
            return {"target_id": r.target_id, "target_type": r.target_type, "digest": r.digest.lower(), "version": r.version}
        return {"trace_id": self.trace_id, "request_reference": ref(self.request_reference), "decision_reference": ref(self.decision_reference), "evidence_references": [ref(r) for r in self.evidence_references], "plan_reference": ref(self.plan_reference), "stage_reference": ref(self.stage_reference), "correlation_reference": ref(self.correlation_reference) if self.correlation_reference else None}


@dataclass(frozen=True, slots=True)
class TraceEvent:
    event_id: str
    trace_id: str
    event_type: TraceEventType
    reference: TraceReference
    edge_type: EdgeType | None = None
    parent_event_id: str | None = None
    causation_event_id: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.trace_id.strip():
            raise TraceIntegrityError("event and trace identifiers are required")
        if self.edge_type is EdgeType.CORRELATION and self.causation_event_id:
            raise TraceIntegrityError("correlation cannot carry causation")

    def to_dict(self) -> dict[str, object]:
        return {"event_id": self.event_id, "trace_id": self.trace_id, "event_type": self.event_type.value, "reference": self.reference.__dict__ if hasattr(self.reference, "__dict__") else {"target_id": self.reference.target_id, "target_type": self.reference.target_type, "digest": self.reference.digest.lower(), "version": self.reference.version}, "edge_type": self.edge_type.value if self.edge_type else None, "parent_event_id": self.parent_event_id, "causation_event_id": self.causation_event_id, "correlation_id": self.correlation_id}


def canonical_bytes(value: object) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return unicodedata.normalize("NFC", text).encode("utf-8")


def digest_for(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_lineage(events: Iterable[TraceEvent]) -> None:
    items = tuple(events)
    by_id = {e.event_id: e for e in items}
    if len(by_id) != len(items):
        raise TraceIntegrityError("duplicate event identifier")
    for event in items:
        for parent in (event.parent_event_id, event.causation_event_id):
            if parent and parent not in by_id:
                raise TraceIntegrityError("missing lineage reference")
        if event.edge_type is EdgeType.CORRELATION and event.causation_event_id:
            raise TraceIntegrityError("correlation cannot be causal")
    graph = {e.event_id: tuple(x for x in (e.parent_event_id, e.causation_event_id) if x) for e in items}
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting: raise TraceIntegrityError("lineage cycle detected")
        if node in visited: return
        visiting.add(node)
        for parent in graph[node]: visit(parent)
        visiting.remove(node); visited.add(node)
    for node in graph: visit(node)
