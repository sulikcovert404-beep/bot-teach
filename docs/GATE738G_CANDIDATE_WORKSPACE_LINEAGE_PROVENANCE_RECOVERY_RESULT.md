# Gate738G — Candidate Workspace & Lineage Provenance Recovery

Mode: read-only audit. No production, staging, database, container, SSH, or migration execution was performed. The only write in this Gate was this audit report.

## Finding

The exact Gate738E replacement candidate files for revisions 20261003_0027 through 20261003_0031 are present in the canonical Gate738E worktree. All five SHA-256 values match the hashes recorded in `docs/GATE738E_CANDIDATE_LINEAGE_RECONSTRUCTION_RESULT.md`. The files remain untracked and uncommitted; no independent source commit was found. This is exact byte-level recovery/confirmation against the Gate738E hash record, not independent Git commit provenance.

The older candidate revision `20260924_0023` remains `LOST_UNRELEASED`; its bytes were not found or reconstructed. The 0027–0031 files are the replacement candidate chain documented by Gate738E.

## Evidence

Canonical candidate worktree:

- Path: `D:\project\ai-teacher-gate731-target`
- Branch: `codex/gate731-target`
- HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- The current `gate493-master` workspace points to the same HEAD, but is a separate worktree.
- Gate738E report and all five candidate migrations are present here. Among 42 registered worktrees, this was the only one found containing both the Gate738E report and the full 0027–0031 candidate set.
- Worktree contains pre-existing modifications and untracked files; they were left untouched.

| File | Revision | Parent | Bytes | SHA-256 | Classification |
|---|---|---|---:|---|---|
| `migrations/versions/20261003_0027_submission_revision_parent_identity.py` | `20261003_0027` | `20260921_0022` | 1881 | `DA114AD085304C17842FAAB41382A51968A6FB4B6AEEA524B2C405E4DB95E76B` | `VERIFIED_EXACT` |
| `migrations/versions/20261003_0028_submission_revision_expand.py` | `20261003_0028` | `20261003_0027` | 9719 | `411345DBA09A3D9F7E7F9B1C5364D9E03CFDC85876F9468D447C6554D3D808DB` | `VERIFIED_EXACT` |
| `migrations/versions/20261003_0029_submission_review_revision_index.py` | `20261003_0029` | `20261003_0028` | 1108 | `C8D4A226649646DBB43A30BC59FB828564C2C111371A92C06AA16C690F8F957A` | `VERIFIED_EXACT` |
| `migrations/versions/20261003_0030_submission_revision_contract.py` | `20261003_0030` | `20261003_0029` | 2723 | `0EC1A23855137F1608D0C04918E2AAC18521E70DC3F35972E88A5768A8C4BCBA` | `VERIFIED_EXACT` |
| `migrations/versions/20261003_0031_submission_revision_compat_cleanup.py` | `20261003_0031` | `20261003_0026` | 690 | `821C60545969A177EA175AA4A5EDBFA75655D0FE1AB7BE67B6299FE279BA3232` | `VERIFIED_EXACT` |

The hashes above exactly equal the corresponding values in the Gate738E report. The Gate738E report describes these as workspace-only, uncommitted candidate files and says no source commit for the earlier 0022 artifact could be independently read from the local Git object database.

Git evidence:

- `git log --all --full-history` for the five migration paths returned no commits.
- No matching Gate738E or 0027–0031 entry was found in the all-ref reflog search.
- No matching migration paths were found in unreachable commit trees (22 unreachable commits and 1459 unreachable blobs were observed in the scan).
- The five current file Git blob IDs are absent from the Git object database, reachable and unreachable.
- `git status` marks all five migrations and the Gate738E report untracked.
- No project archive entry matching these migration filenames or the Gate738E report was found in 19 archives under the current project and candidate worktree roots.

Alembic metadata:

- Canonical worktree command: `python -m alembic heads`
- Result: `20261003_0031 (head)`
- This verifies local graph resolution only; no migration was executed.
- Revision 0031 depends on local candidate revision 0026. Revisions 0024–0026 are also untracked candidate files in the same worktree and were not changed.

## Risk

The candidate bytes are exact relative to the Gate738E SHA-256 record, but they are not anchored by a commit, signed artifact, or separately trusted archive. The Gate738E report is itself untracked in the same worktree. This establishes consistency with that prior record, not an independent publisher identity or released-artifact provenance. The lost 0023 bytes remain unavailable. No production or staging state was accessed or changed.

## Recommended resolution

Retain the recovered candidate files and this evidence unchanged. Treat the replacement candidate as `VERIFIED_EXACT` against Gate738E's recorded hashes, while keeping it workspace-only and unreleased. Any subsequent migration, test run that mutates a database, staging action, commit, or deployment requires a separate Commander Gate.

## Restore and mutation accounting

- Candidate restore performed: NO — exact files were already present.
- Migration edits: NONE.
- Alembic migration execution: NONE.
- Production/Staging: NONE.
- Database/schema/data mutation: NONE.
- Commit/deploy: NONE.
- Workspace changes: this audit report only.

## Verdict

`RECOVERED_EXACT` — all five Gate738E candidate migration files are present in the identified worktree and match the exact recorded SHA-256 values. Independent commit/artifact provenance remains unavailable.

## Per-file provenance metadata

Each file's source type is the untracked filesystem copy in the canonical Gate738E worktree. The Git blob IDs below are the IDs that `git hash-object --no-filters` would assign to the current bytes; `git cat-file -e` confirmed none of these blobs exists in the repository object database. Thus no Git object or commit identity can be assigned. All five files were reported as untracked by `git status`.

| File | Git blob ID probe (object absent) | Last modified (UTC) |
|---|---|---|
| `20261003_0027_submission_revision_parent_identity.py` | `28e65beae59e57f101d1fd0ab089f572289e5168` | `2026-10-03T17:05:50.0631881Z` |
| `20261003_0028_submission_revision_expand.py` | `e099f6992e71227f3533ef23f2f7d1c1d08015fe` | `2026-10-03T16:52:07.8117842Z` |
| `20261003_0029_submission_review_revision_index.py` | `c919f99489b563d63829312229375fee5f203e28` | `2026-10-03T16:52:07.8122886Z` |
| `20261003_0030_submission_revision_contract.py` | `1a4b9d3ba5c7a17aead548fc4610d1f8762d65de` | `2026-10-03T17:00:37.4429620Z` |
| `20261003_0031_submission_revision_compat_cleanup.py` | `df9f0a0b831441ef61c3088b48909de58cc2b353` | `2026-10-03T16:52:07.8128121Z` |

All five migration paths and the Gate738E report are untracked in the canonical worktree. The target has pre-existing tracked and untracked changes; this Gate did not modify or stage them. The current `gate493-master` worktree and canonical `codex/gate731-target` worktree are distinct paths sharing HEAD `e4140c4d55a2943c53ecc187a28729663073d48d`.

Local archive check was limited to the current AI Teacher workspace and the canonical Gate738E worktree: 19 archives inspected by listing entries only; no matching candidate filenames or Gate738E report entries were found. No extraction was performed.
