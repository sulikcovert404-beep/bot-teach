# Production Recovery Final Provenance Escalation — 2026-09-15

## Executive status

`API-RUNTIME-PROVENANCE-001 = OPEN`  
`RESTORE GATE = HOLD`  
`Production mutation = NONE`

The new server is reachable and its canonical runtime configuration file is present by metadata. PostgreSQL/Redis are healthy, but no API container is running. Release archives are checksum-verified, while the release-to-commit-to-image chain is not authoritative.

## Evidence collected

- Host: `95.135.208.167` / `srv20708.deluxhost.net`.
- Canonical env metadata: `/etc/apps/ai-teacher/staging.env`, owner `codex:codex`, mode `600`, size `767` bytes; contents were never read.
- Canonical compose: `/opt/apps/ai-teacher/deploy/staging/docker-compose.yml`; API service uses build context and canonical env file.
- Running dependencies: `staging-postgres-1`, `staging-redis-1`, Compose project `staging`.
- API candidates: `staging-api:latest` (`sha256:f13e836c...`), `canonical-0020` (`sha256:1b7bfe45...`), `canonical-0021-candidate` (`sha256:24c0135f...`), and RC image (`sha256:bfbb9100...`). All are distinct.
- Release archive `canonical-release-prod-convergence-00c8fb7.tar.gz` SHA256 matches the recorded `e897693b...`; exam archive checksum also verified.
- CI Docker workflow uses `push: false` and emits no digest/attestation. Existing parity documentation references obsolete digest `sha256:17bb6c3a...`.

## Resolved items

- Runtime config presence: resolved.
- Release archive integrity: verified.
- Host storage incident: no new mutation or recovery action; remains watch-only.

## Final blocker

No signed or CI-generated record binds:

`release ID → commit SHA → CI run → image digest → registry/reference → runtime target`.

Selecting an image by tag, timestamp, archive filename, or local presence could run an unapproved artifact against the database and make rollback non-reproducible.

## Exact owner/CI request

Provide an approved manifest containing, at minimum:

- release identifier
- source commit SHA
- GitHub Actions workflow/run ID
- immutable Docker image digest
- registry reference (if applicable)
- build timestamp
- approval/signature or protected artifact location

No secret or credential is requested.

## Forbidden until evidence arrives

Do not start/recreate/build/pull the API, run Compose, migrate, edit env/config, rollback, change Cloudflare/Webhook, or alter database/volumes.

## Gate condition

Only after the manifest is independently verified may a separate Commander gate consider a single canonical API lifecycle action. If no manifest can be produced, retain `STOP + REPORT` and keep Recovery in SAFE HOLD.
