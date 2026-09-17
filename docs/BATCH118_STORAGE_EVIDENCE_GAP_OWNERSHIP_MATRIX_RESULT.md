# BATCH118 — Storage Evidence Gap Ownership Assignment Matrix

Date: 2026-09-17  
Mode: Documentation-only; no acquisition or remediation

| Gap | Evidence required | Expected owner | Current status | Next valid transition |
|---|---|---|---|---|
| Provider telemetry | Storage backend metrics, node/device attribution | Provider/storage infrastructure | Missing | S3 → S4 when ownership is evidenced |
| Historical storage metrics | Host volume history and saturation timeline | Provider + host operations | Missing/partial | Supports cause and ownership |
| Kernel/storage details | Kernel journal, device latency, filesystem signals | Host/runtime operations | Partial | Correlate workload or provider layer |
| Workload I/O attribution | Per-process/container I/O source | Host/runtime/application operations | Missing | Establish cause/owner |
| SSH observability | Repeatable read-only collection access | Server owner/operations | Available but bounded | Evidence collection only under authorization |

## Responsibility boundary

- **Provider:** storage infrastructure and platform telemetry.
- **Host/runtime:** kernel, filesystem, Docker and workload evidence.
- **Application:** application-level I/O correlation only; it cannot establish provider ownership alone.

## State transition

```text
Current: S3 — Root Cause Partial
Required: S4 — Ownership Identified
Gate: ownership evidence must be attributable and reviewable
```

Until S4, remediation remains unauthorized. Paths A (obtain ownership evidence) and B (bounded observation) are decision options; path C is documentation-only. No evidence acquisition, provider submission, remediation, restart/reboot, Docker operation, cleanup, tuning, migration, or DB/config/deploy/env change occurred.

Production mutation: NONE
