# Developer Onboarding Consistency Review — 2026-09-15

## Reviewed documents

- `README.md`
- `.env.example`
- `pyproject.toml`
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `scripts/staging-smoke.ps1`
- `docs/STAGING_CHECKLIST.md`

## Current setup flow

The README provides a coherent local Python flow: create/activate `.venv`, install `.[dev]`, run `uvicorn`, then use Ruff, mypy, and pytest. It correctly directs secrets to a local ignored `.env` and identifies health, readiness, Mini App, and platform endpoints.

The Compose flow is more demanding than the README currently states. `docker-compose.yml` requires `POSTGRES_PASSWORD`, `APP_RUNTIME_PASSWORD`, and `EXPECTED_MIGRATION_HEAD`; the example environment file does not define `APP_RUNTIME_PASSWORD` or `EXPECTED_MIGRATION_HEAD`. A developer following only the README and `.env.example` will therefore fail at Compose interpolation.

## Outdated or inconsistent references

1. `scripts/staging-smoke.ps1` defaults to migration head `20260909_0015` when `EXPECTED_MIGRATION_HEAD` is not supplied. Current CI and migration qualification target `20260912_0021`. The script should be invoked with the explicit environment variable (or aligned in a separately approved change); this review makes no code change.
2. README setup does not document the required Compose-only variables or the explicit migration target. This is an onboarding documentation gap.
3. `docs/STAGING_CHECKLIST.md` is a checklist rather than a runnable setup guide; it does not replace the missing Compose prerequisites.
4. Historical documents contain older migration revisions by design. They should not be treated as current setup instructions unless explicitly marked historical.

## Test execution guidance

- Local quality: `\.venv\Scripts\python.exe -m ruff check app tests migrations scripts`, `\.venv\Scripts\python.exe -m mypy app`, and `\.venv\Scripts\python.exe -m pytest -q`.
- CI migration qualification uses explicit revision `20260912_0021` and asserts `alembic current` after upgrade and re-upgrade.
- Compose smoke requires all interpolation variables and should use an isolated/disposable environment. Never use `alembic upgrade head` for qualification.

## Recommended updates

- Add a README subsection documenting Compose prerequisites with placeholders only, including `APP_RUNTIME_PASSWORD` and `EXPECTED_MIGRATION_HEAD=20260912_0021` for the current development qualification.
- Make the staging smoke script's fallback explicit or fail closed when the expected head is absent, so a stale default cannot produce misleading readiness results.
- Link the README directly to the staging checklist and the CI hardening report for the distinction between local, CI, disposable, and live environments.
- Add a short deprecation note to historical operational docs when they mention superseded revisions.

## Production impact

NONE. This review is documentation/read-only analysis; no workflow, application, runtime configuration, secret, database, migration, deployment, or production state was changed.
