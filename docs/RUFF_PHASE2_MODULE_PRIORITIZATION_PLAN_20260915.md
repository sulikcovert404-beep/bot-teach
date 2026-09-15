# Ruff Phase 2 Module Prioritization Plan

Date: 2026-09-15  
Scope: UP006/UP035 only; planning and ranking, no source changes.

## Inventory and ranking

| Rank | Module/file group | Findings | Risk | Recommendation |
|---:|---|---:|---|---|
| 1 | `app/adapters/bale.py` | 1 | Medium: adapter Protocol boundary and async signatures | First implementation candidate after Gate opens; inspect type compatibility and run focused adapter tests. |
| 2 | `app/core/channels.py`, `app/core/client_contract.py` | 2 | Medium-high: shared contracts imported broadly | Candidate only as isolated single-file changes with protocol/type tests; avoid batch edits. |
| 3 | `scripts/postgresql_backup.py`, `scripts/r2_offsite_packager.py` | 2 | Low runtime coupling, but operational consequences | Defer until application modules are qualified; require script dry-run tests and review of CLI annotations. |
| 4 | `app/api/routes/*` | 35 | High: FastAPI/Pydantic dependency and request/response contracts | Defer; select one route only after focused endpoint tests and type-checking. |
| 5 | `app/services/*` | 866 | High: dense service coupling, async boundaries, domain invariants | Defer; split into small independently tested batches, never broad autofix. |
| 6 | `migrations/versions/20260912_0020_merge_production_staging_lineage.py` | 1 | Critical: migration lineage and schema impact | Exclude from Phase 2; requires a separate migration gate. |

Counts are from `.ruff-report.json` filtered to `UP006` and `UP035` (907 findings total).

## Selection criteria

A Phase 2 candidate must have low coupling, no migration logic, no runtime schema impact, a bounded diff, and focused tests that exercise its public interfaces. Type changes must preserve Python 3.12 runtime annotation behavior, Protocol variance, FastAPI/Pydantic contracts, and async return types. Operational scripts require dry-run coverage before acceptance.

## Proposed first batch

Select **one file at a time**, starting with `app/adapters/bale.py` because it has one finding and a bounded provider boundary. If inspection shows a Protocol variance or runtime annotation risk, defer it and use one of the core contract files only after adding/confirming a static type assertion. Do not combine adapter and core changes in one patch.

## Gate criteria

Before implementation: Commander opens the Phase 2 implementation gate. During implementation: run targeted tests, `ruff check` for the selected file, and a Python 3.12 static check where available. After implementation: inspect the diff, verify no behavior/schema/config changes, run the relevant test subset, and record results. Any failure, import/runtime annotation issue, or contract mismatch stops the batch for review.

## Explicit exclusions

No UP006/UP035 edits, autofix, Ruff configuration changes, dependency/workflow changes, migration edits, Production/Recovery actions, deploys, restarts, or environment changes are authorized by this plan.
