# BATCH 160 — PostgreSQL Concurrency Harness Preparation

Date: 2026-09-17
Verdict: HARNESS_READY_RUNTIME_PENDING

## Scope
A PostgreSQL-only pytest entry point was added at `tests/test_exam_attempt_concurrency_postgres.py`. It is deliberately fail-safe:

- no PostgreSQL, Docker, service, migration, or production connection is created;
- absent `TEST_DATABASE_URL` produces an explicit skip;
- non-PostgreSQL URLs fail immediately;
- production/staging-looking URLs are rejected;
- SQLite is never accepted as concurrency evidence.

## Runtime qualification contract
When an explicitly disposable PostgreSQL fixture is provisioned later, extend/execute this entry point for:

- same assignment + same student with two concurrent `start_attempt` calls;
- same assignment + different students concurrently;
- uniqueness of `(assignment_id, student_id, attempt_no)`;
- no uncaught `IntegrityError` or HTTP 500;
- no partial transaction corruption;
- bounded attempt numbering and no unnecessary serialization.

The preparation stage intentionally does not claim those runtime outcomes.

## Validation
- preparation test: explicit SKIP when `TEST_DATABASE_URL` is absent;
- full existing suite: no runtime or database action from this Gate;
- Gate 160 commit: HOLD pending Commander authorization.

## Safety
No secrets, credentials, database URLs, migrations, Docker actions, server/SSH actions, or schema changes were introduced.

## Latest validation
- Ruff: PASS (	ests/test_exam_attempt_concurrency_postgres.py)
- Focused concurrency qualification: 1 passed, 1 explicit PostgreSQL-runtime skip, 0 failed.

