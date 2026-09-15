# RUFF PHASE 2 BATCH 100 SELECTION REVIEW — 2026-09-15

Candidate: `tools/ai_metrics.py`

HEAD findings: 1 UP035 finding, confirmed by Ruff JSON (`typing.Iterable`).

Symbols: `Iterable` import and annotations in `parse_event_lines` and `build_snapshot`.
Remediation: import-only modernization (`typing.Iterable` → `collections.abc.Iterable`); no annotation shape change required.

Blast radius: Low. This is a read-only metrics CLI utility and is outside application runtime paths.
Contract/runtime/introspection risks: Minimal; `collections.abc.Iterable` preserves runtime and typing semantics for these annotations.
Focused tests: No dedicated test file found; validate module compile and direct function smoke.
Validation proposed: targeted Ruff UP006/UP035, py_compile, direct import/function smoke, git diff --check, secret scan, scope review.

Production impact: NONE
Recovery impact: SAFE HOLD

Implementation status: NOT STARTED; awaiting Commander Implementation Gate.
