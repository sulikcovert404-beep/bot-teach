# Lesson Asset Identity Migration Draft

Status: disposable design only. No migration is created or applied.

The existing `generated_assets` table cannot enforce the complete product identity
for a lesson pack. `job_id` points to a content version, but stage, language, and
profile version are not first-class queryable fields. Free-text conventions are
intentionally rejected.

## Proposed minimal provider-neutral shape

Add immutable identity fields to `generated_assets`:

- `content_version_id` (explicit product content identity, nullable for legacy rows)

- `school_stage` (`ELEMENTARY`, `LOWER_SECONDARY`, `UPPER_SECONDARY`)
- `language` (BCP-47 string, for example `fa-IR`)
- `profile_version` (application contract version)

Keep provider, model, voice, and generation details in structured metadata and
outside the uniqueness contract. Add a unique constraint over:

`(content_version_id, asset_type, school_stage, language, profile_version)`

`job_id` remains the execution and trace reference; it is not used as the
product uniqueness key. The existing job uniqueness key remains the generation
request idempotency key.

## Qualification sequence

1. Create a migration descending from the current staging lineage (`20260910_0016`).
2. Upgrade a disposable PostgreSQL database and inspect columns/constraints.
3. Exercise retry and concurrent insert races and verify one canonical asset.
4. Rehearse downgrade and re-upgrade with the application active.
5. Stop at the disposable boundary for Commander review; do not migrate staging.

Current verdict: `SCHEMA MIGRATION REQUIRED`, `LIVE STAGING UNCHANGED`,
`PRODUCTION UNCHANGED`.
