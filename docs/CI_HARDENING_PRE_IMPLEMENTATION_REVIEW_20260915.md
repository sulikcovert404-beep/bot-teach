# CI Hardening Pre-Implementation Review

Date: 2026-09-15  
Status: Checklist only — Implementation Gate pending

## Scope confirmation

### Files eligible for a future change

- `.github/workflows/ci.yml`
- A release-manifest or CI metadata file that contains the explicit expected revision, if approved by the Gate
- Focused disposable test/support files required to verify the workflow behavior

### Out of scope

- Migration revision files and database schemas
- Production or staging runtime configuration and secrets
- Docker/Compose production lifecycle
- Cloudflare, Telegram, webhook, or provider configuration
- Unrelated application features or refactors

## Risk review

- **Migration qualification:** explicit revision targets must be used and current revision asserted after upgrade, downgrade, and re-upgrade.
- **Smoke validation:** staging smoke must consume the same expected-head source as migration qualification; stale hard-coded values must be removed.
- **CI runtime:** bounded timeouts and deterministic failure diagnostics must not weaken cleanup or hide failures.
- **Security:** no secret values may enter manifests, logs, workflow arguments, or artifacts.

## CI-only rollback plan

If the workflow change fails review or CI qualification:

1. Revert the workflow commit in the development branch.
2. Do not touch migration files, databases, production, or runtime configuration.
3. Re-run the prior CI workflow to restore the previous development validation path.

## Merge gate

```text
[ ] workflow diff reviewed
[ ] single-source expected revision approved
[ ] disposable explicit-revision migration test passes
[ ] current revision assertions pass after each step
[ ] staging smoke expected-head check passes
[ ] focused pytest gate passes
[ ] Ruff/mypy/secret scan pass
[ ] bounded timeout behavior reviewed
[ ] Commander approval received
[ ] merge approval received
```

## Current prohibition

Until the Implementation Gate is explicitly opened, do not modify `.github/workflows`, migration files, CI secrets, deployment configuration, databases, or production state.

## Status

```text
Development: ACTIVE
CI Hardening: AWAITING IMPLEMENTATION GATE
Recovery: SAFE HOLD
Production: UNCHANGED
```
