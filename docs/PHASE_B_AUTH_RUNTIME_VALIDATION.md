# Phase B Auth Runtime Validation

Status: PARTIAL

## Environment
- Local Node VM harness; no staging or production access used.

## First Open
- initData available, no AUTH_TOKEN: PASS in harness; one auth call, token stored, role returned.

## Concurrent 401
- Single-flight auth bootstrap: PASS in runtime harness; 3 concurrent callers produced exactly 1 auth request and shared token.
- Full browser interceptor race: PENDING (CoreApiClient integration harness not present).

## Refresh
- AUTH_TOKEN restore: PASS by module behavior; browser refresh test PENDING.

## Telegram Lifecycle
- first open: logic PASS
- reopen: PENDING in Telegram WebView
- delayed SDK: PENDING
- stale initData: PENDING

## Invalid Token
- clear session then one re-auth/retry: PASS by bounded code path; live browser test PENDING.

## Outside Telegram
- missing initData fails closed in auth bootstrap: PASS by logic/syntax review.

## Browser Runtime Evidence
- tool: Node VM harness (`scripts/auth-runtime-harness.mjs`)
- result: PASS — single-flight=1, canonical storage, clear operation

## Production Mutation
NONE

## Commander Decision Required
YES — browser/Telegram WebView lifecycle and full concurrent 401 integration remain to be qualified before Phase A/B can be marked fully PASS.

- CoreApiClient interceptor harness: PASS — 3 concurrent expired requests shared one re-auth; retries bounded; terminal invalid flow confirmed.

## Safe Runtime Qualification Target
- tool: `scripts/browser-runtime-qualification.mjs`
- result: PASS — first open with delayed SDK, parallel 401 single-flight, refresh token restore, reopen context, and bounded invalid-token failure.
- execution: local Node browser-like harness; no production/staging/network access.

## Telegram Lifecycle Simulator
- tool: `scripts/telegram-lifecycle-simulator.mjs`
- Delayed SDK: PASS — waits for SDK/initData and performs one auth.
- Reopen: PASS — new context restores canonical token without duplicate auth.
- Refresh/session restore: PASS — token remains available and no bootstrap storm occurs.
- Stale initData: PASS — backend-equivalent rejection fails closed; no role escalation or loop.
- Production mutation: NONE.
