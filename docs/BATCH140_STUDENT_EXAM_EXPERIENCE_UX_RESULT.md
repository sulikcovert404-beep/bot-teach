# Gate 140 — Student Exam Experience UX Result

Date: 2026-09-17

## Status

IMPLEMENTED LOCALLY — frontend flow now uses the persisted student exam contracts.

## Before

The Mini App loaded `/api/v1/exams/bank` and graded answers in the browser, exposing question-bank data outside an assignment flow and allowing client-side score calculation.

## After

- Loads the authenticated student's published assignments from `/api/v1/student/v1/assignments`.
- Shows an honest empty state when no assignment exists.
- Starts the selected assignment through `/api/v1/student/exam-assignments/{assignment_id}/attempts`.
- Renders the persisted question snapshot returned by the service.
- Saves answers through the PATCH attempt contract.
- Submits through the POST attempt contract and displays the server result.
- Disables the submit action during the request and surfaces authorization/network errors.
- Escapes server-provided text before rendering.

## Validation

- `node --check web/mini-app/app.js`: PASS
- Backend focused exam/assignment suites: 20 passed, 4 skipped, 0 failed, 1 upstream deprecation warning.
- No frontend test harness was present; no dependency was installed.

## Boundaries

No schema, migration, backend contract, production, Telegram, provider, or server changes were made.

## Remaining contract limitation

The current backend does not expose a dedicated assignment detail/status endpoint or a resume endpoint. The UI consumes the existing start/save/submit/result contracts and reports unavailable states from their responses; richer pre-start publish/close status remains a backend contract gap.

Gate 140 commit: HOLD
