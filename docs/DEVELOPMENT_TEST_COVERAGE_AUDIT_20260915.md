# Development Test Coverage Audit

Date: 2026-09-15  
Track: Development (non-production)

## Current coverage

- Pytest collection: **955 tests collected**.
- Focused release-risk suite: **58 passed, 0 failed, exit code 0**.
- Focused suite covered exam/assignment, authentication, tenant isolation, migration round-trip, retrieval benchmark/dataset/evaluation, and vector-store contracts.
- No production services, secrets, environment files, Docker lifecycle, migrations, or databases were touched by this audit.

## Validated areas

| Area | Evidence | Result |
|---|---|---|
| Exam and assignment contracts | `test_exam*` / `test_assignment*` inventory | Collected; focused execution passed |
| Authentication and authorization | `test_auth*` inventory | Focused execution passed |
| Tenant isolation/context | `test_tenant*` inventory | Focused execution passed |
| Migration compatibility | `test_migration_roundtrip_qualification.py` | Passed (2 tests) |
| Retrieval dataset/evaluation/benchmark | `test_retrieval_*.py` | Focused execution passed |
| Vector store contracts | `test_vector_store.py` | Focused execution passed |
| Persian/RTL behavior | `test_persian_text.py` and related audit tests | Collected; covered by suite |

## Missing or weak coverage

This audit did not claim production or live-provider coverage. The following remain explicitly outside the safe local audit:

- Real production runtime/configuration and Telegram delivery.
- Real Gemini/provider availability and quota behavior.
- Live PostgreSQL/PGVector performance and storage fault behavior.
- Browser-level dashboard and Mini App E2E against a running deployment.

These are environment qualifications, not reasons to fabricate local PASS results.

## Flakiness and tooling observations

- No failures occurred in the focused execution.
- Pytest emitted three non-blocking deprecation warnings: Starlette `TestClient`/httpx compatibility and Alembic `path_separator` fallback.
- `pyproject.toml` is the active project configuration; no separate `pytest.ini`, `tox.ini`, or `noxfile.py` was found in the repository root.
- CI workflow exists at `.github/workflows/ci.yml`; this audit did not alter or execute remote CI.
- The repository contains many historical helper scripts and temporary handoff trees; they were excluded from the focused test command and were not staged.

## Recommended next tests

1. Keep the 58-test focused gate in local/CI smoke checks for release-risk changes.
2. Add explicit markers or a documented test-selection command so the focused gate is reproducible without filename glob assumptions.
3. Address the three deprecation warnings in a separate reviewed maintenance change.
4. Qualify live-provider, browser E2E, and PGVector performance only in their authorized environments and gates.

## Status

```text
Development Track: ACTIVE
Production Recovery: SAFE HOLD
Production Mutation: NONE
Audit verdict: PASS for local release-risk coverage; live-runtime coverage remains unqualified
```
