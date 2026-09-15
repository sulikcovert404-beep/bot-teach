# Production Recovery Evidence Bundle — 2026-09-14

## Scope

This bundle consolidates read-only evidence for the production recovery decision after migration 0021. It does not authorize recovery, deployment, restart, migration, or configuration changes.

## Migration Timeline

```text
20260912_0020
    ↓ artifact alignment and image promotion
Migration execution
    ↓
20260912_0021
```

- Migration lineage is explicitly `20260912_0020 → 20260912_0021`.
- Commander-provided production evidence reports DB revision `20260912_0021`.
- Local repository evidence reports one Alembic head: `20260912_0021`.
- No migration command was issued during this evidence task.

## Current Runtime State

| Item | Evidence / status |
|---|---|
| Target host | `95.135.208.167` / `srv20708.deluxhost.net` |
| SSH transport | PASS: TCP/22 reachable; known host key matches; public-key authentication as `codex` succeeded |
| Remote command execution | NOT QUALIFIED: bounded non-interactive command did not return |
| Sudo | UNKNOWN; no password prompt or secret exposure occurred |
| Runtime image | `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd` (reported production evidence) |
| API readiness | BLOCKED pending Docker/host recovery |
| Database | `20260912_0021` (reported evidence) |
| Docker/host | HOLD because of the recorded Docker socket stall and host I/O degradation |

## Incident Timeline

1. Migration 0021 completed.
2. Readiness failure was attributed to stale `EXPECTED_MIGRATION_HEAD` validation.
3. A correction path was identified but runtime recovery remained pending.
4. Docker socket stall and I/O PSI degradation were observed.
5. Recovery was placed on HOLD; no rollback or additional mutation was issued.

## Gate History

| Gate | Status |
|---|---|
| Artifact qualification | PASS |
| Image build | PASS (reported evidence) |
| Image promotion | PASS |
| Migration 0021 | PASS / applied |
| Readiness correction | BLOCKED |
| Docker recovery | HOLD |
| Security evidence archive | COMPLETE |
| Operational runbook | COMPLETE |
| Recovery status record | COMPLETE |

## Recovery Decision Inputs

The following evidence is required before opening a recovery gate:

- remote command execution completes within a bounded timeout;
- sudo capability is explicitly qualified without exposing credentials;
- Docker socket responds consistently;
- host filesystem and I/O indicators are normal and show no D-state recurrence;
- canonical API container can be inspected safely;
- local and public `/health` and `/health/ready` checks return 200;
- the DB head remains `20260912_0021` without migration or schema mutation.

## Hard No-Mutation Boundary

Until an explicit recovery decision is issued, do not run Docker lifecycle commands, restart or recreate containers, build/pull/prune images, write to the database, run migrations, edit environment or credentials, change Cloudflare or webhooks, reboot the host, modify the old production environment, or touch `mentor-bot`.

## Evidence and Confidentiality

- No secrets, tokens, credentials, environment values, or private user data are included.
- SSH checks were read-only and made no server changes.
- The local workspace cannot independently query the live catalog because its local SQLAlchemy URL is invalid; live DB claims remain explicitly attributed to prior Commander-provided evidence.
- No synthetic health, readiness, Docker, or migration PASS was created.

## Decision Snapshot

```text
Production: RECOVERY HOLD
Database: 20260912_0021
Readiness: BLOCKED
Docker/Host: HOLD
SSH transport: PASS
Remote execution: NOT QUALIFIED
Sudo: UNKNOWN
Production mutation: NONE
Next decision input: host/Docker stability plus bounded command-execution qualification
```
