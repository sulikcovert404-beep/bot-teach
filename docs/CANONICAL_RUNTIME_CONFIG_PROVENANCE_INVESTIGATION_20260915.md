# Canonical Runtime Config Provenance Investigation

Date: 2026-09-15  
Mode: Read-only investigation

## Sources Checked

### Repository

- Git history, branches, tags, release references, `app/core/config.py`, `.env.example`, Compose files, deploy scripts, CI references, and secret-manager documentation.
- The repository contains development templates and configuration contracts only; no approved production secret source or generator is present.

### Release artifacts

- Release directories, manifests, image metadata, and deployment descriptors on `95.135.208.167` were inventoried by name/metadata.
- No release artifact identifies an authoritative generator or secret-manager object for the runtime environment.

### Host metadata

- Host: `95.135.208.167` (`srv20708.deluxhost.net`).
- Canonical Compose file exists at `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`.
- Docker/Compose metadata and the documented deployment contract reference `/etc/apps/ai-teacher/staging.env`.
- The expected file is absent; `staging-api-1` is absent. PostgreSQL/Redis artifacts remain present.
- No approved systemd unit, provisioning script, or runtime-config generator for this application was found.

### Infrastructure ownership trace

- No repository, release, host, or provider automation reference links the expected path to a secret manager or owner-controlled provisioning workflow.
- `.env.example` and local `.env` conventions are development scaffolding and are not authoritative production sources.

## Findings

| Item | Result |
|---|---|
| Canonical runtime path | `/etc/apps/ai-teacher/staging.env` (expected by Compose metadata) |
| Official config source | **NOT FOUND** |
| Generator/provisioning script | **NOT FOUND** |
| Secret manager reference | **NOT FOUND** |
| Host file present | **NO** |
| Safe substitute | **NO** |
| Secret values read or emitted | **NO** |

## Compatibility Evidence

- Repository and host metadata do not prove that any available image can start with an approved configuration.
- Runtime/image/database compatibility for recovery or rollback is therefore **UNKNOWN**.
- No rollback, deploy, restart, restore, migration, env edit, Cloudflare/Webhook change, or production mutation was performed.

## Decision

**STOP + REPORT.** The canonical configuration source and owner are unresolved. Obtain or restore `/etc/apps/ai-teacher/staging.env` through an approved secure owner/provider channel, preserving permissions and without sharing secret values. Only after provenance is verified may a separate config-validation and API-restoration gate be considered. Blind rollback is rejected.

## Production Impact

`NONE` — read-only inspection only.
