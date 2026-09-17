# BATCH081 — Alembic Path Separator Qualification Result

Mode: read-only configuration audit. No alembic.ini/config change, migration upgrade/downgrade/stamp, DB mutation, dependency upgrade, or code change.

## Current configuration
`alembic.ini` contains:
- `script_location = migrations`
- `prepend_sys_path = .`
- `sqlalchemy.url =` (empty)
- no `path_separator` option

The missing `path_separator` causes Alembic 1.19.1 to emit its legacy fallback warning when `prepend_sys_path` is processed.

## Version and discovery
- Alembic: 1.19.1
- `alembic heads`: `20260912_0021 (head)` — migration source discovery succeeds.
- `alembic current` cannot connect in this local shell because `sqlalchemy.url` is empty; this is existing configuration behavior, not changed in this Gate. Migration tests provide their own configured URL.

## Proposed option (not applied)
Adding `path_separator = os` would select the platform-native separator for `prepend_sys_path` and remove the fallback warning. It is configuration-only, but must be qualified against the project’s migration test harness and CI before adoption. Rollback is a one-line removal/revert of that config entry.

## Compatibility impact
No migration discovery impact is expected for the single path `.`; however, the setting should be tested in disposable migration discovery and CI environments before changing the canonical config. No local action was taken.

Verdict: cause understood; safe boundary and rollback path defined; migration/config mutation deferred.
Commit Gate 081: HOLD pending Commander approval.
