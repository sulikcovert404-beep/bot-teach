# Post Migration Validation Plan — 2026-09-14

## Status
READY / BLOCKED BY PRODUCTION ACCESS

This document defines verification only. It does not authorize SSH, backup, migration, restart, deploy, environment, role, or database changes.

## Verification Matrix

### Database
- Confirm `alembic current` is exactly `20260912_0021`.
- Verify `exams.tenant_id` is NOT NULL and deterministic backfill has no unresolved rows.
- Verify `assignments.exam_id` nullability and tenant-aware FKs/unique constraints.
- Verify `exam_attempts` and `exam_results` exist with expected indexes and constraints.
- Verify RLS is enabled and forced on required exam tables; no unexpected heads.

### Application
- `/health` = 200.
- `/health/ready` = 200.
- Runtime role is restricted (`NOSUPERUSER`, `NOBYPASSRLS`).
- Resolver and transaction-local tenant context work; pool reuse leaves no context leakage.

### Exam and authorization
- Student start/save/submit/result positive flow passes.
- Unassigned, wrong classroom, cross-tenant, other-student, time-window and legacy-ID requests deny.
- Teacher sees only own tenant/class-scoped results.
- School admin sees own school/tenant only.
- Revoked membership denies required operations while preserving attempt/result rows.

## Rollback Triggers
Stop and investigate; invoke approved rollback/restore decision for:
- migration failure or revision mismatch;
- readiness/health failure;
- RLS, resolver or permission failure;
- tenant leakage or authorization regression;
- Exam smoke failure;
- unexpected lock, storage or I/O degradation.

## Monitoring Window
At execution time, define a named operator and observe:
- API health/readiness and 5xx rate;
- DB errors, lock waits, connection pool saturation;
- Redis errors;
- RLS denials and authorization failures;
- Exam attempt/result errors;
- CPU, memory, disk, I/O PSI and container restarts.

Close only after a documented stable observation window agreed by Commander/owner. Any anomaly keeps the gate open.

## Final Operator Checklist
Before: SSH verified, fresh backup hash verified, exact head `20260912_0020`, preflight PASS.

During: explicit `alembic upgrade 20260912_0021` only after a separate execution authorization.

After: revision/schema/RLS checks, health/readiness, Student/Teacher/Admin smoke, negative security suite, monitoring and Commander close/rollback decision.

## Remaining Blockers
- SSH access to production remains blocked.
- Fresh backup and final preflight are pending.
- Live DB remains `20260912_0020`; migration execution is locked.

## Production Mutation
NONE.

## Commander Decision Required
YES — plan is ready. Do not execute until SSH, fresh backup and final preflight gates pass and a separate migration execution authorization is issued.
