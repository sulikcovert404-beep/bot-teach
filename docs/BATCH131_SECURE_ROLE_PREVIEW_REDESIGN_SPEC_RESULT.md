# BATCH131 — Secure Role Preview Redesign Specification

Date: 2026-09-17
Scope: Documentation/design only. No production code, tests, schema, DB, server, Telegram, deploy, or secrets changed.

## Canonical context

`CanonicalPrincipal` contains `real_role` (the DB-resolved canonical role), optional request-scoped `effective_role`, `preview_id`, `preview_tenant_id`, `preview_started_at`, `preview_expires_at`, and `preview_active`. `real_role` remains `SUPER_ADMIN` for the owner; preview never mutates the DB role. Outside an active preview, effective role equals real role.

## Start lifecycle

1. Resolve the authenticated principal from the server-side session.
2. Require `real_role == SUPER_ADMIN`; never authorize from `effective_role` or client role data.
3. Resolve the requested tenant identifier against the owner's server-side allowlist.
4. Validate target role is exactly `STUDENT`, `TEACHER`, or `SCHOOL_ADMIN`.
5. Reject if an active preview already exists (nested preview).
6. Issue a bounded, server-signed context containing purpose, audience, issued/expiry timestamps, preview id, canonical subject, target role, and validated tenant.
7. Emit `preview_started` audit metadata without credentials.

Tenant identifiers are requests only; tenant authority comes from the canonical server-side allowlist. Unknown, inactive, cross-tenant, or otherwise unauthorized targets are denied before data access.

## Active request and exit

Authorization dependencies resolve the signed preview context, verify expiry, audience, purpose, signature, and canonical subject, then apply the effective role only to the permitted request scope. A preview principal cannot issue previews or mutate owner/security permissions. On explicit exit, invalidate the context server-side when supported, restore the effective role from the canonical real role, and emit `preview_ended`. Expiry causes fail-closed access and server-derived restoration; client-provided role values are ignored.

Durable replay revocation is not assumed without a persistence decision. If single-use/revocation is required, report `SCHEMA_REQUIRED` before implementation.

## Components affected

- principal/auth context: represent canonical and effective roles separately
- preview service: resolve allowlist, issue/validate/expire contexts, reject nesting
- preview endpoints: start/exit with canonical-role authorization
- authorization dependency: derive effective scope server-side and preserve tenant isolation
- audit integration: `preview_started`, `preview_ended`, `preview_expired`
- tests: positive and negative matrix below

## Negative test plan

| Case | Expected |
|---|---|
| non-SUPER_ADMIN start | DENY |
| forged effective_role | DENY / ignore client value |
| forged tenant | DENY |
| unknown tenant | DENY |
| expired token | DENY |
| wrong audience | DENY |
| wrong purpose | DENY |
| cross-tenant reuse | DENY |
| nested preview | DENY |
| tampered preview_id | DENY |
| exit with forged role | IGNORE/DENY; restore canonical role |
| DB role before/during/after | unchanged |
| valid canonical SUPER_ADMIN preview | ALLOW within validated role/tenant scope |

Tests must also assert no secret/token appears in audit metadata, no preview context grants owner/security operations, and tenant filtering occurs before data access.

## Verdict

**READY_FOR_TEST_FIRST_IMPLEMENTATION**. The redesign closes the documented security gaps at the contract level and identifies the components and tests required. Implementation remains a separate gate; schema is not required for the initial expiring context unless durable revocation/replay prevention is requested.

## Commit and mutation status

Gate 131 commit remains HOLD. No production implementation, test code, schema/migration, DB role mutation, server/SSH/Docker, deploy, environment, secret, or Telegram runtime change was performed.
