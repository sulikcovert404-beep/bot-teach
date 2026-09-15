# Ruff Phase 3 Batch 001 — Selection Review v2 (2026-09-15)

## Status
Selection review only; no source edits, autofix, deployment, or production impact.

## Candidate
- **Canonical path:** `app/main.py`
- **Finding:** `I001` = 5
- **Forbidden behavior rules:** `B008=0`, `BLE001=0`, `DTZ003=0`, `F811=0`, `F841=0`
- **Rationale:** import-order-only scope with no behavior-oriented findings, giving a bounded and mechanically verifiable change surface.

## Focused validation
`app/main.py` is the application entrypoint and is imported by existing health/metrics tests (`tests/test_health.py`, `tests/test_metrics.py`). These provide focused startup and health coverage after an approved fix. Additional checks: `python -m py_compile app/main.py`, Ruff `I001` before/after, and diff review.

## Risk assessment
The file is central at runtime, so import-order changes must remain limited to Ruff's `I001` fix. No manual restructuring or broad autofix is authorized. No schema, API contract, auth, tenant, migration, recovery, or deployment changes are in scope.

## Proposed implementation (pending approval)
1. Run Ruff `I001` fix only for `app/main.py`.
2. Review the exact diff.
3. Run py_compile and focused health/metrics tests.
4. Confirm all forbidden rule counts remain zero and report results.

## Commander decision required
Approve or reject `app/main.py` as Phase 3 Batch 001 candidate. Implementation must not begin until explicit approval.
