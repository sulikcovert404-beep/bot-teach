# Adaptive Lesson Pack Hardening Report

> **Historical qualification record:** migration revisions and staging references in this document describe the 2026-09-09/10 qualification wave. They are not the current development target; current CI qualification uses explicit revision `20260912_0021`.

## Scope
Controlled hardening after Commander approval. No migration, staging deployment, production, webhook, or external Telegram changes.

## Completed
- `max_script_words` enforced using deterministic whitespace word counting; over-limit generation fails with `SCRIPT_WORD_LIMIT_EXCEEDED`.
- Cache identity includes the active stage word limit.
- Lesson-pack assets carry explicit placeholder metadata.
- Telegram delivery rejects placeholder assets by default (`PLACEHOLDER_ASSET_NOT_DELIVERABLE`); controlled tests can opt in explicitly.
- Approval, content-version, lesson, tenant, and entitlement checks are enforced in the Telegram lesson path. Asset tenant can be supplied separately to detect cross-tenant requests.
- Negative tests cover over-limit scripts, placeholder delivery, wrong lesson, missing entitlement, and related delivery failures.

## Validation
Focused suite: **31 passed**.

## Remaining partial items
- Provider failure telemetry and full retry taxonomy are not yet wired to lesson-pack persistence.
- Cache axes for provider, prompt/template, and profile versions are not yet complete.
- Real provider/media qualification and External Telegram E2E remain blocked/held.

## Verdict
`Partial PASS` for controlled internal hardening. No claim of Telegram E2E or production readiness is made.

## Provider and cache completion evidence
- LessonPack cache identity now includes provider_version, prompt_version, profile_version, and max_script_words.
- generation_parameters exposes the same version axes for idempotency consumers.
- AIGateway rejects empty/whitespace provider responses as INVALID_RESPONSE; such outputs cannot become successful assets.
- Added cache isolation and empty-provider failure tests.
- Latest focused validation: 33 passed.

## Provider resiliency and cache identity closure
- AIGateway now emits metadata-only gateway_success/gateway_failure events with provider, model, attempt, latency, category, and usage fields; prompts/responses/credentials are excluded.
- Empty or whitespace AIResponse and text responses raise INVALID_RESPONSE and are never successful outputs.
- Cache identity includes provider_version, prompt_version, profile_version, and max_script_words; generation parameters expose these axes.
- Added cache isolation, empty-response, and event emission tests.
- Latest focused validation: 34 passed.
