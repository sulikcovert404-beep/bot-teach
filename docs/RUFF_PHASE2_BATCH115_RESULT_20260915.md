# Ruff Phase 2 Batch 115 Result

File: `app/services/next_capability_prioritization.py`

Before: 14 UP006/UP035 findings.
After: 0 targeted findings.

Change limited to built-in `tuple[...]` annotations and removal of deprecated typing imports. Prioritization contract, decisions, defaults, ordering, serialization, runtime behavior, and introspection remain unchanged.

## Validation

- Ruff (`UP006,UP035`): PASS (0)
- `py_compile`: PASS
- `typing.get_type_hints()`: PASS
- Focused pytest: 3 passed, 952 deselected (1 warning)
- `git diff --check`: PASS
- Secret scan: PASS

Production impact: NONE
Recovery impact: SAFE HOLD
