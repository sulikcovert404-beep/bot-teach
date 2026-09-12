"""Database-free typed audit contract for admin workflow results."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any, Callable, Protocol

@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    command_id: str
    correlation_id: str
    causation_id: str
    actor: dict[str, Any]
    action: str
    target: dict[str, Any]
    previous_state: dict[str, Any] | None
    new_state: dict[str, Any] | None
    result_status: str
    schema_version: str
    timestamp: str
    digest_reference: str | None = None

    def serialize(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

class AuditSink(Protocol):
    def emit(self, event: AuditEvent) -> None: ...

class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

class AuditHook:
    """Observer-only projection; it never changes the workflow result."""
    def __init__(self, sink: AuditSink, clock: Callable[[], datetime] | None = None) -> None:
        self.sink = sink
        self.clock = clock or (lambda: datetime.now(timezone.utc))
    def project(self, *, event_id: str, command_id: str, correlation_id: str, causation_id: str,
                actor: dict[str, Any], action: str, target: dict[str, Any], result_status: str,
                previous_state: dict[str, Any] | None = None, new_state: dict[str, Any] | None = None,
                schema_version: str = "audit-v1", digest_reference: str | None = None) -> AuditEvent:
        if not event_id or not command_id or not correlation_id or not causation_id or not action or not result_status:
            raise ValueError("audit identifiers and status are required")
        timestamp = self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        event = AuditEvent(event_id, command_id, correlation_id, causation_id, dict(actor), action, dict(target), previous_state, new_state, result_status, schema_version, timestamp, digest_reference)
        self.sink.emit(event)
        return event
