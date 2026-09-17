# BATCH116 — Storage Investigation Next Action Decision Matrix

Date: 2026-09-17
Mode: Documentation-only; no remediation or acquisition
Current state: `S3 — Root Cause Partial`

| Path | Trigger | Required evidence | Expected outcome | Blocked conditions |
|---|---|---|---|---|
| A — Obtain ownership evidence | Provider or runtime evidence can be requested under a later authorization | Provider telemetry or workload attribution | Transition S3 → S4 | Missing owner evidence |
| B — Continue bounded observation | No new external evidence available | Repeat read-only snapshots with bounded commands | Improve confidence and detect recurrence | Storage pressure persists without attribution |
| C — Prepare remediation design | Ownership and cause are sufficiently established | Evidence-backed design and risk review | Candidate plan for S4 → S5 | Execution remains prohibited; no authorization |

## Current recommendation boundary

Paths **A** and **B** are allowed as future decisions. Path **C** may be documented only; remediation execution, provider submission, evidence acquisition, restart/reboot, Docker operation, cleanup, tuning, migration, and DB/config/deploy/env changes remain blocked.

## Transition rules

- S3 → S4 requires ownership evidence.
- S4 → S5 requires an approved remediation plan.
- S5 → S6 requires verification evidence.

Production mutation: NONE
