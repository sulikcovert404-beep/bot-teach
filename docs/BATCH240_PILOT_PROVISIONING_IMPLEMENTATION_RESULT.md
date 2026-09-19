# Gate 240 — Pilot Provisioning Implementation Result

Date: 2026-09-19
Mode: Controlled source implementation; no deployment

## Implementation

Added:

- `app/services/test_identity_provisioning.py`
  - transactional provisioning service
  - provider/subject identity resolution
  - role allow-list (`STUDENT`, `TEACHER`, `SCHOOL_ADMIN`)
  - explicit prohibition of `SUPER_ADMIN`
  - tenant existence and role compatibility checks
  - role-specific profile/membership creation
  - idempotent existing-identity handling
  - audit record creation in the same transaction
  - rollback on integrity/validation failure
  - subscriptions and entitlements excluded

- `POST /api/v1/admin/test-identities` in `app/api/routes/admin.py`
  - canonical `SUPER_ADMIN` dependency
  - canonical owner read-back before provisioning
  - bounded request schema
  - no arbitrary numeric `user_id`
  - `active_until` rejected until a separate entitlement gate

- `tests/test_test_identity_provisioning.py`
  - student creation and idempotent retry
  - missing tenant denial
  - forbidden owner-role denial

## Validation

```text
Focused provisioning tests: 2 passed
Auth regression pair:       3 passed, 1 warning
Python compile:             PASS
Ruff E9/F:                  PASS
Full regression:            977 passed, 5 skipped, 0 failed
Full regression exit code:  0
```

The warning is the existing Starlette/httpx deprecation warning; no failure occurred.

## Boundaries respected

```text
Production user creation:    NONE
Subscription mutation:       NONE
Entitlement activation:      NONE
Migration:                   NONE
Secret change:               NONE
Cloudflare/DNS:              NONE
Deploy:                      NONE
Commit:                      HOLD
```

The implementation exists only in the working tree. It was not deployed or exercised against the production database.

## Verdict

```text
PILOT_PROVISIONING_IMPLEMENTED
```

A separate deployment gate and a separate first-test-identity execution gate are still required.
