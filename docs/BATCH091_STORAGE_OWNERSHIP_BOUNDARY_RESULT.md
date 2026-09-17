# Gate 091 — Storage Ownership Boundary Report

Date: 2026-09-17
Target: `95.135.208.167`
Mode: Documentation/read-only; no remediation

## Current evidence

Gates 038, 044, 089 and 090 independently record recurring severe host I/O pressure. PSI, iowait, blocked processes and multi-second vda write latency recur while the application and database dependencies remain reachable/healthy in sampled windows. Gate 089 accepted the correlation and Gate 090 added a fresh matching sample. No mutation has been performed.

## Confirmed facts

- Recurring high storage pressure is observed.
- Application availability can remain healthy during host pressure.
- PostgreSQL and Redis were healthy in the latest sampled runtime.
- No restart, cleanup, Docker mutation, migration, DB action, configuration change, deploy or provider action was performed.
- Root/console observability is not consistently available; post-auth SSH session failures were recorded in Gates 052–053.

## Ownership and missing evidence

| Evidence class | Status | Needed to assign ownership |
|---|---|---|
| `PROVIDER_STORAGE_METRICS` | Missing | Hypervisor/volume latency, IOPS/throttle and node incident telemetry for matching timestamps |
| `HOST_BLOCK_DEVICE_HISTORY` | Partial | Synchronized historical device latency/utilization and kernel block-layer records |
| `WORKLOAD_IO_ATTRIBUTION` | Missing | Per-process/container I/O attribution collected during a bounded incident window |
| `KERNEL_STORAGE_DETAILS` | Partial | Root/console journal and block/filesystem error records |
| `OTHER` | Open | Any provider incident ID or host-level diagnostic unavailable to `codex` |

## Closure criteria

Storage investigation may be closed only when all of the following are available:

1. Synchronized host samples show PSI/iowait and device latency within an agreed healthy bound over a meaningful observation window.
2. Provider/node telemetry covers the same window and either confirms/removes a provider storage incident.
3. Workload attribution rules out an unbounded application-generated I/O source, or a separately approved workload finding is recorded.
4. Kernel/filesystem evidence contains no unresolved storage errors.
5. Root/console observability is reliable enough to reproduce the above evidence.
6. A new read-only qualification confirms application availability and dependencies independently.

A public `/health` 200 alone does not satisfy closure.

## Classification

Current classification remains `RECURRING_STORAGE_SATURATION`; the responsible owner remains **UNRESOLVED**. Evidence supports recurrence, but not a definitive provider-versus-workload causal split.

## Safe continuation

Request provider telemetry and owner/root-console evidence, then run a synchronized read-only revalidation. Preserve the runtime while the investigation is open. No remediation, performance tuning, restart, Docker action, migration, database/config change, deploy or provider-side change is authorized by this report.

## Mutation audit

Production mutation: NONE

STATUS: Completed
Completed: Defined storage ownership boundary, missing evidence classes and closure criteria from Gates 038, 044, 089 and 090
Blocked: Storage closure and remediation pending provider/root-cause evidence
Next Recommended Task: Obtain provider storage telemetry and reliable root/console observability
Commander Decision Required: Yes — decide evidence acquisition path before any remediation
