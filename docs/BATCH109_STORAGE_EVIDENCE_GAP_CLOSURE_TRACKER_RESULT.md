# BATCH109 — Storage Evidence Gap Closure Tracker

Date: 2026-09-17
Classification: `RECURRING_STORAGE_SATURATION`
Status: OPEN — evidence collection only

| Evidence gap | Status | Required evidence | Expected owner | Closure condition |
|---|---|---|---|---|
| Provider storage telemetry | OPEN | Volume latency, IOPS, queue depth, health timeline | Hosting provider | Provider telemetry received and correlated |
| Historical device metrics | OPEN/PARTIAL | Time-series device utilization and await history | Host/provider | Reliable history covering incident windows |
| Kernel/storage details | PARTIAL | Correlated kernel journal, block-device and filesystem evidence | Host owner | Complete incident-window evidence without ambiguity |
| Workload I/O attribution | OPEN | Process/container-to-device I/O correlation | Runtime owner | Workload source identified or excluded |
| SSH observability completeness | PARTIAL | Stable command execution and repeatable snapshots | Host owner | Repeated observations complete without session loss |

## Dependency tracking

- External dependency: provider storage telemetry.
- Internal dependency: additional read-only evidence when needed.
- Remediation, tuning, restart, cleanup, migration, DB/config changes, and provider submission remain unauthorized.

## Current evidence

- Repeated high I/O pressure and elevated storage latency are confirmed.
- Application, PostgreSQL, and Redis remained available during the latest sample.
- Storage owner and workload attribution remain unresolved.

## Closure rules

The investigation may close only when the pressure is resolved or explained, ownership is identified, evidence is sufficient, and no critical blocker remains. Until then it remains OPEN/PARTIAL.

Production mutation: NONE
