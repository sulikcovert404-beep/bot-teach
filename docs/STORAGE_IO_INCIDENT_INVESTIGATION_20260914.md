# Storage/I/O Incident Investigation (Read-only)

Date: 2026-09-14 13:40 UTC
Host: srv20708.deluxhost.net (95.135.208.167)

## Result

Status: DEGRADED / MONITOR MODE

Three read-only samples showed no active D-state process (0 in each sample), low current iowait (2–6%), and load 0.48–0.72 / 3.08–3.35 / 3.31–3.43. I/O PSI had no recent pressure (avg10 0.00→0.12%, avg60 0.87→0.63%, avg300 32.77→30.40%; full avg10 0.00%, avg60 0.79→0.54%, avg300 29.48→27.34%). Historical five-minute pressure remains elevated, so monitor mode is retained.

## Kernel and storage

No matching kernel journal errors were found in the last 30 minutes (I/O, block, ext4, hung-task, timeout patterns). No write probe or filesystem mutation was performed in this investigation.

## Docker/runtime

`staging-api-1`, `staging-postgres-1`, and `staging-redis-1` are running and healthy. Restart count is 0 and OOMKilled is false for all three. Docker event correlation showed no restart events in the sampled window. Container block-I/O counters were not available to the unprivileged `codex` account; no runtime mutation was attempted.

## Application availability

Local and public endpoints returned HTTP 200:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/ready`
- `https://bot.codeshow.ir/health`
- `https://bot.codeshow.ir/health/ready`

No migration or database mutation was performed. Read-only `http://127.0.0.1:8000/health/ready` returned `{"status":"ready","migration_head":"20260912_0020"}`.

## Anomalies and limitations

- Elevated historical I/O PSI (300-second window) persists but is declining and is not accompanied by current D-state, iowait, kernel errors, OOM, or restarts.
- Docker block-I/O detail requires privileged access; provider-side evidence is unavailable from this environment.

## Production mutation

NONE. No restart, deploy, env/credential change, migration, Cloudflare, webhook, volume, or filesystem change.

## Recommendation

Continue read-only monitoring. Do not perform recovery or restart while current health remains stable; escalate only if PSI rises with D-state, kernel/storage errors, latency, or container instability.
