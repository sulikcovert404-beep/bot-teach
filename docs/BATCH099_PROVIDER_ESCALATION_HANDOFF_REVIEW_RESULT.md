# Gate 099 — Provider Escalation Handoff Package Review

Date: 2026-09-17
Target: `95.135.208.167` (`srv20708.deluxhost.net`)
Mode: Documentation-only sanitized review; no provider submission or server action.

## Sanitization review

- Secrets: none.
- Credentials: none.
- Internal tokens: none.
- Private user data: none.
- Evidence references: intact and limited to repository reports.
- Timestamps: consistent with the referenced Gate reports (2026-09-17).

## Incident summary

Repeated synchronized observations show `RECURRING_STORAGE_SATURATION`: very high I/O PSI/full pressure, elevated iowait, blocked processes, and multi-second `vda` write latency. Latest Gate 095 observed healthy filesystem capacity/memory and running healthy containers with local health/readiness HTTP 200; these application signals do not close storage instability.

## Observed metrics

- Gate 038: PSI some 99.99%, full 94.31%, iowait ~95.9%, write await ~57,770 ms.
- Gate 044: PSI/full above 85%, iowait ~96.5–96.8%, write await ~3,748 ms.
- Gate 090: PSI some avg60 96.37%, full avg60 91.98%, iowait 96.02%, write await ~3,882 ms.
- Gate 095: PSI some avg60 95.16%, full avg60 88.75%, iowait samples 17/40/49%, write await ~3,914.65 ms, one blocked process.

## Impact boundary

Application availability was observed during samples; no container restart loop, OOM, filesystem capacity pressure, or memory pressure was observed in Gate 095. Root-cause ownership remains unresolved because provider telemetry, complete historical block-device metrics, and workload attribution are unavailable.

## Requested provider evidence

Please provide storage latency, IOPS, queue depth/throttling, volume and node health, maintenance/migration events, hypervisor I/O saturation indicators, kernel/storage incident telemetry, and confirmation of any VPS impact for the synchronized observation windows.

## Exact unanswered questions

1. Was the VPS volume or host node throttled or saturated during the recorded windows?
2. Were there maintenance, migration, degraded-volume, or neighboring-workload events?
3. What were latency, queue depth, IOPS, and error/reset metrics at the volume and node layers?
4. Can provider timestamps be correlated with the Gate 038/044/090/095 samples?
5. What remediation or monitoring evidence can the provider supply?

## Boundary and status

This package is ready for owner/provider review only. It has not been sent externally. No server, Docker, database, migration, configuration, secret, Cloudflare, webhook, or provider change occurred.

STATUS: Completed
Completed: Reviewed and sanitized the provider escalation handoff package.
Blocked: External telemetry and root-cause attribution remain unavailable.
Next Recommended Task: Commander authorization for external submission of this package.
Commander Decision Required: Yes — approve or reject provider submission.

## Commit

HOLD pending Commander review.
