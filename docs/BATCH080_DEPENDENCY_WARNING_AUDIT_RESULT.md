# BATCH080 — Remaining Dependency Warning Audit Result

Mode: read-only. No dependency, requirements, config, warning-filter, code, or operational changes.

## Traced warnings

| Warning source | Package/version | Ownership | Classification | Local action |
|---|---|---|---|---|
| `fastapi/testclient.py:1` importing Starlette TestClient | FastAPI 0.141.1 / Starlette 1.6.0 / httpx 0.28.1 | upstream dependency compatibility | UPSTREAM-WAIT / NO-LOCAL-ACTION | wait for compatible upstream/test tooling; no local suppression |
| `alembic/config.py:604` (3 occurrences) missing `path_separator` | Alembic 1.19.1 | dependency/config interaction | CONFIG-ONLY candidate | changing alembic config is outside this audit; assess in dedicated migration/tooling gate |

Total remaining warnings: 4 (1 Starlette/httpx, 3 Alembic). No evidence requires an immediate package upgrade. No local action was taken.

## Recommendation
Track upstream Starlette/httpx compatibility and evaluate Alembic `path_separator` only with migration test coverage. Do not suppress warnings or alter requirements/config opportunistically.

No code or operational mutation. Commit Gate 080: HOLD pending Commander approval.
