# Recovery Operator Action Sheet — 2026-09-14

## Purpose
Short, read-only handoff for the operator after authorized SSH access returns. This sheet does not authorize recovery by itself.

## Current State Snapshot

```text
Target: 95.135.208.167 (srv20708.deluxhost.net)
Database/migration: 20260912_0021 (recorded complete)
Approved runtime: staging-api-1
Approved image: last-known-good digest recorded in the handoff archive
Recovery: SAFE HOLD
SSH: authentication blocked
Production mutation: NONE
```

## First Actions After Access Restore

1. Verify SSH identity and target host.
2. Verify `sudo` without changing configuration.
3. Verify Docker responsiveness and host stability.
4. Inspect canonical Compose state.
5. Restore only `staging-api-1` using the explicitly approved recovery command.
6. Verify the running image digest against the approved evidence.
7. Check local and public health/readiness endpoints.
8. Run the authorized smoke validation and record evidence.

## Success Criteria

```text
staging-api-1 = RUNNING
/health = 200
/health/ready = 200
migration_head = 20260912_0021
PostgreSQL = healthy
Redis = healthy
No unexpected 5xx, restart loop, OOM, D-state, or I/O degradation
```

## Abort Conditions

Stop and report if any of these occur:

- Docker command timeout or host/storage stall
- unexpected image or digest mismatch
- database or migration mismatch
- readiness failure
- permission or identity mismatch
- any request for migration, environment edit, rebuild, or unrelated service change

## Protected Boundaries

Do not touch PostgreSQL, Redis, volumes, migration state, credentials, Cloudflare, webhook, old production, or unrelated services during the first recovery pass. Do not use `alembic upgrade head`.

## Evidence to Capture

Record command outcomes, timestamps, HTTP status codes, container state, image digest, migration head, and anomaly details. Never record secrets, tokens, passwords, or environment values.

## Current Verdict

`OPERATOR ACTION SHEET = READY FOR FUTURE ACCESS RESTORATION`

Execution remains blocked until SSH authentication is restored and the Commander authorizes the recovery sequence.
