import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from tools.ai_metrics import build_snapshot, classify_health, parse_event_lines


def test_parse_and_snapshot_is_redacted_and_provider_neutral() -> None:
    lines = [
        'INFO ai_provider_event={"event_type":"ai_request_started","provider":"gemini","model":"flash"}',
        'INFO ai_provider_event={"event_type":"ai_request_completed","provider":"gemini","model":"flash","duration_ms":100}',
        'INFO ai_provider_event={"event_type":"ai_request_failed","provider":"gemini","model":"flash","error_type":"ProviderQuotaError","retry_after":2}',
        'INFO ai_provider_event={bad}',
    ]
    events, malformed = parse_event_lines(lines)
    snapshot = build_snapshot(events, malformed=malformed)
    assert snapshot["events"] == {"total": 3, "started": 1, "completed": 1, "failed": 1}
    assert snapshot["success_rate"] == 50.0
    assert snapshot["failure_rate"] == 50.0
    assert snapshot["errors"] == {"ProviderQuotaError": 1}
    assert snapshot["retry_after"] == [2]
    assert snapshot["latency_ms"] == {"count": 1, "avg": 100.0, "p50": 100.0, "p95": 100.0, "max": 100.0}
    assert snapshot["data_quality"]["malformed_events"] == 1
    assert snapshot["health_status"] == "INSUFFICIENT_DATA"
    assert snapshot["warnings"] == ["sample_size_too_small"]
    assert "prompt" not in str(snapshot).lower()


def test_empty_window_has_null_rates_and_latency() -> None:
    snapshot = build_snapshot([])
    assert snapshot["success_rate"] is None
    assert snapshot["failure_rate"] is None
    assert snapshot["latency_ms"]["count"] == 0
    assert snapshot["health_status"] == "INSUFFICIENT_DATA"


def test_health_classification_is_deterministic_for_thresholds() -> None:
    base = {"events": {"completed": 95, "failed": 5}, "failure_rate": 5.0, "latency_ms": {"p95": 1000}}
    assert classify_health(base, minimum_terminal_requests=100) == ("NORMAL", "Continue monitoring", [])
    warning = {**base, "failure_rate": 6.0}
    assert classify_health(warning, minimum_terminal_requests=100)[0] == "WARNING"
    critical = {**base, "failure_rate": 16.0}
    status, recommendation, warnings = classify_health(critical, minimum_terminal_requests=100)
    assert (status, recommendation, warnings) == ("CRITICAL", "Investigate provider failures", ["failure_rate_critical"])


def test_small_sample_wins_over_apparently_healthy_rate() -> None:
    snapshot = {"events": {"completed": 2, "failed": 0}, "failure_rate": 0.0, "latency_ms": {"p95": 1}}
    assert classify_health(snapshot) == ("INSUFFICIENT_DATA", "Continue collection", ["sample_size_too_small"])
