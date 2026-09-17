# BATCH134 — Preview Tenant Authority Canonicalization

Date: 2026-09-17
Scope: Read-only discovery; no implementation or runtime changes.

## Tenant registry

Canonical registry found: `app.db.models.SchoolTenant` (`school_tenants`, unique `tenant_id`). The existing `/admin/tenants/schools` endpoints read this registry, but their guard uses legacy `require_roles("ADMIN")`, while the canonical platform role is `SUPER_ADMIN`. Therefore registry existence is proven, but owner authorization to it is not yet aligned.

`UserTenantMembership` is a user membership source, not an appropriate default owner-wide preview scope. `SchoolAdminMembership`, `TeacherProfile`, and `ClassMembership` are role-specific relations and must not define owner preview authority.

## Role-specific preview semantics

The safe v1 contract is role preview, not user impersonation:

- `real_role = SUPER_ADMIN`
- `effective_role = STUDENT | TEACHER | SCHOOL_ADMIN`
- `preview_tenant_id =` server-resolved `SchoolTenant.tenant_id`
- no target user id is accepted or fabricated

Current teacher/student API flows often require real profile or membership rows, so a tenant-only effective role may render static shells but cannot be assumed to provide a complete role workflow. This is an explicit implementation test gap.

## Boundary recommendation

Use a dedicated platform security router for `POST /platform/preview/start` and `/platform/preview/exit`, guarded by a dependency that checks canonical `real_role == SUPER_ADMIN`. Resolve the requested tenant by querying `SchoolTenant` server-side and require an eligible licensing/isolation state according to a policy still to be specified. Integrate effective context as a request-scoped dependency after JWT decode; do not add global middleware unless required.

## Conflicts and blockers

- Legacy `ADMIN` guards and canonical `SUPER_ADMIN` guards compete on existing administrative endpoints.
- No explicit owner preview eligibility policy exists for `SchoolTenant.licensing_status` or `data_isolation_verified`.
- Role dashboards may require real target profiles; no fake profile is allowed.

## Verdict

**USER_IMPERSONATION_MODEL_REQUIRED**. A canonical tenant registry exists, but owner authorization semantics and eligible tenant policy are not defined consistently, and role-specific flows may require real profiles. Gate 132 remains blocked because role-scoped workflows require a real target profile; a role-only preview cannot safely impersonate those flows. A separate decision is required on whether to support user impersonation or restrict preview to shell/tenant-level surfaces.

No code, tests, schema, DB, server, Telegram, deployment, environment, or secret changes were made. Gate 134 commit remains HOLD.

