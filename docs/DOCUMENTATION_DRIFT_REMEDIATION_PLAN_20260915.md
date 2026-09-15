# Documentation Drift Remediation Plan — 2026-09-15

## Scope

This is a plan only. No implementation, workflow change, merge, runtime change, secret access, database action, migration, or production action is authorized by this document.

## Findings to remediate

1. **Compose prerequisites:** document `APP_RUNTIME_PASSWORD` and `EXPECTED_MIGRATION_HEAD` in `.env.example` using safe placeholders, and add a README subsection explaining that these are required for Compose interpolation.
2. **Smoke revision fallback:** remove the stale `scripts/staging-smoke.ps1` fallback (`20260909_0015`) or make the script fail closed when the expected revision is absent. The implementation must consume the approved expected revision source and never silently target a historical head.
3. **Historical references:** label older migration revisions in operational documents as historical and link readers to the current qualification target (`20260912_0021`) where appropriate.

## Proposed implementation sequence

1. Commander opens a small Development Implementation Gate.
2. Update `.env.example` with placeholders only; verify no secret values are introduced.
3. Update README local/Compose setup and local-vs-CI qualification guidance.
4. Update the smoke script to require or explicitly receive the expected head; preserve `-UseExistingRuntime` behavior.
5. Add or adjust focused tests for missing expected-head handling and current-head assertions.
6. Mark only genuinely historical documents; do not rewrite historical evidence.
7. Run `git diff --check`, secret scan, Ruff/mypy as applicable, focused tests, and a script syntax check.
8. Produce a diff review and request a separate merge gate; do not merge automatically.

## Acceptance criteria

- A new developer can identify all Compose prerequisites without seeing real credentials.
- Missing `EXPECTED_MIGRATION_HEAD` fails clearly rather than selecting a stale revision.
- CI and local qualification guidance name the same explicit target where applicable.
- Historical evidence remains traceable and is not presented as current.
- Production, staging runtime, database, migrations, Cloudflare, Telegram, and secrets remain unchanged.

## Commander decision required

Approve or reject the Development Documentation Drift Remediation Implementation Gate. Until approval, this plan remains advisory and no listed file is modified.
