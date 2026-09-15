# Exam 0021 Pre-Implementation Audit

Status: PASS / ANALYSIS ONLY  
Production mutation: NONE  
Current qualified production head: `20260912_0020`  
Candidate revision: `20260912_0021`

## Current DB and migration chain

The repository has a single script head at `20260912_0021`. Revision `20260912_0021` descends directly from `20260912_0020`; `20260912_0020` is the dual-parent merge of `20260909_0009` and `20260910_0019`. Production remains explicitly pinned to `20260912_0020`; this audit did not connect to or mutate production.

The candidate is therefore a linear post-merge migration, but it is not qualified for live execution. A future gate must rehearse `0020 → 0021` on a disposable PostgreSQL database, including downgrade and re-upgrade, before any staging decision.

## Schema impact (static review)

`20260912_0021_exam_persistence.py`:

- Adds non-null `exams.tenant_id` after deterministic backfill from `teacher_profiles`; unresolved rows abort the upgrade.
- Adds nullable `assignments.exam_id` with `ON DELETE SET NULL` and an index.
- Creates `exam_attempts` with tenant, assignment, student, status, question snapshot, answers, timestamps, a status check, and unique `(assignment_id, student_id, attempt_no)`.
- Creates `exam_results` with tenant, one-to-one attempt FK, score fields, grading metadata, and indexes.
- Adds composite tenant uniqueness and tenant-aware foreign keys for exams, assignments, attempts, and results.
- Enables and forces RLS on `exams`, `exam_attempts`, and `exam_results` with transaction-local `app.tenant_id` policies.

### Constraints and risks requiring qualification

1. Existing `exams` rows without a matching teacher profile cause a deliberate fail-closed abort; the unresolved count must be measured before live consideration.
2. Composite foreign-key creation must be verified against the existing primary-key/unique definitions on PostgreSQL.
3. Forced RLS requires the runtime role and background jobs to set tenant context correctly; the current production runtime must not be changed by this audit.
4. The downgrade drops exam attempt/result tables and removes tenant data from exams. It is destructive and may only be rehearsed on disposable data with a verified backup.
5. `ExamAttempt.student_id` references `users.id`, while service code resolves `StudentProfile`; identity consistency must be tested.
6. The candidate script is PostgreSQL-specific (RLS and inspector behavior); SQLite model tests do not prove migration correctness.

## Static application and regression matrix

Existing implementation/tests cover assignment persistence, exam route authentication, attempt lifecycle helpers, publish/close checks, tenant predicates, and migration lineage assertions. The repository also contains tests for:

- concurrent start and tenant context behavior;
- unassigned/wrong-class/cross-tenant access;
- other-student attempt/result access;
- before `publish_at` and after `close_at` denial;
- legacy direct `exam_id` bypass;
- teacher result visibility and student progress.

These tests are readiness evidence only until they run against disposable PostgreSQL at `0021`. Remaining qualification gaps are:

- real concurrent `start_attempt` calls and duplicate numbering/IntegrityError handling;
- membership removal as the canonical revoked-access semantic (no `revoked_at` field should be invented);
- PostgreSQL RLS under the restricted runtime role, including missing/invalid tenant context;
- tenant-aware FK and forced-RLS verification after upgrade, downgrade, and re-upgrade;
- persisted-chunk/result citation and complete positive Exam E2E.

## Production safety plan (design only)

1. Freeze candidate and record current head `20260912_0020`.
2. Create a disposable PostgreSQL database from a verified schema/data fixture.
3. Run explicit `alembic upgrade 20260912_0021` (never `alembic upgrade head` or `stamp`).
4. Inspect columns, constraints, indexes, RLS/forced-RLS, and `alembic_version`.
5. Run positive and negative application E2E plus concurrency tests with a restricted runtime role.
6. Rehearse explicit downgrade to `20260912_0020`, verify expected data-loss boundary on disposable data, then re-upgrade to `0021`.
7. Only after a clean rehearsal may a separate Commander gate consider staging; production remains unchanged.

## Risk register

| Risk | Status | Required mitigation |
|---|---|---|
| Tenant backfill unresolved | Unknown until disposable inspection | Count and fail closed; do not bypass. |
| RLS/runtime-role incompatibility | Open | Test with restricted role and transaction-local context. |
| Concurrent attempt numbering | Open | Real two-session qualification; require no duplicate or unhandled IntegrityError. |
| Membership revocation semantics | Open | Verify removal/absence behavior before schema changes. |
| Destructive downgrade | High | Disposable rehearsal and verified backup only. |
| SQLite false confidence | Open | PostgreSQL-only migration and RLS tests. |
| Legacy `exam_id` bypass | Open | Explicit denial test on every exam operation. |

## Disposable qualification evidence (2026-09-14)

An isolated local PostgreSQL 16/pgvector Compose project (`exam0021qual`) was created and removed after testing. The explicit sequence `0020 → 0021`, downgrade to `0020`, and re-upgrade to `0021` all completed successfully. Final `alembic current` was `20260912_0021 (head)`.

Schema inspection passed: `exams.tenant_id` is NOT NULL; `assignments.exam_id` is nullable; `exam_attempts` and `exam_results` exist; all three exam tables have enabled and forced RLS with `tenant_isolation` policies; tenant unique constraints are present. The isolated database, network, and volume were removed after the run. No production resource was touched.

Targeted repository regression: `7 passed, 0 failed` (exit 0; 3 non-blocking dependency warnings).

Application-level PostgreSQL negative and concurrency E2E remain open; this qualification did not claim those tests as passed.

## Decision

The disposable migration/schema qualification is **PASS**, but `20260912_0021` is **NOT READY for production migration** until the application-level PostgreSQL negative/concurrency suite and restricted-role RLS checks are separately qualified. No production implementation, migration, deployment, environment change, or database mutation was performed.

## Commander Decision Required

Approve a separate disposable PostgreSQL qualification gate for `0020 → 0021`, or request design changes. Production target remains `20260912_0020`.
