# RUFF Phase 2 Batch 93 Selection Review — 2026-09-15

Candidate: `app/services/operational_control_plane_foundation.py`

## Findings on current HEAD

- Total: **8** UP006/UP035 findings
- 1 × UP035: deprecated `typing.Tuple` import
- 7 × UP006: `Tuple[...]` annotations on the immutable contract fields
- Symbols: `OperationalControlPlaneFoundation` fields `control_architecture`, `policy_evaluation_semantics`, `command_ownership`, `workflow_boundaries`, `escalation_model`, `audit_boundary`, and `blockers`.

## Proposed controlled remediation

Remove the deprecated/unused `Tuple` import and replace only these annotations with built-in `tuple[...]`. No logic, outcome precedence, defaults, field names, data shape, serialization, or runtime behavior should change.

## Risk and blast radius

Blast radius is low: one pure dataclass contract module. The primary compatibility check is annotation introspection because the module is a design-only contract. No production endpoint or persistence path imports it directly.

## Tests and validation

A focused test exists at `tests/test_operational_control_plane_foundation.py`; run it after implementation. Required checks: targeted Ruff UP006/UP035, `py_compile`, `typing.get_type_hints`, focused pytest, `git diff --check`, and secret scan. Review the diff to confirm only import/annotation modernization.

Production impact: NONE
Recovery impact: SAFE HOLD
Implementation: NOT STARTED — awaiting Commander Implementation Gate.
