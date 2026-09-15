# Resolver Implementation Qualification

## Status

**PASS (disposable only)**

The qualification used a fresh PostgreSQL 16 container and was destroyed after the run. No repository migration, runtime configuration, production role, or live database was changed.

## Function

- Mechanism: PostgreSQL `SECURITY DEFINER` SQL/PLpgSQL resolver.
- Owner: `migration_owner` (`NOLOGIN`).
- Runtime grant: `app_runtime` receives `EXECUTE` only; membership table remains unreadable to it.
- Security: fixed `search_path = pg_catalog, public`, parameterized subject predicate, active status filter, single result only; zero matches return NULL and multiple active matches raise a typed failure path (`ambiguous tenant binding`).
- No dynamic SQL, mutation, tenant enumeration, or `BYPASSRLS`.

## Tests

- Active membership resolves the single tenant.
- Missing membership returns no tenant (deny).
- Revoked membership returns no tenant (deny).
- Ambiguous active memberships raise and are denied.
- Resolver accepts only the supplied authenticated user id; no API for listing tenants exists.

The disposable SQL qualification completed with PostgreSQL exit code 0 and `ON_ERROR_STOP=1`; cleanup removed the temporary roles, tables, function, and container.

## RLS Integration

`tenant_records` was enabled with `FORCE ROW LEVEL SECURITY`. After resolving the tenant, a transaction-local `app.tenant_id` context was set and the runtime role could observe only the matching tenant row. The resolver itself does not weaken or bypass RLS.

## Audit

The boundary is intentionally limited to the resolver result. Production audit event wiring remains a follow-up implementation item; no secrets, tokens, or headers are stored by this qualification.

## Migration Impact

None. This is a disposable proof only. Any real schema/function migration requires a separate Commander approval and explicit `0020 → next revision` rehearsal.

## Production Mutation

NONE. Production remains pinned to `20260912_0020`.

## Commander Decision Required

YES — approve or reject promoting the qualified resolver into a migration-design gate. Exam 0021 remains blocked until that decision and subsequent application wiring qualification.
