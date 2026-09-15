# Disposable PostgreSQL Application Context Qualification

## Status

**PARTIAL.** The transaction/context harness passes on a fresh PostgreSQL 16 container, but the FastAPI dependency and Exam service are not yet wired to call it.

## Request Boundary

Harness sequence `authenticated user → resolver → BEGIN → set_config(..., true) → tenant query → COMMIT/ROLLBACK` completed successfully for tenant A and tenant B.

## Tenant Resolver

Active memberships resolve to exactly one tenant. Missing and revoked users return no tenant and are denied.

## Context Injection / Pool Safety

- Transaction-local context cleared after commit (`context_cleared = t`).
- A subsequent request on the same connection explicitly resolved tenant B and saw only B data.
- Rollback path completed without retaining tenant context.

## RLS

`tenant_data` used enabled + forced RLS; each context saw exactly one matching tenant row. Runtime role was `NOSUPERUSER/NOBYPASSRLS` in the disposable proof.

## Exam Routes

**PENDING.** Current `get_session` and `exam_attempts` still do not invoke the resolver/context boundary. This harness is not evidence that FastAPI Exam endpoints are qualified.

## Production Mutation

NONE. No migration, role/JWT/config/deploy or live DB change. Production remains `20260912_0020`.

## Commander Decision Required

YES — authorize wiring this boundary into the disposable FastAPI/Exam request path, followed by restricted-role E2E and concurrency tests. Production migration remains NO-GO.
