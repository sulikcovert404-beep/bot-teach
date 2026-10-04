# Gate738AA — Migration Surface Repair & Release Invocation Hardening

Date: 2026-10-04  
Mode: repository repair and local/static validation only

## Verdict

`SCOPED_REPAIRS_COMPLETE_WITH_ARCHIVAL_DOCUMENTATION_REVIEW_REQUIRED`

The active, named release and restore paths in this Gate were repaired and verified locally. This is not a Docker image qualification, staging release, Gate738L qualification, or production approval. Older operational/historical documents elsewhere in the repository still contain legacy revision and direct-Alembic examples; those files were outside this Gate's named edit scope and require a separate documentation decision before they can be treated as active guidance.

## Pre-change freeze and migration metadata

- Frozen manifest: `docs/GATE738V_CANDIDATE_MANIFEST.json`
- Manifest SHA-256: `E7720C946F0D84F683DADBF344346779E8DE2DA6E5B5E21DE77858C0B9CAB378`
- Frozen entries: 407 candidate files + 5 verification inputs = 412
- Independent pre-change size/hash verification: 412/412 matched
- Sole Alembic head, both before and after repairs: `20261004_0033`
- The frozen Gate738V manifest bytes remain unchanged. Since repairs alter candidate files, this manifest is historical pre-repair evidence and must not be used as the post-repair candidate identity or regenerated under this Gate.
- Post-repair comparison against its 412 entries finds exactly three expected content mismatches: `Dockerfile`, `docker-compose.yml`, and `tests/test_gate738p_contract_guard.py`. The report is not in the manifest.

## Repairs made

- Docker image now packages the canonical `scripts/gate738p_contract_upgrade.py` runner. Qualification evidence remains an explicit read-only runtime input at `/run/migration-gate/qualification-evidence.json`; it is not embedded in the image. `compose.migration-evidence.example.yml` provides an optional read-only bind mount with required host path and `create_host_path: false`.
- Compose keeps migration behind the `migration-gate` profile, requires an explicit expected revision, points only to the canonical allow-listed runner, and does not automatically migrate when the API starts.
- CI staging smoke now uses the explicitly allow-listed pre-contract target `20261003_0029`, runs the migration profile before API startup, and tests only its local disposable database. Image publication depends on both quality and staging smoke. The smoke does not claim to qualify 0033 hard-crash evidence, Gate738L, or production.
- `scripts/staging-smoke.ps1` now makes the disposable dependency → migration runner → API sequence explicit and fails on command errors.
- `scripts/restore-drill.ps1` restricts the revision to the runner's exact target allowlist, rejects non-loopback/non-PostgreSQL URLs and anything outside a `gate738aa_restore_*` database, refuses query/fragment routing, calls the canonical runner, and verifies readiness reports the exact requested revision before success. Archive restore is therefore guarded to the named local disposable namespace; the script was not executed.
- Gate738P PostgreSQL test setup now refuses non-loopback URLs and any database other than the exact gate-owned `gate738p_admin` namespace before connecting. This cannot establish where a user-configured local port-forward terminates; integration execution remains separately controlled.
- The Gate735B test-only re-upgrade now requests exact fixture target `20261003_0026`, not `head`.
- `.env.example` has a blank expected-revision default with fail-closed guidance. README, `docs/MIGRATIONS.md`, and `docs/OPERATIONS.md` now direct operators to an explicit approved target and the migration-gate runner; restore guidance limits drills to disposable local databases and says production backup/restore needs a separate environment and authorization.

Files changed by this Gate:

```text
.env.example
.github/workflows/ci.yml
Dockerfile
README.md
docker-compose.yml
compose.migration-evidence.example.yml (new)
docs/MIGRATIONS.md
docs/OPERATIONS.md
docs/GATE738AA_MIGRATION_SURFACE_REPAIR_RESULT.md (new)
scripts/restore-drill.ps1
scripts/staging-smoke.ps1
tests/test_gate735b_class_enrollment_postgres.py
tests/test_gate738p_contract_guard.py
tests/test_gate738aa_invocation_safety.py (new)
```

## Validation

- Full workspace suite: **1027 passed, 23 skipped, 1 warning**. Skips include PostgreSQL/Gate integration tests requiring separately configured disposable resources; no such resource was exercised here.
- Focused Ruff checks for the new safety tests and Gate738P contract tests: **PASS**.
- `git diff --check`: **PASS** (Git emitted line-ending conversion notices only).
- PowerShell parser checks for restore and staging-smoke scripts: **PASS**.
- YAML parser checks for CI workflow, primary Compose file, and optional evidence overlay: **PASS**.
- Read-only Alembic metadata: `python -m alembic heads` → `20261004_0033 (head)`.
- No GitHub Actions run, Compose render, Docker build, Docker lifecycle, database connection, or Alembic migration was performed. The user's report that Docker is running does not substitute for image/runtime qualification.

## Residual documentation scope

Repository search still finds old revision values and direct Alembic examples in dated Gate reports/runbooks and in `docs/PRODUCTION_OPERATIONAL_HANDOFF.md`. They were not edited because Gate738AA named only the current README/environment configuration, `docs/MIGRATIONS.md`, `docs/OPERATIONS.md`, and restore guidance, and explicitly bounded the repair. Their status as archive versus still-used instructions has not been independently established. A separate scoped review should identify and label or update those records before asserting repository-wide documentation consistency.

## Mutations and safety

- Workspace files: the 14 paths listed above only; pre-existing unrelated dirty/untracked project files were left untouched.
- Frozen manifest: not edited or regenerated.
- Docker commands/build/container lifecycle: **NONE**.
- Database writes, schema changes, Alembic upgrade/downgrade/stamp, or restore: **NONE**.
- Staging/production, SSH, deploy, DNS, secrets, and commit: **NONE**.

## Final

The scoped repairs are implemented and locally validated. Do not treat them as permission to build/publish/deploy or execute a migration. Obtain a separate qualification Gate and a current post-repair artifact identity before any release activity. Resolve the residual historical-document classification in a separately scoped review.
