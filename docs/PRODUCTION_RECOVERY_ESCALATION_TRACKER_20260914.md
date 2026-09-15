# Production Recovery Escalation Tracker — 2026-09-14

## Active incidents

| ID | Issue | Severity | Owner | Status |
|---|---|---|---|---|
| RUNTIME-CONFIG-001 | Missing canonical runtime configuration | HIGH | Owner/Provider | OPEN |
| HOST-IO-002 | Host I/O degradation | HIGH | Provider | OPEN |

## Current impact

- API runtime restoration blocked.
- Database revision `20260912_0021` preserved.
- Migration complete.
- Rollback rejected pending compatibility and configuration evidence.

## Required external actions

1. Restore or formally identify the canonical runtime configuration.
2. Investigate node/storage I/O degradation, including latency, throttling, and filesystem stalls.

## Resume conditions

- HOST-IO-002 resolved.
- Canonical config source verified.
- API Runtime Restoration Gate reopened by Commander.

## Prohibited until resolution

API recreation, Docker restart, host reboot, environment creation, database/migration change, and rollback.

Production remains in Safe Hold. No secrets, credentials, or private data are recorded here.
