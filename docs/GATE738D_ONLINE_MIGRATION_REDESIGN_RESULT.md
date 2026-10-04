# Gate738D — Online Migration Redesign

**Mode:** local/worktree and new disposable PostgreSQL only  
**Status:** blocked before implementation
**Production/Staging access or mutation:** none

## Pre-edit lineage gate

- Previously qualified Production database revision: `20260921_0022` (readiness evidence and Commander accepted lineage).
- The prior Gate737A manifest recorded candidate `20260924_0023` as an untracked workspace migration (SHA-256 `79132ca63ed00786921be8a04c6313d9f508c9ddb57b5e4f02fb3faed538eeaf`). The Production OCI revision observed in the accepted provenance record is `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`, whose source is at the 0022 lineage. No evidence places 0023 in Production.
- Prior lineage decision: `0023 deployed to Production = NO; Production revision = 0022; candidate-only = YES`. The present Gate738D recheck found the candidate source missing locally, so its pre-edit contents and checksum cannot now be verified. If contrary deployment evidence appears, stop and request a lineage decision.
- The existing synthetic PostgreSQL container `ai-teacher-gate732-pg` is pre-existing and explicitly excluded. Gate738D will use only newly created, separately named resources.

## Design constraints

- Preserve compatibility with the 0022 API during expand and batched backfill.
- Add nullable structures and security-definer compatibility triggers first; do not run bulk backfill under an ACCESS EXCLUSIVE lock.
- Backfill in bounded, deterministic, restartable batches; trigger behavior must serialize with concurrent legacy writes and avoid duplicate or lost revisions.
- Validate data and deferred constraints before the short contract migration. Final cutover may perform metadata/constraint attachment only; it must not perform the bulk copy/update.
- Keep the compatibility bridge through a rolling runtime transition; do not disable it as part of an unqualified release.
- Downgrade is not treated as recovery once revision data exists. Recovery states and safe retry behavior must be documented.

## Lineage and source-integrity recheck

The pre-edit assumptions above could not be reproduced in the current worktree:

- `git rev-parse HEAD` = `e4140c4d55a2943c53ecc187a28729663073d48d`.
- `migrations/versions/20260924_0023_submission_revisions.py` is absent from the filesystem and from `git ls-tree HEAD`.
- `git log --all -- migrations/versions/20260924_0023_submission_revisions.py` contains no committed copy.
- The earlier Gate737A manifest records the candidate's SHA-256 as `79132ca63ed00786921be8a04c6313d9f508c9ddb57b5e4f02fb3faed538eeaf`, but the manifest does not contain the migration source.
- The untracked `20261003_0024_canonical_tenant_context.py` still declares `down_revision = "20260924_0023"`.
- `python -m alembic heads` fails with `KeyError: '20260924_0023'` after warning that the referenced revision is absent.
- Existing candidate tests depend on 0023's schema and migration behavior, but they are not a substitute for the missing migration source.

This contradicts the earlier evidence that 0023 was present as an untracked candidate. No Production/Staging state was queried or changed to investigate this local discrepancy.

## Design and validation status

No migration, application, or test files were edited. No disposable PostgreSQL resources were created. Therefore the following required Gate738D qualifications remain **NOT RUN**: expand compatibility with the 0022 runtime, restartable/concurrent backfill, deterministic validation, contract lock measurements across SMALL/MEDIUM/STRESS, recovery-state rehearsal, and deployment-ordering compatibility tests. Their results cannot be inferred from the previous one-shot migration design or the older lock rehearsal.

## Finding

**LINEAGE BLOCKED:** the exact candidate migration to be redesigned is unavailable, while later candidate revisions depend on it. Reconstructing or replacing it from summaries/tests alone would not preserve exact artifact provenance and could conceal destructive or compatibility semantics. The required pre-edit hash therefore cannot be checked against source bytes.

**Risk:** the local Alembic graph is currently unresolvable; migrations and the dependent disposable qualification cannot safely proceed. No evidence from this local failure changes the previously accepted read-only Production lineage conclusion that the observed Production revision is 0022.

**Recommended resolution:** recover the exact source blob matching the recorded SHA-256 from the qualified Gate737A snapshot or another trusted candidate archive, verify the hash, and re-run the lineage gate. If that exact source cannot be recovered, issue a separate decision explicitly authorizing a replacement candidate migration and requalification of all dependent migrations/tests. Do not run Alembic against any persistent environment while the graph is broken.

**Confidence:** high for current worktree state and Alembic graph failure; high that no Gate738D implementation/qualification was performed; no new claim about Production runtime state.

## Verdict

`ONLINE_MIGRATION_REDESIGN_BLOCKED` — stopped at the required source-integrity gate. No candidate implementation changes, database actions, builds, deploys, or commits were performed. Existing unrelated workspace changes remain untouched.
