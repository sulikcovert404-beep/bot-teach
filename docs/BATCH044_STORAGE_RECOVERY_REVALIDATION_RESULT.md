# BATCH044 — Storage Recovery Revalidation

Date: 2026-09-17
Target: 95.135.208.167 (srv20708.deluxhost.net)
Mode: Read-only

## Result

**Status: FAIL / STOP — recurring storage saturation persists.**

## Host

- Uptime: 7:26
- Load average: 3.52 / 5.32 / 4.68 on 2 CPUs
- Memory: 3859 MiB total, 3050 MiB available
- Swap: 0 configured/in use
- Root filesystem: 15% used (49G available)

## I/O evidence

- PSI some: avg10 5.32%, avg60 59.82%, avg300 86.98%
- PSI full: avg10 5.08%, avg60 56.86%, avg300 82.28%
- vmstat samples reached 78% and 97% iowait with 6 blocked processes
- iostat: vda reached 99.94% utilization; write await peaked at 9165 ms

These values show the storage/I/O incident has not cleared, despite normal filesystem capacity and available memory.

## Docker runtime

- staging-api-1: Up 5 hours, port 8000 published
- staging-postgres-1: Up 7 hours, healthy
- staging-redis-1: Up 7 hours, healthy
- No restart or mutation performed

## Application

- Local `http://127.0.0.1:8000/health`: `{"status":"ok"}`

## Decision

Storage is not green. Do not proceed to load testing or release/artifact reconciliation until the provider/storage cause is resolved and a new read-only revalidation shows bounded I/O latency and no recurrence.

Production mutation: NONE
Migration: NONE
Environment changes: NONE
Restart/build/pull: NONE
