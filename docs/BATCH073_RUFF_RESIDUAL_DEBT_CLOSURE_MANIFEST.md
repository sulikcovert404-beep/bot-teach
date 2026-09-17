# BATCH073 — Ruff Residual Debt Closure Manifest

Mode: read-only final inventory; no code changes, auto-fix, refactor, server, deployment, migration, environment, or database actions.

## Current inventory (fresh after commit 6d3c69e)
- Total findings: 1550
- I001: 523
- F401: 167
- C408: 80
- UP017: 29
- UP045: 10

Other rules remain tracked in the fresh Ruff artifact (`.gate073-ruff-full.json`).

## Wave history
- Import sorting waves (Gates 060–065): I001 reduced from 741 to 591 through scoped waves; residual now 523 after later import edits.
- Residual I001 audit (Gate 066): no safe candidates; remaining classified and frozen.
- F401 waves (Gates 068–069): F401 reduced 474 to 167; sensitive/framework/typing/uncertain imports excluded.
- C408 audit (Gate 071): 80 findings inspected; no safe automatic fixes.
- UP017/UP045 audit (Gate 072): 39 findings classified as datetime/runtime or type/API sensitive.

## Deferred boundaries
Security/auth, migrations/DB, deployment/bootstrap, runtime-sensitive initialization, framework/plugin imports, TYPE_CHECKING and uncertain findings remain deferred. C408, UP017 and UP045 require manual semantic review.

## Recommended future order
1. Per-file review of residual F401 only where ownership and side effects are proven.
2. Manual C408 review with constructor/kwargs semantics preserved.
3. Explicit datetime and typing contract review for UP017/UP045.
4. Security/runtime/migration findings only under dedicated Commander Gates.

No further broad auto-cleanup is recommended. Production and operational environments remain unchanged.

Commit Gate 073: HOLD pending Commander approval.
