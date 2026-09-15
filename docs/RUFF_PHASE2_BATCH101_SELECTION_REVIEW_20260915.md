# RUFF PHASE 2 BATCH 101 SELECTION REVIEW — 2026-09-15

Candidate: `app/services/pre_execution_certification_master_package.py`

HEAD findings: 12 UP006/UP035 findings, confirmed from Ruff JSON on current HEAD.
Symbols: deprecated `typing` collection imports and corresponding generic annotations.
Remediation: import-only cleanup plus annotation modernization (`Tuple[...]`/related deprecated forms to built-in or `collections.abc` forms as applicable); no behavior changes.

Blast radius: Low and isolated to a frozen certification package service.
Contract/runtime/introspection risks: Preserve dataclass/validation contracts, defaults, ordering, serialization and runtime introspection exactly.
Focused tests: discover before implementation; run any dedicated certification tests if present.
Validation proposed: targeted Ruff UP006/UP035, py_compile, typing.get_type_hints, focused pytest, annotation/import-only diff review, git diff --check, secret scan.

Production impact: NONE
Recovery impact: SAFE HOLD
Implementation status: NOT STARTED; awaiting Commander Implementation Gate.
