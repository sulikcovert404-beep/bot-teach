# API Runtime State Investigation — 2026-09-14

## Status
**FOUND — Recovery remains BLOCKED**

## Findings
- Docker daemon and socket responded to bounded read-only commands.
- Running containers: `staging-postgres-1` and `staging-redis-1`, both healthy.
- `staging-api-1` is absent; no exited API container with that name was found.
- Canonical compose file exists at `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml` and defines service `api`, plus `postgres`, `redis`, and a migration profile.
- The `api` service is defined with a build context and port `8000:8000`; it is not currently instantiated.
- Canonical candidate image exists on host as `staging-api:canonical-0021-candidate` with the recorded digest, alongside older images.
- Networks include `staging_default`; no API container is attached.
- Public `/health` and `/health/ready` return 502 because the port 8000 API upstream is unavailable.

## Root Cause
The compose definition is present, but the canonical `api` service/container is missing from the running project. This explains the public 502. The evidence does not authorize creating or starting it under this investigation gate.

## Required Recovery Action
A separate explicit recovery gate must authorize the minimal canonical API lifecycle operation after verifying image/build provenance, SSH/sudo stability, and host I/O. Do not use `compose up`, migration profile, rebuild, or environment edits as part of this report.

## Production Mutation
NONE.
