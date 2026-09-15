# Local Qualification Environment Review — 2026-09-15

## Missing dependency

The local `.venv` cannot collect the FastAPI health tests because `python-multipart` is not installed. FastAPI raises its form-data dependency error while importing `app.main`.

## Declared in project

`pyproject.toml` declares `python-multipart>=0.0.18,<1.0` in the main runtime dependency set. The GitHub Actions quality job installs `.[dev]`, which includes the project runtime dependencies, so CI should receive this package through the normal editable install.

## CI parity

**PARTIAL locally / expected PASS in CI:** the declaration and CI install flow are correct, but the existing local virtual environment predates or lacks the declared dependency. No package was installed during this review.

## Recommended action

Recreate or refresh the local virtual environment using `pip install -e ".[dev]"`, then rerun health/environment tests. This is a development-environment action only and must not be performed against production or live staging. If the refreshed environment still fails, inspect the install log and lock/dependency resolution before changing project files.

## Validation evidence

- `tests/test_migration_roundtrip_qualification.py`: 2 passed, 0 failed.
- Health/environment collection: blocked solely by missing local `python-multipart`.
- CI workflow explicitly installs `.[dev]`.
- Production, runtime configuration, secrets, database, migrations, and deployment state: unchanged.
