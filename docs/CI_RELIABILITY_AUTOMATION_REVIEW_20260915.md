# CI Reliability & Test Automation Review

Date: 2026-09-15  
Track: Development (non-production, read-only review)

## CI Test Flow Review

Workflow: `.github/workflows/ci.yml`

- `quality` installs the editable package with dev dependencies, then runs Ruff, mypy, the full pytest suite, tracked-file secret scanning, production settings validation, and migration checks.
- `docker` builds the image after `quality` succeeds; it does not push or deploy.
- `staging-smoke` creates an isolated Compose stack, waits for readiness, checks a migration head, verifies a PostgreSQL dump listing, and tears down with `if: always()`.
- `dependency-audit` runs `pip-audit` against the installed package.
- Python is pinned to 3.12 in CI and project metadata requires Python >=3.12.

## Reproducibility result

**PASS for workflow structure.** Dependency installation, quality gates, isolated Docker build, staging teardown, and dependency audit are explicit and ordered.

The local audit collected 955 tests and executed the focused release-risk suite with 58 passed and 0 failed. This supports the test command itself; remote runner behavior remains subject to GitHub Actions availability.

## Reliability findings

### High priority: migration command policy drift

The workflow uses `python -m alembic upgrade head` and later `downgrade -1`/`upgrade head`. The current operational policy requires an explicit known revision and forbids implicit `upgrade head` for production lineage. Even though this job is isolated CI, the command can silently advance when a new head is added and does not prove the intended release revision.

**Recommendation:** replace with an explicit CI target revision or a checked single-source expected-head value, and assert the resulting revision before rollback/re-upgrade.

### High priority: staging smoke expected-head drift

The staging smoke job asserts migration head `e2f3a4b5c6d7`. Current repository/release evidence uses later explicit revisions, including `20260912_0021`. This hard-coded assertion is likely to fail or become misleading as the release lineage advances.

**Recommendation:** derive the expected head from the qualified release manifest or an explicitly versioned CI variable; do not copy a production secret or runtime env file into CI.

### Medium priority: warning visibility

The local focused run produced three non-blocking deprecation warnings (Starlette/httpx TestClient and Alembic `path_separator`). CI currently displays them but does not track or budget them.

**Recommendation:** retain a warning report or CI annotation and address them in a separate maintenance change.

### Medium priority: test selection ergonomics

The full suite is reproducible via `python -m pytest -q`, but no explicit markers divide fast contract tests from environment-dependent tests. A documented marker taxonomy would make retries and failure diagnosis more deterministic.

## Failure resilience

- Staging teardown runs even after failures.
- Readiness polling has a bounded 45-attempt loop and emits service status/logs on failure.
- No explicit job-level timeout is configured; a hung external command could consume runner time until platform limits.
- No test parallelization is configured, avoiding shared-state races but increasing wall-clock time.
- No flaky-test quarantine or retry is configured, which preserves signal quality; future additions should classify flaky behavior rather than silently retrying it.

## Security and scope

- CI uses synthetic values only for production settings validation.
- Secret scanning is limited to tracked files in the workflow.
- No production credentials, runtime config, Cloudflare, Telegram, or live database access is used by these jobs.

## Verdict

```text
CI reliability structure: PASS
Local release-risk test gate: PASS (58/0)
Migration command determinism: NEEDS IMPROVEMENT
Staging expected-head determinism: NEEDS IMPROVEMENT
Failure cleanup: PASS
Production impact: NONE
```

No CI, production, migration, database, Docker, or environment change was made in this review.
