# Production Migration Decision Bundle — 2026-09-14

## Status
PACKAGE READY / EXECUTION BLOCKED

This bundle is planning evidence only. It authorizes no SSH action, backup creation, migration, deploy, restart, environment change, role change, or database mutation.

## Execution Checklist

### GO criteria (all mandatory)
- Approved SSH identity works and `sudo -n true` succeeds where required.
- `/health` and `/health/ready` return 200.
- Live Alembic head is exactly `20260912_0020`; no unexpected heads.
- PostgreSQL and Redis are healthy; storage, I/O, memory and disk pressure are normal.
- A fresh production backup is created by an explicitly approved gate, hash verified, and restore/list check passes.
- Migration artifact is the reviewed `20260912_0021` with parent `20260912_0020` and verified checksum.
- Rollback owner, maintenance/traffic window and monitoring operator are named.

### STOP criteria
- SSH or sudo failure.
- Health/readiness failure or DB head mismatch.
- Backup unavailable, hash mismatch, or restore verification failure.
- I/O stall, D-state, filesystem/storage degradation, or unacceptable lock estimate.
- Unresolved tenant backfill rows.
- Any RLS, role, FK, or post-migration smoke failure.

## Operator Command Sequence (review only)
1. Read-only preflight and exact-head check.
2. Approved fresh backup and verification.
3. Capture baseline health, DB load, lock state and storage metrics.
4. Run explicit `alembic upgrade 20260912_0021` only after the execution gate.
5. Verify revision, schema, constraints/FKs, forced RLS, readiness and role behavior.
6. Run Student/Teacher/Admin Exam smoke and cross-tenant denial checks.
7. Record evidence and close only if all acceptance checks pass.

Never use `alembic upgrade head` or `alembic stamp`.

## Rollback Decision Matrix

| Event | Action |
|---|---|
| Migration command failure | Stop; preserve logs; restore/rollback using approved runbook |
| Readiness or health failure | Stop and investigate; rollback if caused by migration |
| RLS or tenant leakage | Immediate rollback/restore; block traffic if needed |
| Exam smoke failure | Hold release; rollback/restore after evidence capture |
| Backup/restore verification failure | Do not execute migration |
| Storage/I/O degradation | Stop; no retry until host is stable |

Rollback is an explicit Commander/owner decision. Downgrade is destructive for exam attempt/result data and must not be used as an implicit undo.

## Owner Decision Record
- Migration owner: Commander/production operator to be named at execution gate.
- Approval point: after fresh backup and final preflight, immediately before explicit upgrade.
- Rollback authority: Commander/owner or delegated incident operator.
- Monitoring owner: to be named before execution.

## Current Blockers
- SSH access to production is rejected with `Permission denied (publickey,password)`.
- Fresh production backup has not been authorized or created in this gate.
- Production migration remains NOT AUTHORIZED; live DB remains pinned at `20260912_0020`.

## Evidence References
- `docs/PRODUCTION_MIGRATION_PREFLIGHT_20260914.md`
- `docs/PRODUCTION_MIGRATION_PACKAGE_FINAL_REVIEW_20260914.md`
- `docs/EXAM_0021_PRODUCTION_MIGRATION_READINESS_20260914.md`
- `docs/FINAL_DISPOSABLE_HTTP_ROUTE_QUALIFICATION_20260914.md`

## Production Mutation
NONE.

## Commander Decision Required
YES — restore approved SSH access and explicitly open Fresh Backup + Final Production Precheck Gate before any execution decision.
