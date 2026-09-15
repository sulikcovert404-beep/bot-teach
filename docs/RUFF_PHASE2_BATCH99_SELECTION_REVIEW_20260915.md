# RUFF PHASE 2 BATCH 99 SELECTION REVIEW — 2026-09-15

Candidate: `app/services/persistence_foundation_validation.py`
HEAD findings: 12 UP006/UP035 (lowest remaining count; confirmed by Ruff JSON).
Remediation: remove deprecated `typing.Tuple` import and convert `Tuple[...]` to `tuple[...]` only.
Risk: low to moderate; preserve persistence validation contract fields, defaults, ordering, validation, serialization, runtime and introspection.
Focused test: identify existing focused coverage before implementation.
Validation: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, diff check, secret scan.
Production: NONE
Recovery: SAFE HOLD
Implementation: NOT STARTED; awaiting Commander Gate.
