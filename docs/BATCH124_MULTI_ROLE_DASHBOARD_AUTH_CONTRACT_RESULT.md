# Gate 124 — Multi-Role Dashboard Contract & Authorization Qualification

Date: 2026-09-17

## Route and surface matrix

| Role | Dashboard surface | Data boundary |
|---|---|---|
| STUDENT | /student-dashboard/ | /api/v1/student/* |
| TEACHER | /teacher-dashboard/ | /api/v1/teacher/* |
| SCHOOL_ADMIN | /admin-dashboard/ | /api/v1/admin/* |
| SUPER_ADMIN | /platform/ | existing role-protected platform APIs |

All four HTML surfaces are public static shells. Protected data endpoints require a bearer session and role guard. Secure Role Preview and impersonation were excluded.

## Implementation

Added tests/test_multi_role_dashboard_authorization_contract.py with canonical-role acceptance, wrong-role denial, anonymous data-endpoint denial, and role matrix coverage. No production code, schema, migration, environment, provider, Telegram, or server changes were made.

## Validation

- New contract tests: 17 passed, 4 skipped (same-role cases in the negative matrix).
- Collection: 979 tests collected.
- Ruff on new test: PASS after import ordering correction.
- Full suite reached 100% with no test failure output; pytest exited 1 during temporary-directory cleanup because Windows denied access to pytest-current (WinError 5). This is an environment cleanup failure, not a test assertion failure.
- Full-suite result: test assertions passed; process exit code 1 due to cleanup permission.

## Dashboard status

| Dashboard | Result |
|---|---|
| Student | VERIFIED shell and guard contracts; persisted/runtime flow remains a gap |
| Teacher | VERIFIED guard contract; persisted membership/fallback qualification remains a gap |
| School Admin | VERIFIED shell and guard contract; multi-tenant runtime workflow remains a gap |
| Super Admin | VERIFIED shell/role guard contract; real Telegram /platform/ smoke and secure preview remain unverified |

## Findings and boundaries

The shared require_roles guard correctly rejects missing credentials and wrong canonical roles with 401/403 semantics. Static dashboard shells do not establish authorization by themselves. Storage/server, Telegram/public runtime, Gemini/provider, migration/RLS, and Secure Role Preview remain outside this Gate.

## Verdict

Gate 124 contract coverage is locally qualified for the new tests. Full-suite completion and runtime/persisted qualification remain open; no production impact.
