# BATCH075 — Test Infrastructure & Warning Audit

Mode: read-only audit; no test changes, warning suppression, dependency upgrade, code/Ruff fix, or operational action.

## Pytest baseline
- Collection: 955 tests (`pytest --collect-only -q`)
- Latest controlled execution: 955 passed, 0 failed, exit 0
- Runtime: approximately 764 seconds (12m44s)
- Warnings: 6 non-blocking deprecation warnings

## Warning classification
- DEPENDENCY: Starlette TestClient/httpx compatibility deprecation (1)
- DEPENDENCY/TOOLING: Alembic `path_separator` fallback deprecation (3 occurrences)
- APPLICATION_CODE: `datetime.utcnow()` deprecations in teacher route (2 occurrences)
- TEST_CODE: 0
- OTHER: 0

Warnings were recorded only; none were suppressed or fixed.

## Test distribution (largest modules)
- tests/test_telegram_navigation.py: 17
- tests/test_telegram_route.py: 13
- tests/test_gemini_provider.py: 12
- tests/test_evidence_validation.py: 12
- tests/test_retrieval_evaluation.py: 10
- tests/test_baseline_change_control.py: 10
- tests/test_auth_dependencies.py: 10

## Performance/isolation observations
No per-test duration profile was captured in the existing baseline run. A future diagnostic run may use `--durations=20` and xdist qualification separately; neither is executed in this Gate. Existing baseline completes deterministically with no failures.

## Future recommendations (not executed)
1. Track dependency deprecations during planned upgrades.
2. Review application datetime deprecations under a dedicated semantic gate.
3. Capture duration profile before introducing parallelization; preserve fixture isolation.

Commit Gate 075: HOLD pending Commander approval.
