# Browser E2E Ownership Proposal — 2026-09-15

## Ownership model

| Area | Proposed owner | Responsibility |
|---|---|---|
| Dependency and versioning | Application team | Maintain package manifest, lockfile, and Playwright upgrades with security review |
| Test scenarios | QA/Test ownership | Map critical journeys to stable test IDs and maintain assertions |
| CI job | DevOps/Platform | Runner image, cache, timeout, teardown, and workflow health |
| Disposable fixtures | QA + Backend | Synthetic seed data, tenant boundaries, reset and cleanup |
| Trace and artifact policy | Security/Platform | Redaction, retention, access review, and incident response |
| Gate approval | Commander/Release owner | Authorize dependency, workflow, and execution changes |

## Suggested defaults

- Pin a supported Node LTS and Playwright version in a repository-owned lockfile.
- Start with Chromium in a dedicated CI job; expand the browser matrix only after runtime and flake data justify it.
- Retain redacted traces/screenshots only for failed runs and delete them on a short, documented schedule.
- Keep fixture data synthetic and disposable, with QA/Backend jointly accountable for teardown.

These are recommendations, not decisions.

## Approval boundary

Implementation starts only after ownership is accepted, dependency/runner decisions are closed, and Commander issues an explicit Browser E2E Implementation Gate. Until then, do not create package files or lockfiles, modify workflows, install browsers, or execute E2E.

## Status

**OWNERSHIP PROPOSAL READY / PENDING DECISION.** Production, runtime, secrets, database, migrations, Cloudflare, Telegram, and deployment remain unchanged.
