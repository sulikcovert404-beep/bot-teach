# Gate 089 — Storage Recurrence Evidence Correlation

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: Read-only evidence correlation; zero remediation

## Scope and boundary

This report correlates the available Gate 038, 044, 050, 051, 052, 053 and 088 evidence. It does not add a causal claim beyond the recorded measurements. Application availability is observed independently from host/storage stability; a healthy application endpoint alone is insufficient to close the storage investigation.

## Evidence timeline

| Gate | Time/context | Host/load | Storage evidence | Runtime/application | SSH observability |
|---|---|---|---|---|---|
| 038 | 2026-09-17, recovery observation | Load `10.48/7.56/3.83` on 2 CPUs | PSI some `99.99` / full `94.31`; iowait ~`95.9%`; vda 100% util; write await ~`57,770 ms` | Containers Up; PostgreSQL/Redis healthy; qualification command timed out | Command timeout before full output |
| 044 | 2026-09-17, 6h33m uptime | Load `3.40/1.58/1.17` | PSI some `93.59/87.34/38.41`; full `85.99/82.06/36.23`; iowait `96.5–96.8%`; vda write await `3,748 ms`; blocked processes reached 4 | API/PostgreSQL/Redis Up; dependencies healthy; local health body `status=ok` | Session available for this snapshot |
| 050 | Post-reconciliation observation | Initial load `6.84/3.95/1.95` | Host-level extension not qualified | Five health/readiness samples passed; containers healthy; restart 0; low resource use | Later SSH command timed out |
| 051 | Extended observation | Not measurable | Not measurable | Public `/health` and `/health/ready` returned 200; host/storage metrics unavailable | SSH timed out |
| 052 | SSH recovery check | Not measurable | Not measurable | Public app reachable | TCP/22 and key authentication passed; post-auth session execution timed out |
| 053 | SSH session diagnosis | Not measurable | Not measurable | Prior public health remained available | `/bin/echo` and `/bin/sh` timed out post-auth; root unavailable |
| 088 | Repository baseline audit | No new host sample | Gate 044 anomaly preserved as `OPEN INVESTIGATION` | Repository evidence consistent; no operational mutation | Historical observability limitation retained |

## Correlation classification

**Classification: `RECURRING_STORAGE_SATURATION` (evidence-based, causal owner unresolved).**

Two independent host samples on the same target and date (Gates 038 and 044) show extreme PSI pressure, very high iowait, and multi-second to tens-of-seconds device write await. This is recurrence of severe storage saturation rather than a single low-impact latency sample. Gates 050–053 add repeated loss of post-auth SSH observability, but do not supply host metrics and therefore cannot independently prove storage causality. Application containers and health endpoints remained available in portions of the window, demonstrating that application health and host/storage health can diverge.

## Unknowns and evidence gaps

- Provider/node-level telemetry, hypervisor volume metrics, SMART/underlying-device data, and kernel journal output for the incident windows are unavailable.
- Exact timestamps for individual PSI/iostat samples are not included in every historical artifact, limiting cross-gate minute-level correlation.
- No controlled attribution test was performed to distinguish provider storage from application-generated I/O; performance tuning and remediation were explicitly out of scope.
- SSH post-auth execution failures remain a separate observability symptom; they are consistent with resource pressure but not conclusive proof of it.

## Current operational boundary

- Application health: observed independently where recorded (`/health`/`/health/ready` available in Gates 044, 050, 051).
- Host/storage health: requires independent validation; public health must not be used as a substitute.
- Storage investigation remains **OPEN**. No load qualification, release closure, or remediation is implied by this report.

## Next safe investigation direction

Obtain provider-side node/storage telemetry and reliable root/console observability, then repeat a read-only host correlation window with synchronized timestamps. Preserve the current runtime and avoid restart, cleanup, Docker operations, migration, database changes, deploy, provider action, or performance tuning until a separately authorized gate exists.

## Mutation audit

- Restart/reboot: NONE
- Docker operation: NONE
- Cleanup/build/pull: NONE
- Migration/DB action: NONE
- Environment/secret change: NONE
- Deploy/provider-side action: NONE

STATUS: Completed
Completed: Correlated Gates 038, 044, 050, 051, 052, 053 and 088; documented timeline, classification, boundary and gaps
Blocked: Storage investigation and operational closure remain blocked pending provider telemetry and independent host observability
Next Recommended Task: Obtain provider/node storage evidence and repeat synchronized read-only validation
Commander Decision Required: Yes — review Gate 089 correlation before any remediation or commit
