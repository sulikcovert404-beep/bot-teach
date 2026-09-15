# Tenant Request Context Qualification

## Status

**BLOCKED — application wiring not implemented.** The disposable schema, backfill, resolver, and RLS primitives are qualified, but the current application cannot yet execute the required identity → resolver → transaction context → Exam flow.

## Resolver Integration

FAIL/PENDING. The repository has no `UserTenantMembership` ORM model or production resolver call. `app/api/routes/auth.py::get_session` only opens an `AsyncSession`; it does not resolve a verified subject or set tenant context. JWTs currently carry subject/role only.

## Transaction Boundary

FAIL/PENDING. `app.db.base.set_tenant_context()` correctly requires an active transaction and uses transaction-local `set_config`, but no Exam request boundary invokes it before service queries. Pool reuse safety therefore cannot be claimed for the real application.

## Exam Flow

NOT QUALIFIED. `app/services/exam_attempts.py` receives a caller-supplied `tenant_id` and applies SQL predicates. `start_attempt`, `save_answers`, `submit_attempt`, and result access are not preceded by authoritative resolver/context injection.

## Negative Security

The disposable resolver/RLS primitives deny missing, revoked, ambiguous, wrong-user, and cross-tenant cases. Application-level denial through the real FastAPI dependency remains untested and must not be inferred from those primitive results.

## Pool Safety / RLS

NOT QUALIFIED at application level. The helper is transaction-local, but connection reuse, rollback, savepoint, autocommit, concurrent requests, and exception cleanup require wiring before they can be tested end to end.

## Production Mutation

NONE. No migration, role, JWT, deployment, environment, Cloudflare, webhook, or production DB change was made. Production remains pinned to `20260912_0020`.

## Next Required Work

Create the ORM/service boundary and disposable-only request-context harness, then run authenticated positive and negative Exam flows under `app_runtime` (`NOSUPERUSER/NOBYPASSRLS`). Do not create or execute a production Alembic revision until this gate passes.

## Commander Decision Required

YES — authorize disposable application wiring implementation/qualification, or adjust the boundary design. Current verdict is **BLOCKED**, not a production failure.
