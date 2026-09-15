# Ruff Phase 2 Batch 14 Selection Review — 2026-09-15

## Candidate
`app/services/control_plane.py`

Inventory shows one UP035 finding (`Mapping` imported from `typing`). The module is a pure provider-neutral admin control-plane contract with focused tests in `tests/test_control_plane.py` and conformance coverage.

## Assessment
A single import-only modernization has a bounded diff, but blast radius is medium because outcome handling, canonical serialization, projection failure isolation, and NFC normalization are contract-sensitive.

## Proposed scope (pending Commander gate)
- Change only the `Mapping` import to `collections.abc`.
- Preserve outcome precedence, canonical JSON ordering/encoding, projection error behavior, and Persian NFC handling.
- No routes, migrations, deployment, provider, config, or production changes.

## Required validation after approval
Targeted Ruff UP006/UP035, py_compile, `tests/test_control_plane.py`, conformance tests, serialization/normalization/projection behavior review, secret scan, and static typing if available.
