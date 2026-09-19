# Gate 167 — New Server Migration Readiness Checklist

**Mode:** Read-only qualification
**Target:** `antigravity@92.118.190.101` (`hamicard`)
**Result:** `MIGRATION_BLOCKED`
**Mutations:** None

## Evidence

The target remains a clean Ubuntu 24.04.5 host. Python 3.12.3 is present. Docker, Docker Compose, PostgreSQL client, Redis CLI, Nginx, Node, and npm are not installed or discoverable. `/opt/apps`, `/opt/apps/ai-teacher`, `/etc/apps`, and `/var/www` are absent; `/opt` and `/srv` exist but are empty. Only SSH (22), local DNS, and the pre-existing loopback 6011 listener are present. No application, database, Redis, or HTTP listener was found. Existing users are `myjafar` and `antigravity`; no project service account or `docker` group was found.

DNS read-only observation from the workstation resolves `bot.codeshow.ir` through Cloudflare to `104.21.82.137` and `172.67.202.125`; no DNS change was attempted.

## Checklist

| Requirement | Status | Evidence / decision |
|---|---|---|
| Required system packages | **MISSING** | Docker/Compose, PostgreSQL client, Redis CLI, Nginx, Node/npm absent; Python 3.12.3 available. Installation requires a separate approved preparation gate. |
| Required runtime versions | **PARTIAL** | Python 3.12.3 matches the application family; Docker runtime is unavailable. |
| Required directories | **MISSING** | `/opt/apps/ai-teacher` and `/etc/apps` do not exist. Creation requires mutation approval. |
| Required users/service accounts | **MISSING** | No dedicated application service account or Docker group. Existing SSH users were not changed. |
| Required ports | **AVAILABLE (design)** | No 8000/80/443/5432/6379 listener; ports are unallocated, but firewall/public binding requires approval. |
| Required DNS/domain changes | **REQUIRES_APPROVAL** | `bot.codeshow.ir` is currently Cloudflare-fronted; no DNS or tunnel change made. |
| Required secrets transfer method | **REQUIRES_APPROVAL** | No secret was read or transferred. Use an approved secret manager or a root-controlled 0600 runtime file in a later gate. |
| Database migration strategy | **REQUIRES_APPROVAL** | Use disposable qualification, explicit pinned Alembic revision, verified backup/restore, then explicit upgrade; never `alembic upgrade head`. |
| Rollback strategy | **AVAILABLE (design)** | Immutable release directory plus preserved old production/backup and explicit traffic switch; rehearsal required before cutover. |
| Coexistence with other projects | **AVAILABLE (design)** | Separate `/opt/apps/<project>` trees, Compose project names, networks, volumes, service accounts, and internal-only DB/Redis. |

## Required next approvals

1. Approve host preparation (system packages, Docker/Compose, dedicated account, directories, log rotation, and resource policy).
2. Approve secret provisioning method and exact non-printing path/manager.
3. Approve public edge/DNS and port allocation plan.
4. Approve disposable migration/restore rehearsal before any live data transfer.

## Safety boundaries honored

No `apt` action, Docker installation, Compose operation, repository clone, file transfer, DNS/Cloudflare change, firewall or SSH change, database restore, migration, or service restart was performed.

## Verdict

`MIGRATION_BLOCKED` — the host is clean and suitable for planning, but controlled migration cannot begin until the listed preparation and ownership approvals are issued.
