# Release Boundary Completeness Review — Exam 0021

Date: 2026-09-14

## Status

**BLOCKED pending Commander inclusion decision.** The candidate release commit contains migration 0021 only. The application implementation required to qualify the migration is present in the main workspace as untracked files and is absent from the candidate worktree and artifact.

## Commit boundary

- Candidate branch: `release/exam-0021-candidate`
- Candidate commit: `993989a0e2ae8a6269b8b6ebff8263b71c967e5c`
- Parent: `b5b34e7bca4fb5ace2c32940759a2fceebc61b38`
- Commit change: only `migrations/versions/20260912_0021_exam_persistence.py`
- Migration parent: `20260912_0020`
- Migration SHA256: `E227211BA4247D8A2E41D3682338BBF111E11A24C34F54C5ED1058D8CF09D6E8`
- Candidate artifact SHA256: `15a5e7c43b3ae16785acafec9c96702a5f55686f1d6d30c12c1a30b7cd3d5323`

## Current workspace files outside the boundary

- `app/services/exam_attempts.py` — untracked; required by the Exam application flow.
- `app/security/tenant_resolver.py` — untracked; needed for tenant context integration.
- `tests/test_tenant_resolver.py` — untracked.
- Existing route tests cover authentication/status guards but no persisted Exam attempt lifecycle.

The candidate Docker build copies only the candidate worktree. Importing `app.services.exam_attempts` from that image fails with `ModuleNotFoundError`, so the application security gate cannot run against this artifact.

## Canonical inclusion decision required

Commander must decide whether the following are part of Release 0021:

1. `app/services/exam_attempts.py`
2. `app/security/tenant_resolver.py` and tenant context wiring used by the service
3. persisted Exam lifecycle and authorization tests (student, teacher/admin, membership and cross-tenant negatives)
4. any directly required model/API files already modified in the workspace

If yes, create a new official commit from the appropriate complete baseline, rebuild the artifact and rerun disposable qualification. If no, migration 0021 must remain schema-only and the application gate remains blocked.

## Production safety

- Production migration: NONE
- Production deployment: NONE
- Production DB: unchanged at `20260912_0020`
- Secrets/environment: unchanged
