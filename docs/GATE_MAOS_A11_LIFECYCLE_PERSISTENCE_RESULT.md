# GateMAOS-A11 — Account Lifecycle Authority Persistence V1

## Verdict

`A11_LOCAL_DISPOSABLE_QUALIFICATION_PASS_WITH_UNRELATED_TEST_FAILURE`

The lifecycle migration and focused PostgreSQL qualification passed on disposable PostgreSQL 16. Work remains local and uncommitted as required. This does not authorize staging, production, operational lifecycle writes, or external effects.

## Source and lineage

- Base commit: `dc69a2c3dd3ce0308e41f71039a1d018fdafe79a`
- Verified predecessor head: `20261006_0034`
- New revision: `20261006_0035`
- Parent: `20261006_0034`
- Historical migrations: unchanged
- Explicit disposable replay: `20261004_0032` → `20261003_0030` → `20261003_0031` → `20261004_0033` → `20261006_0034` → `20261006_0035`
- Final sole repository head: `20261006_0035`

## Implementation

- `migrations/versions/20261006_0035_account_lifecycle_authority.py` adds authoritative append-only lifecycle events and a rebuildable current-state projection. Events keep opaque principal/actor/authority/evidence/audit references and a per-principal hash chain. No account foreign key or cascade can delete lifecycle history.
- Database functions enforce the exact `UNRECONCILED`, `ACTIVE`, `SUSPENDED`, `DISABLED` transitions, idempotent event replay, initial anchor, monotonic time, event-chain integrity, and projection agreement. Missing history resolves to `UNRECONCILED`; inconsistent history/projection raises an error.
- Dedicated `NOLOGIN`, non-superuser, non-BYPASSRLS owner and writer roles are created. `app_runtime` has no schema, table, resolver, or writer access. No operational login receives the lifecycle writer role.
- `tests/maos/test_lifecycle_persistence_postgres.py` exercises the PG16 persistence and security contract, including an unanchored-history rejection case.
- `tests/test_migration_roundtrip_qualification.py` now asserts the exact head `20261006_0035` and its parent `20261006_0034`.
- Authority V1, Kernel V1, A10 migration `0034`, and readiness sources were not changed.

## Qualification evidence

- Actual explicit migrations on the disposable PG16 database reached `20261006_0035`; PostgreSQL confirmed the final revision.
- The lifecycle PostgreSQL integration test passed with the final unanchored-history regression (`1 passed`); an earlier version passed once before that case was added. Coverage includes transition/replay/terminal rules, missing and unanchored history, projection corruption and rebuild, `app_runtime` denial, append-only protections, and no cascade deletion.
- Authority V1 contracts plus the migration-lineage head test: `16 passed`.
- Canonical Linux/Python 3.12 mypy baseline gate: baseline `579`, current `579`, new `0`.
- Ruff: pass on canonical-mode copies of the changed Python files. The Windows bind mount exposes all source files as mode `777`, which triggers false `EXE002` reports; copied files were set to the tracked mode `0644` before linting.
- `py_compile`: pass.
- `git diff --check`: pass.
- An independent disposable PG16 restore retained revision `0035`, 8 synthetic lifecycle events, 4 projections, the `DISABLED` resolution, lifecycle function ownership, and `app_runtime` denial. Post-restore UPDATE, DELETE, and TRUNCATE attempts were rejected by the append-only triggers.
- Custom-format dump: `C:\Users\IT\AppData\Local\Temp\maos-a11-pg16-restore.dump`
- Dump SHA-256: `897213b9d194ebd2505159b9c86a8906cab4c1d530c9afc997ae09fe701947c4`
- `pg_restore --list`: pass, 770 archive entries.

## Failure and limits

- The first PG16 DDL attempt found invalid `pg_catalog.extract(...)` syntax. PostgreSQL rolled the transaction back to `0034`; the new migration was corrected to use `extract(...)` and then applied successfully as explicit target `0035`.
- A broader selected pytest invocation exposed one unrelated legacy in-memory test failure: `test_migration_roundtrip_0019_0018_0019_and_post_smoke` expects `school_tenants` in `Base.metadata`, but that isolated test imports only `app.db.base` and leaves the metadata empty. It is outside A11 and was not modified. The separate head/lineage test passes after exact `0035` alignment.
- Restore qualification used the same locally disposable PG16 image family on a separate fresh instance; it does not represent production backup qualification.
- No commit, push, CI, shared staging, production, provider call, runtime lifecycle wiring, or external effect occurred.

## Files and workspace state

- Added: `migrations/versions/20261006_0035_account_lifecycle_authority.py`
- Added: `tests/maos/test_lifecycle_persistence_postgres.py`
- Updated: `tests/test_migration_roundtrip_qualification.py`
- Added: `docs/GATE_MAOS_A11_LIFECYCLE_PERSISTENCE_RESULT.md`
- No other project containers were changed. Only the disposable `maos-a11-*` containers/database were used; the disposable API container was removed after migration qualification. The independent restore container remains available for inspection.

## Next recommended task

Have Commander review the A11 local qualification and issue the next Gate for a separately controlled lifecycle mutation/control-plane integration. Keep approval, delegation, risk runtime, provider dispatch, external effects, staging, and production blocked until their own Gates.
