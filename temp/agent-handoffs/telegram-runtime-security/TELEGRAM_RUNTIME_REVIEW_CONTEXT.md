# Telegram Runtime Review Context

## Current verified facts

- Docker staging API, PostgreSQL/pgvector, and Redis are healthy.
- Migration head is 20260910_0018; no migration was run for this review.
- Disposable app_runtime endpoint qualification was run with controlled non-PII fixtures and minimal grants; the privilege matrix is included.
- AI output token configuration is in the application config layer; focused tests passed previously.
- RLS, production role changes, production deployment, and webhook changes remain unchanged and on hold.

## Required acceptance categories

1. update_id deduplication and replay protection
2. delivery receipts and checked send failures
3. initData/JWT authentication
4. artifact download authorization
5. tenant/class/grade isolation
6. app_runtime grant matrix completeness
7. background-job context
8. state-machine/CAS behavior
9. Persian grade/profile binding
10. observability and staging-bot separation

## Evidence limits

The excerpts are intentionally sanitized and may omit runtime-only configuration. Do not infer secrets, credentials, database contents, or production behavior. Label unverified claims as hypotheses and specify the exact evidence needed.
