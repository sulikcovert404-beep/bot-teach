from app.core.logging import TelegramMetrics


def test_telegram_metrics_allowlist_and_snapshot() -> None:
    metrics = TelegramMetrics()
    metrics.auth_attempt()
    metrics.auth_failure("not-a-real-class")
    metrics.webhook_request("5xx")
    metrics.webhook_validation_failure("invalid_secret")
    metrics.dependency_failure("not-a-real-dependency")
    snapshot = metrics.snapshot()
    counters = snapshot["counters"]
    assert any("unknown_safe" in key for key in counters)
    assert all("not-a-real" not in key for key in counters)


def test_prometheus_output_is_bounded_and_redacted() -> None:
    metrics = TelegramMetrics()
    metrics.auth_failure("invalid_init_data")
    metrics.observe_latency("telegram_auth_latency_seconds", 0.125)
    output = metrics.prometheus()
    assert 'telegram_auth_failure_total{value="invalid_init_data"} 1' in output
    assert "telegram_auth_latency_seconds_sum_millis 125" in output
    for forbidden in ("Authorization: Bearer", "raw-secret-value", "full-payload", "student prompt"):
        assert forbidden not in output
