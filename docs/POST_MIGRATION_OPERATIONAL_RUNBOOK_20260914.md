# POST MIGRATION OPERATIONAL RUNBOOK

Date: 2026-09-14
Scope: Controlled recovery procedure and evidence requirements
Authority: Commander gate required before every production mutation

## Current status

```text
Migration 0021: COMPLETE / reported
Security evidence: ARCHIVED
Docker/Host recovery: HOLD
API lifecycle recovery: HOLD
Production mutation in this runbook: NONE
```

This document is a runbook. It does not itself authorize a restart, container lifecycle operation, migration, environment edit, database change, Cloudflare change, webhook change, or deployment.

## Recovery sequence

Run in this order only after the corresponding gate is explicitly open:

```text
Host stability PASS
        ↓
Docker daemon and socket stable
        ↓
API container lifecycle recovery
        ↓
/health verification
        ↓
/health/ready verification
        ↓
DB/Redis and migration verification
        ↓
role, tenant, and exam smoke validation
        ↓
monitoring window
        ↓
Commander close or rollback decision
```

Any failed prerequisite stops the sequence. Do not skip ahead or infer PASS from an earlier report.

## API recovery procedure

Preflight, read-only:

- Confirm canonical host, Compose project, service name, image provenance, and approved environment source without printing values.
- Confirm target container is exactly `staging-api-1`.
- Confirm expected image digest is `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`.
- Confirm database target is `20260912_0021`.
- Confirm PostgreSQL and Redis are healthy and must remain untouched.

Only if the recovery gate explicitly authorizes the action, execute the narrow API-only lifecycle command specified by the Commander. Do not build, pull, recreate unrelated services, change volumes, or use `alembic upgrade head`.

If Docker hangs, the socket times out, D-state returns, or I/O pressure recurs, stop immediately and report `STORAGE/DOCKER RECURRENCE`.

## Validation matrix

| Area | Expected evidence |
|---|---|
| `/health` | HTTP 200 |
| `/health/ready` | HTTP 200 and exact head `20260912_0021` |
| Alembic | current/head exactly `20260912_0021`, single head |
| PostgreSQL | healthy; no restart or mutation |
| Redis | healthy; no restart or mutation |
| Runtime role | `NOSUPERUSER`, `NOBYPASSRLS`, least privilege |
| Tenant isolation | cross-tenant reads/writes denied |
| Classroom/grade isolation | out-of-scope candidates excluded before ranking/query |
| Exam smoke | authorized student flow passes |
| Negative authorization | unassigned, wrong class, other tenant/student, time-window, legacy-ID bypass denied |
| Teacher scope | assigned classes and own tenant only |
| Admin scope | own school/tenant policy preserved |
| Monitoring | no unexpected 5xx, OOM, restart loop, DB/Redis errors, or migration drift |

## Rollback and escalation criteria

### Application recovery only

Use only when the host and Docker are healthy, the database and Redis are healthy, and the failure is isolated to the API container lifecycle or stale runtime configuration already approved by the Commander.

### Rollback/restore review

Escalate for an explicit rollback decision when any of these occur:

- migration head or schema mismatch;
- readiness or health failure after the authorized recovery;
- RLS, resolver, privilege, or tenant authorization failure;
- cross-tenant or cross-role leakage;
- exam smoke or data-integrity failure;
- backup/hash or restore-list verification failure.

Preserve the original database and backups. Do not downgrade, stamp, delete historical rows, or alter production state without a separate gate.

### Host/storage escalation

Stop all lifecycle operations and escalate when:

- Docker socket or daemon is unresponsive in repeated bounded probes;
- I/O PSI remains severe or worsens;
- D-state, blocked tasks, filesystem errors, or kernel storage warnings recur;
- disk/inode pressure or latency becomes abnormal.

Do not reboot or restart Docker as an improvised recovery.

## Incident timeline

```text
Migration 0021 applied successfully
        ↓
Readiness failure traced to stale EXPECTED_MIGRATION_HEAD
        ↓
Environment expectation corrected in controlled scope
        ↓
API-only lifecycle attempt met Docker daemon / host I/O stall
        ↓
Recovery gate closed; no rollback or extra mutation
        ↓
Security evidence archive completed
        ↓
Runbook finalized; recovery remains HOLD
```

## Required final report

Use the following fields after an authorized recovery attempt:

```text
POST MIGRATION OPERATIONAL RECOVERY

Host/Docker stability: PASS/FAIL
Canonical API container: RUNNING/OTHER
Image digest: MATCH/MISMATCH
/health: 200/OTHER
/health/ready: 200/OTHER
Alembic current/head: 20260912_0021/OTHER
PostgreSQL: HEALTHY/OTHER
Redis: HEALTHY/OTHER
Tenant/RLS checks: PASS/FAIL
Exam smoke: PASS/FAIL
Unexpected 5xx/restarts/OOM: NONE/PRESENT
Rollback trigger: NONE/<reason>
Production mutation: NONE/<authorized action>
Commander close decision: REQUIRED
```

## Hard boundaries

- Never use `alembic upgrade head`.
- Never touch `mentor-bot`.
- Never change Cloudflare, webhook, credentials, or old production as part of this runbook.
- Never declare PASS without current evidence from the actual target runtime.
