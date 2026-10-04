# Gate738R — Migration 20260921_0022 Provenance & Lineage Closure

Date: 2026-10-04

## Verdict

`PROVENANCE_VERIFIED` — Gate738R PASS for the exact source provenance and migration lineage of `20260921_0022`.

This closes the `0022` provenance question only. Gate738L remains `CRASH_QUALIFICATION_ENV_BLOCKED / NOT QUALIFIED`; the candidate is frozen and qualification-incomplete, not release-approved. Production and staging remain NO-GO.

## Frozen candidate and workspace

| Item | Observed value |
|---|---|
| Worktree | `D:\project\ai-teacher-gate731-target` |
| Branch | `codex/gate731-target` |
| HEAD | `e4140c4d55a2943c53ecc187a28729663073d48d` |
| Candidate manifest | `docs/GATE738P_CANDIDATE_MANIFEST.json` |
| Manifest SHA-256 | `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1` |
| Manifest entries | 407 |
| Alembic head (`alembic heads`) | `20261004_0033` — exactly one head |
| Current `0022` status | Untracked in this workspace; unchanged by this audit |

## Workspace migration identity

| Field | Value |
|---|---|
| Path | `migrations/versions/20260921_0022_provisioning_idempotency.py` |
| Size | 2,203 bytes |
| SHA-256 | `cfe5045c895894469f953ce2c3bdb9fc61713dd8d99261fd5c5a216a40bd47c6` |
| Revision | `20260921_0022` |
| `down_revision` | `20260912_0021` |
| Manifest entry SHA-256 | `cfe5045c895894469f953ce2c3bdb9fc61713dd8d99261fd5c5a216a40bd47c6` — exact match |

## Canonical source and exact-byte evidence

The migration originates in Git commit:

```text
commit: 2d7ed4cc1dafcb8dbd395a07259fe7e00bfe490f
parent: 0cf6758e326636c84764867a9d4c8393494988f2
subject: fix: add provisioning idempotency persistence
author/commit date: 2026-09-21 07:24:48 +0330
path: migrations/versions/20260921_0022_provisioning_idempotency.py
Git blob: b3b3cffb0590e5cae7798ca89c61cc8c1f170c49
```

The commit is present on `origin/codex/provisioning-idempotency-schema-656` and is an ancestor of the fetched `origin/master` ref (`77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`). `git log --all --raw` identifies the commit as the addition of this path. The raw 2,203-byte blob extracted from that commit has SHA-256 `cfe5045c895894469f953ce2c3bdb9fc61713dd8d99261fd5c5a216a40bd47c6` and compares byte-for-byte equal to the current workspace file.

Other inspected worktrees have the same Git tree blob ID. Their on-disk SHA-256 differs because this Windows Git installation has `core.autocrlf=true`; the committed blob bytes and the current candidate file were compared directly and match exactly. No conflicting Git blob for this revision was found among 1,459 safely inspected unreachable blob objects. No stash entry was present. Branches, tags, available reflogs, and all registered worktrees were inspected read-only.

Classification: `PROVENANCE_VERIFIED`. This is an exact canonical Git source, not a conclusion based on report copies or similarity.

## Lineage integrity

`alembic history --verbose` reports the following single path from `0022` to the frozen head:

```text
20260912_0021
→ 20260921_0022
→ 20261003_0024
→ 20261003_0025
→ 20261003_0026
→ 20261003_0027
→ 20261003_0028
→ 20261003_0029
→ 20261004_0032
→ 20261003_0030
→ 20261003_0031
→ 20261004_0033 (sole head)
```

Revision `20261003_0027` has direct parent `20261003_0026`; the graph reaches canonical `0022` through `0026 → 0025 → 0024 → 0022`. Thus `0027` is transitively connected to the exact canonical `0022`; it does not claim a direct parent relationship. Alembic recognizes `20260912_0020` as the mergepoint joining the earlier `20260909_0009` and `20260910_0019` histories. The Alembic graph has exactly one head, `20261004_0033`, and no duplicate revision IDs. The `20260921_0023` revision is absent from Alembic history and no migration reference to that ID was found.

## Risk and release impact

No provenance conflict was found for `0022`; its workspace bytes and Gate738P manifest entry match the origin Git commit exactly. The candidate lineage is structurally connected and resolves to one head. No migration was executed to establish these facts.

This finding does not qualify runtime behavior, resolve the Gate738L environment blocker, verify a real backup restore, or authorize a release. The candidate remains `FROZEN / QUALIFICATION-INCOMPLETE / NOT RELEASE-APPROVED` until its independent qualification blockers are closed.

## Mutations

```text
Migration execution: NONE
Database access/write: NONE
Production: NONE
Staging: NONE
SSH: NONE
Registry mutation: NONE
Commit/merge/deploy: NONE
Source migration edit: NONE
Other project/worktree edits: NONE
```

The only created file is this Gate-local evidence report.
