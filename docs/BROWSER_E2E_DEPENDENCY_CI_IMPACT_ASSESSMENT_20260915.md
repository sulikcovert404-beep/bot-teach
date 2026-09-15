# Browser E2E Dependency & CI Impact Assessment — 2026-09-15

## Existing tooling

- Node is available and `scripts/browser-runtime-qualification.mjs` is an existing dependency-free browser-like lifecycle harness.
- A Playwright CLI is available on the current workstation, but no `package.json`, lockfile, npm metadata, or repository-managed browser dependency exists.
- Python/CUA helpers exist for manual inspection, but they are not a reproducible CI browser runner.

## Required additions

To run true browser E2E in CI, the repository would need a pinned package manifest/lockfile, a supported Playwright runner and browser binaries, deterministic fixture setup, trace redaction, and a dedicated workflow job. These are implementation changes and are not applied here.

## CI impact

**Medium.** Browser binaries increase cache/artifact size and job duration. A separate job with explicit timeout, readiness wait, and `if: always()` teardown is required to avoid affecting the existing quality job.

## Security impact

**Medium.** Browser traces and screenshots can capture tokens, user data, or provider responses. Redaction and synthetic identities are mandatory; live credentials and Production URLs must be prohibited by job configuration.

## Recommendation

Keep the current Node harness for local lifecycle checks. Before adding Playwright to CI, obtain an implementation gate covering dependency pinning, runner image/browser version, fixture seeding, trace retention, and execution cost. Do not install packages or modify workflow/package files as part of this assessment.

## Current decision

**PLANNING COMPLETE / IMPLEMENTATION NOT AUTHORIZED.** Production, runtime, database, migration, Cloudflare, Telegram, and secrets remain unchanged.
