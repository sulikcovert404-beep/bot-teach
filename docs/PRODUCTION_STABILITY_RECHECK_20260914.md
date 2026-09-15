# Production Stability Recheck

Status: DEGRADED / STOP

## Host

- host: srv20708.deluxhost.net (95.135.208.167)
- uptime: 2 days 4 hours at check
- load average: 3.20 / 6.71 / 4.25 on 2 CPUs (later sample 2.22 / 6.20 / 4.15)
- D-state: no D-state process observed in the available process snapshot
- I/O PSI: avg10 about 0.13%, avg60 about 27.23%, avg300 about 66.47%; full avg10 about 0.11%, avg60 about 24.61%, avg300 about 59.80%
- iowait: 0.0% in top sample
- memory: 3.8 GiB total, about 2.9 GiB available; no swap configured
- kernel/storage errors: none in recent journal query

## Storage

- filesystem: `/dev/vda1` ext4, 14% used, `errors=remount-ro`
- recent storage error patterns: none found
- bounded latency probe: sync plus 4 MiB temporary write completed in 0.19s and the temporary file was removed; no persistent file retained

## Docker

- staging-api-1: running/healthy, restart count 0, OOM false
- PostgreSQL: no adverse state observed in container summary
- Redis: running/healthy

## Application

- public `/health`: 200
- public `/health/ready`: 200
- `/mini-app/`, `/platform/`, `/student-dashboard/`, `/teacher-dashboard/`, `/admin-dashboard/`: 200
- readiness response confirms service ready; migration head was not changed or exposed

## Anomalies

Historical I/O pressure remains high in PSI 60/300 second windows despite current iowait and short-term PSI being low. This is a stability concern under the Commander stop criteria and should be investigated before any recovery or production mutation.

## Production Mutation

NONE. No restart, reboot, deploy, env/credential change, migration, Cloudflare change, webhook change, or container orchestration action performed.

## Commander Decision Required

Determine whether to open a separate storage/I/O incident investigation or continue observation. No recovery action was taken.
