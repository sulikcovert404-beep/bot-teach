"""Read-only AI provider health snapshots from structured journal events."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Iterable

MARKER = "ai_provider_event="
DEFAULT_MIN_TERMINAL_REQUESTS = 100
DEFAULT_FAILURE_WARNING_PERCENT = 5.0
DEFAULT_FAILURE_CRITICAL_PERCENT = 15.0
DEFAULT_P95_WARNING_MS = 8000.0


def parse_event_lines(lines: Iterable[str]) -> tuple[list[dict[str, object]], int]:
    events: list[dict[str, object]] = []
    malformed = 0
    for line in lines:
        if MARKER not in line:
            continue
        try:
            event = json.loads(line.split(MARKER, 1)[1])
        except (TypeError, ValueError, json.JSONDecodeError):
            malformed += 1
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            malformed += 1
    return events, malformed


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((percentile / 100) * len(ordered) + 0.999999) - 1))
    return round(ordered[index], 2)


def classify_health(
    snapshot: dict[str, object],
    *,
    minimum_terminal_requests: int = DEFAULT_MIN_TERMINAL_REQUESTS,
    failure_warning_percent: float = DEFAULT_FAILURE_WARNING_PERCENT,
    failure_critical_percent: float = DEFAULT_FAILURE_CRITICAL_PERCENT,
    p95_warning_ms: float = DEFAULT_P95_WARNING_MS,
) -> tuple[str, str, list[str]]:
    """Return a deterministic advisory status, recommendation, and warnings.

    Reliability status is deliberately ``INSUFFICIENT_DATA`` until the minimum
    sample is available. This prevents a low-traffic window from being treated
    as healthy or from triggering an automated routing decision.
    """
    events = snapshot.get("events", {})
    terminal = int(events.get("completed", 0)) + int(events.get("failed", 0))
    warnings: list[str] = []
    if terminal < minimum_terminal_requests:
        warnings.append("sample_size_too_small")
        return "INSUFFICIENT_DATA", "Continue collection", warnings

    failure_rate = snapshot.get("failure_rate")
    latency = snapshot.get("latency_ms", {})
    p95 = latency.get("p95") if isinstance(latency, dict) else None
    if isinstance(failure_rate, (int, float)) and failure_rate > failure_critical_percent:
        warnings.append("failure_rate_critical")
        return "CRITICAL", "Investigate provider failures", warnings
    if isinstance(failure_rate, (int, float)) and failure_rate > failure_warning_percent:
        warnings.append("failure_rate_elevated")
    if isinstance(p95, (int, float)) and p95 > p95_warning_ms:
        warnings.append("p95_latency_elevated")
    if warnings:
        return "WARNING", "Investigate provider health", warnings
    return "NORMAL", "Continue monitoring", warnings


def build_snapshot(events: Iterable[dict[str, object]], *, malformed: int = 0) -> dict[str, object]:
    items = list(events)
    counts = Counter(str(event.get("event_type", "unknown")) for event in items)
    completed = [event for event in items if event.get("event_type") == "ai_request_completed"]
    failed = [event for event in items if event.get("event_type") == "ai_request_failed"]
    durations = [float(event["duration_ms"]) for event in completed if isinstance(event.get("duration_ms"), (int, float))]
    errors = Counter(str(event.get("error_type", "unknown")) for event in failed)
    distributions = Counter(
        (str(event.get("provider", "unknown")), str(event.get("model", "unknown"))) for event in items
    )
    started = counts.get("ai_request_started", 0)
    terminal = len(completed) + len(failed)
    snapshot = {
        "events": {"total": len(items), "started": started, "completed": len(completed), "failed": len(failed)},
        "success_rate": round(len(completed) / terminal * 100, 2) if terminal else None,
        "failure_rate": round(len(failed) / terminal * 100, 2) if terminal else None,
        "errors": dict(sorted(errors.items())),
        "retry_after": sorted({event.get("retry_after") for event in failed if event.get("retry_after") is not None}),
        "provider_models": {f"{provider}/{model}": count for (provider, model), count in sorted(distributions.items())},
        "latency_ms": {
            "count": len(durations),
            "avg": round(mean(durations), 2) if durations else None,
            "p50": _percentile(durations, 50),
            "p95": _percentile(durations, 95),
            "max": round(max(durations), 2) if durations else None,
        },
        "data_quality": {"malformed_events": malformed, "missing_duration": sum("duration_ms" not in e for e in completed)},
    }
    status, recommendation, warnings = classify_health(snapshot)
    snapshot["health_status"] = status
    snapshot["recommendation"] = recommendation
    snapshot["warnings"] = warnings
    return snapshot


def read_journal(period: str) -> list[str]:
    result = subprocess.run(
        ["journalctl", "-u", "ai-teacher", "--since", period, "--no-pager", "-o", "cat"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a redacted AI provider health snapshot.")
    parser.add_argument("--period", default="24 hours ago", help="journalctl --since value")
    args = parser.parse_args()
    events, malformed = parse_event_lines(read_journal(args.period))
    print(json.dumps({"period": args.period, "generated_at": datetime.now(timezone.utc).isoformat(), **build_snapshot(events, malformed=malformed)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
