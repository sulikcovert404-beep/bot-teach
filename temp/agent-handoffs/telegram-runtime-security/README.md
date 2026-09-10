# Telegram Runtime Security Review Handoff

Purpose: evidence-based advisory review only. No implementation, deployment, webhook, migration, RLS, role mutation, or production change is authorized by this handoff.

## Scope

Review the Telegram journey:

`/start → registration/diagnosis → grade → lesson → Lesson Pack → PDF, Podcast, MCQ, Descriptive, image, Tutor`

Focus areas:

- Telegram `update_id` idempotency and replay protection
- initData/JWT authentication and identity propagation
- app_runtime least-privilege dependencies
- tenant, classroom, grade, and role isolation
- generated asset download authorization
- delivery receipts, send-error handling, and Telegram `file_id` reuse
- background-job tenant context
- Persian profile binding, citations, and observability

## Sanitization statement

This directory contains source excerpts, contracts, and test/evidence summaries only. It contains no API keys, bot tokens, passwords, credentials, database dumps, environment values, or private user data. Provider agents must treat all conclusions as advisory and evidence-gated.

## Files

- `app_adapters_telegram.py`
- `app_api_routes_telegram.py`
- `app_core_config.py`
- `app_security_dependencies.py`
- `app_services_lesson_pack.py`
- `app_services_lesson_pack_orchestrator.py`
- `app_services_telegram_bot.py`
- `app_services_telegram_lesson_service.py`
- `docs_APP_RUNTIME_PRIVILEGE_MATRIX.md`
- `TELEGRAM_RUNTIME_REVIEW_CONTEXT.md`
- `AI_TEAM_REVIEW_CONTEXT.md`

## Review output

Return strengths, MUST FIX BEFORE TELEGRAM E2E, SHOULD FIX, FUTURE HARDENING, missing evidence, required tests, and blockers. Do not implement or create side effects.
