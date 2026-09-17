# BATCH123 — LOCAL PRODUCT READINESS GAP AUDIT

Date: 2026-09-17. Scope: local read-only inspection; no server, Docker, database, migration, environment, secret, code, or test changes.

## Evidence

Inspected API routes/services, web surfaces under `web/student`, `web/teacher`, `web/admin`, `web/platform`, `web/mini-app`, focused dashboard/Mini App/auth/exam/feedback tests, and existing readiness reports.

## Readiness matrix

| Flow | Status | Evidence / gap |
|---|---|---|
| Student auth/session | IMPLEMENTED_PARTIAL_TESTS | Telegram auth route and WebApp bootstrap exist; real initData/provider remains external. |
| Student dashboard | IMPLEMENTED_PARTIAL_TESTS | Shell, assignments/progress/content calls and tests exist; persisted-data E2E is open. |
| Student lesson/content | IMPLEMENTED_PARTIAL_TESTS | Mini App tabs and classroom-content request exist; persisted index qualification is external. |
| Student exam attempt/result/feedback | IMPLEMENTED_PARTIAL_TESTS | Exam routes/services/models and feedback controls exist; DB lifecycle/concurrency E2E is separate Gate 0021. |
| Teacher dashboard | IMPLEMENTED_PARTIAL_TESTS | Classrooms, assignments, analytics and review queue are wired; real membership E2E is incomplete. |
| Teacher generation/publish/close | IMPLEMENTED_PARTIAL_TESTS | Routes and UI controls exist; Gemini and persistent publication/index qualification are blocked. |
| Teacher feedback/cohorts | IMPLEMENTED_PARTIAL_TESTS | Analytics/submission paths exist; persisted tenant/class data qualification is open. |
| School Admin dashboard/workflows | IMPLEMENTED_PARTIAL_TESTS | Admin shell, users/schools/content/billing/observability routes and tests exist; multi-tenant DB E2E is open. |
| Super Admin dashboard | IMPLEMENTED_PARTIAL_TESTS | Platform surface and auth bootstrap exist; real Telegram `/platform/` smoke remains pending. |
| Secure role preview | IMPLEMENTED_UNVERIFIED | Role dependencies exist; preview/impersonation is a separate security Gate. |
| Telegram/Mini App navigation | IMPLEMENTED_PARTIAL_TESTS | WebApp integration, tabs and dashboard links exist; public runtime/initData require external qualification. |
| Core/provider dependencies | IMPLEMENTED_PARTIAL_TESTS | Fail-closed auth/error states exist; Gemini is credential-blocked. |

## Findings

1. Dashboard shells are present, RTL-marked and served; focused tests verify assets and unauthenticated fail-closed responses.
2. Clients call Core API paths and expose loading/error states, but shell tests do not prove persisted data, tenant isolation or complete role workflows.
3. Teacher routes have a persisted numeric-classroom path but legacy/non-numeric paths return fallback payloads; qualification must not treat these as persisted readiness.
4. Exam/result/feedback code exists, but DB-backed negative, concurrency and lifecycle qualification is not implied by route presence.
5. “در انتظار احراز هویت” is consistent with absent/invalid Telegram initData or unavailable auth API and needs runtime smoke evidence.

## Gap classification

**Locally executable:** expand dashboard contract/role authorization tests; add route/link and malformed-response tests; flag teacher fallback paths.  
**Storage/server dependent (do not touch here):** PostgreSQL dashboard/content E2E, Telegram Web/Desktop smoke, Cloudflare/webhook/Docker/runtime, real Gemini, migration/RLS.  
**Security-sensitive (separate Gate):** Secure Role Preview, auth/session redesign, tenant/RLS changes, production deployment/provider activation.

## Ranked workstreams

1. Dashboard contract and authorization test expansion (local, low risk).
2. Teacher fallback-path and canonical membership qualification (medium risk).
3. Mini App/platform auth-state and navigation contract tests (local; real smoke separate).
4. Persisted dashboard/content E2E on disposable staging (runtime dependent).
5. Secure Role Preview design review (security Gate required).

## Verdict

Dashboard/product surfaces are broadly implemented but remain **IMPLEMENTED_PARTIAL_TESTS**. Release completeness requires persisted role/tenant data, Telegram auth/navigation, and provider-dependent qualification. No restricted mutation was performed.
