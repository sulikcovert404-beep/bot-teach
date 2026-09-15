# Ruff Phase 2 Batch 31 Result — 2026-09-15

File: `app/services/retry_recovery.py`

Before: 1 UP035 (`Mapping` from `typing`).
After: 0 UP006/UP035 findings.

Only the import was moved to `collections.abc`; retry classification, recovery actions, canonical serialization, NFC normalization, and runtime behavior are unchanged.

Validation:
- Targeted Ruff UP006/UP035: PASS
- Python compile: PASS
- Focused tests `tests/test_retry_recovery.py`: 3 passed / 0 failed
- Import-only diff: PASS
- `git diff --check`: PASS
- Secret scan: PASS
- Python 3.12/type validation: not available
- Production impact: NONE
- Recovery: SAFE HOLD
