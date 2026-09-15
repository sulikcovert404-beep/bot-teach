# POST MIGRATION RECOVERY VALIDATION CHECKLIST

Date: 2026-09-14
Mode: Read-only preparation; no server or production mutation

## Current state

- Production database target: `20260912_0020` until an explicit migration gate says otherwise.
- Candidate migration: `20260912_0021`; never use `alembic upgrade head`.
- Current blocker: Docker/host I/O stability is not cleared. Container lifecycle operations remain blocked.
- Last observed public endpoints: `/health` and `/health/ready` returned 200 in the prior stability check; re-verify after the host gate is cleared.
- No SSH, Docker lifecycle, database, migration, environment, Cloudflare, webhook, or credential mutation is authorized by this checklist.

## Required evidence after recovery gate opens

### Database

- [ ] `alembic current` is exactly `20260912_0021`.
- [ ] `alembic heads` has one head and equals `20260912_0021`.
- [ ] `exams.tenant_id` is `NOT NULL`; unresolved backfill count is zero.
- [ ] `assignments.exam_id` has the intended nullability and tenant-aware foreign keys/unique constraints.
- [ ] `exam_attempts` and `exam_results` exist with expected primary keys, indexes, and constraints.
- [ ] Required exam tables have RLS enabled and forced; policy behavior is verified under the restricted runtime role.
- [ ] Runtime role is `NOSUPERUSER` and `NOBYPASSRLS`; no elevated bypass is used.

### Application readiness

- [ ] `GET /health` returns 200.
- [ ] `GET /health/ready` returns 200 and reports the exact migration head.
- [ ] Tenant resolver and transaction-local context fail closed for missing/invalid context.
- [ ] Connection-pool reuse and interleaving show no tenant-context leakage.
- [ ] No unexpected 5xx, restart loop, OOM, DB error, Redis error, or migration drift occurs during observation.

### Exam authorization and lifecycle

- [ ] Student positive flow: start, save, submit, and result access.
- [ ] Deny: unassigned student, wrong classroom, cross-tenant, other student's attempt/result.
- [ ] Deny outside `publish_at`/`close_at` windows.
- [ ] Deny legacy direct `exam_id` bypass.
- [ ] Deny invalid state transitions.
- [ ] Membership removal/revocation denies start, save, submit, and result while preserving historical rows.
- [ ] Teacher results remain limited to assigned classes and own tenant.
- [ ] School admin remains limited to own school/tenant.
- [ ] Two concurrent `start_attempt` calls produce no duplicate attempt number, unhandled integrity error, or corrupt active attempt.

### Infrastructure and rollback safety

- [ ] Docker daemon responds consistently across multiple bounded samples.
- [ ] Docker socket and storage driver are responsive.
- [ ] I/O PSI is normalizing; no D-state, filesystem error, or blocked-task recurrence.
- [ ] API, PostgreSQL, and Redis containers are healthy with no restart/OOM anomalies.
- [ ] Rollback trigger list is reviewed: health/readiness failure, head mismatch, lock/storage degradation, RLS/authorization failure, tenant leakage, or exam smoke failure.
- [ ] Backup hash and restore-list verification are recorded before any authorized live migration.

## Execution order (only after separate authorization)

1. Capture read-only preflight and backup evidence.
2. On a disposable database, rehearse explicit `0020 → 0021` upgrade, schema checks, downgrade, and re-upgrade.
3. Qualify the application under the restricted runtime role.
4. Obtain a separate Commander execution gate.
5. If authorized, run only `alembic upgrade 20260912_0021` on the approved target.
6. Re-run database, application, authorization, concurrency, and monitoring checks.
7. Report evidence and wait for Commander close/rollback decision.

## Prohibited while this checklist is active

- Container remove/recreate/restart while Docker stability is uncleared
- Docker daemon or host restart
- `alembic upgrade head`, `stamp`, or downgrade on live production
- Environment, credential, role, RLS, schema, volume, Cloudflare, webhook, or Telegram changes
- Any claim of PASS based only on unit tests, mocks, or stale reports

## Current decision

- Recovery gate: HOLD
- Database/migration mutation: HOLD
- Production mutation performed: NONE
- Commander decision required: yes, before any recovery or live migration
