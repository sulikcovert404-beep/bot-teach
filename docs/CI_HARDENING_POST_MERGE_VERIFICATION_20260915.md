# CI Hardening Post-Merge Verification Plan

Date: 2026-09-15  
Status: Plan prepared; merge destination and execution are external to this worktree

## Verification checklist

```text
[ ] Record merged commit reference
[ ] Confirm workflow run is triggered from the merged commit
[ ] Confirm quality job passes
[ ] Confirm explicit migration revision qualification passes
[ ] Confirm downgrade/re-upgrade current-revision assertions pass
[ ] Confirm staging smoke uses 20260912_0021 and reaches ready state
[ ] Confirm Docker build job passes without push/deploy
[ ] Confirm dependency audit passes
[ ] Confirm secret scan passes
[ ] Confirm no production/runtime/config/DB mutation
```

## Evidence to capture

- Workflow run URL and commit SHA (metadata only).
- Job conclusions and relevant logs with secrets redacted.
- Migration qualification output showing explicit expected revision and `alembic current` assertions.
- Staging smoke readiness and migration-head assertion.
- Production impact statement: `NONE`.

## Failure handling

If a post-merge CI job fails, revert the CI-only commit in the development branch, preserve failure logs, and rerun the prior workflow. Do not alter migration files, production databases, runtime configuration, Docker production state, Cloudflare, Telegram, or webhook settings.

## Boundaries

This verification is limited to CI and disposable test infrastructure. It does not authorize production deployment, live migration, runtime restoration, or recovery actions.

## Current status

```text
CI Hardening: IMPLEMENTED / AWAITING MERGE VERIFICATION
Recovery: SAFE HOLD
Production: UNCHANGED
```
