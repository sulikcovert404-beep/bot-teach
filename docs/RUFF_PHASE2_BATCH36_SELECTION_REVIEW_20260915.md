# Ruff Phase 2 Batch 36 Selection Review — 2026-09-15

Candidate: `app/services/runtime_entry_decision.py`

Finding count: exactly 1 `UP035` (`Mapping` imported from `typing`).

Imported symbols: `Any` remains in `typing`; only `Mapping` moves to `collections.abc`.

Blast radius: LOW. This is an import-only modernization in the runtime entry decision service. Decision outcomes, payload hashing, and canonical serialization must remain unchanged.

Contract/runtime risks: preserve all entry decisions, digest behavior, reference handling, and public interfaces; do not alter control flow.

Required validation: targeted Ruff `UP006/UP035`, `py_compile`, focused tests if present, import-only diff review, decision/hash/serialization behavior review, `git diff --check`, secret scan, and Python 3.12/type validation when available.

Production impact: NONE. Recovery impact: SAFE HOLD.

Recommendation: approve an implementation gate limited to moving `Mapping` from `typing` to `collections.abc`.
