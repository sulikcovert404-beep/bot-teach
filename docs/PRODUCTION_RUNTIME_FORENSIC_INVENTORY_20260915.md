# Production Runtime Forensic Inventory — 2026-09-15

## Scope

Read-only inventory of `95.135.208.167` (`srv20708.deluxhost.net`) to locate canonical runtime configuration. No restart, Docker lifecycle action, deploy, rollback, migration, environment edit, secret read/copy/export, Cloudflare change, or webhook change was performed.

## Sources checked

- Host identity and filesystem listings for `/etc/apps`, `/opt/apps`, and `/etc`/`/opt` provenance paths.
- Limited `find` searches (directory depth 4; deployment/compose/service filenames depth 5).
- `docker ps -a`, `docker compose ls`, and metadata-only `docker inspect` for existing containers.
- systemd unit inventory, cron references, and bounded text references to the canonical env path.

## Host and paths found

- Host: `srv20708.deluxhost.net`; SSH user: `codex`.
- `/etc/apps/ai-teacher` exists, owned by `root:root`, mode `0750`; listing its contents and stat of `staging.env` returned **Permission denied** for `codex`.
- `/opt/apps/ai-teacher` exists and contains the application tree and deployment assets.
- `/opt/apps/ai-teacher-staging-rc` exists and contains a separate RC tree.
- `/opt/data/ai-teacher` exists (data path observed by bounded directory search).
- No other `ai-teacher` directory was found under `/etc` or `/opt` within the requested depth.

## Docker evidence (metadata only)

- Compose project `staging` is running with config `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`.
- Running containers observed: `staging-postgres-1` and `staging-redis-1`; no `staging-api-1` container is present in `docker ps -a`.
- Compose labels on both running containers reference environment file `/etc/apps/ai-teacher/staging.env` and the canonical compose file.
- `cutoverclone-db-1` and `cutoverclone-redis-1` are exited and reference the RC project `.env`; they were not touched.
- No container environment values were read. Mounts/labels only were inspected.

## Compose and provenance references

Both `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml` and the RC compose file reference `/etc/apps/ai-teacher/staging.env` three times through `env_file`. No alternate runtime env source was found in the bounded search.

No matching systemd unit or cron entry was found. Bounded reference search found project documentation and compose files, plus provisioning-related scripts under `/opt/apps/ai-teacher`; these are repository artifacts, not evidence of an active generator or secret manager.

## Canonical configuration status

**NOT FOUND / NOT VERIFIABLE by current account.** The canonical directory exists but is root-only and `staging.env` cannot be listed or stat'ed by `codex`. Docker metadata proves the path is the declared source, but does not prove that the file exists or that an active provisioning process owns it. No generator, bootstrap service, CI agent, or secret-manager reference was established on-host.

## Generator/provisioning status

No active systemd/cron generator was identified. Repository scripts with provisioning names exist under `/opt/apps/ai-teacher`, but no running ownership or invocation evidence was found.

## Secret manager reference status

No secret-manager or external credential-provider reference was found in the bounded, secret-safe search. No secret values were accessed or printed.

## Blockers

1. `codex` lacks permission to inspect `/etc/apps/ai-teacher`; file existence and metadata of `staging.env` remain unverifiable.
2. Canonical API container `staging-api-1` is absent, while PostgreSQL and Redis are running.
3. No authoritative generator/provisioning source was identified; runtime provenance remains unresolved.

## Recommendation

Keep Recovery in **SAFE HOLD**. Do not create an env file, start/recreate the API, rollback, migrate, or alter Cloudflare/Webhook. Request an owner-authorized, read-only metadata check by root (file mode/owner/size/timestamp only, never contents) or locate the documented provisioning system outside this host. After provenance is established, perform a separate Commander gate for any runtime action.

## Root metadata audit (Commander-authorized, read-only)

A root-authorized metadata check resolved the earlier permission ambiguity without reading file contents:

- `/etc/apps/ai-teacher`: `root:root`, mode `0750`, directory.
- `/etc/apps/ai-teacher/staging.env`: exists as a regular file, owner `codex:codex`, mode `0600`, size `767` bytes; mtime `2026-09-14 18:11:23 +0100`. Contents were not read.
- Running `staging-postgres-1` and `staging-redis-1` both belong to Compose project `staging`, canonical config `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`, working directory `/opt/apps/ai-teacher/deploy/staging`; both are running.
- API images present include `staging-api:latest` digest `sha256:f13e836c...`, `staging-api:canonical-0020`, and `staging-api:canonical-0021-candidate`; no API container is present.
- Compose shape confirms `postgres`, `redis`, `api`, and `migrate` services; `api`/`migrate` use the canonical env path through `env_file`. No lifecycle command was run.

## Updated status

Canonical env **exists and its metadata is now verified**, but API runtime provenance is still incomplete: there is no `staging-api-1` container, no active systemd/cron generator, and multiple candidate API images are present without an authoritative selection record. Recovery remains SAFE HOLD; a separate Commander gate is required before starting or recreating any API container.
