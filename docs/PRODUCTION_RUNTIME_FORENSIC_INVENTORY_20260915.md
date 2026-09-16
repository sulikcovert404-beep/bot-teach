# Production Runtime Forensic Inventory — 2026-09-15

## Scope
Read-only inspection of `95.135.208.167` (`srv20708.deluxhost.net`). No restart, container mutation, deployment, migration, environment read/edit, secret export, Cloudflare, or webhook changes were performed.

## Sources inspected
- `/etc/apps`, `/opt/apps`, `/etc`, `/opt` bounded inventories
- Docker container metadata, labels, mounts, and Compose project metadata
- systemd unit inventory/status and user cron inventory
- bounded references to `/etc/apps/ai-teacher/staging.env`

## Host identity and filesystem evidence
- Host: `srv20708.deluxhost.net`
- SSH account: `codex` (sudo and docker groups); no privilege escalation used.
- `/etc/apps/ai-teacher` exists and is root-owned/restricted.
- `/opt/apps/ai-teacher` exists, plus `/opt/apps/ai-teacher-staging-rc`, release archives, and `/opt/data/ai-teacher`.
- This is not a fresh host: it contains active staging data paths, releases, compose files, and database/cache directories.

## Docker evidence (metadata only)
- Compose project `staging` is running from `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`.
- `staging-postgres-1` and `staging-redis-1` are running and healthy; restart count reported as 0.
- Container labels identify environment file path `/etc/apps/ai-teacher/staging.env`; no environment values were read.
- No API container appeared in `docker ps -a` at inspection time.
- Exited `cutoverclone-*` containers are present; untouched.

## Canonical runtime configuration status
`/etc/apps/ai-teacher/staging.env` is referenced by the canonical Compose file for postgres, API, and migration services, and also by the RC Compose file. The file itself was not opened or copied. Docker metadata confirms it as the Compose project environment-file reference, but its existence/readability was not asserted by content inspection.

## Provisioning / ownership evidence
- No `ai-teacher.service` systemd unit exists.
- No related user crontab entries were present; standard system cron files only.
- No bounded systemd/bootstrap reference to the staging env path was found.
- Repository docs describe external, root-owned env provisioning and explicitly state the env is outside Git; these are documentation evidence, not proof of a live generator.

## Generator / secret-manager status
- No active generator, bootstrap, CI/CD agent, or secret-manager reference was found in the bounded server search.
- Secret values were never printed, read, copied, or exported.

## Blockers and risks
1. Canonical env path is consumed by Compose but no live provisioning owner/generator is evidenced.
2. API container is absent from the observed container list, so runtime availability cannot be established from this read-only snapshot.
3. Multiple release/RC trees and exited cutoverclone containers create provenance ambiguity.
4. Host contains prior project/runtime artifacts; it must not be treated as fresh.

## Recommended continuation
Obtain owner-approved provenance for `/etc/apps/ai-teacher/staging.env` (existence, ownership, mode, and provisioning source) without exposing values; reconcile the canonical release/container set; then perform a separately authorized runtime health check. Do not infer or recreate secrets from repository files.

## Mutation record
NONE — read-only inspection only.
