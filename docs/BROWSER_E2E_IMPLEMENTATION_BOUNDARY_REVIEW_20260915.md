# Browser E2E Implementation Boundary Review

Date: 2026-09-15  
Status: Preparation only; implementation gate not opened

## Approved Scope

The first implementation gate may touch only the isolated development/CI path:

- `package.json` and `package-lock.json` for the approved Node 22/npm contract;
- Playwright configuration and minimal browser harness;
- disposable E2E fixture structure and synthetic test data;
- one isolated browser-E2E CI job using the approved pinned Playwright image;
- disposable environment boot/support required by that job.

No production runtime, credentials, live database, or Telegram account is a valid fixture source.

## Explicitly Out of Scope

- Production runtime or runtime configuration;
- production secrets or secret rotation;
- live database, migrations, schema, or RLS;
- Cloudflare, DNS, webhook, or Telegram changes;
- the existing recovery path and old production;
- application architecture, provider activation, or feature work;
- mentor-bot.

## Dependency Change Impact

Before implementation, the gate package must record:

| Check | Required evidence |
|---|---|
| Dependency diff | Only Node/Playwright test dependencies; no production dependency drift |
| Lockfile | Deterministic `npm ci` with reviewed lockfile |
| CI duration | Isolated job budget and timeout documented |
| Artifact policy | Failure-only, redacted traces; seven-day retention |
| Network scope | Disposable endpoints only; no production credentials |

## Implementation Sequence (Proposal Only)

1. Add the approved dependency contract.
2. Validate frozen install with Node 22 and npm.
3. Add the smallest Playwright harness and Chromium baseline.
4. Add synthetic fixtures owned jointly by QA and Backend.
5. Add one isolated CI job for pull requests and pushes to the protected base branch.
6. Run disposable qualification and inspect redaction/cleanup behavior.

## Final Gate Criteria

Implementation GO requires all of the following to be reviewed and true:

- boundary review accepted;
- dependency and lockfile diff reviewed;
- CI diff reviewed;
- no production coupling or secret exposure;
- disposable fixture ownership confirmed;
- failure artifacts are redacted and retention is enforced;
- rollback of the development-only change is straightforward.

## Current Restrictions

This review performs no package installation, lockfile creation, workflow change, browser installation, E2E execution, deployment, or Recovery action. A separate Commander Implementation Gate is required before any such mutation.

## Decision

`READY FOR IMPLEMENTATION GATE REVIEW` — not an implementation authorization.

Production and Recovery remain unchanged (`SAFE HOLD`).
