# Recovery Monitoring Baseline — 2026-09-14

## Purpose
Baseline for comparison before and after an explicitly authorized production recovery gate. This document records known evidence without executing host, Docker, DB, migration, environment, or restart operations.

## Current Snapshot
| Area | Baseline |
|---|---|
| Host | `95.135.208.167` / `srv20708.deluxhost.net` |
| SSH transport | Authenticated; remote execution stability not qualified |
| Docker daemon | DEGRADED; socket timeouts previously observed |
| Host I/O | High PSI previously observed; recurrence must be checked read-only |
| Canonical API | `staging-api-1` |
| Runtime image | `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd` |
| Database revision | `20260912_0021` |
| Recovery state | HOLD |
| Production mutation in this baseline | NONE |

## Required Read-only Measurements at Gate Opening
- Hostname, uptime, load average, memory, swap, disk usage, and timestamped I/O PSI.
- D-state process count and recent kernel/filesystem/storage errors.
- Docker daemon responsiveness, socket accessibility, running-container snapshot, restart/OOM indicators.
- Canonical container state and image digest.
- PostgreSQL and Redis health/connection state without writes.
- Local and public `/health` and `/health/ready`; migration revision.

## Recovery Trigger
Recovery may be considered only when all are evidenced:
- Docker socket stable and bounded commands complete without timeout.
- Host I/O normalized with no D-state recurrence.
- SSH command execution and sudo are stable.
- Canonical container/image provenance matches.
- Database revision remains `20260912_0021`.

## Abort Signals
Any Docker timeout, renewed I/O degradation, D-state, filesystem/kernel error, unexpected container/image state, readiness/schema mismatch, or request for unapproved mutation requires STOP + REPORT.

## Prohibited During Baseline
Docker restart/recreate, host reboot, DB operation, migration, environment edit, credential change, Cloudflare/webhook change, and unrelated service changes.

## Ownership
Commander controls the recovery gate. Provider/Infrastructure owner controls host remediation. This baseline grants no operational permission.

## Status
**Migration: COMPLETE · Runtime: WAITING API RECOVERY · Infrastructure: HOLD · Production: UNCHANGED**
