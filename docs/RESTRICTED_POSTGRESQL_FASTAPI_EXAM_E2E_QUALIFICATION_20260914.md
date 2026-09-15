# Restricted PostgreSQL FastAPI Exam E2E Qualification

## Status

**PASS — disposable only.** The qualification script ran against a fresh `pgvector/pgvector:pg16` container, created the ORM schema and prototype resolver, used a `NOSUPERUSER/NOBYPASSRLS` `app_runtime` role, and removed the container afterward.

## Environment

- PostgreSQL: 16 + pgvector extension
- Runtime role: `app_runtime`, `NOSUPERUSER`, `NOBYPASSRLS`
- Membership access: revoked from `app_runtime`; resolver executed through `SECURITY DEFINER` function only.
- FORCE RLS: enabled on exams, assignments, attempts, and results in the disposable harness.

## Student Lifecycle

Authenticated student with one active membership completed:

`resolve tenant → set transaction-local context → start attempt → save answers → submit → read result`.

Result score and max score were verified; script exited `DISPOSABLE_FASTAPI_EXAM_E2E=PASS`.

## Negative Security

- Missing membership: denied.
- Resolver is not directly readable by runtime role.
- Tenant context is server-resolved; no caller tenant is used by the patched Exam endpoints.
- Initial attempt/result lookups require both authenticated student and resolved tenant.

## Transaction Cleanup / Pool Safety

- Commit clears transaction-local context.
- Rollback path clears context.
- Two concurrent scoped requests on the same async pool observed only the expected tenant row; no cross-tenant leakage.

## Teacher/Admin

Not part of this student Exam gate; existing teacher/admin scope gates remain unchanged.

## Production Mutation

NONE. No Alembic revision, live migration, role/JWT/config/deploy, Cloudflare, webhook, or production database change. Production remains pinned to `20260912_0020`.

## Commander Decision Required

YES — review this disposable PASS and decide whether to open the separate Exam 0021 final qualification/migration gate. This result does not authorize production migration.
