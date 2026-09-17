# BATCH076 — Warning Provenance & Datetime Semantic Audit

Mode: read-only. No code/test changes, suppression, dependency upgrade, Ruff fix, or operational action.

## Warning traceability

| Source | Warning | Origin | Trigger | Ownership | Classification |
|---|---|---|---|---|---|
| `site-packages/fastapi/testclient.py:1` | Starlette TestClient/httpx deprecation | dependency | TestClient imports in test suite | dependency-owned | UPSTREAM-DEPRECATION / TEST-TOOLING |
| `site-packages/alembic/config.py:604` (3 occurrences) | missing `path_separator` fallback | Alembic configuration | migration-related tests | dependency/tooling | NO-LOCAL-ACTION / UPGRADE-CANDIDATE |
| `app/api/routes/teacher.py:498` | `datetime.utcnow()` deprecated | application code | `test_pilot_http_assignment_publish_and_student_access` | application-owned | DATETIME-SEMANTIC |
| `app/api/routes/teacher.py:508` | `datetime.utcnow()` deprecated | application code | `test_pilot_http_assignment_publish_and_student_access` | application-owned | DATETIME-SEMANTIC |

Total warnings: 6 (2 application, 4 dependency/tooling).

## Datetime semantic assessment

The two application calls populate `publish_at` and `close_at` in the assignment lifecycle and are compared/serialized by API and persistence code. Replacing them with `datetime.now(datetime.UTC)` produces timezone-aware values, which may change comparisons or database serialization if current columns and consumers expect naive UTC. Therefore no replacement was applied. A dedicated future gate must inspect column timezone configuration, API payload format, and all comparisons before choosing an aware-UTC migration or an explicit naive-UTC compatibility helper.

Required focused tests for any future change: publish/close persistence round-trip, API JSON timestamp shape, before/after time comparisons, timezone-aware and naive inputs, and existing assignment access/closure behavior.

## Dependency warnings

The Starlette/httpx warning is upstream test-tooling compatibility; the Alembic warning is configuration/tooling. Package upgrade or config edit was not authorized and was not performed.

No warning suppression was added. Unrelated worktree remains untouched.

Commit Gate 076: HOLD pending Commander approval.
