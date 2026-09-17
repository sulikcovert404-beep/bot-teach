# Gate 090 — Storage Investigation Evidence Expansion

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: Read-only; no runtime or configuration mutation

## Current observation

A bounded SSH read-only sample completed successfully. Host uptime was 6h41m with load average `5.01 / 4.17 / 2.63` on 2 CPUs. Memory was healthy (`3859 MiB` total, `3048 MiB` available, swap `0`). Filesystem capacity was not altered or inspected by a mutating command.

I/O pressure remains severe:

- PSI some: `avg10=99.03`, `avg60=96.37`, `avg300=83.15`
- PSI full: `avg10=94.36`, `avg60=91.98`, `avg300=78.93`
- vmstat: blocked processes `b=4`; sampled iowait reached `95%`
- iostat: first interval iowait `15.96%`, second interval `96.02%`; vda write await `3882.20 ms` in the first interval; second interval produced no device row during the stall

Runtime snapshot:

- `staging-api-1`: Up 4 hours, image `staging-api:canonical-0021-candidate`
- `staging-postgres-1`: Up 6 hours, healthy
- `staging-redis-1`: Up 6 hours, healthy
- Docker stats showed low CPU/memory usage and no restart evidence in this snapshot
- Local API health body: `{"status":"ok"}` (the shell wrapper did not emit a numeric HTTP code)

## Correlation with prior gates

| Evidence | Storage signal | Runtime signal | Interpretation |
|---|---|---|---|
| Gate 038 | PSI ~100%, iowait ~95.9%, vda 100%, write await ~57,770 ms | Containers Up; DB/Redis healthy | Severe prior recurrence |
| Gate 044 | PSI some `93.59`, full `85.99`; iowait `96.5–96.8%`; await `3,748 ms` | API/DB/Redis Up; health body OK | Severe recurrence while app available |
| Gate 089 | Correlation accepted; causal owner unresolved | Application and host health separated | No remediation performed |
| Gate 090 current | PSI some `96.37` (60s), full `91.98` (60s), iowait `96.02%`, await `3,882 ms` | All three containers Up; DB/Redis healthy; health body OK | New matching sample confirms recurrence |

## Classification update

**`RECURRING_STORAGE_SATURATION` remains supported.** Gate 090 supplies a new synchronized sample with the same signature as Gates 038 and 044: sustained PSI full pressure, very high iowait, blocked processes, and multi-second vda write latency while containers remain nominal. This does not identify whether the provider node/storage layer or an application workload is the ultimate owner; `Provider/root-cause unresolved` remains explicit.

The current sample does not justify `APPLICATION_IO_CORRELATION`: container CPU and memory were low, and no workload attribution or per-process I/O profile was collected. It also cannot close the investigation because host-level pressure is still present.

## Evidence gaps

- Provider/hypervisor storage telemetry and kernel storage error history were not available in this bounded command.
- The second iostat interval lacked a device row during the stall, so its device await/utilization is unknown.
- Numeric HTTP status was not captured by the shell wrapper, although the body was `status=ok`.
- No controlled workload attribution was performed.

## Operational boundary and restrictions

Application availability was observed independently. Host/storage stability remains unqualified and is contradicted by the current PSI/iowait sample. No restart, reboot, cleanup, Docker operation, image/build/pull, migration, DB action, deploy, configuration/secret change, provider action, or performance tuning was performed.

## Safe next direction

Keep runtime untouched. Request provider/node storage telemetry and restore reliable root/console observability, then repeat a synchronized read-only sample. Do not proceed to load qualification or remediation until a separately authorized gate addresses the active storage condition.

STATUS: Completed
Completed: Gate 090 host/storage and runtime evidence expansion; current sample correlated with Gates 038, 044 and 089
Blocked: Storage recurrence investigation and load/release qualification remain blocked by active host I/O saturation
Next Recommended Task: Provider-side storage telemetry and independent host observability
Commander Decision Required: Yes — review evidence before any remediation
