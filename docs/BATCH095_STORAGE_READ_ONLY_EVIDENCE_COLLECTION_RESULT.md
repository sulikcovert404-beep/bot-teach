# BATCH 095 — Storage Read-only Evidence Collection

Timestamp: 2026-09-17T05:24:01+01:00
Scope: read-only observation only; no restart, cleanup, tuning, migration, configuration, or deployment.

## Collected Evidence

### Host
- Uptime: 6h51m; load average 2.69 / 3.96 / 3.40 on 2 CPUs.
- Memory: 3859 MiB total, 3051 MiB available; swap 0.
- Root filesystem `/dev/vda1`: 15% used (8.2G/58G).
- I/O PSI: some avg10 93.39%, avg60 95.16%, avg300 94.51%; full avg10 86.84%, avg60 88.75%, avg300 88.90%.
- Memory PSI: zero; CPU PSI low (some avg60 1.26%).
- vmstat samples showed 1 blocked process and iowait 17%, 40%, 49%.
- iostat: vda first interval write await 3914.65 ms, 18.28% utilization; subsequent intervals had no device rows while iowait remained 48.50% and 44.00%.

### Runtime
- `staging-api-1`: running, image `staging-api:canonical-0021-candidate`, restart count 0, OOM false.
- `staging-postgres-1`: running and healthy, restart count 0, OOM false.
- `staging-redis-1`: running and healthy, restart count 0, OOM false.
- Resource snapshot: API 0.43% CPU / 2.58% memory; PostgreSQL 13.22% CPU / 1.74% memory; Redis 1.54% CPU / 0.36% memory.

### Application
- Local `/health`: HTTP 200, `{"status":"ok"}`.
- Local `/health/ready`: HTTP 200, migration head `20260912_0021`.

## Unavailable Evidence

Provider storage telemetry, complete historical block-device metrics, and definitive workload-to-device attribution are unavailable from the current access boundary.

## Comparison / Classification

The current snapshot confirms a recurring storage-saturation pattern consistent with Gates 038, 044, and 090: very high I/O PSI and sustained iowait while application containers and database services remain reachable. Filesystem capacity, memory pressure, OOM, and container restart loops were not observed. Root cause ownership remains unresolved.

Classification: `RECURRING_STORAGE_SATURATION`.

## Production Mutation

NONE. No restart/reboot, Docker mutation, cleanup, tuning, migration, DB/config change, deployment, Cloudflare/Webhook change, or secret access occurred.

## Recommended Next Evidence Only

Obtain provider storage latency/IOPS history and host-level block-device history, then correlate process/container I/O during the same window. Keep remediation and closure decisions separate from this observation.

## Commit

HOLD pending Commander review.
