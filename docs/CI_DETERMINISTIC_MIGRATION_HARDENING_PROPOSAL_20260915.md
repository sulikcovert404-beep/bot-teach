# CI Deterministic Migration Hardening Proposal

Date: 2026-09-15  
Status: Proposal only — no workflow or migration changes applied

## Current problem

The CI workflow currently uses implicit Alembic targets:

```text
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

The staging smoke job also asserts a hard-coded migration identifier (`e2f3a4b5c6d7`) that is stale relative to current release evidence (`20260912_0021`). These patterns can silently advance lineage or produce false readiness failures.

## Proposed fix

1. Define one explicitly versioned expected migration revision for each qualified release/CI run.
2. Pass that revision to upgrade and rollback/re-upgrade commands; never use an implicit `head` target for release qualification.
3. Assert `alembic current` equals the expected revision after each upgrade and re-upgrade.
4. Source the staging smoke expectation from the same release manifest or checked CI variable used by migration qualification.
5. Add a documented marker taxonomy for fast contract tests versus environment-dependent checks.
6. Add bounded job/step timeouts where supported and keep failure logs plus unconditional teardown.
7. Track existing Starlette/httpx and Alembic deprecation warnings as a separate maintenance item.

## Migration safety rules

CI must never:

- silently advance the migration lineage;
- validate against a stale revision;
- mutate a production database;
- treat a failed disposable rollback as success.

The proposal does not alter migration files, database state, CI secrets, deployment settings, or production configuration.

## Required approval and qualification

Before implementation:

- review the expected-head single source of truth;
- add or update a focused disposable CI test proving explicit upgrade, downgrade, re-upgrade, and current-revision assertions;
- run the workflow change in an isolated branch and disposable database;
- obtain Commander approval before merging `.github/workflows/ci.yml` changes.

## Current status

```text
Development Track: ACTIVE
Proposal: READY FOR REVIEW
Workflow changes: NONE
Migration execution: NONE
Production: UNCHANGED
Recovery: SAFE HOLD
```
