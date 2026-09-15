# Ruff Phase 2 Batch 2 Selection Review

Date: 2026-09-15  
Scope: selection review only; no implementation authorized by this document.

## Candidate comparison

| Candidate | Findings | Coupling/risk | Decision |
|---|---:|---|---|
| `app/core/client_contract.py` | 1 | Shared contract imported by multiple layers; medium blast radius | **Recommended candidate** with isolated diff and contract/type checks. |
| `app/core/channels.py` | 1 | Provider-neutral protocols and identity types; medium-high compatibility risk | Defer until client contract result is accepted. |
| `scripts/r2_offsite_packager.py` | 1 | Operational packaging path; low application coupling but operational side effects | Defer; requires dedicated dry-run/CLI validation. |
| `app/services/audit_trail.py` | 1 | Service/domain coupling and audit invariants | Defer to a service-specific gate. |
| `migrations/versions/20260912_0020_merge_production_staging_lineage.py` | 1 | Migration lineage and schema impact | Exclude; separate migration gate required. |

The remaining 906 UP006/UP035 findings are unchanged. Counts are from the current Ruff JSON baseline.

## Recommendation

If Commander opens Batch 2 implementation, select only `app/core/client_contract.py`. It is a single-finding, bounded contract module with no migration or FastAPI route logic. Because it is shared, implementation must be limited to the exact UP006/UP035 import modernization and must preserve runtime annotations and Protocol signatures.

## Required gate checks

Before and after the change: targeted Ruff check, `py_compile`, focused contract tests, static type validation where available, diff review, and secret scan. Python 3.12 validation is unavailable in the current environment (Python 3.13.14); record this explicitly. Any import/runtime annotation or contract mismatch stops the batch.

## Explicit exclusions

No source edits are made by this review. No services/routes/scripts/migrations, broad autofix, Ruff configuration, dependency/workflow, Production, Recovery, deployment, restart, database, or environment changes are included.

## Decision required

Commander decision required before implementation of Batch 2.
