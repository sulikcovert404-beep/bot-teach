# Production Runtime Config Ownership Handoff

## Current blocker

The canonical production runtime configuration source is missing. The deployment expects:

```text
/etc/apps/ai-teacher/staging.env
```

As a result, the API container cannot be instantiated safely.

## Confirmed facts

- The Compose deployment declares an `env_file` dependency for the API.
- `/etc/apps/ai-teacher/staging.env` was checked and is absent.
- Docker, Compose, PostgreSQL, Redis, and the canonical candidate image are available.
- `staging-api-1` is missing and health endpoints are unavailable.
- Other `.env` files and templates were identified by name only; none is approved as the production source.
- No secret was read, printed, copied, or transmitted.
- No server, database, migration, Docker, Cloudflare, webhook, or repository runtime mutation occurred.

## Required owner/provider action

The owner or provider must do exactly one of the following through an approved secure channel:

1. Restore the canonical env file from a verified backup, with its intended ownership and permissions; or
2. Identify and approve the official replacement path for runtime configuration.

## Resume sequence

```text
Config source verified
        ↓
API Runtime Restoration Gate
        ↓
staging-api-1 restore
        ↓
health/readiness validation
```

## Prohibited until ownership handoff is complete

- Creating or reconstructing an env file
- Copying another `.env` or template
- Printing or sharing secret values
- Starting or recreating the API container
- Compose, migration, schema, DB, Redis, image, or deployment changes

## Operational status

```text
Production: SAFE HOLD
API restore: HOLD
Next valid event: canonical runtime config restored or formally approved
```

