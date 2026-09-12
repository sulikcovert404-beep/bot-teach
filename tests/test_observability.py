from datetime import datetime, timezone

import pytest

from app.services.observability import (
    MetricEvent,
    ObservabilityHook,
    StructuredLogEvent,
    TraceContext,
)


class Observer:
    def __init__(self, fail: bool = False) -> None:
        self.events = []
        self.fail = fail

    def observe(self, metric, log) -> None:
        if self.fail:
            raise RuntimeError("observer unavailable")
        self.events.append((metric, log))


def test_trace_and_metric_serialization_is_deterministic_and_preserves_zwnj() -> None:
    context = TraceContext("t1", "c1", "cmd1", "کاربر\u200c۱")
    assert context.serialize() == context.serialize()
    observer = Observer()
    hook = ObservabilityHook(observer, lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    metric = hook.project(context=context, metric_name="command_completed", result_status="accepted", command_type="publish")
    assert "کاربر\u200c۱" in observer.events[0][1].serialize()
    assert metric.timestamp == "2026-01-01T00:00:00.000000Z"


def test_missing_trace_context_is_rejected() -> None:
    with pytest.raises(ValueError):
        TraceContext("", "c", "cmd")


def test_observer_failure_does_not_change_projection() -> None:
    observer = Observer(fail=True)
    hook = ObservabilityHook(observer)
    metric = hook.project(context=TraceContext("t", "c", "cmd"), metric_name="command_rejected", result_status="rejected", command_type="x")
    assert metric.metric_name == "command_rejected"
    assert hook.observer_failures == 1


def test_metric_contract_rejects_unknown_name_and_negative_duration() -> None:
    with pytest.raises(ValueError):
        MetricEvent("unknown", "e", "2026-01-01T00:00:00Z", "t", "c", "cmd")
    with pytest.raises(ValueError):
        MetricEvent("workflow_duration", "e", "2026-01-01T00:00:00Z", "t", "c", "cmd", duration_ms=-1)


def test_structured_log_rejects_sensitive_fields() -> None:
    with pytest.raises(ValueError):
        StructuredLogEvent("x", "failed", "2026-01-01T00:00:00Z", {"password": "no"})
