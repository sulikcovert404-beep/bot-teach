# CI Deterministic Migration Hardening Implementation Plan

Date: 2026-09-15  
Status: Preparation only — implementation gate not executed

## Implementation sequence

1. **Define the expected revision source.** Select a release manifest or explicitly versioned CI variable as the single source of truth. It must be reviewable without secrets.
2. **Replace implicit migration targets.** Update CI qualification commands to use the selected revision and assert `alembic current` after upgrade, downgrade, and re-upgrade.
3. **Align staging smoke.** Remove the stale hard-coded expectation and consume the same expected revision source used by migration qualification.
4. **Add test markers.** Classify fast contract tests and environment-dependent tests without changing their semantics.
5. **Bound execution.** Add job/step timeouts where supported; preserve failure diagnostics and unconditional disposable teardown.
6. **Run focused qualification.** Execute the disposable migration round-trip, focused pytest gate, and staging smoke in CI-only/disposable context.

## Required validation before merge

```text
[ ] CI workflow diff review
[ ] Disposable explicit-revision migration test
[ ] Upgrade/current assertion
[ ] Downgrade/re-upgrade/current assertion
[ ] Focused pytest gate
[ ] Staging smoke expected-head validation
[ ] CI-only rollback/revert plan
[ ] Secret-scan and lint pass
```

## Approval boundary

Implementation requires Commander approval, workflow review, and merge approval. Until then, do not modify `.github/workflows`, migration files, CI secrets, production configuration, databases, or deployment state.

## Risk controls

- Use an explicit known revision; never silently advance lineage.
- Keep all migration qualification disposable.
- Fail closed when the expected revision is missing or inconsistent with the release manifest.
- Keep runtime and production recovery independent from this CI-only change.

## Current status

```text
Development Track: ACTIVE
Plan: READY FOR IMPLEMENTATION GATE
Workflow changes: NONE
Migration changes: NONE
Production: UNCHANGED
Recovery: SAFE HOLD
```
