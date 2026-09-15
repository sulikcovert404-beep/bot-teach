# Production Recovery Watch Baseline — 2026-09-14

## Current Locked State

- Database: `20260912_0021`
- Migration: complete
- Release images: available
- API runtime: not restored
- Blocker: `RUNTIME-CONFIG-001` (canonical runtime configuration unavailable)

## Periodic Read-only Checks

Allowed checks are limited to SSH availability, Docker daemon responsiveness, PostgreSQL health, Redis health, and presence/absence of `/etc/apps/ai-teacher/staging.env` and `staging-api-1`. Secret contents must not be read.

## Resume Trigger

Canonical runtime configuration is restored or an approved official replacement source is provided, followed by config validation and an API restore gate.

## Abort Boundaries

No environment creation, secret extraction, fallback configuration, rollback, migration, or database mutation.

## Operational State

WAITING FOR OWNER/PROVIDER RUNTIME CONFIG RECOVERY

No secrets, credentials, or private data are recorded in this document.
