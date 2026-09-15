# Recovery State Delta Log — 2026-09-14

Last read-only check (UTC): 2026-09-15T11:31:27.7715635Z

## Blockers

- RUNTIME-CONFIG-001: unchanged, canonical /etc/apps/ai-teacher/staging.env absent.
- HOST-IO-002: open/high; host I/O remains degraded.

## I/O delta

Latest observed PSI:

- some: avg10 87.45%, avg60 91.48%, avg300 72.41%
- full: avg10 76.77%, avg60 82.62%, avg300 65.41%

Compared with the prior recorded check, pressure remains severe and has not stabilized.

## Runtime/config delta

- staging-api-1: still absent.
- Canonical runtime config: still absent.
- PostgreSQL: healthy.
- Redis: healthy.
- Migration/database state: preserved at 20260912_0021.

## Decision

SAFE HOLD ACTIVE.

No restore, rollback, restart, reboot, environment edit, migration, database mutation, or secret access was performed.

## Resume triggers

- Provider/Owner confirms host I/O stability and resolves HOST-IO-002.
- Canonical runtime configuration or an approved official source is provided.
