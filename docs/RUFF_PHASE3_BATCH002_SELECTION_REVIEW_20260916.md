# Ruff Phase 3 Batch 002 — Selection Review (2026-09-16)

## Scope
Selection review only. No source edit, autofix, refactor, production, recovery, or configuration action.

## Candidate
- **Canonical path:** `app/security/teacher_scope.py`
- **Rule inventory:** `I001=1`; `B008=0`, `BLE001=0`, `DTZ003=0`, `F811=0`, `F841=0`.
- No additional Ruff findings are present in this module.

## Risk classification
Import-only normalization. The module contains teacher class-scope policy and is security-sensitive by purpose, but the proposed change is limited to deterministic import ordering; no authorization logic or runtime behavior is altered.

## Why selected
The candidate has exactly one I001 finding, no runtime-sensitive findings in the same module, minimal blast radius, and direct focused coverage in `tests/test_teacher_scope.py` plus contract coverage in `tests/test_assignment_contract.py`.

## Focused validation plan (after approval)
- Ruff `I001` targeted check before/after (expect 0).
- `python -m py_compile app/security/teacher_scope.py`.
- `pytest -q tests/test_teacher_scope.py tests/test_assignment_contract.py`.
- `git diff --check`, secret scan, and exact diff review confirming import-only changes.

## Impact
Production: NONE. Recovery: SAFE HOLD. No migration, API, auth-policy, tenant-policy, or deployment changes.

## Commander decision required
Approve or reject this candidate for Ruff Phase 3 Batch 002 implementation.
