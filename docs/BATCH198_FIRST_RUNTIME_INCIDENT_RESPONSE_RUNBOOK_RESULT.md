# BATCH198 — First Runtime Observability & Incident Response Runbook

**Gate:** 198 — First Runtime Observability & Incident Response Runbook
**Mode:** Design-only / no runtime execution
**Date:** 2026-09-19
**Environment:** New server `92.118.190.101` (hamicard)
**Production impact:** NONE

## Verdict

`INCIDENT_RESPONSE_READY`

This document defines the evidence-first procedure for the first controlled runtime start. It does not start services, read secrets, create environment files, connect to databases, run migrations, change edge routing, or install monitoring.

## First-start observation checklist

1. Record UTC timestamp, operator, release path, release commit, compose file path, and Gate authorization.
2. Verify container state and restart count using metadata only.
3. Validate local health and readiness endpoints after an authorized start.
4. Check PostgreSQL and Redis container health and dependency failure indicators.
5. Observe CPU, memory, disk, inode, I/O pressure, and OOM indicators.
6. Review logs in this order: API startup, migration result (if separately authorized), PostgreSQL, Redis, then reverse proxy/edge.
7. Capture exit codes, timestamps, and bounded log tails without environment values.
8. Stop observation and escalate if any stop trigger below occurs.

## Incident categories and evidence

| Category | Indicators | Required evidence |
|---|---|---|
| Startup failure | container exits, restart loop, non-zero process status | container status, exit code, bounded logs |
| Configuration failure | missing variable, interpolation error, permission error | redacted validation output, file metadata only |
| Database failure | unhealthy DB, refused connection, schema mismatch | health metadata, bounded error logs, explicit revision output |
| Cache failure | Redis unhealthy or connection errors | health metadata and bounded logs |
| Migration failure | migration command failure or uncertain revision | command result, revision, no automatic retry |
| External provider failure | provider timeout/auth/quota error | redacted category/status; never credentials |
| Host/storage incident | D-state, I/O pressure, filesystem/kernel errors | `vmstat`, PSI, filesystem and kernel evidence |

## Stop and rollback triggers

Stop the first-start procedure immediately on:

- missing or invalid environment configuration;
- failed `/health` or `/health/ready`;
- port collision or unexpected public exposure;
- database/Redis unhealthy state;
- migration uncertainty, drift, or unapproved schema change;
- secret validation failure or suspected leakage;
- restart loop, OOM, D-state, filesystem hang, or material I/O degradation;
- evidence that a sibling project could be affected.

Do not retry blindly. Rollback is allowed only after the Commander authorizes it, the rollback target and compatibility are identified, and the incident evidence is preserved. No rollback is authorized by this runbook alone.

## Evidence collection policy

- Record UTC timestamps and exact commands executed.
- Capture only bounded, redacted output.
- Never print, copy, upload, or store secret values, tokens, passwords, or complete environment files.
- Keep evidence in the project documentation tree; do not place secrets in Git, Docker history, logs, or reports.
- Preserve container IDs, image digests, exit codes, health results, and migration revision strings when non-sensitive.
- If a command could expose secrets, do not run it; use metadata or redacted alternatives.

## Multi-project safety

- Scope every command to the AI Teacher release and compose project.
- Do not use global cleanup, prune, broad restart, or host-wide configuration changes.
- Do not touch `mentor-bot` or sibling projects.
- Keep Docker networks, volumes, users, and backups project-scoped.
- Escalate any ambiguous ownership or cross-project reference before proceeding.

## Authorization boundary

This runbook is preparatory. A separate Commander gate is required for controlled first runtime start, database migration, edge exposure, recovery, or rollback. The canonical environment file remains owner-provisioned at `/etc/apps/ai-teacher/staging.env` with `root:root` ownership and mode `0600`.

## Current known blocker

At authoring time the canonical environment file is absent. Runtime remains blocked until the owner provisions it securely and Gate 197 redacted validation passes.
