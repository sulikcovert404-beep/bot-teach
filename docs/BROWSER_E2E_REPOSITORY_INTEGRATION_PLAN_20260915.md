# Browser E2E Repository Integration Plan — 2026-09-15

## 1. Dependency strategy

- Add a repository-owned `package.json` only in a separate approved implementation gate.
- Pin Node and Playwright versions plus a lockfile; use the CI-supported Node LTS and a pinned Playwright container/image.
- Keep browser dependencies isolated from the Python runtime and existing quality job.
- Cache only the exact browser binary/version key; invalidate on lockfile or runner-image changes.

## 2. CI integration strategy

- Add a separate `browser-e2e` job after quality and disposable staging readiness.
- Install from the lockfile, start an isolated Compose project, seed synthetic fixtures, and run the focused scenario matrix.
- Set an explicit job timeout, bounded readiness retries, and unconditional teardown (`if: always()`).
- Upload traces/screenshots only on failure, after redacting tokens, cookies, headers, personal data, and provider output.
- Keep live URLs, Telegram production, and production secrets impossible through job environment configuration.

## 3. Security controls

- Synthetic identities only, across at least two tenants and all supported roles.
- No real `TELEGRAM_BOT_TOKEN`, provider key, JWT secret, or production environment file.
- Trace retention must be time-limited and reviewed; failed artifact upload must not print raw environment values.
- Server-side authorization remains the source of truth; UI visibility alone is never a PASS.

## 4. Implementation gate requirements

Before implementation, Commander must approve:

- dependency owner and version strategy;
- Node/Playwright runner image and browser matrix;
- lockfile and cache policy;
- fixture seed/teardown mechanism;
- CI job timeout and artifact redaction/retention;
- exact scenario-to-test mapping and expected failure behavior.

## Current status

**INTEGRATION PLANNING COMPLETE / IMPLEMENTATION NOT AUTHORIZED.** No `package.json`, lockfile, workflow, browser dependency, E2E run, secret, runtime, database, migration, Cloudflare, Telegram, or Production change was made.
