# Local Environment Recovery Procedure — 2026-09-15

## Diagnosis

Symptom: FastAPI health/environment tests fail during collection with a form-data error.

Cause: the local `.venv` has dependency drift and lacks `python-multipart`, although the package is declared in `pyproject.toml` and installed by CI's editable project install.

## Approved recovery

From the repository root, refresh the development environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

This is a suggested local command. It is not executed automatically and must never be run against a production or live-staging host.

## Validation sequence

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests/test_health.py tests/test_environment_readiness.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_migration_roundtrip_qualification.py -q
```

Record collection count, failures, and any remaining warnings. Keep migration qualification explicit; do not use `alembic upgrade head`.

## Boundaries

- No production or staging runtime changes.
- No secret handling or credential output.
- No database, migration, CI workflow, Cloudflare, Telegram, or Docker production action.
- If the refreshed environment still fails, preserve the install output and open a new development diagnosis rather than changing project dependencies blindly.
