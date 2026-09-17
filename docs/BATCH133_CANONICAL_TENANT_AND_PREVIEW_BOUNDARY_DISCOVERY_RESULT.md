# BATCH133 — Canonical Tenant Authority & Preview Boundary Discovery

Date: 2026-09-17
Scope: Read-only architecture discovery. No code, tests, schema, DB, runtime, or deployment changes.

## Findings

### Tenant authority

Verdict: **MULTIPLE_COMPETING_SOURCES**.

- `app/security/tenant_resolver.py::resolve_tenant` resolves a single active tenant from `UserTenantMembership`, failing closed on none or ambiguity.
- `app/security/tenant_scope.py::enforce_tenant` uses `SchoolAdminMembership` and `TeacherProfile` for non-super roles, but returns any requested tenant for `SUPER_ADMIN` without an allowlist lookup.
- `app/security/admin_scope.py` provides presentation-level scope selection and is not an authority boundary.
- Models include `UserTenantMembership`, `SchoolTenant`, `SchoolAdminMembership`, `TeacherProfile`, and `ClassMembership`, each with tenant relations.

These sources have different semantics. In particular, no canonical owner-to-tenant allowlist was found for Secure Role Preview. A client-supplied tenant cannot safely be accepted for the owner preview flow.

### Canonical principal

- `app/security/principal.py::CanonicalPrincipal` is the dependency-based authenticated principal (`subject`, canonical `role`) derived from verified JWT claims.
- `app/security/canonical.py::require_canonical_roles` is the canonical role guard.
- `app/security/dependencies.py` contains legacy string-based guards still used by many routes.

For Preview, the dependency-based principal path is the least invasive integration point, but it needs a separate effective-principal wrapper; no such runtime layer exists today.

### Preview boundary

No preview routes currently exist. The logical boundary is a new platform/security router, alongside `app/api/routes/admin.py`, protected by `require_principal("SUPER_ADMIN")` and checking `principal.role` as the canonical `real_role`. It must not be placed under teacher, student, or dashboard routers.

Candidate contracts (not implemented): `POST /platform/preview/start` and `POST /platform/preview/exit`.

### Effective-principal integration

Use a request-scoped dependency after JWT decode and before role-scoped handlers. It should derive `effective_role` only from a validated signed preview context, while retaining `real_role` for preview/security operations. A global middleware is unnecessary unless existing dependency injection cannot carry the context.

## Verdict

**ARCHITECTURE_BLOCKED**. Multiple tenant sources exist and there is no canonical SUPER_ADMIN preview allowlist. Implementing Gate 132 without resolving this would require guessing tenant authority and could create cross-tenant privilege escalation. Gate 132 remains STOPPED; no workaround or mutation was made.

## Required decision

Define one authoritative owner tenant-scope source (or explicitly approve a new schema/domain source) before resuming implementation. Then re-run Gate 133 and Gate 132 test-first.
