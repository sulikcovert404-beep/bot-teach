# RUFF PHASE 2 BATCH 98 SELECTION REVIEW — 2026-09-15

Candidate: `app/services/transition_assurance_certification_package.py`
HEAD findings: 11 UP006/UP035 (lowest remaining count; confirmed by Ruff JSON).
Remediation: remove deprecated `typing.Tuple` import and convert `Tuple[...]` to `tuple[...]` only.
Risk: low to moderate; preserve certification contract fields, defaults, ordering, validation, serialization, runtime and introspection.
Focused test: identify existing focused coverage before implementation.
Validation: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, diff check, secret scan.
Production: NONE
Recovery: SAFE HOLD
Implementation: NOT STARTED; awaiting Commander Gate.
