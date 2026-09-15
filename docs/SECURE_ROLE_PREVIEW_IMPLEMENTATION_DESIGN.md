# Secure Role Preview Implementation Design

Status: DESIGN ONLY — NOT IMPLEMENTED

## Token Contract

Issue a short-lived server-signed JWT from a dedicated SUPER_ADMIN-only endpoint, for example `POST /api/v1/admin/role-preview`. Require the canonical authenticated principal to have persistent role `SUPER_ADMIN`; never trust client role or tenant claims. Claims:

- `sub`: real owner identity
- `real_role`: `SUPER_ADMIN`
- `effective_role`: one of `STUDENT`, `TEACHER`, `SCHOOL_ADMIN`
- `preview_tenant`: server-validated tenant id
- `preview_id`: unique non-secret correlation id
- `purpose`: `role_preview`
- `aud`: `secure-role-preview`
- `iat`, `exp`: short TTL (recommended 10 minutes, configurable lower bound)

Do not place credentials or sensitive user data in the token. Reject malformed, expired, wrong-purpose, wrong-audience, or forged claims.

## Backend Flow

```text
SUPER_ADMIN bearer token
  -> dedicated preview endpoint
  -> server-side target-role/tenant validation
  -> issue immutable preview JWT
  -> resolve EffectivePrincipal(real_actor, effective_role, preview_tenant)
  -> apply existing role and tenant policies
  -> emit preview_started audit event
  -> on exit/expiry emit preview_ended or preview_expired
```

The original owner token remains unchanged. Preview context is request-scoped and must not mutate `users.role` or memberships.

## Authorization Matrix

| Actor | Target role | Target tenant | Expected |
|---|---|---|---|
| SUPER_ADMIN | STUDENT / TEACHER / SCHOOL_ADMIN | allowlisted existing tenant | ALLOW |
| SUPER_ADMIN | SUPER_ADMIN | any | DENY (no privileged preview) |
| STUDENT | any | any | DENY |
| TEACHER | any | any | DENY |
| SCHOOL_ADMIN | any | any | DENY |
| any | valid role + invalid/unowned tenant | any | DENY |
| any | forged query/storage claims | any | DENY |
| any | expired or wrong audience/purpose | any | DENY |

Effective role must never grant cross-tenant access or owner-only operations.

## Audit Events

Use existing `AuditLog`/`record_audit_log()` with non-sensitive fields:

- `preview_started`
- `preview_access_denied`
- `preview_ended`
- `preview_expired`

Record actor id, effective role, target tenant, preview id, timestamp, purpose, and outcome. Never record token values, secrets, raw authorization headers, or user payloads.

## Test Matrix

- SUPER_ADMIN preview student, teacher, and school admin: PASS.
- Student/Teacher/School Admin attempting preview: DENY.
- Invalid, cross-tenant, or unallowlisted tenant: DENY.
- Forged role/tenant query parameter or client storage: DENY.
- Expired token, wrong purpose, or wrong audience: DENY.
- Original persistent owner role remains SUPER_ADMIN after start/end/expiry.
- No membership or database role mutation.
- Audit start/deny/end/expiry events contain no sensitive metadata.
- Preview context cannot access owner-only mutation endpoints.

## Migration Need

NO for the initial expiring signed-context design. A durable revocation denylist or persistent preview-session history would require a separate migration gate.

## Production Mutation

NONE. This document is design-only.

## Commander Decision Required

Approve or reject this implementation design. No implementation, migration, role mutation, frontend change, deployment, environment change, or credential change is authorized by this design.
