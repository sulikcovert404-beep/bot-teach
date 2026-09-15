# Tenant Identity Migration Design

Status: PASS / DESIGN ONLY  
Production mutation: NONE  
Migration file: NOT CREATED

## Migration order

1. Create the membership structure and required tenant/user foreign keys.
2. Add status/timestamp consistency constraints and active-membership uniqueness.
3. Add indexes for `(user_id, status)` and `(tenant_id, status)` plus resolver lookups.
4. Backfill candidate bindings in a staging/quarantine mode; do not silently assign ambiguous or missing users.
5. Produce orphan, ambiguity, duplicate-active, and unresolved counts; abort if policy thresholds are not met.
6. Provision the resolver read boundary and test it with the restricted runtime role.
7. Only after qualification, enable request-bound tenant context for Exam paths.

The migration must descend explicitly from the current production lineage and be qualified on disposable PostgreSQL. It must not re-parent or rewrite existing revisions.

## Backfill plan

- **Teacher:** `teacher_profiles.teacher_id → tenant_id`; deduplicate identical active candidates and quarantine conflicting candidates.
- **School Admin:** copy active/non-revoked `school_admin_memberships` bindings, preserving status and revocation history.
- **Student:** derive candidates from `ClassMembership → Classroom.tenant_id`; zero candidates and multiple-tenant candidates are quarantined for explicit enrollment resolution. No first-row selection.
- Record source and migration version for every generated binding. Preserve existing membership rows.

## Safety checks before migration

Read-only preflight must report:

- orphan users without a resolvable tenant;
- ambiguous users with multiple active tenant candidates;
- duplicate active bindings;
- classrooms whose tenant has no `SchoolTenant` row;
- invalid/revoked source memberships;
- expected row counts and deterministic backfill digest.

Any unexpected count or nondeterministic mapping stops the migration gate.

## Resolver security boundary

The resolver must query only bindings for the authenticated user and return no cross-user/global dataset. Its database access must be a narrowly scoped, security-reviewed boundary; it must not grant `BYPASSRLS` to `app_runtime` or disable FORCE RLS on tenant-owned tables. The exact role/view strategy remains a required pre-implementation decision and must be documented with grants and audit events.

## RLS compatibility

After resolver success:

```text
resolve active binding
→ begin transaction
→ set_tenant_context(..., is_local=true)
→ tenant-owned queries under FORCE RLS
→ commit/rollback
→ release connection
```

Missing, ambiguous, revoked, or mismatched binding fails closed. Pool interleaving, savepoint, autocommit, exception, and concurrent request tests are mandatory.

## Rollback strategy

Rollback is rehearsal-only until separately approved. It must preserve historical membership rows and not invalidate existing tenant data. Use an explicit revision target, verified backup, disposable downgrade/re-upgrade, and a compatibility window for old JWTs. Do not roll back by deleting rows or weakening RLS.

## Qualification gates

1. AI/team-reviewed migration design and resolver access boundary.
2. Disposable PostgreSQL schema/backfill rehearsal.
3. Restricted-role resolver + request-context integration tests.
4. Exam 0021 application E2E re-qualification.
5. Separate staging/production migration decision.

## Commander Decision Required

Approve this migration design and the resolver read-boundary design, then authorize a dedicated implementation gate. Until approval, no table, model, JWT, RLS, role, environment, or production change is permitted; production remains at `20260912_0020`.
