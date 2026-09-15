# Operations Documentation Hardening Result

Status: PASS  
Mode: Documentation / read-only / non-production  
Production mutation: NONE

## Canonical runbook

**Primary host:** `95.135.208.167` (`srv20708.deluxhost.net`)  
**Compose file:** `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`  
**Canonical API container:** `staging-api-1`  
**Canonical DB target:** `20260912_0020`  
**Environment file:** `/etc/apps/ai-teacher/staging.env` (values are never printed)

### Startup and health sequence

Use the existing canonical container and inspect its state before any action. If a recovery gate explicitly authorizes a start, use `docker start staging-api-1`; do not rebuild or recreate. Verify, in order:

1. API container is `running` and `healthy`.
2. PostgreSQL and Redis are `healthy`.
3. Local `/health` and `/health/ready` return 200.
4. Public `/health` and `/health/ready` return 200 and readiness reports `20260912_0020`.
5. Confirm dashboard and Mini App routes respond.

### Rollback sequence

Rollback is emergency-only and requires a Commander gate. Preserve the new host, old host (`107.173.47.76`), old tunnel, backups, and `mentor-bot`. Revert traffic first, then restore a verified backup to an isolated database or follow the approved restore procedure. Validate health/readiness and the explicit target revision after each step. Never improvise a migration downgrade on live data.

### Forbidden actions during a read-only stability or documentation gate

No deploy, build, pull, restart, reboot, `compose down/up`, env or credential edit, database mutation, migration, volume change, prune, Cloudflare route change, webhook change, old-host deletion, or `mentor-bot` change.

**Migration invariant:** never use `alembic upgrade head` or `alembic stamp` for production. Any future migration must target an explicit revision after disposable rehearsal and approval.

## Incident timeline (sanitized)

| Event | Finding / resolution | Production impact |
|---|---|---|
| Storage/I/O incident | D-state/journal stall history identified; later PSI samples showed residual pressure without active failure. | No mutation; monitoring and provider ticket remain open. |
| Wrong Compose invocation | Compose was run outside the project directory and could not find configuration. | No production change. |
| API-only recovery | Canonical runtime was qualified with provenance checks; health/readiness remained stable. | No unauthorized recovery action. |
| Auth hardening | Isolated release qualified and deployed under an approved gate. | Regression remained green. |
| Observability hardening | Metrics and health instrumentation qualified and deployed under an approved gate. | No schema or credential change. |
| Telegram webhook investigation | Delivery correlation and 502/401 evidence collected read-only. | Webhook/Cloudflare unchanged. |

## Operational decision log

- **Decision:** no migration beyond `20260912_0020`. **Owner:** Commander. **Status:** active.
- **Decision:** Storage/I/O incident remains `DEGRADED → MONITOR MODE`; recovery is `NO-GO`. **Status:** active.
- **Decision:** Credential rotation waits for owner provisioning; no secret values are recorded here. **Status:** pending.
- **Decision:** Secure Role Preview and Exam migration `0021` remain on hold. **Status:** pending future gates.
- **Boundary:** `mentor-bot` is independent and must not be touched.

## Current risk register

| Risk | Status | Owner action |
|---|---|---|
| Storage recurrence | Monitoring | Continue lightweight health watch and provider follow-up. Stop and report on D-state, filesystem error, Docker hang, health failure, or sustained PSI spike. |
| Credential exposure/rotation | Pending | Owner provisions replacement; then use the approved controlled rotation gate. |
| Auth regression | Closed | Monitor; reopen only on a verified bug. |
| Exam migration 0021 | Hold | Run a separate approved qualification gate. |
| Secure Role Preview Phase B | Hold | Resume after Stability decision. |

## Verification evidence

The companion read-only report is [`STORAGE_IO_INCIDENT_INVESTIGATION_20260914.md`](STORAGE_IO_INCIDENT_INVESTIGATION_20260914.md). It records three PSI samples, zero D-state, no recent kernel errors, healthy containers, and local/public health 200 responses. No secrets, tokens, credentials, or private data are included.

## Commander decision required

No decision is required to keep the current monitor mode. A new decision is required before any recovery, migration, credential rotation, route change, or feature gate is opened.
