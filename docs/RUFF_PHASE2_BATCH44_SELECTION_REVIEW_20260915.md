# Ruff Phase 2 Batch 44 Selection Review — 2026-09-15

Candidate: `app/services/validation_gates.py`

Finding count: exactly 1 `UP035` diagnostic, covering `Mapping` and `Sequence` imported from `typing`.

Imported symbols: retain `Any` and `Protocol` from `typing`; move only `Mapping` and `Sequence` to `collections.abc`.

Blast radius: LOW. Import-only modernization at the validation-gates boundary.

Contract/runtime risks: preserve gate outcomes, validation contracts, protocol typing, serialization, and runtime semantics. No control-flow, dependency, or configuration changes.

Focused tests: locate validation-gate and readiness tests before implementation and run them after the import-only edit.

Required validation: targeted Ruff (`UP006`, `UP035`), `py_compile`, focused tests, import-only diff review, gate outcome/serialization/runtime review, `git diff --check`, secret scan, and Python 3.12/static typing when available.

Production impact: NONE. Recovery impact: SAFE HOLD.

Recommendation: approve implementation only for moving `Mapping` and `Sequence` to `collections.abc`; retain `Any` and `Protocol` from `typing`.
