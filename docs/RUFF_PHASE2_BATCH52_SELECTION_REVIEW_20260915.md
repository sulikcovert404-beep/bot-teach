# Ruff Phase 2 Batch 52 Selection Review — 2026-09-15

## Candidate
`app/api/routes/controlled_external_beta.py`

## Findings
- UP035: 2 findings on the `typing.Dict` and `typing.List` import (line 4).
- UP006: 1 annotation finding (`Dict` usage at line 86).
- Total: 3 findings (2 UP035, 1 UP006).

## Scope assessment
This is not import-only: removing `Dict`/`List` requires rewriting the annotation at line 86 to built-in generics (or an equivalent narrowly scoped typing update). The file is an API route, so response typing and route contract must be reviewed before implementation. No source changes are authorized by this Selection Review.

## Blast radius and risks
Potentially limited to one route module, but annotation changes can affect static type checking and generated schema tooling. Endpoint paths, request/response models, dependencies, authorization, status codes, serialization, and runtime behavior must remain identical. No migration, dependency, configuration, deployment, or production action is in scope.

## Tests and validation required after a future Gate
Run targeted Ruff UP006/UP035, `py_compile`, focused external-beta/API tests (or record `NO MATCHING TEST FILES`), route inventory before/after, response-shape and authorization review, import/annotation-only diff review, `git diff --check`, and secret scan.

Production impact: NONE
Recovery impact: SAFE HOLD
Status: SELECTION REVIEW COMPLETE — IMPLEMENTATION GATE REQUIRED
