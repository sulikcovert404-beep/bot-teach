# Ruff Remediation Execution Plan

Date: 2026-09-15  
Status: Planning only; no remediation started

## Guardrails

- Preserve runtime behavior and the existing full-lint command.
- Work in small, reviewable commits with targeted tests.
- No broad auto-fix, Ruff configuration change, workflow change, dependency update, or Production/Recovery action without a separate approval gate.

## Phase 1 — Low-Risk Tranche

Scope:

- `I001` import ordering/formatting;
- `F401` unused imports;
- formatting-only corrections where behavior is unchanged.

Method:

1. Select one directory or bounded file set.
2. Generate a reviewed diff (auto-fix may be used only within that bounded set).
3. Run targeted tests and the secret scan.
4. Re-run Ruff and record the count delta.

## Phase 2 — Compatibility Review

Review `UP006` and `UP035` manually against the supported Python 3.12 target and public typing contracts. Confirm annotations, runtime imports, and adapters remain compatible before editing.

## Phase 3 — Behavioral Review

Handle `B008`, `ASYNC210`, and `ASYNC230` one finding at a time, with explicit review of FastAPI dependency construction, async handlers, file/network operations, cancellation, and exception paths. Each change requires targeted behavior tests.

## Validation Per Tranche

- [ ] diff reviewed by owner;
- [ ] targeted tests pass;
- [ ] relevant full regression pass;
- [ ] Ruff count and remaining rules recorded;
- [ ] secret scan pass;
- [ ] no production impact.

## CI and Rollout

Keep the current CI gate unchanged while planning. A later gate may decide whether to require full lint immediately or introduce a reviewed baseline/changed-lines policy; either choice must retain visibility of legacy debt and be validated in CI.

## Abort Conditions

Stop and report if a lint fix changes runtime behavior, requires a dependency/schema/config change, touches Production or Recovery, or exposes secret/private data.

## Recommendation

Begin with a single low-risk directory tranche and establish a before/after evidence record. Do not claim the quality gate green until a subsequent CI run proves it.

`Production impact: NONE`.
