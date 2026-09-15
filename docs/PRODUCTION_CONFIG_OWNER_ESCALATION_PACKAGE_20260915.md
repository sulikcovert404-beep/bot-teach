# Production Config Owner Escalation Package

Date: 2026-09-15  
Target: `95.135.208.167` (`srv20708.deluxhost.net`)

## Required recovery input

Please restore the canonical runtime configuration file:

```text
/etc/apps/ai-teacher/staging.env
```

or provide the official, approved replacement source used by the staging Compose deployment. The source must be delivered through a secure owner/provider channel and retain its intended permissions and ownership.

## Evidence

- Canonical Compose file: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`.
- Docker metadata references `/etc/apps/ai-teacher/staging.env` as the project environment file.
- The expected env file is currently absent.
- `staging-api-1` is absent; PostgreSQL and Redis are healthy.
- Database revision is `20260912_0021`.
- Canonical 0020 and 0021 image metadata is present.
- Forensic review: commit `3fa2d7d`, [CANONICAL_RUNTIME_CONFIGURATION_FORENSIC_REVIEW_20260915.md](CANONICAL_RUNTIME_CONFIGURATION_FORENSIC_REVIEW_20260915.md).

## Explicit non-requests

This escalation does not request:

- immediate rollback;
- database downgrade or migration;
- manual recreation of an env file;
- copying a development `.env` or template;
- sharing secrets in chat, reports, Git, or Docker history.

## Resume criteria

```text
Canonical config source verified
        ↓
Config validation gate
        ↓
API Runtime Restoration Gate
        ↓
Health/readiness validation
```

Rollback qualification may be considered only after config provenance and complete image/DB compatibility are independently proven. Blind rollback remains rejected.

## Current status

```text
RUNTIME-CONFIG-001: OPEN
HOST-IO-002: WATCH / requalification pending
API runtime restoration: BLOCKED
Production: SAFE HOLD
Production mutation: NONE
```
