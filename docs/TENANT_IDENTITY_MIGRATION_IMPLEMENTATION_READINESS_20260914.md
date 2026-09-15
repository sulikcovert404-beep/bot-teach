# Tenant Identity Migration Implementation Readiness

## Status

**PASS — design/readiness only.** No Alembic revision was created or executed. Production remains at `20260912_0020`.

## Migration Components

Proposed next revision (identifier to be assigned only after approval):

- `user_tenant_memberships`: `id`, `user_id`, `tenant_id`, `status` (`ACTIVE|REVOKED|SUSPENDED`), `created_at`, `created_by`, `revoked_at`, and optional monotonic `membership_version`.
- Foreign keys to `users.id` and `school_tenants.tenant_id`; check constraint for status; uniqueness on `(user_id, tenant_id)`.
- Partial unique index for one active binding per user if product policy remains single-tenant; otherwise explicit tenant-selection semantics are required before enabling it.
- Lookup indexes on `(user_id, status)` and `(user_id, tenant_id)`.
- Resolver function deployed after the table/indexes and before request-context wiring; grants are explicit and minimal.

## Backfill Strategy

Authoritative sources are existing `class_memberships → classrooms.tenant_id` for students, `teacher_profiles` for teachers, and `school_admin_memberships` for school admins. `SUPER_ADMIN` is server-scoped and is not backfilled as a tenant membership.

Backfill is deterministic and idempotent. Missing or ambiguous mappings are quarantined and abort promotion; no tenant is guessed. Before write, validate orphan users, missing tenants, duplicate active candidates, invalid/revoked sources, expected counts, and a stable digest of the candidate set. Preserve source IDs and provenance for rollback/audit.

## Resolver Deployment Order

1. Create table, constraints, and indexes.
2. Run deterministic backfill into a disposable database.
3. Validate/quarantine and verify digest.
4. Create the fixed-`search_path` `SECURITY DEFINER` resolver owned by `migration_owner`.
5. Revoke public access; grant `EXECUTE` only to the resolver principal.
6. Qualify resolver + `set_tenant_context(is_local=true)` + FORCE RLS with the real application under `app_runtime`.
7. Wire request boundary, then re-qualify Exam 0021.

## Compatibility

Existing JWT `sub`/`role` claims remain readable. Tenant scope is resolved server-side from the verified subject; clients cannot provide or select a tenant. During rollout, old tokens remain valid while resolution is available, but tenant-dependent endpoints fail closed when no unique active binding exists.

## Rollout Plan

Disposable upgrade/downgrade/re-upgrade first, including application process under `NOSUPERUSER/NOBYPASSRLS` runtime role. Then a staging rehearsal from `20260912_0020` using an explicit revision (never `alembic upgrade head`), backup verification, lock/latency checks, and readiness validation. Production requires a separate Commander gate, maintenance/rollback plan, and explicit target revision.

## Rollback

Rollback is an explicit downgrade rehearsal with verified backup and preserved membership history. Do not delete source memberships or weaken RLS. Keep a compatibility window so old JWTs fail closed rather than silently broadening access. Any mismatch, ambiguous backfill, lock stall, or app incompatibility stops promotion.

## Exam 0021 Dependency Plan

`Tenant Identity Migration Qualification` → `Resolver production-like qualification` → `request-context wiring` → `Exam 0021 re-qualification` → separate production migration gate. Until all pass, Exam 0021 and live RLS/role changes remain blocked.

## Production Mutation

NONE.

## Commander Decision Required

YES — approve the migration design for disposable implementation planning, or request changes. This document does not authorize schema creation, Alembic execution, role changes, deployment, JWT changes, or production mutation.
