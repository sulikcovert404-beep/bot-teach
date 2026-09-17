# BATCH114 — Storage Ownership Evidence Plan

Date: 2026-09-17
Mode: Documentation-only; no evidence acquisition or remediation
Current state: `S3 — Root Cause Partial`

| Potential owner | Supporting evidence needed | Current evidence | Missing evidence | Status |
|---|---|---|---|---|
| Provider/storage layer | Provider latency, IOPS, queue, volume/node health and maintenance timeline | Guest device saturation and latency | Provider-side telemetry and ownership confirmation | OPEN |
| Host/kernel layer | Kernel, block-device and filesystem correlation across incident window | High iowait/PSI and device utilization | Complete host timeline and owner attribution | PARTIAL |
| Runtime/workload layer | Process/container I/O correlation and runtime snapshots | Containers healthy during samples | Workload-to-device attribution | OPEN |
| Application layer | Request/log correlation with I/O spikes | API remained available | Evidence tying application behavior to storage pressure | OPEN |

## S4 transition criteria

Move from `S3` to `S4 — Ownership Identified` only when at least one condition is evidenced:

- provider confirms a storage-side issue;
- host/runtime evidence attributes the source to a workload;
- application evidence proves the I/O source.

Until then, remediation remains unauthorized and the investigation stays at S3.

Production mutation: NONE
