# Docker/Host Stability Requalification — 2026-09-14

## Status
**FAIL / STOP — Recovery Gate CLOSED**

## Evidence (read-only)
| Check | Result |
|---|---|
| SSH transport/command execution | PASS; bounded command completed |
| Host | `srv20708.deluxhost.net` |
| Uptime/load | 2 days; load `0.18, 0.55, 3.15` |
| D-state | `0` |
| I/O PSI | current `some avg10=0.12`, `full avg10=0.00`; 300s averages remained elevated (`3.52`/`3.22`) |
| Memory/swap | 3.8 GiB; swap 0; available ~3.0 GiB |
| Filesystem | `/` 15% used, 49G available |
| Docker daemon | PASS; version 29.1.3 |
| Docker socket | PASS for bounded commands |
| PostgreSQL | `staging-postgres-1` healthy |
| Redis | `staging-redis-1` healthy |
| `staging-api-1` | MISSING (inspect returned no container) |
| sudo | FAIL/UNKNOWN; non-interactive sudo unavailable |
| Public `/health` | 502 |
| Public `/health/ready` | 502 |
| DB/migration mutation | NONE |

## Interpretation
Host basic telemetry and Docker responsiveness improved enough for observation, but recovery cannot open. The canonical API container is absent, sudo is not qualified, historical I/O pressure remains visible in the PSI window, and public availability is 502. No lifecycle action was attempted.

## Required Decision
Provider/Owner must restore stable privileged execution and the canonical API container before a new recovery gate. Do not recreate, restart, migrate, edit env, or modify Cloudflare/webhook under this report.

## Production Mutation
NONE.
