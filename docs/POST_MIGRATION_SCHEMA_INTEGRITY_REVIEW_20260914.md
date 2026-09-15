# POST MIGRATION SCHEMA INTEGRITY REVIEW

Date: 2026-09-14
Mode: Read-only repository/schema artifact review
Production mutation: NONE

## Status

`PARTIAL — local artifacts and ORM contracts pass; live database introspection is unavailable from this workspace.`

## Migration state

- `alembic heads` reports one head: `20260912_0021`.
- `alembic current` could not connect because the local SQLAlchemy URL is not configured/parseable. This is an environment limitation, not evidence of a live mismatch.
- Migration `20260912_0021_exam_persistence.py` explicitly descends from `20260912_0020`.

## New schema objects declared by migration 0021

The migration declares:

- `exams.tenant_id` added, deterministically backfilled from teacher profiles, then made `NOT NULL`.
- Nullable `assignments.exam_id` with an index and foreign key to `exams`.
- `exam_attempts` with tenant, assignment, student, attempt number, lifecycle status check, and identity uniqueness.
- `exam_results` with tenant, unique attempt reference, score fields, grading metadata, and indexes.
- Composite tenant-aware uniqueness and foreign keys for exam, assignment, attempt, and result chains.
- RLS enabled and forced on `exams`, `exam_attempts`, and `exam_results` with fail-closed `app.tenant_id` policies.

These are artifact declarations; actual catalog state still requires read-only inspection against the target database.

## ORM alignment

- `Exam`, `Assignment`, `ExamAttempt`, and `ExamResult` expose the expected tenant and lifecycle fields.
- ORM classes include the single-column foreign keys and core uniqueness/check constraints.
- The migration's composite tenant-aware constraints are database-level protections and are not fully represented as composite `ForeignKeyConstraint` declarations in the ORM models. This is a review finding to validate explicitly with SQLAlchemy metadata and live catalog introspection; no code change is authorized by this review.
- The migration creates `fk_assignments_exam_id` before the composite `fk_assignments_exam_tenant`; both must be confirmed in the live catalog and tested for intended delete/update behavior.

## RLS and tenant security

- Migration policy uses transaction-local `current_setting('app.tenant_id', true)` and forces RLS.
- The repository's disposable qualification documents restricted runtime role and tenant-context behavior.
- Live role attributes, policy definitions, and table flags are not verifiable from this local environment; do not infer PASS from disposable evidence.

## Integrity checks required against live DB

- Catalog columns, nullability, constraints, indexes, foreign keys and RLS flags for all affected tables.
- Orphan counts across assignment → exam, attempt → assignment, result → attempt chains.
- Duplicate indicators for `(assignment_id, student_id, attempt_no)` and one-result-per-attempt.
- Null `exams.tenant_id` count and tenant mismatch counts across every chain.
- Exact Alembic `current` and `heads`.
- Runtime role `NOSUPERUSER`/`NOBYPASSRLS` and policy behavior under transaction-local context.

## Validation evidence

- `pytest -q tests/test_assignment_persistence_models.py tests/test_persistence_readiness.py tests/test_persistence_foundation_validation.py` → **8 passed**.
- These tests validate repository contracts only; they do not prove live schema or production readiness.
- `alembic current` was not a valid live check locally because the database URL is unavailable/invalid.

## Gate result

```text
Migration artifact lineage: PASS
Single local Alembic head: PASS
ORM contract tests: PASS (8)
Live catalog verification: BLOCKED
Live RLS/role verification: BLOCKED
Orphan/duplicate live checks: BLOCKED
Production mutation: NONE
Commander decision required: YES
```

No migration, DB write, Docker operation, restart, environment change, credential change, Cloudflare change, or webhook change was performed.
