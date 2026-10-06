# GateMAOS-A10R — Migration Repair Qualification Result

## Verdict

`A10R_QUALIFIED_ON_DISPOSABLE_POSTGRESQL_16`

The narrowly authorized trigger-function ACL repair passed real-lineage replay, post-revoke runtime checks, a custom-format dump, and an independent PostgreSQL 16 restore. This does not accept GateMAOS-A10 as deployable: runtime readiness still expects `20261004_0033`, and artifact/source qualification remains outside A10R.

No commit, push, CI run, staging or production access, deployment, external provider effect, cleanup, or action against another project occurred.

## Source and provenance

- Worktree: `D:\project\ai-teacher-maos-a5o`
- Branch: `codex/gate-maos-a5o`
- Parent/source commit: `29edcfa3fc34c509eb0342ce84a8a16530e596a8`
- Migration revision: `20261006_0034`
- Parent revision: `20261004_0033`
- Trigger function identity, read from the actual predecessor catalog: `public.gate738k_guard_writer()`
- Repaired migration SHA-256: `0f9e1a6e8e9743d273f325dd9adda9945fe857572fcebfa045c4c9dec4e8035d`
- Repaired migration Git blob: `a27339adaee11586cd98078769d61fbbba2d0af7`
- Repaired migration size: `20,329` bytes
- The A10 source extension pins that exact migration SHA, blob, and size and retains the frozen base manifest SHA/blob.

The migration grants EXECUTE on the exact zero-argument function to the no-login `maos_audit_owner` immediately before `SET LOCAL ROLE` and trigger creation. After `RESET ROLE`, it revokes that grant before dropping temporary role membership. No grant is made to `PUBLIC` or `app_runtime`; the grant does not persist.

## Validation

- Canonical environment: Linux x86_64, CPython `3.12.15`; locked dependencies installed with `pip --require-hashes`, lock SHA-256 `4891ea0d685df0c127aa0d79991e451541b886f1a345e81f64ce6af6d8d528ac`.
- Mypy baseline: `579`; current `579`; new findings `0`; resolved `0`.
- Focused tests: `50 passed`, `1 warning` (existing Starlette/httpx deprecation).
- Full suite: `1243 passed, 24 skipped, 1 failed`. The sole failure was `test_config_fingerprint_matches_canonical_git_blob`: the Python 3.12 runner has no `git` executable, and its `.git` worktree pointer resolves to `/mnt/d/project/bot telegram teacher/.git/worktrees/ai-teacher-maos-a5o`, which is not mounted in this runner. This is an execution-environment failure; the test did not reach its fingerprint assertion. The same test passed separately on the host (`Python 3.13.14`, `1 passed`), confirming the contract itself works when the real worktree metadata and Git are available. No environment repair was attempted.
- Ruff: PASS on the migration and PostgreSQL test with `EXE002` ignored because the Windows bind mount reports every source as executable inside Linux. All remaining configured checks passed.
- `git diff --check`: PASS.

## Real-lineage migration and security evidence

A fresh task-namespaced PostgreSQL 16 cluster used image digest `sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`, dedicated container `maos-a10r-lineage-pg16`, and loopback port `18581`. The actual migration lineage was replayed with explicit targets through `20260921_0022`, `20261003_0029`, `20261004_0032`, `20261003_0030`, `20261003_0031`, `20261004_0033`, and repaired target `20261006_0034`. No `head`, stamp, or downgrade was used to apply the target.

Immediately before 0034, the catalog identified the guard as `gate738k_guard_writer()`, owned by `postgres`, with no EXECUTE for `PUBLIC` or `app_runtime`. After 0034, the catalog showed the same owner and ACL `{postgres=X/postgres}`; `PUBLIC`, `app_runtime`, and `maos_audit_owner` had no EXECUTE. Six MAOS writer-fence triggers reference the guard. The migration completed with `alembic_version=20261006_0034`.

After the temporary grant was revoked, the runtime role successfully exercised operation reservation/replay, audit append, and effect-intent/state functions through the installed triggers. The real-lineage probe also verified fail-closed `UNKNOWN` blind retry, tenant isolation and forged-tenant denial, forced RLS, append-only and truncate denial, absence of direct runtime table privileges, and absence of sensitive-payload-shaped columns. A downgrade attempt was rejected as forward-only; a subsequent read-only check remained at `20261006_0034`.

## Backup and independent restore qualification

- Source database: disposable `gate738e_a10r_lineage` on `maos-a10r-lineage-pg16`.
- Archive: PostgreSQL custom format; `pg_dump` and `pg_restore` version `16.15`; 711 TOC entries.
- Archive SHA-256: `05e473819403248ed097c5c8210351349077bd6e8bd58c79ec8b492f193decdc`.
- `pg_restore --list`: PASS.
- Independent target: fresh task-namespaced PostgreSQL 16 container `maos-a10r-restore-pg16`, dedicated network `maos-a10r-restore-20261006`, loopback port `18582`, same pinned image digest.
- Copied archive SHA-256 matched the source exactly; `pg_restore --exit-on-error` completed successfully.
- Restored checks: `alembic_version=20261006_0034`; six MAOS tables; all six enforce and force RLS; guard ACL has no EXECUTE for audit owner, runtime, or PUBLIC; restored guard triggers present. Before the post-restore probe, the dump contained 13 operation reservations, 8 audit events, 6 effect intents, and 18 effect events.
- On the restored database, the candidate runtime role successfully set principal context, reserved an operation, appended an audit event, prepared an effect, and advanced the effect state through the guarded tables after the migration grant had been revoked.

Both databases, containers, and networks are disposable resources created for this task. They remain available for inspection; no prune or cleanup was run.

## Scope and remaining blockers

The migration, its focused PostgreSQL test, and the exact migration entry in the additive A10 provenance extension are the A10R repair artifacts. Earlier A10Q worktree changes and reports were preserved. The frozen candidate manifest, Kernel and Authority source extensions, and `app/api/routes/health.py` were not changed by A10R. No other project resource was touched.

Readiness remains blocked because `app/api/routes/health.py` still expects `20261004_0033`; resolving that against the frozen candidate manifest requires the separately deferred GateMAOS-A10P decision. This A10R result does not qualify a deployable artifact, authorize migration on shared staging, or authorize production use.
