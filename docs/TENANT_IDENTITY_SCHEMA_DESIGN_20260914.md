# Tenant Identity Schema Design

Status: PASS / DESIGN ONLY  
Production mutation: NONE  
Migration: NOT CREATED

## Proposed canonical binding

Introduce a canonical `user_tenant_memberships` relation (name subject to repository conventions):

```text
id              bigint/integer primary key
user_id         FK users.id, not null
tenant_id       FK school_tenants.tenant_id, not null
status          ACTIVE | REVOKED | SUSPENDED
created_at      timestamptz, not null
updated_at      timestamptz, not null
revoked_at     timestamptz, nullable
created_by      FK users.id, nullable
membership_version integer, not null, default 1
```

Use a uniqueness rule that prevents duplicate active bindings while preserving history. If PostgreSQL partial unique indexes are selected, enforce at most one active row per `(user_id, tenant_id)` and retain revoked history. Status/revoked_at consistency must be checked (`ACTIVE` implies `revoked_at IS NULL`; revoked statuses require a timestamp).

## Resolver contract

```text
resolve_tenant(user_id, requested_scope?)
  → exactly one validated active tenant
  → AmbiguousTenant when multiple active tenants and no explicit selection
  → NoTenant when none
  → Revoked/Forbidden when binding is inactive
```

The resolver is the only component allowed to translate identity to tenant. It must run before tenant-owned queries and return an immutable request context. For multi-tenant users, selection is authenticated and server-validated against active bindings; never choose the first row.

## Access boundary and RLS

The binding is an identity-resolution source, not a bypass for tenant data. Its read path needs a narrowly scoped resolver boundary (for example, a security-reviewed view or dedicated resolver transaction) that can read only the requesting user’s bindings. It must not grant the application `BYPASSRLS` or disable FORCE RLS. After resolution, the normal request transaction calls `set_tenant_context(..., is_local=true)` and all tenant-owned tables remain RLS protected.

## Backfill strategy

- Teachers: derive candidate bindings from existing `teacher_profiles.tenant_id`, deduplicate deterministically, and record conflicts for review.
- School admins: derive from active/non-revoked `school_admin_memberships`.
- Students: derive from active `ClassMembership → Classroom.tenant_id`; users with zero or multiple tenant candidates must be quarantined for explicit enrollment resolution, never guessed.
- No backfill may silently assign a tenant or delete historical membership data. Produce orphan/ambiguity counts before migration.

## Migration and rollback risks

Schema migration is required and must be a separate reviewed gate. It must include FK/index/constraint design, data backfill rehearsal, orphan and ambiguity report, downgrade/re-upgrade on disposable PostgreSQL, and resolver compatibility tests. Rollback must preserve historical membership rows and avoid invalidating currently valid sessions without an explicit transition plan.

## Security and audit controls

Membership create, activate, suspend, revoke, and context selection must be authorization-checked and audit logged. Revoked bindings deny new context issuance immediately. Context tokens, if later added, are derived hints with bounded expiry and membership revalidation.

## Commander Decision Required

Approve this schema direction and authorize a dedicated AI/team-reviewed migration design gate. Until then, do not modify models, JWTs, RLS policies, production roles, or production DB; Exam 0021 remains blocked and production remains at `20260912_0020`.
