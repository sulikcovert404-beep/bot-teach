# Production Auth Qualification Preparation

Status: BLOCKED — preparation only; no production mutation

## Release
- Current branch: `agent-handoff/miniapp-auth-review-20260914`
- Current HEAD: `b5b34e7` (sanitized handoff publication)
- Auth hardening is uncommitted in the working tree (`web/platform/ui/provider.js`, `web/student/app.js`, plus `web/platform/ui/auth-bootstrap.js`).
- The working tree also contains unrelated application, migration, dashboard, and test changes. A clean auth-only commit/artifact does not yet exist.
- Build artifact/hash: NOT GENERATED (would require an approved clean release boundary).

## Rollback
- Current production artifact: not changed or verified in this local-only gate.
- Rollback target: existing production release must be resolved by Commander from the deployment ledger before any deploy.
- DB impact: NONE; the auth hardening changes are frontend-only and no migration was run.

## Smoke Test Plan
- first open: Telegram initData -> `/api/v1/auth/telegram` -> token -> dashboard
- refresh: restore `AUTH_TOKEN` from sessionStorage without duplicate auth
- 401 recovery: clear token -> one re-auth -> one retry -> controlled failure
- dashboard: backend role/tenant response controls route; no client privilege authority

## Security Checklist
- secrets: BLOCKED for release packaging until untracked sensitive files are excluded and a secret scan is clean. No values printed.
- logging: no token or initData logging added.
- role trust: backend source of truth.
- tenant trust: backend source of truth.
- retry: bounded to one re-auth/retry.
- localStorage sensitive persistence: removed from changed auth paths.
- debug code: no debug code added to production modules.

## Production Mutation
NONE

## Commander Decision Required
YES — create/identify a clean auth-only release boundary and explicitly resolve untracked sensitive files before artifact generation. Production deploy remains NO-GO.

## Current Production (read-only ledger)
- Primary host: `95.135.208.167`
- Public hostname: `bot.codeshow.ir`
- Current DB revision: `20260912_0020`
- Canonical production commit: `00c8fb71c6f8475280e4bd8e599afcca03c2f43a`
- Canonical release artifact: recorded in `docs/PRODUCTION_OPERATIONAL_HANDOFF.md`; no replacement artifact generated.
- Rollback point: old host `107.173.47.76` and old tunnel remain rollback standby per handoff.

## Deployment Safety
- DB impact: NONE expected for frontend-only auth hardening.
- Migration required: NO.
- Rollback: artifact/bundle rollback can be performed without DB mutation, but exact deploy artifact must be resolved after a clean auth-only commit.
