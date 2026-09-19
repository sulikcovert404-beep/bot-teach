# Gate 168 — New Server Preparation Plan

**Mode:** Plan only; no execution
**Target:** `92.118.190.101` (`hamicard`)
**Verdict:** `READY_FOR_CONTROLLED_PREPARATION`
**Mutation performed:** None

This plan is based on the Gate 165 inventory and Gate 167 readiness checklist. The target is a clean shared host; all actions below require a separate, explicit preparation gate.

## 1. System packages

| Package | Decision | Rationale / boundary |
|---|---|---|
| Docker Engine | REQUIRED | The canonical application is Compose-based. Install from the approved Ubuntu/Docker source only after package-source and reboot policy review. |
| Docker Compose plugin | REQUIRED | Required for the pinned Compose workflow; use the plugin, not an unpinned standalone binary. |
| PostgreSQL client | REQUIRED | Needed for read-only health/backup verification and restore rehearsal; database server remains project-local or separately approved. |
| Redis CLI | REQUIRED | Read-only connectivity/health checks; Redis server remains internal to the project stack. |
| Nginx | OPTIONAL | Only if the approved edge design places a host reverse proxy on this server. Do not install by default. |
| Node.js/npm | NOT_REQUIRED for initial API stack | The image builds and serves the current web assets without a host Node runtime. Re-evaluate only if a separately approved frontend build workflow requires it. |
| Python 3.12 | AVAILABLE | Already present; application runtime remains container-pinned rather than host Python. |

## 2. Project isolation

Use the following project-local layout:

```text
/opt/apps/
  ai-teacher/
    releases/<immutable-id>/
    deploy/
    runtime/
    backups/
    shared/
  <other-project>/...
/etc/apps/
  ai-teacher/
  <other-project>/...
```

Create one dedicated service account and group per project (names to be approved), with project-owned paths and no shared write permission. Compose uses a unique project name such as `ai-teacher-staging`; no global container names, host network, privileged mode, or Docker socket bind. Each project receives unique volume names, network names, container labels, and internal service names.

Expected permissions are owner read/write on deploy/runtime where needed, group read-only for controlled operators, and no access to another project's trees. Secrets are never stored in the repository, image, labels, or command arguments.

## 3. Secrets boundary

Use an approved secret manager if available; otherwise a root-controlled environment file under `/etc/apps/ai-teacher/` with mode `0600`, owned by root and readable only by the intended service account. Keep database owner, application runtime, Telegram, and AI-provider credentials separate. Exclude the file and `/opt/apps/ai-teacher/backups/` from Git and Docker build context. Secret provisioning must be a separate gate; this plan reads and transfers no secret.

## 4. Edge/DNS design

Keep the application API private to the project network. If Cloudflare Tunnel remains the edge, route the approved hostname to the API's explicit local port through the designated tunnel connector. If Nginx is approved, terminate TLS and proxy only to the project-local API port; do not expose PostgreSQL or Redis. DNS, Cloudflare, webhook, TLS, and firewall changes are outside this plan and require an explicit edge gate.

## 5. Database and migration approach

Qualify a disposable Compose stack first, using the pinned release and explicit Alembic revision. Verify schema, backup/restore, downgrade/re-upgrade rehearsal, and readiness before any live transfer. The migration service uses the owner credential; the API uses `app_runtime` with least privilege. Never run `alembic upgrade head`. Live restore or migration requires a separate approval and a verified rollback path.

## 6. Disposable rehearsal sequence

1. Build or obtain the immutable release artifact in a disposable environment.
2. Validate image digest and scan the artifact for secrets.
3. Start an isolated Compose project with non-production volumes.
4. Run the explicit migration revision and verify readiness.
5. Exercise API, PostgreSQL, Redis, backup, and rollback procedures.
6. Tear down only the disposable environment and archive evidence.

No step above was executed during Gate 168.

## 7. First mutation gate prerequisites

Before any target-host mutation, require explicit approval covering package source/install, service account and directory creation, Docker daemon policy, secret provisioning, backup destination, firewall/ports, edge/DNS, and a maintenance/rollback window. Preserve the current clean host inventory as the baseline.

## Verdict

`READY_FOR_CONTROLLED_PREPARATION`

Gate 168 is a planning artifact only. No package, user, directory, Docker, DNS, firewall, SSH, database, secret, or application state changed.
