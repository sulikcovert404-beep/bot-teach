# Browser E2E Final Architecture Decision Record — 2026-09-15

## Decision summary

Adopt a separate, disposable Browser E2E track using a repository-pinned Node/Playwright toolchain, synthetic fixtures, and an isolated CI job. Keep the existing dependency-free Node lifecycle harness for fast local checks.

## Accepted defaults

- Tooling: Playwright-compatible runner when implementation is authorized; existing Node harness remains a lightweight fallback.
- Browser strategy: Chromium first, pinned to the runner image; expand only with evidence.
- Environment: disposable Compose application with dedicated database and Redis.
- Fixtures: synthetic four-role, two-tenant data with deterministic teardown.
- CI: separate job with explicit timeout, readiness wait, versioned cache, and unconditional cleanup.
- Artifacts: failure-only traces/screenshots, redacted and short-retention.
- Ownership proposal: Application (dependency/version), QA (scenarios/fixtures), DevOps/Platform (CI), Security/Platform (trace policy), Commander (gate approval).

## Open decisions requiring explicit approval

- Accept the proposed ownership assignments.
- Select Node LTS, package manager, and lockfile format.
- Confirm the pinned runner image and Chromium version.
- Set trace retention duration and access owner.
- Confirm CI trigger policy (pull request only or push plus pull request).

## Implementation boundary

No package manifest, lockfile, browser installation, workflow modification, E2E execution, Production access, runtime configuration change, secret handling, database mutation, migration, Cloudflare change, or Telegram live test is authorized by this ADR. A separate Commander Implementation Gate must close the open decisions first.

## Status

**ARCHITECTURE RECORD READY / PENDING DECISION.** Release remains Not Ready and Recovery remains Safe Hold.
