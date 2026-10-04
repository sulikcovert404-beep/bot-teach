# Gate738T — Legacy 410 OpenAPI Contract Alignment

Date: 2026-10-04
Mode: Controlled workspace-only documentation and contract-test change
Worktree: `D:\project\ai-teacher-gate731-target`
Branch / HEAD: `codex/gate731-target` / `e4140c4d55a2943c53ecc187a28729663073d48d`

## Verdict

`PASS` — OpenAPI now reflects the retired endpoint's existing runtime contract. A valid authenticated TEACHER request and an authenticated ADMIN request still receive HTTP 410; authentication and role rejection remain in force; the endpoint does not resolve a database session. No runtime business logic was changed.

The external-client absence question remains **UNKNOWN / NOT PROVEN**. Gate738T only removes the misleading documented success response; it does not close that separate compatibility uncertainty.

## Frozen before-state

| Item | Before Gate738T |
|---|---|
| Endpoint | `POST /api/v1/teacher/v2/classrooms/{classroom_id}/members` |
| Source file | `app/api/routes/teacher.py` |
| Source SHA-256 | `7e377d01513ade7ddd226d0cfbdff8c6785ebddc37dbc39dd023668c87abeafb` (Gate738S) |
| Runtime | Authenticated TEACHER/ADMIN route handler raises HTTP 410, fixed detail; no DB-session dependency |
| OpenAPI operationId | `add_persistent_member_api_v1_teacher_v2_classrooms__classroom_id__members_post` |
| OpenAPI responses | `201`, `422`; no documented `410` |
| Deprecated | Not set |
| Alembic head | `20261004_0033` |

## Changes

- In `app/api/routes/teacher.py`, changed the decorator metadata to status 410, marked the operation deprecated, and documented its retired/no-mutation behavior.
- Added `LegacyMembershipRetiredResponse` to represent the handler's existing stable `{"detail": "Legacy classroom membership mutation is disabled"}` response.
- Preserved the operationId and the current handler body, authorization dependency, role set, and 410 detail.
- Added `tests/test_gate738t_legacy_410_openapi_contract.py` for HTTP/auth/session and generated-schema assertions.
- No migration or generated-client artifact was changed.

Current `app/api/routes/teacher.py` SHA-256: `78d79948c990a35efb827dc6b866b657d83b0c837f4faeb9528081bd1510e8c5`.

## OpenAPI after

- Exact path and POST operation remain present.
- `deprecated = true`.
- OperationId remains `add_persistent_member_api_v1_teacher_v2_classrooms__classroom_id__members_post`.
- `410` is documented with the response model containing the actual string `detail` field.
- `201` is absent.
- `422` remains because an authenticated malformed body reaches FastAPI validation and returns 422; the contract test proves this.

## Contract and security tests

Focused run:

`python -m pytest -p no:cacheprovider -q tests/test_legacy_tenant_membership_boundary.py tests/test_gate738t_legacy_410_openapi_contract.py`

Result: **3 passed**.

Assertions include:

- No credentials + valid body → 401.
- Authenticated STUDENT + valid body → 403.
- Authenticated TEACHER + valid body → 410 with the existing detail.
- Authenticated ADMIN + valid body → 410; no ADMIN compatibility bypass.
- Authenticated TEACHER + malformed body → 422.
- A fail-if-resolved `get_session` override records **zero calls** across those requests.
- Generated OpenAPI has 410/deprecated, no 201, stable operationId, and the response detail schema.

No database connection or mutation was used in these tests.

## Regression and static checks

- Full pytest: **1007 passed, 23 skipped, 0 failed**.
- Skip reasons: 19 tests require explicitly named disposable PostgreSQL URLs/ports that were not configured; 4 are intentionally skipped because their positive case is covered by another acceptance test.
- Pytest emitted one existing Starlette/httpx deprecation warning for `TestClient`.
- Ruff on the new Gate738T test: **PASS**.
- Whole-file Ruff on `teacher.py` reports 44 findings in its existing broader file contents; none falls on the new response model or route metadata. No autofix was applied; Gate738T Ruff delta is **0**.
- Python compileall on the two changed Python files: **PASS**.
- `git diff --check` on the route and explicit whitespace scan for the new test/report: **PASS**.
- Alembic head remains the single `20261004_0033`; migration files are unchanged.

## Client risk and replacement wording

Gate738S found no active first-party caller in the inspected sources/artifacts, but external dependency absence was not proven. That status remains UNKNOWN.

The available enrollment route is SCHOOL_ADMIN-only and is not a drop-in replacement for TEACHER/ADMIN clients. This Gate does not claim otherwise, redesign an API, or migrate a client.

## Mutations

- Runtime behavior / authorization: **NONE**
- Database or schema: **NONE**
- Migration: **NONE**
- Docker: **NONE**
- Production / Staging / SSH / deploy: **NONE**
- Commit: **NONE**
- Changed for Gate738T: route documentation metadata, contract test, this report only.

The Gate738S client-dependency report is `docs/GATE738S_LEGACY_410_CLIENT_DEPENDENCY_RESULT.md`. External consumer risk remains open independently of this OpenAPI correction.

## Final

`OPENAPI CONTRACT ALIGNED`

Production/Staging deployment and endpoint re-enablement remain outside this Gate.

