# Ruff Phase 2 Batch 3 Selection Review

Date: 2026-09-15  
Scope: candidate selection only; no source implementation.

## Candidate comparison

| Candidate | Findings | Coupling/risk | Decision |
|---|---:|---|---|
| `app/core/channels.py` | 1 | Shared provider-neutral protocols and identity contracts; medium-high blast radius | **Recommended candidate**, only as a one-file import modernization with protocol/type checks. |
| `scripts/postgresql_backup.py` | 1 | Operational backup CLI; low app coupling but high operational consequence if behavior changes | Defer; requires dry-run and command construction tests. |
| `scripts/r2_offsite_packager.py` | 1 | External storage packaging path; operational side effects | Defer to an operations-specific gate. |
| `app/services/audit_trail.py` | 1 | Domain audit invariants and service consumers | Defer; service coupling makes it unsuitable for the next smallest batch. |
| `migrations/versions/20260912_0020_merge_production_staging_lineage.py` | 1 | Schema lineage and migration execution | Exclude; separate migration gate required. |

The remaining inventory is 904 UP006/UP035 findings after the two completed batches. No broad autofix was used.

## Recommendation

If Commander opens Batch 3 implementation, select only `app/core/channels.py`. It is a bounded provider-neutral contract module with one finding and no migration or FastAPI route logic. Because it is imported broadly, the change must remain exactly the allowed import modernization; no refactor, Protocol redesign, or annotation cleanup is included.

## Required validation

Run targeted Ruff UP006/UP035, `py_compile`, all focused channel/contract tests, and static type validation where available. Add a diff review confirming Protocol method signatures, async return types, postponed annotations, and public enum/dataclass behavior are unchanged. Record that Python 3.12 validation is unavailable if the local runtime remains Python 3.13.14. Run secret scan by scope.

## Explicit exclusions

No source edits, services/routes/scripts/migrations changes, broad autofix, Ruff config, workflow/dependency changes, Production/Recovery action, deployment, restart, database, or environment changes are part of this review.

## Decision required

Commander decision required before any Batch 3 implementation.
