# API Runtime Restoration Preparation — 2026-09-14

## Status
READ-ONLY PREPARATION COMPLETE — EXECUTION GATE NOT OPEN

## Host
- Host: `srv20708.deluxhost.net` (`95.135.208.167`)
- SSH command execution: PASS as `codex`
- sudo non-interactive: unavailable (not used)

## Compose identity
- File: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml` — present
- Project: `staging`
- Services resolved: `postgres`, `redis`, `api`
- API service: build-defined (`context: ../..`, `Dockerfile`), no instantiated `staging-api-1`
- Compose config inspection did not expose a concrete API image reference
- API service declares an env_file, but the canonical path `/etc/apps/ai-teacher/staging.env` is absent on this host

## Runtime inputs and dependencies
- Candidate image digest `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`: present
- `staging-api-1`: absent
- PostgreSQL: `staging-postgres-1` running and healthy
- Redis: `staging-redis-1` running and healthy
- Volumes: present; untouched
- No container lifecycle operation executed

## Blocking findings
1. Canonical env file `/etc/apps/ai-teacher/staging.env` was not found. Starting/recreating API without resolving the runtime input would violate the execution gate.
2. Compose defines API through `build`, while the candidate image is separately present; image provenance mapping must be confirmed before any lifecycle action.
3. `docker compose config --format json` was unavailable/returned no JSON in this environment; service identity was confirmed through `config --services` and file inspection.

## Safety boundaries
- Docker/Compose: no start, stop, recreate, build, pull, down, or prune
- PostgreSQL/Redis: untouched
- Migration/DB/env/Cloudflare/webhook: unchanged

## Decision
`API Runtime Restoration` execution gate remains CLOSED pending Commander decision on the missing canonical env and image provenance. No recovery action was performed.
