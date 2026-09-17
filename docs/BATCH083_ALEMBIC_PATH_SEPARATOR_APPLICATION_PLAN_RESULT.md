# BATCH 083 — Alembic Path Separator Application Plan

Status: READ-ONLY PLAN / NO MUTATION
Date: 2026-09-17

## Target

- Canonical target file: `alembic.ini` at repository root.
- Section/key: `[alembic]`, immediately after `prepend_sys_path = .`.
- Exact future one-line change: `path_separator = os`.
- No change was applied in this Gate.

## Current configuration

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url =
```

`sqlalchemy.url` is intentionally empty in the checked-in config; runtime/CI supplies database configuration separately. This Gate does not add or expose a URL.

## References and impact

- CI migration commands use explicit revision targets through `EXPECTED_MIGRATION_HEAD`; they do not depend on implicit discovery for the target.
- Migration source is `migrations`; `alembic heads` currently resolves to `20260912_0021`.
- Gate 082 disposable qualification added only `path_separator = os`: before and after heads were `20260912_0021`, and history lineage was unchanged.
- The option selects the platform-native separator when parsing `prepend_sys_path`; it addresses Alembic 1.19.1's legacy fallback warning. It does not alter `script_location`, revision traversal, revision identifiers, or migration ordering.
- Existing documentation/scripts contain historical `alembic upgrade head` examples. They are outside this config-only plan and must not be treated as production execution guidance; production policy remains explicit revision targets.

## Future validation (separate execution Gate)

1. Record clean working tree/config hash and warning count.
2. Apply only the one-line `[alembic]` setting in a controlled workspace.
3. Run `alembic heads`, `alembic history`, and migration discovery checks; confirm head `20260912_0021` and unchanged lineage.
4. Run the project migration qualification harness with its existing disposable database configuration (no implicit `upgrade head`).
5. Run the pytest baseline and compare behavior/results; confirm the three Alembic fallback warnings are removed and no unrelated warning/failure appears.
6. Review diff and config parse before any commit. A separate Commander approval is required for the actual config mutation.

## Rollback boundary

Remove only `path_separator = os` (or restore the previous `alembic.ini` bytes). No downgrade, stamp, database rollback, deployment, dependency, environment, or secret operation is part of this rollback.

## Risk boundary

Low, configuration-only candidate qualified in disposable discovery. Remaining risk is workflow-specific behavior in the configured migration harness/CI; it is addressed by the future validation Gate. Production and live databases remain untouched.

## Acceptance for Gate 083

- Target and exact one-line mutation defined: PASS
- Warning rationale and expected reduction (3 Alembic fallback warnings) documented: PASS
- Discovery/script location/revision impact assessed: PASS
- Rollback defined without DB action: PASS
- Validation commands and pytest comparison defined: PASS
- Canonical config mutation: NOT PERFORMED
- Commit of config change: NOT PERFORMED
- Migration/DB/deploy/env/dependency mutation: NONE

Commit status: HOLD pending Commander approval for this report.
