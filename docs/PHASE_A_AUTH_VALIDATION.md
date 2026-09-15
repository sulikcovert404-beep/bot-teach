# Phase A Auth Validation

Status: PARTIAL / NOT QUALIFIED

## Tests Executed

- `node --check web/platform/ui/auth-bootstrap.js` — PASS
- `node --check web/platform/ui/provider.js` — PASS
- `node --check web/student/app.js` — PASS
- `python -m pytest -q tests/test_auth_dependencies.py tests/test_auth_subscription_e2e.py tests/test_staging_auth_fixture.py` — **13 passed, 0 failed**, exit code 0 (one non-blocking dependency deprecation warning)

## Auth Flow Evidence

- First open without token: backend bootstrap path exists; no dedicated Phase A integration test proving exactly one request.
- No token outside Telegram: `web/platform/ui/auth-bootstrap.js` fails closed when `Telegram.WebApp.initData` is absent; `web/student/app.js` currently falls back to a client-only rendered state after load errors.
- Re-auth: present on 401, but `web/student/app.js` recursively calls `request()` after every successful re-auth with no explicit retry budget.
- Invalid token: a re-auth attempt exists; terminal behavior is not bounded/qualified.
- Retry limit: **FAIL** — no hard one-attempt limit in `web/student/app.js`; provider request path also retries after forced auth without a separate single-flight guard.
- Single-flight/mutex: **FAIL / NOT IMPLEMENTED** — concurrent callers can initiate duplicate bootstrap requests.
- Storage contract: **FAIL** — student app writes/reads `studentToken` in both `sessionStorage` and `localStorage`; platform bootstrap uses `accessToken` and multiple session keys.
- Telegram lifecycle: **NOT QUALIFIED** — delayed SDK readiness, stale `initData`, refresh, and close/reopen require Phase B tests.

## Security Checks

- Role source: backend returns role; frontend consumes it for display/routing, but server-side authorization remains authoritative.
- Tenant source: no client-provided tenant trust was accepted in the inspected bootstrap call; explicit response contract still needs qualification.
- Client trust issues: persistent localStorage token and unbounded retry are unresolved findings.

## Production Mutation

NONE.

## Decision

Phase A is **NOT PASS**. Existing syntax/unit coverage is green, but mandatory hardening acceptance criteria (bounded retry, single-flight, canonical session key, and explicit lifecycle tests) are not met. Phase B must not open until Commander decides whether to authorize a bounded local hardening patch or request additional review.
