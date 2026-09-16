# RUFF PHASE 3 BATCH 062 SELECTION REVIEW

Candidate: `tests/test_mvp_pilot_authorization.py`

Inventory (target rules): I001=1; B008=0; BLE001=0; DTZ003=0; F811=0; F841=0.

Risk: LOW-MEDIUM. Test-only authorization contract coverage; proposed change is import ordering only and does not alter assertions, fixtures, routes, auth behavior, or production configuration.

Focused validation: `pytest -q tests/test_mvp_pilot_authorization.py` (6 tests collected).

Plan after approval: apply only Ruff I001 normalization, run targeted Ruff and companion rules, py_compile, focused pytest, diff check, secret scan, and scope review.

Production/Recovery impact: NONE; no migration, runtime, DB, deployment, or recovery action.
