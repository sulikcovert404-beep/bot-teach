# RUFF PHASE 3 BATCH 063 SELECTION REVIEW

Candidate: `tests/test_mvp_pilot_foundation.py`

Inventory: I001=1; B008=0; BLE001=0; DTZ003=0; F811=0; F841=0.

Risk: LOW-MEDIUM. Test-only credential-free school lifecycle and isolation fixture; proposed change is import formatting only with no test semantics, data, schema, or runtime changes.

Focused validation: `pytest -q tests/test_mvp_pilot_foundation.py` (1 test collected).

Plan after approval: apply only I001 normalization, run targeted Ruff/companion rules, py_compile, focused pytest, diff check, secret scan, and scope review.

Production/Recovery impact: NONE.
