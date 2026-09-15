# Auth Review Consolidation

Status: PARTIAL — review evidence consolidated; implementation remains HOLD.

## Agent Consensus

- **Claude Sonnet 5:** `CLAUDE UNAVAILABLE — FALLBACK USED` (grounded rerun unavailable after quota/context constraints). Grounded partial review identified an unauthenticated owner identity diagnostic, JWT scope ambiguity, default-role risk for new users, inconsistent browser storage keys, unbounded 401 recursion, and silent auth failures.
- **Gemini:** BLOCKED. The requested conversation redirected to the country-availability page and exposed no composer or review response.
- **Qwen:** `APPROVE_WITH_CHANGES`. Backend HMAC and webhook-secret checks are strengths. Required changes include bounded 401 recovery, a shared bootstrap mutex, one canonical session storage key, stale `initData` handling, role propagation, and integration coverage for concurrency, storage isolation, and retry behavior.

## Consensus Findings

1. The current direction is viable for qualification, but it is not ready for production patching.
2. The frontend 401 path can recurse without a hard retry bound and needs a single-flight authentication guard.
3. Token persistence is inconsistent (`localStorage`/`sessionStorage` and differing keys); use one explicit session policy and clear it on invalidation.
4. Telegram WebView lifecycle needs explicit handling for first open, refresh, close/reopen, delayed SDK readiness, and stale `initData`.
5. Backend role and tenant scope must be returned and enforced server-side; frontend role display must never grant privilege.
6. Auth failures must be observable and fail closed instead of being hidden by catch-all handling.

## Conflicts Between Agents

- Claude's grounded verdict was unavailable, so no independent final verdict exists from that agent.
- Gemini supplied no lifecycle findings because the provider page was unavailable.
- Qwen focused on implementation and lifecycle safeguards; Claude's partial security findings additionally flag the owner diagnostic and JWT tenant-scope contract for explicit review. These are additive findings, not a resolved disagreement.

## Architecture Decision

**MODIFY (bounded hardening), not redesign.** Preserve the provider-neutral Telegram auth boundary and backend-issued token contract, then qualify focused changes for retry bounds, single-flight bootstrap, storage consistency, scope/role propagation, and lifecycle handling. No production implementation is authorized by this report.

## Required Changes

- Replace recursive 401 retry with one bounded re-auth attempt and a terminal signed-out state.
- Add a shared bootstrap promise/mutex so concurrent requests cannot mint duplicate sessions.
- Define one session storage key and policy; avoid long-lived `localStorage` tokens unless separately approved.
- Validate freshness and availability of Telegram `initData` on each bootstrap; handle refresh and WebView reopen explicitly.
- Make `/api/v1/auth/telegram` contract explicit for identity, role, tenant scope, expiry, and error classes.
- Ensure the owner identity diagnostic is non-mutating and authorization-protected, or remove it from externally reachable routes.
- Add tests proving no privilege escalation, no tenant leakage, bounded retries, storage isolation, and truthful error reporting.

## Qualification Plan

- **Phase A — Local validation:** static/type checks; unit tests for token parsing, HMAC validation, role/scope mapping, storage policy, bounded retry, mutex behavior, and error states. Test outside-Telegram requests fail closed.
- **Phase B — Staging/safe runtime validation:** deploy only to an isolated staging target after Commander approval. Exercise first open without token, delayed SDK readiness, re-auth, protected API 200, refresh, close/reopen, invalid token, concurrent bootstrap, and role/tenant negative cases. Capture sanitized logs and verify no loop or duplicate session.
- **Phase C — Production deployment criteria:** all Phase A/B tests pass; security review accepts owner diagnostic and scope contract; no unbounded retry or storage inconsistency remains; canary/rollback procedure is rehearsed; Commander explicitly approves production mutation. Until then, production deployment and bundle replacement remain HOLD.
- **Phase D — Rollback criteria:** immediately revert bundle/API patch if auth errors, repeated bootstrap requests, 401 loops, cross-role access, tenant leakage, missing `/platform/` routing, or elevated 5xx appear. Restore the last known-good artifact and verify health/readiness before further action.

## Acceptance Criteria

- First open without token obtains exactly one valid session or reaches a clear signed-out state.
- Telegram re-auth succeeds once and does not recurse.
- Protected API returns 200 with valid session and 401 is terminal after the bounded retry.
- `/platform/` loads only for the authorized role; role changes in the client cannot grant access.
- Refresh and close/reopen preserve or re-establish a valid session according to the explicit policy.
- Invalid or stale token is cleared and re-auth is requested.
- Outside Telegram, no fabricated identity or privileged fallback is used.
- Concurrent protected requests share one bootstrap operation.
- No privilege escalation, cross-tenant leakage, or infinite auth loop occurs.

## Production Mutation

NONE.

## Commander Decision Required

YES — approve or revise this bounded qualification plan before any auth patch, frontend bundle replacement, staging mutation, or production deployment.
