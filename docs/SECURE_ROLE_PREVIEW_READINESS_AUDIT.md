# Secure Role Preview Readiness Audit

Status: PASS / READY FOR DESIGN — IMPLEMENTATION HOLD

## Authorization Flow

- Telegram WebApp authentication issues a JWT from the authenticated backend identity.
- `app/security/tokens.py` uses HS256 with `sub`, `iat`, `exp`, and optional `role`.
- `app/security/principal.py` and `app/security/dependencies.py` resolve the canonical principal and enforce roles server-side.
- Persistent owner role remains `SUPER_ADMIN`; no preview fields exist in the current principal.
- Tenant scope is currently enforced through server-side policy (`SUPER_ADMIN` explicit scope, school membership, teacher profile/class membership).

## Preview Model

- A short-lived server-issued preview JWT is design-compatible without schema migration.
- Required claims: `real_role=SUPER_ADMIN`, `effective_role`, validated `preview_tenant`, `preview_id`, `purpose`, `aud`, `iat`, `exp`.
- Client query parameters and storage must never be authority for role or tenant.
- Current effective-role support is NOT IMPLEMENTED; this is a design gap, not an approved change.

## Audit Capability

`AuditLog` and `record_audit_log()` can record `preview_started` and `preview_ended` with actor, effective role, target tenant, preview id, timestamp, purpose, and outcome. Existing sensitive-key filtering prevents credential material in metadata.

## Schema Impact

Initial expiring preview context can be implemented without migration. Durable revocation or persistent preview-session history would require a separate schema decision and migration gate.

## Risks

- Forged role or tenant claims must be rejected by a SUPER_ADMIN-only issuer.
- Expired or wrong-purpose/audience preview tokens must fail closed.
- Effective role must not grant privileged operations beyond the selected preview scope.
- Exit behavior is natural expiry/context discard unless a separate revocation mechanism is approved.
- Safe preview tenant and role fixtures have not been verified from source-only evidence.

## Acceptance

- Current auth integration: CLASSIFIED
- Schema impact: CLASSIFIED (NO migration for initial design)
- Security risks: IDENTIFIED
- Implementation recommendation: PREPARED
- Production mutation: NONE

## Commander Decision Required

Approve a separate implementation-design gate only after controlled fixture selection. No implementation, migration, role mutation, frontend change, deploy, environment change, or credential change was performed.
