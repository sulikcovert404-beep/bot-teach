# BATCH110 — Storage Evidence Priority Ranking

Date: 2026-09-17
Classification: `RECURRING_STORAGE_SATURATION`
Mode: Documentation-only; no server or production mutation

| Evidence gap | Priority | Why it matters | Expected uncertainty reduction | Dependency |
|---|---|---|---|---|
| Provider storage telemetry | HIGH | Distinguishes host volume/node saturation from guest workload | High: identifies owner and incident scope via latency, IOPS, queue depth and volume health | Hosting provider |
| Workload I/O attribution | HIGH | Tests whether a process/container correlates with pressure | High: separates application workload from infrastructure fault | Runtime observability |
| Historical device metrics | MEDIUM | Establishes whether pressure is episodic or persistent | Medium: supplies incident timeline and recurrence pattern | Host/provider history |
| Kernel/storage details | MEDIUM | Corroborates device and filesystem symptoms locally | Medium: narrows failure class, limited owner evidence | Host read-only access |
| SSH observability completeness | LOW | Determines confidence in repeated snapshots | Low to medium: improves evidence reliability but does not identify cause alone | Stable host access |

## Current decision support

Provider telemetry and workload attribution are first because together they most reduce uncertainty about ownership and causation. Historical metrics and kernel details provide corroboration. SSH observability supports collection quality.

## Boundaries

Allowed: documentation and evidence review only.

Blocked: provider submission, server action, monitoring setup, restart/reboot, Docker changes, cleanup, tuning, DB/config/deploy/env changes.

Production mutation: NONE
