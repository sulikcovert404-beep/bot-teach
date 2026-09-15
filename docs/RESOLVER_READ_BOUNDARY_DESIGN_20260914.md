# Resolver Read Boundary Design

Status: RECOMMENDATION / DESIGN ONLY  
Production mutation: NONE  
Migration: NOT CREATED

## Selected mechanism

Prefer a narrowly scoped PostgreSQL `SECURITY DEFINER` resolver function owned by the migration owner, with a fixed `search_path`, explicit argument/type checks, and `EXECUTE` granted only to the runtime resolver principal. The function returns the minimum active binding fields (`tenant_id`, status/version) for the authenticated subject and never exposes a tenant-wide list. It must be paired with an application dependency that derives the subject from the verified token and records an audit event.

Alternatives considered:

- **Restricted view:** simple, but still needs a pre-RLS row filter and is easy to expose broadly.
- **Dedicated resolver role/connection:** workable, but increases pool/credential complexity and must prevent arbitrary subject enumeration.
- **Application-side cache:** not authoritative and creates revocation/staleness risk; may only be a bounded optimization after validation.

The selected function is a boundary, not a general RLS bypass. `app_runtime` retains `NOSUPERUSER`/`NOBYPASSRLS`; tenant-owned tables keep FORCE RLS.

## Security model

The resolver may return only active bindings for the authenticated subject supplied by the trusted request dependency. It must reject malformed IDs, inactive/revoked rows, and ambiguous selection unless an explicit validated tenant is supplied. Function SQL must use a fixed schema-qualified search path and parameterized predicates. No tenant enumeration endpoint or arbitrary user lookup is exposed. A separate security review must verify whether the function should bind subject through a transaction-local authenticated identity setting or a dedicated resolver principal/connection; passing arbitrary client IDs is prohibited.

## Privilege boundary

Migration owner owns the function and table. The normal runtime role receives no direct `SELECT` on the membership table; it receives only narrowly scoped `EXECUTE` (or uses a dedicated resolver principal with equivalent least privilege). The function must not call dynamic SQL, modify data, or set `BYPASSRLS`. Membership mutations remain service-authorized and audited.

## Audit and observability

Record resolution success, denial, ambiguity, revocation, and context mismatch with actor, outcome, and correlation ID only. Do not record tokens, secrets, or full membership dumps. Alert on repeated denied/ambiguous resolution and anomalous lookup volume.

## Performance

Index `(user_id, status)` and `(user_id, tenant_id)`; benchmark lookup latency and lock behavior on disposable PostgreSQL. A short-lived cache is optional only after authoritative validation, with membership-version/revocation invalidation and bounded TTL.

## Integration flow

```text
verified token subject
→ resolver boundary (minimal binding)
→ explicit transaction
→ set_tenant_context(tenant_id, is_local=true)
→ Exam tenant queries under FORCE RLS
→ commit/rollback
→ connection release
```

Zero bindings, multiple bindings without selection, revoked bindings, resolver errors, and context failures all fail closed.

## Migration impact

Requires a separate migration design/qualification for the binding table, function or equivalent boundary, grants, indexes, audit hooks, and backfill. Qualification must include tenant enumeration attempts, wrong-subject attempts, revocation races, pool interleaving, rollback, and restricted-role tests. No schema or runtime change is authorized by this document.

## Commander Decision Required

Approve the SECURITY DEFINER minimal resolver direction, or select another boundary after security review. Implementation and migration remain unauthorized; Exam 0021 and production remain blocked at `20260912_0020`.
