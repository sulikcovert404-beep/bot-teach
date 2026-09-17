# BATCH044 — Storage Recovery Revalidation (Read-only)

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: READ-ONLY

## Result

**Status: FAIL / STOP — storage saturation persists.** No restart, cleanup, image change, migration, build/pull, or environment change was performed.

## Host

- Uptime: 7:08; load average 3.60 / 2.31 / 2.53 on 2 CPUs.
- Memory: 3859 MiB total, 3051 MiB available; swap 0.
- Root filesystem `/dev/vda1`: 58G total, 8.2G used, 49G available (15%).
- I/O PSI: `some avg10=96.60 avg60=93.40 avg300=68.16`; `full avg10=85.89 avg60=86.47 avg300=63.86`.
- `vmstat 5 3`: iowait samples 18%, 53%, 47%.
- `iostat -xz 5 3`: `vda` write await reached ~3914 ms in initial sample and ~22,257 ms in final sample; utilization reached 100% in final sample.

## Runtime

- `staging-api-1`: Up 5 hours, port 8000 published.
- `staging-postgres-1`: Up 7 hours, healthy.
- `staging-redis-1`: Up 7 hours, healthy.
- Container stats showed low CPU/memory usage and no restart evidence in the snapshot.
- Local `GET http://127.0.0.1:8000/health`: `{"status":"ok"}` (HTTP success).

## Interpretation

Filesystem capacity and memory are healthy, and containers are running. However, sustained I/O pressure, high iowait, multi-second write latency, and 100% device utilization demonstrate that storage has **not** recovered. The Gate 044 condition for a green storage result is not met.

## Production mutation

NONE.

## Next recommendation

Keep recovery/load work stopped and escalate the recurring storage saturation to the provider/node layer. Resume candidate qualification only after a fresh read-only observation shows bounded I/O latency and materially reduced PSI/iowait.
