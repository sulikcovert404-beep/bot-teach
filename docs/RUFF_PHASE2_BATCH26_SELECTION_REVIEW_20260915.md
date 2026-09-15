# Ruff Phase 2 Batch 26 Selection Review — 2026-09-15

Candidate: `app/services/patch_landing_inventory.py`

Finding: exactly 1 UP035 (`Mapping` imported from `typing`; `Any` remains there).
Blast radius: LOW; patch landing inventory utility, proposed import-only change.
Contract/runtime risks: no expected behavior or serialization change; retain `Any` in `typing` and move only `Mapping`.
Required validation: Ruff UP006/UP035, py_compile, focused tests, import-only diff, behavior/serialization review, git diff --check, secret scan.
Production impact: NONE.
Recovery impact: SAFE HOLD.
Recommendation: approve implementation gate limited to moving `Mapping` to `collections.abc`.
