# Observability Hardening Proposal

Status: PROPOSAL ONLY — no production mutation
Date: 2026-09-14

## Purpose

Improve diagnosis of Telegram and Mini App failures without recording secrets, credentials, authorization headers, full initData, Telegram payloads, prompts, source text, or personal data.

## Current evidence and gaps

- `RequestLoggingMiddleware` already emits method, path, status, request_id, and duration.
- `/metrics/prometheus` currently exposes aggregate totals and status counts only.
- `/api/v1/auth/telegram` and `/api/v1/telegram/webhook` have no dedicated outcome or dependency metrics.
- The historical auth 503 had no structured failure category or dependency timing, so its cause could not be proven.
- Webhook 401s are distinguishable by route/status but not by safe validation reason or source class.

## Proposed bounded metrics

Add low-cardinality counters/histograms, preferably through the existing metrics adapter:

- `telegram_auth_requests_total{status_class,outcome}`
- `telegram_auth_latency_seconds`
- `telegram_webhook_requests_total{status_class,validation_result}`
- `telegram_webhook_latency_seconds`
- `telegram_dependency_failures_total{operation,failure_class}`
- `telegram_callback_requests_total{outcome}`
- `readiness_failures_total{dependency}`

Allowed label values are fixed enums such as `2xx`, `4xx`, `5xx`, `accepted`, `invalid_request`, `missing_secret`, `invalid_secret`, `bot_unavailable`, `timeout`, `provider_error`, and `db_error`. Never use user IDs, chat IDs, request bodies, secrets, URLs with query strings, or arbitrary exception text as labels.

## Structured event fields

For auth/webhook events, emit only:

- timestamp, request_id, route name, status code, duration_ms
- outcome/failure_class from an allowlist
- dependency name and duration_ms when applicable
- source class (`docker_bridge`, `cloudflare`, `unknown`) derived without retaining raw addresses where possible

Do not log Telegram update IDs, chat IDs, initData, authorization values, tokens, or provider response bodies.

## Correlation rules

Reuse the middleware request ID. Propagate it to internal dependency spans and include it in the response header. Use a separate short-lived correlation ID for a webhook callback only when it cannot be linked to an HTTP request. Correlation IDs must be opaque and bounded.

## Health distinction

Keep `/health` dependency-free. Keep `/health/ready` as the DB, Redis, and migration readiness signal. Add alert thresholds separately for liveness, readiness, and dependency failure so one transient auth error cannot be mistaken for an outage.

## Alert suggestions

- sustained 5xx rate over a short rolling window
- repeated Telegram auth `provider_error` or `bot_unavailable`
- webhook 401 spike grouped by safe validation result
- readiness failures for DB/Redis/migration
- P95 latency regression

Thresholds must be configured outside application secrets and reviewed before activation.

## Security and privacy review

Metrics and logs must pass a redaction test that rejects secret-like fields, authorization headers, full payloads, prompts, source text, and personal identifiers. Sampling must never bypass redaction. Keep labels bounded to prevent cardinality attacks.

## Implementation boundary

This document authorizes no code, schema, deployment, restart, webhook registration, environment edit, or provider change. A later implementation gate should add unit tests for classification/redaction, middleware correlation tests, and a staging-only scrape verification before any production rollout.

## Acceptance for a future gate

A future gate may be considered ready when a controlled auth failure and webhook validation failure can be distinguished by request ID, status class, safe failure class, and latency, while `/health` and `/health/ready` remain separately observable and no sensitive value appears in logs or metrics.

## Commander Decision Required

Approve or revise this proposal before implementation.
