# Tenant Context Wiring Design

Status: PASS / DESIGN ONLY  
Production mutation: NONE  
Migration impact: NO

## Injection point

Inject the PostgreSQL tenant context at the authenticated request dependency/transaction boundary, after canonical identity and tenant membership resolution, and before any tenant-owned domain query. A middleware alone is insufficient because it does not own the SQLAlchemy transaction or the resolved tenant. A session factory alone cannot choose a request tenant safely. The Exam service must receive a session whose context has already been established; services must not infer context from caller-supplied IDs.

Recommended flow:

```text
Authentication
  → canonical user/role
  → authoritative tenant resolver (membership/assignment)
  → begin transaction on request session
  → set_tenant_context(session, resolved_tenant)
  → Exam service/repository queries
  → commit or rollback
  → connection release (is_local context disappears)
```

For `SUPER_ADMIN`, an explicit, validated tenant scope is required for tenant-owned operations. No scope means fail closed for Exam operations. For ordinary users, tenant must come from server-side membership/profile data; query parameters and JWT claims alone are not authoritative.

## Transaction model

- Begin an explicit transaction before calling `set_tenant_context`.
- Use the existing parameterized helper with `is_local=true`.
- Keep context and all Exam reads/writes in the same transaction.
- Roll back on any exception, including authorization failure and IntegrityError.
- Release the connection only after rollback/commit; pooled connections must never carry a session-level tenant setting.
- Add pool interleaving tests (A → release → B) and savepoint/autocommit tests.

## Failure behavior

Fail closed with a typed authorization/context error when tenant is missing, membership is absent/revoked, tenant does not match the assignment/class, or `set_tenant_context` fails. Do not retry with an unscoped query, fall back to a global search, or disable/bypass RLS. A context mismatch or RLS denial must roll back the transaction and return the adapter's standard authorization/error mapping.

## Scope

The immediate qualification target is the Exam request path (`start`, `save`, `submit`, `result`). The same boundary pattern should become the canonical mechanism for all tenant-aware domains, but adoption outside Exam requires its own inventory and tests. Existing `sources.py` usage of `set_tenant_context` should be aligned with this transaction wrapper rather than duplicated ad hoc.

## Test strategy (disposable PostgreSQL only)

1. Valid Student membership: context is set before the first Exam query and lifecycle succeeds.
2. Missing/revoked membership: request is denied and no unscoped query runs.
3. Wrong tenant/class: denied before mutation.
4. Tenant A then Tenant B on a reused pooled connection: zero leakage.
5. Missing/invalid context: empty/deny under FORCE RLS.
6. Savepoint, rollback, exception, autocommit and concurrent requests: context isolation and no stale state.
7. Teacher and school-admin result paths: scope is resolved server-side and cross-tenant access is denied.

## Non-go decisions

Do not alter RLS policies, remove FORCE RLS, grant BYPASSRLS, change production roles, add a migration, or deploy this design. Implementation requires a separate approved non-production gate followed by the application E2E qualification.

## Commander Decision Required

Approve implementation of the request-boundary transaction/context wrapper on disposable infrastructure, or request design changes. Production remains pinned to `20260912_0020`.
