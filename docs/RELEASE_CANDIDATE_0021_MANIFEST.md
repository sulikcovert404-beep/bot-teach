# Release Candidate 0021 Manifest

## Scope

Canonical, provider-neutral release reference. Documentation only; this file does not authorize deployment, rollback, migration, or configuration changes.

## Release identity

- Candidate image: `staging-api:canonical-0021-candidate`
- Candidate digest: `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`
- Previous runtime digest: `sha256:f13e836c7500fb84eb856bbbd70f7e2ff4fed42c46a254b423c6faab72b16315`
- Expected migration head: `20260912_0021`
- Migration chain: `20260912_0020 → 20260912_0021`

## Runtime references

- Host: `95.135.208.167`
- Canonical compose: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`
- Canonical environment reference: `/etc/apps/ai-teacher/staging.env` (values intentionally omitted)
- API container: `staging-api-1`
- Health: `https://bot.codeshow.ir/health`
- Readiness: `https://bot.codeshow.ir/health/ready`

## Backup and rollback references

- Backup: `/var/backups/postgresql/education_post_cutover.dump`
- Backup SHA-256: `8f7a6b4b614959bfb6a1680c8d1b612130fb0ac05f5d857551e8297d9aa16d14`
- Rollback requires a new incident-specific Commander decision, verified runtime compatibility, and an explicit bounded procedure. Database downgrade is not implied by image rollback.

## Smoke endpoints

`/mini-app/`, `/platform/`, `/student-dashboard/`, `/teacher-dashboard/`, `/admin-dashboard/`, and `/health/ready` were recorded as HTTP 200 in the immediate post-reconciliation evidence. Extended host observability remains pending SSH session recovery.

## Current status

Application reconciliation: complete on last verified checks. Host operational closure: pending internal observability. No secrets, credentials, tokens, or environment values are included.
