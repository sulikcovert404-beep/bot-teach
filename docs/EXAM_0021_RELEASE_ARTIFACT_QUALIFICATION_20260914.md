# Exam 0021 Release Artifact Qualification

Date: 2026-09-14

## Result

**FAIL — artifact qualification incomplete.**

The disposable Compose run built the candidate image successfully and began the Alembic chain, but the follow-up `alembic current` returned `20260910_0018`, not `20260912_0021`. Therefore the artifact was not proven to upgrade to 0021. The prior `EXAM_0021_ARTIFACT_QUAL=PASS` marker is rejected as an invalid assertion because the command did not verify the expected revision.

## Artifact

- Branch: `release/exam-0021-candidate`
- Commit: `993989a0e2ae8a6269b8b6ebff8263b71c967e5c`
- Artifact: `temp/canonical-release-exam-0021-993989a.tar.gz`
- Artifact SHA256: `15a5e7c43b3ae16785acafec9c96702a5f55686f1d6d30c12c1a30b7cd3d5323`
- Migration 0021 present: YES
- Parent: `20260912_0020`

## Evidence

- Disposable image build: PASS
- Disposable database startup: PASS
- Alembic chain started: PASS
- `alembic current`: `20260910_0018` (unexpected)
- Expected: `20260912_0021`
- Upgrade/downgrade/re-upgrade: NOT QUALIFIED

## Production safety

- Production database: unchanged (`20260912_0020`)
- Production deployment: none
- Production migration: none
- Environment/secrets: unchanged

## Next action

Commander decision required. Investigate the migration graph/qualification command and rerun with an explicit assertion that current revision equals `20260912_0021`; do not promote or execute the artifact on Production until that passes.

## Lineage Investigation Update

- Build branch: `release/exam-0021-candidate`
- Commit: `993989a0e2ae8a6269b8b6ebff8263b71c967e5c`
- Dockerfile build context: candidate worktree; `COPY migrations ./migrations` includes 0019, 0020, and 0021.
- Image graph: `alembic heads` = `20260912_0021 (head)`.
- Root cause of the earlier apparent 0018 result: the base Compose migration command is `alembic upgrade "$EXPECTED_MIGRATION_HEAD"`, and the normal local `.env` carries the stale expected head `20260910_0018`. The migration itself exited successfully at that requested revision; it did not attempt 0021.
- Corrected disposable run with an ephemeral env override targeting `20260912_0021`: upgrade exited 0 and `alembic current` returned `20260912_0021 (head)`.
- Production mutation: NONE.

The artifact is lineage-valid for the migration target under the corrected qualification command. Full downgrade/re-upgrade, RLS, and Exam E2E acceptance remain unqualified.

## Full Disposable Qualification Update

- Upgrade to `20260912_0021`: PASS
- Downgrade to `20260912_0020`: PASS; current revision verified as `20260912_0020 (mergepoint)`.
- Re-upgrade to `20260912_0021`: PASS; current revision verified as `20260912_0021 (head)`.
- RLS flags: `exams`, `exam_attempts`, and `exam_results` have row security and FORCE RLS enabled. The canonical assignment table is named `assignments` (not `exam_assignments`).
- Disposable resources were removed after qualification.
- Application-level Exam E2E, restricted-role context, and tenant-isolation tests were not executed in this cycle.
- Production mutation: NONE; Production remains at `20260912_0020`.
- Targeted local regression: `5 passed, 0 failed` for migration roundtrip and exam route tests (3 non-blocking deprecation warnings).

## Final Application Security Qualification Attempt

The disposable stack reached migration `20260912_0021`, but the application harness could not import `app.services.exam_attempts`. That service exists only as an untracked workspace file and is absent from the candidate release worktree/artifact. Therefore application-level qualification under the final artifact was not completed.

- Restricted `app_runtime` API E2E: NOT QUALIFIED
- Tenant context/resolver flow: NOT QUALIFIED
- Student start/save/submit/result lifecycle: NOT QUALIFIED
- Teacher/Admin scope: NOT QUALIFIED
- Negative cross-tenant/membership cases: NOT QUALIFIED
- Production mutation: NONE

This is a release-boundary completeness issue. The migration artifact must be assembled with the canonical application service (and its tests) before this gate can pass. No Production migration or deployment was attempted.

## Release 0021 Assembly Gate (non-production)

- Candidate commit: `21c905a` (`release/exam-0021-candidate`)
- Artifact: `temp/canonical-release-exam-0021-assembly-21c905a.tar`
- Artifact SHA256: `1384BDF915DB1052116CE2FF77813C9DEA09887107371A1D81C2FCB58F80AA37`
- Included application wiring: `app/services/exam_attempts.py`, tenant resolver, exam/student/teacher routes, models, DB context, and tenant tests.
- Targeted assembly tests: **11 passed, 0 failed** (2 non-blocking deprecation warnings).
- Production: **UNCHANGED**; no deploy, migration, environment edit, or runtime mutation performed.

Application security qualification remains pending until the assembled artifact is exercised against the disposable database and restricted runtime role.

## Qualification Harness Completion Update

- Candidate commit: `7fb7eda`
- Isolated test run: `25 passed, 919 deselected, 0 failed, exit 0` using `--basetemp temp/pytest-assembly`.
- The prior WinError 5 cleanup failure did not recur with the isolated workspace temp directory.
- This is still a test-level qualification result; restricted app_runtime disposable E2E and live migration remain unperformed.

## Restricted Runtime Qualification Update

- Candidate commit: `86d9da0` (non-production harness alignment)
- Fresh disposable migration reached `20260912_0021`.
- Runtime roles: `migration_owner`, `app_runtime`, `job_runner`; all LOGIN enabled, NOSUPERUSER and NOBYPASSRLS.
- FORCE RLS verified for disposable tenant tables.
- API runtime liveness: `/health` 200; readiness: `{"status":"ready","migration_head":"20260912_0021"}`.
- Source heads matched `20260912_0021`; API import and platform smoke passed.
- Full authenticated Exam E2E probe output was not emitted by the existing wrapper; no E2E PASS is claimed.
- Production remains unchanged at DB head `20260912_0020`.
