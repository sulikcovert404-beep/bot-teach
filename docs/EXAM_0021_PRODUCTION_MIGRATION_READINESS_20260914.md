# Exam 0021 Production Migration Readiness — 2026-09-14

## Status
READINESS REVIEW ONLY. No production migration, deployment, environment, role, or database mutation.

## Backup
- Existing backup/rehearsal evidence is documented in `docs/EXAM_0021_PRE_IMPLEMENTATION_AUDIT_20260914.md`.
- The candidate migration has not been authorized for live execution; a fresh live backup must be taken immediately before any future approved run and verified before proceeding.

## Migration Plan
- Current live target: `20260912_0020`.
- Candidate: `20260912_0021`, direct descendant of `20260912_0020`.
- Explicit order: backup → prechecks → `alembic upgrade 20260912_0021` → schema/readiness checks → application smoke.
- Never use `alembic upgrade head` or `stamp`.
- Candidate adds `exams.tenant_id` with deterministic backfill, nullable `assignments.exam_id`, attempt/result tables, tenant-aware constraints/FKs, and forced RLS.

## Rollback
- Downgrade is destructive for exam attempt/result tables and removes `exams.tenant_id`; only disposable rehearsal is currently evidenced.
- A live rollback requires a verified backup, explicit incident decision, maintenance/traffic plan, and post-restore integrity checks.
- Re-upgrade rehearsal has passed on disposable infrastructure.

## Monitoring
- Monitor migration duration and lock waits, API health/readiness, DB errors, RLS denials, attempt creation, and Telegram/webhook error rates.
- Abort before live mutation if unresolved exam tenant backfill rows, lock pressure, storage/I/O degradation, or readiness drift appears.

## Risks
- Destructive downgrade boundary.
- Forced RLS compatibility with runtime/background roles.
- Existing exam rows without deterministic teacher tenant mapping.
- Composite FK/index compatibility and lock duration.

## Current Qualification Evidence
- Final disposable HTTP route qualification: PASS.
- Teacher/Admin scoped HTTP, revocation denial, pool isolation, and RLS checks: PASS in disposable Compose.
- Production DB remains pinned at `20260912_0020`.

## Production Mutation
NONE.

## Commander Decision Required
YES — decide whether to authorize a separate live migration execution gate after confirming a fresh production backup, prechecks, lock/downtime window, and rollback ownership. This document does not authorize execution.
