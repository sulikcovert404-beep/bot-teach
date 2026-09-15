# Browser E2E Final Decision Record — 2026-09-15

## Selected decisions

| Decision | Selected value | Owner | Rationale |
|---|---|---|---|
| Node | Node 22 LTS | Application / CI | Stable LTS baseline; workstation Node 24 is not used as the CI contract |
| Package manager | npm | Application | Native Node tooling and straightforward lockfile support |
| Lockfile | `package-lock.json` with frozen install | Application | Deterministic dependency resolution |
| Runner image | Official pinned Playwright image | DevOps / Platform | Browser and system dependencies are reproducible |
| Browser | Chromium baseline, pinned by runner image | QA / Platform | Lowest initial cost with deterministic coverage |
| Trace retention | Failure-only, redacted, 7 days | Security / Platform | Enough debugging time with bounded exposure |
| CI trigger | Pull request and push to protected base branch | CI | Validate proposed and landed changes without scheduled noise |
| Fixture ownership | QA + Backend jointly | QA / Backend | Stable synthetic data and reliable teardown |

## Ownership confirmation

- Application: dependency and version updates.
- QA: scenarios, assertions, and fixtures.
- DevOps/Platform: CI runner, cache, timeout, and cleanup.
- Security/Platform: redaction, retention, and artifact access.
- Commander: implementation and release gates.

## Implementation gate

These decisions close the planning questions. A separate Commander Implementation Gate is still required before creating `package.json`/lockfile, editing CI, installing browsers, or running disposable E2E. No live environment or production action is implied.

## Status

**DECISIONS CLOSED / IMPLEMENTATION PENDING GATE.** No package, lockfile, workflow, browser installation, E2E run, Production, runtime, secret, database, migration, Cloudflare, or Telegram change was made.
