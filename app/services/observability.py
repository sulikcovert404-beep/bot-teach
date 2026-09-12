"""Provider-neutral observability contracts for the admin workflow.

The module contains only immutable value objects and an observer boundary.  It
does not import a metrics, tracing, logging, or persistence vendor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Callable, Mapping, Protocol
import uuid


def _timestamp(value: datetime | None = None) -> str:
    instant = (value or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    correlation_id: str
    command_id: str
    actor_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.trace_id or not self.correlation_id or not self.command_id:
            raise ValueError("trace_id, correlation_id, and command_id are required")

    def serialize(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


METRIC_NAMES = frozenset(
    {
        "command_received",
        "command_completed",
        "command_rejected",
        "validation_failed",
        "authorization_failed",
        "lifecycle_conflict",
        "audit_emission_failed",
        "workflow_duration",
    }
)


@dataclass(frozen=True)
class MetricEvent:
    metric_name: str
    event_id: str
    timestamp: str
    trace_id: str
    correlation_id: str
    command_id: str
    result_status: str | None = None
    duration_ms: float | None = None
    reference: str | None = None

    def __post_init__(self) -> None:
        if self.metric_name not in METRIC_NAMES:
            raise ValueError("unsupported metric name")
        if not self.event_id or not self.trace_id or not self.correlation_id or not self.command_id:
            raise ValueError("metric identifiers are required")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")

    def serialize(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_FORBIDDEN = frozenset(
    {
        "password", "passwd", "secret", "token", "credential", "authorization",
        "private_key", "national_id", "iban", "sheba", "raw_payload", "session",
    }
)
_ALLOWED = frozenset(
    {
        "event_type", "status", "trace_id", "correlation_id", "command_id", "actor_reference",
        "event_id", "timestamp", "duration_ms", "result_status", "command_type", "error_code",
        "content_id", "schema_version",
    }
)


def _validate_log_fields(fields: Mapping[str, Any]) -> None:
    for key in fields:
        normalized = key.casefold()
        if key not in _ALLOWED or any(fragment in normalized for fragment in _FORBIDDEN):
            raise ValueError(f"field is not permitted in structured logs: {key}")


@dataclass(frozen=True)
class StructuredLogEvent:
    event_type: str
    status: str
    timestamp: str
    fields: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type or not self.status:
            raise ValueError("event_type and status are required")
        _validate_log_fields(self.fields)
        object.__setattr__(self, "fields", dict(self.fields))

    def serialize(self) -> str:
        payload = {"event_type": self.event_type, "status": self.status, "timestamp": self.timestamp, **self.fields}
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ObservabilityObserver(Protocol):
    def observe(self, metric: MetricEvent, log: StructuredLogEvent) -> None: ...


class ObservabilityHook:
    """Observer-only hook. Observer failures are isolated from workflow results."""

    def __init__(self, observer: ObservabilityObserver, clock: Callable[[], datetime] | None = None) -> None:
        self._observer = observer
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.observer_failures = 0

    def project(self, *, context: TraceContext, metric_name: str, result_status: str,
                command_type: str, duration_ms: float | None = None) -> MetricEvent:
        now = _timestamp(self._clock())
        metric = MetricEvent(metric_name, str(uuid.uuid4()), now, context.trace_id,
                             context.correlation_id, context.command_id, result_status, duration_ms)
        log = StructuredLogEvent(metric_name, result_status, now, {
            "trace_id": context.trace_id, "correlation_id": context.correlation_id,
            "command_id": context.command_id, "actor_reference": context.actor_reference,
            "command_type": command_type, "result_status": result_status,
            **({"duration_ms": duration_ms} if duration_ms is not None else {}),
        })
        try:
            self._observer.observe(metric, log)
        except Exception:
            self.observer_failures += 1
        return metric
