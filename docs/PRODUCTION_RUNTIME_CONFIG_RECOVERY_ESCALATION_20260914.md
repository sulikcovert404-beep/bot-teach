# Production Runtime Configuration Recovery Escalation

## Current blocker

The canonical runtime environment source expected by the staging Compose deployment is missing:

```text
/etc/apps/ai-teacher/staging.env
```

Without this source, `staging-api-1` cannot be restored safely.

## Verified facts

- Target host: `95.135.208.167` (`srv20708.deluxhost.net`)
- SSH transport, authentication, and remote execution: PASS
- Compose file: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml` (present)
- Compose services: `postgres`, `redis`, `api`
- API service definition: present
- Docker daemon and Compose CLI: PASS
- Candidate image: `staging-api:canonical-0021-candidate`
- Candidate image digest: `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`
- PostgreSQL: healthy and unchanged
- Redis: healthy and unchanged
- Database migration state: expected `20260912_0021`
- `staging-api-1`: missing
- Local API health: unavailable because no API container is running
- Production mutation: NONE

## Required owner/provider action

Provide exactly one of the following, through an approved secure channel:

1. Restore `/etc/apps/ai-teacher/staging.env` from a verified backup, preserving its intended ownership and permissions; or
2. Confirm an official replacement path that is the canonical runtime configuration source for this Compose deployment.

The source must be validated against the release/deployment lineage before any API restore is authorized.

## Explicitly prohibited until validation

- Creating `staging.env` manually
- Copying another `.env` file or template as a substitute
- Printing, pasting, or transmitting secret values
- `docker compose up`, container recreate, or API start
- Migration, schema, database, or Redis changes
- Image downgrade or rollback

## Resume criteria

```text
SSH PASS
→ canonical config source VERIFIED
→ API Runtime Restoration Gate
→ health/readiness validation
```

## Safety statement

No secret contents were read or exposed while preparing this escalation. No server, database, Docker, Cloudflare, webhook, or repository runtime configuration was changed.

