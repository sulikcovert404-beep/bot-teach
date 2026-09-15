# Canonical Runtime Configuration Forensic Review

Date: 2026-09-15  
Mode: Read-only investigation

## Sources Checked

### Repository

- Git history, current branch, release references, `app/core/config.py`, `.env.example`, and Compose references were inspected.
- The repository contains development templates and references to an `env_file`, but no approved production secret source.
- No secret values were read or emitted.

### Release artifacts

- Release directories and canonical image lineage were inventoried on the target host.
- Available image tags include `staging-api:canonical-0020` and `staging-api:canonical-0021-candidate`.
- Image IDs/digests were recorded from metadata only; no image was started or changed.

### Compose/deployment

- Canonical Compose file: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`.
- Docker labels on the existing PostgreSQL/Redis containers identify the expected environment file as `/etc/apps/ai-teacher/staging.env`.
- The Compose deployment therefore establishes the expected path, but not the file's contents or an authoritative generator.

### Host inventory

- Host: `95.135.208.167` (`srv20708.deluxhost.net`).
- Release and deployment trees exist under `/opt/apps/ai-teacher`.
- `/etc/apps/ai-teacher/staging.env` is absent.
- `staging-api-1` is absent; PostgreSQL and Redis remain healthy.
- No systemd unit or other approved runtime-config generator was found for this application.

## Config Evidence

| Item | Result |
|---|---|
| Canonical source | **NOT FOUND** |
| Generator/provisioning process | **NOT FOUND** |
| Secret manager reference | **NOT FOUND** |
| Expected path | `/etc/apps/ai-teacher/staging.env` (Compose metadata only) |
| Safe substitute available | **NO** |

Templates such as `.env.example` are development scaffolding and are not an approved production source. No alternate `.env` was promoted or copied.

## Compatibility Evidence

- Database migration state reported for the target environment: `20260912_0021`.
- Candidate images are present for canonical 0020 and 0021 lineages.
- API/schema/runtime-config compatibility for a rollback cannot be proven without the canonical runtime configuration and a qualified application start.
- Compatibility verdict: **UNKNOWN**.

## Blockers

1. `RUNTIME-CONFIG-001`: canonical runtime configuration source and owner are unresolved.
2. `staging-api-1` cannot be safely instantiated without that source.
3. Rollback image/database compatibility is unproven (`UNKNOWN`); a blind rollback is unsafe.

## Commander Recommendation

**HOLD / ESCALATE TO CONFIG OWNER.** Obtain or restore the canonical `/etc/apps/ai-teacher/staging.env` through an approved secure channel, then run the API Runtime Restoration Gate. Consider rollback qualification only after config provenance and full image/DB compatibility are independently verified. No deploy, restore, migration, env edit, restart, Cloudflare/Webhook change, or rollback was performed.

## Production Impact

`NONE` — read-only inspection only.
