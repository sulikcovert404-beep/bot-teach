# BATCH111 — Storage Evidence Acquisition Strategy

Date: 2026-09-17
Mode: Documentation-only; acquisition not executed
Classification: `RECURRING_STORAGE_SATURATION`

| Evidence | Collection method | Access owner | Expected output | Risk |
|---|---|---|---|---|
| Provider telemetry (HIGH) | Request provider-side time series for latency, IOPS, queue depth, volume/node health and maintenance events | Provider/infrastructure owner | Correlated timeline identifying infrastructure ownership or excluding provider fault | External dependency; no submission made |
| Workload attribution (HIGH) | Read-only process/container I/O correlation with runtime resource snapshots during an incident window | Host/runtime owner | Workload-to-device attribution or evidence that workload is not causal | Observation overhead; no agent or monitor installed |
| Historical device metrics (MEDIUM) | Obtain existing host/provider history covering incident windows | Host/provider | Recurrence pattern and time correlation | History may be incomplete |
| Kernel/storage details (MEDIUM) | Correlate existing kernel journal, block-device and filesystem evidence | Host owner | Local corroboration and narrowed failure class | Guest evidence cannot prove provider ownership alone |

## Collection order

1. Provider telemetry and workload attribution.
2. Historical metrics and kernel/storage corroboration.
3. SSH observability review only when collection reliability remains uncertain.

## Safety boundary

This document defines strategy only. No provider contact or submission, tools, monitoring agent, cron, restart/reboot, Docker operation, cleanup, tuning, DB/config/deploy/env change, or persistent collection was performed.

Production mutation: NONE
