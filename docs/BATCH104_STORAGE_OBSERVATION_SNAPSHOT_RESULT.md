# BATCH104 — Storage Observation Snapshot

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: READ-ONLY snapshot

## Timestamp and host evidence

- Timestamp: `2026-09-17T05:48:57+01:00`
- Uptime: 7:16; load average 7.74 / 5.53 / 3.91 on 2 CPUs.
- `vmstat 5 3` iowait: 19%, 96%, 62%.
- I/O PSI: some avg10 95.80%, avg60 97.84%, avg300 92.46%; full avg10 90.50%, avg60 92.57%, avg300 87.06%.
- CPU PSI low; memory PSI zero.
- `vda` initial write await ~4277 ms; device observations continued to show high wait. Filesystem `/dev/vda1` has 49G available (15% used).

## Runtime evidence

- `staging-api-1`: Up 5 hours, image `staging-api:canonical-0021-candidate`.
- `staging-postgres-1`: Up 7 hours, healthy.
- `staging-redis-1`: Up 7 hours, healthy.
- Additional containers: `affectionate_agnesi` Created; `cutoverclone-*` exited 0. No action taken on them.
- Snapshot stats showed low API/PostgreSQL CPU and memory; Redis 6.27% CPU. No restart/OOM data was mutated or inferred beyond the snapshot.

## Application evidence

- Local `/health`: `{"status":"ok"}`.
- Local `/health/ready`: `{"status":"ready","migration_head":"20260912_0021"}`.

## Comparison with Gate 095 / classification

Compared with Gate 095 and Gate 044, I/O pressure remains severe and has worsened in PSI terms. The service remains available, but storage pressure is persistent and correlates with elevated load and high iowait. Classification remains `RECURRING_STORAGE_SATURATION`; root cause remains unresolved. This snapshot is **not a green storage result**.

## Stop boundary and mutations

No monitoring daemon, cron, package installation, restart/reboot, Docker mutation, database action, migration, configuration/environment change, or deployment was performed.
