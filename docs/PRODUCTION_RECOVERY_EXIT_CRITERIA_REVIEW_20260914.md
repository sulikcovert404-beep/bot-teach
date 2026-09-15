# Production Recovery Exit Criteria Review — 2026-09-14

## Scope
Read-only definition and review of the conditions required to close the production recovery Safe Hold. No SSH, Docker, database, migration, environment, or deployment action was performed.

## Current Incident State

```text
Migration: 20260912_0021 (recorded complete)
Database: 20260912_0021 (recorded healthy)
Evidence archive: complete and indexed
API runtime: restoration pending
SSH access: authentication blocked
Recovery: SAFE HOLD
Production mutation: NONE
```

## Exit Criteria

Safe Hold may close only after all conditions below are independently evidenced on the target server:

- [ ] SSH authentication succeeds for the authorized operator
- [ ] `sudo` access is verified
- [ ] Docker commands complete without host/storage instability
- [ ] Canonical `staging-api-1` is restored
- [ ] Runtime image digest matches the approved artifact
- [ ] Local `/health` returns HTTP 200
- [ ] Local `/health/ready` returns HTTP 200
- [ ] Public health and readiness endpoints return HTTP 200
- [ ] Database and Redis health are stable
- [ ] Migration head is exactly `20260912_0021`
- [ ] Required Telegram and dashboard smoke checks pass
- [ ] No unexpected 5xx, restart loop, OOM, D-state, or storage degradation is observed

## Non-Exit Conditions

Do not close recovery while any of the following remains true:

- API runtime is unavailable or readiness fails
- SSH authentication or remote execution is unavailable
- Docker lifecycle safety is unverified
- Migration or image provenance is inconsistent
- A rollback-safety or storage incident is active

## Ownership Boundary

```text
Owner/Provider:
- restore authorized SSH access
- address host/storage instability

Operator:
- restore canonical API runtime after access is available
- verify image, health, readiness, and smoke evidence
```

## Resume Sequence

```text
SSH auth PASS
→ sudo PASS
→ Docker health check
→ restore staging-api-1
→ verify image digest
→ /health
→ /health/ready
→ smoke validation
→ close Safe Hold only if every criterion passes
```

## Hard Boundaries for This Review

```text
NO SSH modification
NO Docker operation
NO API recreate
NO database action
NO migration action
NO environment change
NO Cloudflare or webhook change
```

## Verdict

`RECOVERY EXIT CRITERIA = DEFINED`

`SAFE HOLD = REMAINS ACTIVE` because SSH authentication and live API restoration are still blocked. This document does not authorize or perform a recovery mutation.
