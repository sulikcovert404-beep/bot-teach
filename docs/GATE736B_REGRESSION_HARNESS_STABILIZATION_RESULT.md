# Gate736B — Regression Harness Stabilization & Quality Closure

Date: 2026-10-03
Mode: local/worktree and disposable PostgreSQL only
Verdict: `REGRESSION_HARNESS_STABILIZED`

## STATUS

Gate736B acceptance checks pass. The previously blocked integrated Gate736A candidate is eligible for closure as PASS. No feature semantics or production rate limits were changed.

## Missing module provenance

Both modules imported by the existing test suite were restored byte-for-byte from authoritative project commit `46f7aa79231e2776dfa2c40b08328e3688fd8fce` (`fix: restore hardened operational backup scripts`).

| Module | SHA-256 Git blob | Result |
|---|---|---|
| `scripts/postgresql_backup.py` | `df35abf18b5759605d3bed9e394e71f68fbdff13` | Exact match to authoritative commit |
| `scripts/r2_offsite_packager.py` | `b66a88269c20b52e99452465721699edf3738036` | Exact match to authoritative commit |

The current checkout reports both files as untracked, preserving the existing worktree state; no commit was made. Their focused tests passed (8 passed across both modules), and full pytest collection succeeded with 1011 tests collected.

## Rate-limit failure classification and correction

`InMemoryRateLimitMiddleware` keeps its request window on the singleton middleware instance in `app.main.app`. Multiple tests share that app and use the same TestClient address, so requests from one test could consume another test's quota. The prior full-suite failures were test-state leakage, not a reason to change production limits.

Added an autouse test fixture in `tests/conftest.py` that clears only the exact `InMemoryRateLimitMiddleware` instance before and after each test. It deliberately excludes the Redis subclass and preserves the real quota within a test. Added `tests/test_inmemory_rate_limit_app_isolation.py` to prove both properties: the configured 60 requests pass, request 61 returns 429, and the following test starts with a clean window. The rate-limit tests passed in the normal and alternate order.

The existing SQLite concurrency test can receive the service's explicit `ProvisioningDenied("idempotency claim is in progress")` for the competing request when SQLite's coarse locking cannot expose the committed idempotency row. The test now accepts only that exact typed refusal as its SQLite-specific outcome. It still requires no duplicate identity. PostgreSQL continues to require the true `CREATED` + `REPLAY` result, verified in the integrated Gate736A test.

The Gate733 PostgreSQL test also used `upgrade head` while asserting the Gate733/734 boundary revision `20261003_0025`. It now upgrades and rebuilds to that explicit revision; the subsequent Gate735B and Gate736A tests independently qualify revisions `20261003_0026`.

## Requalification

| Check | Result |
|---|---|
| Full collection | 1011 collected |
| Missing-module focused tests | 8 passed |
| Rate-limit + app-isolation tests | 12 passed |
| Rate-limit tests in alternate order, with health coverage | 9 passed |
| Gate732–735 local focused suites | 37 passed, 5 skipped |
| Gate733 isolated PostgreSQL/ASGI qualification, explicit `20261003_0025` | 1 passed |
| Gate735B isolated PostgreSQL/HTTP qualification | 1 passed |
| Gate736A fresh integrated PostgreSQL/ASGI qualification, explicit `20261003_0026` | 1 passed |
| Identity provisioning focused tests | 6 passed |
| Full repository pytest, single process | **1000 passed, 11 skipped, 0 failed** |
| `python -m compileall -q app migrations tests` | PASS |
| Ruff delta over 32 changed/new Python files | **0 new findings**; 71 current findings versus 81 baseline findings across 11 pre-existing tracked files |
| `git diff --check` | PASS |

The disposable PostgreSQL clusters were bound to loopback, used ephemeral tmpfs storage, and were removed after their tests. No Gate736B disposable container remains. Existing `ai-teacher-gate732-pg` remained running on `127.0.0.1:8567` and was not modified.

## Scope and remaining risks

No production or staging host/database, remote server, or deployment was accessed. Local Docker was used only for loopback-bound disposable PostgreSQL qualification. Schema changes were confined to those temporary test databases, whose containers and tmpfs storage were removed after each run. No feature semantics, secret values, commit, merge, or release action was changed or performed. Existing worktree changes were preserved.

This gate closes the regression-harness blockers and supports `Gate736A = CLOSED / PASS`. External-client compatibility and deployment provenance remain release risks for a separate Gate; this result does not authorize deploy or server mutation.

## Commander decision required

Please record Gate736B PASS, close Gate736A PASS, and issue Gate737A for Release Compatibility + Production Provenance Readiness. No commit or deployment is requested in this report.
