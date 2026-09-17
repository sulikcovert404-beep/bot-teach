# BATCH054 — Release Evidence Index

## Scope

This index consolidates the evidence produced by Gates 045–053. It is documentation only; no server, runtime, database, migration, or configuration action is performed here.

## Evidence map

| Gate | Artifact | Result | Key evidence |
|---|---|---|---|
| 045 | `docs/BATCH045_CANDIDATE_IMAGE_QUALIFICATION_RESULT.md` | PASS | Candidate digest `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`; 0020→0021 lineage present |
| 046 | `docs/BATCH046_DISPOSABLE_CANDIDATE_RUNTIME_RESULT.md` | PASS | Isolated candidate startup/import/health passed; no production mounts or network |
| 047 | `docs/BATCH047_CONTROLLED_RELEASE_RECONCILIATION_PLAN.md` | PLAN COMPLETE | Canonical compose/env references, backup and rollback boundaries documented |
| 048 | `docs/BATCH048_RELEASE_EXECUTION_PREFLIGHT_RESULT.md` | PASS | Dependencies healthy; backup hash verified; readiness at 0021 |
| 049 | `docs/BATCH049_CONTROLLED_RELEASE_RECONCILIATION_EXECUTION_RESULT.md` | PASS (immediate) | `staging-api-1` switched to candidate digest; migration skipped because DB already at 0021 |
| 050 | `docs/BATCH050_POST_RECONCILIATION_STABILITY_RESULT.md` | PASS (immediate) | Five health/readiness samples; API, PostgreSQL and Redis healthy; restart 0/OOM false |
| 051 | `docs/BATCH051_EXTENDED_RUNTIME_STORAGE_OBSERVATION_RESULT.md` | UNVERIFIED | SSH timed out; public health remained 200 |
| 052 | `docs/BATCH052_SSH_OBSERVABILITY_RECOVERY_RESULT.md` | BLOCKED | TCP/key authentication passed; post-auth session timed out |
| 053 | `docs/BATCH053_SSH_SESSION_LAYER_DIAGNOSIS_RESULT.md` | BLOCKED | `/bin/echo` and `/bin/sh` timed out; root rejected; no mutation |

## Consistency validation

- Candidate digest is consistent across Gates 045, 047–050: `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`.
- Database/readiness target is consistently `20260912_0021` in Gates 048–051.
- The verified backup path and SHA256 are consistent in Gates 047–049: `/var/backups/postgresql/education_post_cutover.dump`, `8f7a6b4b614959bfb6a1680c8d1b612130fb0ac05f5d857551e8297d9aa16d14`.
- Immediate application evidence is positive, while host-level extended stability remains explicitly unverified because of the SSH session-layer blocker.
- No report supports a claim of full operational closure.

## Current evidence boundary

The candidate runtime and public health are supported by direct evidence. Internal host/storage metrics after the switch require restored SSH or owner console access. This index preserves that distinction.
