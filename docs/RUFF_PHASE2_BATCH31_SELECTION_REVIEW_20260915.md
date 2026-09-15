# Ruff Phase 2 Batch 31 Selection Review — 2026-09-15

Candidate: `app/services/retry_recovery.py`
Finding count: exactly 1 UP035 (`Mapping` imported from `typing`, line 6).
Imported symbols: only `Mapping`; no mixed typing migration.
Blast radius: LOW; provider-neutral retry/recovery contract module.
Contract/runtime risks: import-only change; retry classification, recovery actions, canonical serialization and NFC behavior must remain unchanged.
Focused tests: `tests/test_retry_recovery.py`.
Required validation: targeted Ruff UP006/UP035, py_compile, focused tests, import-only diff, behavior/serialization review, git diff --check, secret scan, Python 3.12/type validation when available.
Production impact: NONE.
Recovery impact: SAFE HOLD.
Recommendation: approve a separate implementation gate limited to moving `Mapping` to `collections.abc`.
