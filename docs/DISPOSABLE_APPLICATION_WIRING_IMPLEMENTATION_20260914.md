# Disposable Application Wiring Implementation

## Status

**PARTIAL — request boundary implementation added; restricted PostgreSQL FastAPI E2E pending.**

## ORM

Added `UserTenantMembership` to `app/db/models.py` with status check, user FK, tenant identity, provenance timestamps, revocation timestamp, and `(user_id, tenant_id)` uniqueness. No migration was created or run.

## Resolver

Added `app/security/tenant_resolver.py`. It mirrors the approved fail-closed contract: active/non-revoked only, no client tenant input, missing membership denied, and multiple active bindings denied as ambiguous.

## Tests

`pytest -q tests/test_tenant_resolver.py` → **3 passed**.

These tests validate active resolution, missing/revoked denial, and ambiguous denial against an isolated SQLite schema. They do not claim PostgreSQL SECURITY DEFINER or FORCE RLS behavior; those primitives were qualified separately on disposable PostgreSQL.

## Context Injection

Student Exam endpoints now resolve the authenticated subject through `_student_tenant_context` before assignment/attempt/result lookups, set `app.tenant_id` transaction-locally, and scope initial queries by tenant and student. Missing/invalid/revoked/ambiguous bindings fail closed with 403.

## Exam Services / Pool Tests

**PENDING QUALIFICATION.** The implementation is covered by compile checks and existing authorization regression (`tests/test_mvp_pilot_authorization.py`: 6 passed), but positive/negative FastAPI flows under PostgreSQL restricted role, connection reuse, concurrency, savepoint, autocommit, and exception cleanup still require the disposable E2E harness.

## Production Mutation

NONE. No Alembic execution, role/JWT/config/deploy change, or live DB mutation. Production remains pinned to `20260912_0020`.

## Commander Decision Required

YES — approve proceeding to the disposable PostgreSQL application-context harness and then endpoint wiring, or request design changes. This scaffold must not be promoted to production as-is.
