# Gate 093 — Storage Evidence Gap Collection Plan

Date: 2026-09-17
Target: `95.135.208.167`
Mode: Documentation-only; proposal without execution

## Gap-to-evidence mapping

| Missing evidence | Required observation/package | Expected owner |
|---|---|---|
| Provider storage metrics | Node/volume latency, IOPS, throttle and incident history aligned to Gate 038/044/090 timestamps | Infrastructure/provider layer |
| Host block-device history | Continuous synchronized `iostat`/block statistics and filesystem mount context over a bounded window | Host/operator layer |
| Kernel storage details | Kernel journal/block/filesystem errors with timestamps and D-state correlation | Host/operator layer |
| Workload attribution | Per-process/container read/write rates, I/O wait and request correlation during pressure | Host/runtime layer |
| SSH observability | Reliable root/console or equivalent post-auth command execution during the observation window | Host/operator/provider |
| Application impact | Independent health/readiness and dependency samples with numeric HTTP status | Application/operator layer |

## Access boundary

Available: application health and partial host observations through authenticated `codex` sessions. Unavailable: provider telemetry, complete historical device metrics, and consistently reliable post-auth SSH observability. No secret, credential, or private data is required in the evidence package.

## Safe next steps (proposal only)

1. Request provider ticket evidence and node/volume metrics for the exact incident windows.
2. Arrange root/console observability and capture synchronized, bounded host samples.
3. If authorized separately, collect workload-level I/O attribution without changing runtime configuration.
4. Reconcile evidence against Gates 038, 044, 089 and 090, then update the ownership and closure matrix.

## Decision rule

- Provider evidence confirms infrastructure fault → provider remediation gate.
- Workload evidence identifies application pressure → application/storage optimization review.
- Evidence remains insufficient → keep investigation `OPEN`.

This plan authorizes none of those actions. It explicitly forbids restart/reboot, storage tuning, Docker changes, cleanup, migration, DB changes, deploy, provider action and configuration changes.

STATUS: Completed
Completed: Mapped every known storage evidence gap to a required observation, owner and safe proposal
Blocked: Evidence acquisition requires external provider/root-console access and separate authorization
Next Recommended Task: Obtain provider telemetry package and reliable host observability
Commander Decision Required: Yes — choose evidence acquisition path
