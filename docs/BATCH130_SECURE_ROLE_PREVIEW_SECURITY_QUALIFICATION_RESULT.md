# BATCH130 — Secure Role Preview Security Qualification

Date: 2026-09-17
Scope: Read-only source audit and test-design qualification. No implementation or runtime mutation.

## Source audit

`app/security/role_preview.py` provides a server-side, short-lived HS256 token primitive. Issuance requires `SUPER_ADMIN`, restricts effective roles to `STUDENT`, `TEACHER`, and `SCHOOL_ADMIN`, requires a tenant and bounded TTL (1–15 minutes), and binds purpose/audience/expiry claims. Decode validates required claims, audience, purpose, role, and expiry. Preview operations block owner/security mutations. Audit metadata is non-sensitive.

No route, middleware integration, effective-principal resolver, tenant allowlist lookup, replay/revocation store, or preview exit endpoint was found. Existing tests cover owner issuance, non-owner denial, invalid role/scope, expiry/signing failure, forbidden operations, and audit metadata safety.

## Threat matrix

| Threat | Current evidence | Verdict |
|---|---|---|
| Non-SUPER_ADMIN issuer | issuer checks actor role | DENY covered |
| Client-forged effective_role/tenant | signed claims prevent post-issue edits; no route integration | DESIGN CONTROL; integration test required |
| Expired token | JWT expiry validation | DENY covered |
| Wrong audience/purpose | decode checks both | DENY covered |
| Cross-tenant reuse | claim is signed, but tenant membership/allowlist is not resolved | GAP — server-side tenant validation required |
| Nested preview | no explicit `is_preview` issuer guard in issuance path | GAP — reject preview principal as issuer |
| Real DB role mutation | no DB mutation in primitive; forbidden operation guard exists | DESIGN CONTROL; integration test required |
| Student/Teacher/School Admin invoking preview | no endpoint exists | GAP — endpoint authorization test required |
| Preview expiry/exit audit | metadata helper exists; no lifecycle route | GAP — integration required |
| Return to real role | no effective-principal middleware/exit flow | GAP — must be server-derived |

## Existing test validation

`tests/test_role_preview.py`: 4 tests passed in the existing suite. No production or schema changes were made. Runtime Telegram and API integration were not run.

## Verdict

**SECURITY_GAPS_REQUIRE_REDESIGN** for implementation approval. The cryptographic primitive is a sound qualified design path, but implementation must first specify server-side tenant allowlisting, effective-principal middleware, nested-preview rejection, endpoint authorization, lifecycle audit, and server-derived exit semantics. These are security boundaries and cannot be inferred from the current primitive alone.

## Required implementation test gaps

- Forged client role/query/body cannot override signed effective role.
- Forged or unauthorized tenant is denied before data access.
- Only canonical `SUPER_ADMIN` real role can issue.
- Preview principal cannot issue another preview or mutate owner/security permissions.
- Expired, wrong-audience, wrong-purpose, malformed, and replayed contexts fail closed.
- Student, Teacher, and School Admin cannot invoke preview endpoints.
- Cross-tenant preview is denied; selected tenant is validated server-side.
- Start/end/expiry audit events contain no secrets and preserve actor/effective role/tenant/preview id.
- Exit/expiry restores the canonical real role from server context.

## Boundaries

No production code, middleware, schema, migration, DB role, token issuance, server, Telegram, deploy, environment, secret, or frontend changes were made. Gate 130 commit remains HOLD.
