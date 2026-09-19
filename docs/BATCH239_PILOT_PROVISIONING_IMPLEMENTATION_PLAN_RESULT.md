# Gate 239 — Pilot Provisioning Implementation Plan

Date: 2026-09-19
Mode: Pre-implementation design only
Code/DB/deploy changes: NONE

## 1. API surface

Proposed endpoint:

```text
POST /api/v1/admin/test-identities
```

Authorization dependency:

```text
canonical SUPER_ADMIN only
```

Request fields:

```yaml
provider: telegram
subject: validated provider subject (string)
username: optional display username
role: STUDENT | TEACHER | SCHOOL_ADMIN
tenant_id: existing tenant identifier, required for TEACHER/SCHOOL_ADMIN
active_until: optional controlled expiry
plan: optional, handled by a separate entitlement gate
idempotency_key: required opaque key
audit_reason: required bounded string
```

Response fields:

```yaml
status: CREATED | EXISTING | DENIED
audit_id: non-sensitive audit reference
user_id: generated server id when successful
role: assigned role
tenant_id: bound tenant or null
```

The request must never accept an arbitrary numeric `user_id`, raw Telegram `init_data`, password, token, or secret.

## 2. Service-layer transaction

`provision_test_identity()` should:

1. Resolve the canonical actor and authorize `SUPER_ADMIN`.
2. Validate provider/subject and idempotency key.
3. Lock or uniquely resolve an existing identity by `(provider, subject)`.
4. Validate role and tenant compatibility before writes.
5. Create `User` with a server-generated id.
6. Create exactly one role-specific profile/membership.
7. Record audit success in the same transaction.
8. Commit once; return the generated id and audit reference.

On any error, rollback all user/profile/membership/audit writes. Repeat requests with the same idempotency key return the original outcome without duplicate records. Subscription and entitlement writes are excluded and require a later gate.

## 3. Authorization and isolation rules

```yaml
allowed_actor: canonical SUPER_ADMIN
allowed_roles: STUDENT, TEACHER, SCHOOL_ADMIN
forbidden_role: SUPER_ADMIN
student_tenant: no implicit tenant; explicit membership flow required
teacher_tenant: existing tenant + TeacherProfile.tenant_id
school_admin_tenant: existing tenant + active SchoolAdminMembership
cross_tenant_binding: DENY
preview_token: DENY for provisioning
```

The operation must emit denial audits for unauthorized actor, invalid tenant, role incompatibility, duplicate active binding, and forbidden owner creation.

## 4. Test strategy

Before implementation approval, add focused tests for:

- canonical owner allow / non-owner deny;
- role allow-list and SUPER_ADMIN denial;
- valid identity creation;
- same provider/subject idempotency;
- tenant existence and role/tenant compatibility;
- cross-tenant denial;
- exactly one profile/membership;
- atomic rollback on profile or audit failure;
- subscription and entitlement unchanged;
- preview token cannot invoke the service;
- secrets and provider payloads absent from logs;
- audit success and denial records.

Run the focused suite first, then full regression if service/model code changes.

## 5. Deployment impact

```yaml
migration: NONE EXPECTED; re-evaluate only if implementation proves a missing constraint
new_env: NONE
secret_change: NONE
runtime: additive API/service only
DB_write: only in a separately authorized implementation gate
deploy: forbidden in this planning gate
```

Implementation should begin on a disposable/staging branch, with no production or Telegram activation until qualification and a separate execution gate.

## Verdict

```text
IMPLEMENTATION_PLAN_READY
```

Gate 239 commit: HOLD.
