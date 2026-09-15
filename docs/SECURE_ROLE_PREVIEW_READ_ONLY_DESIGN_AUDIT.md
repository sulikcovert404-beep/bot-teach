# SECURE ROLE PREVIEW — READ-ONLY DESIGN AUDIT

## Scope

This audit reviews the existing authentication, authorization, tenant, audit, and frontend session handoff code. No implementation, migration, deployment, role mutation, or production configuration change was performed.

## Findings

**Persistent owner role:** `SUPER_ADMIN` (Commander-confirmed canonical owner).

**Current auth model:** Telegram WebApp authentication issues a JWT access token. `app/security/tokens.py` signs HS256 tokens with `sub`, `iat`, `exp`, and optional `role` claims. `app/security/principal.py` and `app/security/dependencies.py` validate the bearer token and enforce canonical roles server-side.

**Current role source:** The effective role used today is the JWT `role` claim, which is issued from the authenticated backend identity. Database `users.role` remains the persistent authority. The current principal object contains only `subject` and `role`; it has no preview fields.

**Current tenant source:** `SUPER_ADMIN` may supply an explicit tenant scope to `enforce_tenant`; `SCHOOL_ADMIN` is checked against active, non-revoked `SchoolAdminMembership`; teachers are checked through `TeacherProfile`. Class membership is persisted in `ClassMembership` and is classroom/student scoped. No preview tenant context exists today.

**Audit infrastructure:** `AuditLog` and `record_audit_log()` are reusable for `preview_started` and `preview_ended`. Sensitive metadata keys containing password, secret, token, api_key, or authorization are rejected. Preview identifiers and tenant references can be logged without credential material.

**Frontend handoff:** Mini App access tokens are now stored in same-origin `sessionStorage` and restored by dashboard provider code. Client storage is transport only; server authorization remains authoritative.

## Target-model assessment

| Requirement | Result | Evidence / implication |
|---|---|---|
| Preview without schema migration | **YES, design-compatible** | JWT already supports claims and short expiry; add a server-issued preview context/token without changing DB tables. |
| Recommended mechanism | **Short-lived server-issued JWT** | Include `real_role=SUPER_ADMIN`, `effective_role`, `preview_tenant`, `preview_id`, `iat`, `exp`, and a purpose/audience claim. Never accept these from query or client storage as authority. |
| Real actor preserved separately | **YES, design-required** | Keep `sub` and persistent DB role unchanged; authorization code must distinguish real and effective roles. |
| Effective role support | **NO, not currently implemented** | Current `CanonicalPrincipal` has only one role and all dependencies read it as canonical. Requires an explicit preview principal/context implementation. |
| Tenant validation path | **PARTIAL** | Existing `enforce_tenant()` validates non-super roles and allows explicit tenant for `SUPER_ADMIN`; preview must require an allowlisted tenant and server-side existence/ownership checks before issuing context. |
| Preview expiration | **YES** | Existing JWT `exp` validation supports short-lived context. Use a dedicated purpose/audience and short TTL. |
| Exit Preview | **YES, design-compatible** | Discard preview context and return to the original SUPER_ADMIN token; optionally maintain a server-side revocation/jti denylist only if immediate revocation is required. |
| Audit reusable | **YES** | `AuditLog` can record start/end, actor, effective role, target tenant, preview id, expiry, and outcome without tokens. |
| Schema migration required | **NO for initial design** | No new persistent state is needed for an expiring signed context. A migration would only be needed for durable preview sessions/revocation history. |

## Threat checks

- Student forging `preview_role`: **DENY by current architecture; preserve by issuing preview only from a SUPER_ADMIN-authorized endpoint.**
- Teacher forging `preview_role`: **DENY**.
- School Admin forging `preview_role`: **DENY**.
- `?role=student` or client-edited storage: **NO AUTHORITY**.
- Arbitrary tenant: **MUST DENY unless an explicit server-side policy allows that tenant**.
- Expired or wrong-purpose preview token: **DENY through JWT validation and purpose/audience checks**.
- Reuse after exit: **DENY only if server-side revocation is implemented; otherwise exit means context discard and natural expiry.**

## Missing controls before implementation

1. A dedicated SUPER_ADMIN-only preview request endpoint/service.
2. An immutable preview context carrying both real and effective roles.
3. Explicit tenant allowlist and target-context validation (tenant, classroom, and role compatibility).
4. Middleware/dependencies that authorize using effective role while retaining real role for audit and privileged operations.
5. Dedicated JWT `purpose`/`aud` and short TTL; no query-string role or tenant authority.
6. `preview_started` and `preview_ended` audit events with non-sensitive metadata.
7. Exit behavior and tests for forged role, forged tenant, expiry, wrong audience, and cross-tenant access.
8. Read-only verification of safe preview fixtures. No safe tenant/student/teacher/admin context was created or changed during this audit; availability remains **NOT VERIFIED** from source-only evidence.

## Safe fixture status

- Safe preview tenant: **NOT VERIFIED**
- Safe Student context: **NOT VERIFIED**
- Safe Teacher context: **NOT VERIFIED**
- Safe School Admin context: **NOT VERIFIED**

## Final verdict

**READY for Secure Role Preview implementation design, NOT READY for implementation approval.** The existing JWT and audit foundations can support a migration-free short-lived preview context, but effective-role middleware, tenant allowlisting, lifecycle audit, and controlled fixtures must be designed and tested first. Production changes: **NONE**.
