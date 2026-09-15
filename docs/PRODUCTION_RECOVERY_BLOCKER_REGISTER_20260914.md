# Production Recovery Blocker Register

## Active blocker

```text
ID: RUNTIME-CONFIG-001
Title: Missing canonical runtime configuration source
Owner: Owner/Provider
Impact: API runtime cannot be restored
Severity: HIGH
Status: OPEN / SAFE HOLD
```

## Evidence

- The staging Compose definition requires an `env_file` for the API.
- The canonical path `/etc/apps/ai-teacher/staging.env` is missing.
- The candidate API image is present and matches the expected lineage.
- Docker, PostgreSQL, and Redis are healthy.
- The API container is absent and local health endpoints refuse connections.
- No secret was read, exposed, copied, or transmitted.
- No production, database, migration, Docker, Cloudflare, webhook, or runtime mutation occurred.

## Required owner/provider action

Provide the canonical runtime configuration from a verified backup, or formally identify and approve its official replacement path. Do not use another `.env` file or a template without that approval.

## Exit criteria

```text
[ ] Canonical config source provided
[ ] Source ownership and permissions verified
[ ] API Runtime Restoration Gate opened
[ ] API health and readiness validated
```

## Current restrictions

Until all exit criteria are met:

- no env creation or secret copying
- no API recreate/start or Compose operation
- no DB, migration, Redis, image, or deployment change

## Resume trigger

The next valid event is verified recovery or formal approval of the canonical runtime configuration source. Until then, production remains in Safe Hold.

