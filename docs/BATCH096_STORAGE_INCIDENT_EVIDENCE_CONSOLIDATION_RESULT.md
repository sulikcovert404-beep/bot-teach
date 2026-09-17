# Gate 096 — Storage Incident Evidence Consolidation

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: Documentation-only consolidation; no remediation or runtime mutation.

## Evidence trend

| Gate | PSI / iowait / device evidence | Runtime evidence | Interpretation |
|---|---|---|---|
| 038 | PSI some 99.99%, full 94.31%; iowait ~95.9%; vda 100% util; write await ~57,770 ms | Containers up; PostgreSQL/Redis healthy; qualification timed out | Severe storage recurrence |
| 044 | PSI some 93.59/87.34; full 85.99/82.06; iowait 96.5–96.8%; await 3,748 ms; blocked up to 4 | API/DB/Redis up; health body OK | Severe recurrence with app availability |
| 089 | Correlation of prior gates; host metrics unavailable for several observations | Public health available in portions; SSH observability degraded | Recurrence classification retained; causality unresolved |
| 090 | PSI some avg60 96.37%; full avg60 91.98%; iowait 96.02%; blocked 4; await 3,882 ms | Containers up; DB/Redis healthy; low resource use | New synchronized sample confirms recurrence |
| 095 | PSI some avg60 95.16%; full avg60 88.75%; iowait 17/40/49%; blocked 1; await 3,914.65 ms | All containers running/healthy; restart 0; OOM false; health/ready HTTP 200; head 20260912_0021 | Recurring saturation persists despite nominal runtime |

## Current incident state

- Storage status: **OPEN**.
- Classification: **RECURRING_STORAGE_SATURATION**.
- Root-cause owner: **UNRESOLVED**.
- Application health and storage health are separate signals; HTTP 200 does not close this incident.

## Stable findings

- Multiple synchronized samples show sustained I/O PSI/full pressure, high iowait, blocked processes, and multi-second device write latency.
- Filesystem capacity and memory pressure remained healthy in the latest sample.
- Containers and database dependencies remained reachable without restart loops or OOM evidence in the latest sample.
- No evidence justifies attributing the saturation to a specific provider or application workload.

## Closure blockers / missing evidence

- Provider or hypervisor storage telemetry (latency, IOPS, queue depth).
- Complete historical block-device and kernel storage error telemetry.
- Per-process/container I/O attribution during the same observation window.
- Reliable privileged/root or console observability for independent correlation.

## Operational boundary

No restart/reboot, Docker operation, cleanup, tuning, migration, database/configuration/secret change, deployment, Cloudflare/Webhook change, or provider-side action was performed in Gates 038, 044, 089, 090, or 095.

## Recommended next evidence

Request provider/node storage telemetry and restore reliable root/console observability. Repeat a synchronized read-only host/runtime window after evidence becomes available. Keep remediation, load qualification, and closure as separate Commander gates.

## Status

STATUS: Completed
Completed: Consolidated Gates 038, 044, 089, 090, and 095 with evidence trend and boundaries.
Blocked: Storage investigation closure, load qualification, and remediation pending provider telemetry and attribution.
Next Recommended Task: Obtain provider-side storage evidence, then repeat synchronized read-only validation.
Commander Decision Required: Yes — review consolidation before any remediation or commit.

## Commit

HOLD pending Commander review.
