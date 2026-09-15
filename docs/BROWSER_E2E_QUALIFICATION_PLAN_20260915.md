# Browser E2E Qualification Plan — 2026-09-15

## Purpose

Define a controlled browser qualification for critical user journeys without using Production, changing runtime configuration, accessing secrets, or mutating a live database.

## Environment boundary

Preferred order: disposable environment with seeded test identities, then a CI browser runner if available. Local browser checks may validate static routing only. Production and live Telegram remain excluded until a separate Commander gate.

## Tool

Use the repository-approved browser automation harness (Playwright/CUA where available) against the disposable or explicitly isolated base URL. Record browser version, base URL class, commit, and test data identifiers without personal data or tokens.

## Critical scenarios

1. Authentication: unauthenticated request fails closed; valid test session resolves the expected role.
2. Dashboard routing: Student, Teacher, School Admin, and Super Admin reach only their permitted dashboard paths.
3. Mini App navigation: loading, ready, error/retry, BackButton, and MainButton states render correctly.
4. Exam/assignment flow: authorized start/save/submit/result path succeeds; invalid state and cross-user access are denied.
5. Tenant isolation: wrong tenant, classroom, grade, and role cannot expose data or navigation actions.
6. Persian UI: RTL layout, NFC text, ZWNJ, and mixed LTR formulas remain readable and semantically intact.

## Pass/fail criteria

- Each positive journey reaches its expected route and stable success state.
- Each negative journey is denied server-side with no sensitive data rendered.
- No console or network error is ignored when it affects the journey.
- No test uses a real credential, production user, or live data.
- Evidence includes URL, role fixture, response status, and screenshot/log reference where needed.

## Execution and reporting

Run the smallest focused scenario set first, then the complete matrix. Report PASS, FAIL, or BLOCKED per scenario and preserve traces. A missing provider credential or unavailable isolated environment is BLOCKED, never a fabricated PASS.

## Gate boundaries

This plan does not authorize browser tests against Production, Telegram webhook changes, deployment, runtime configuration changes, database mutation, migrations, Cloudflare changes, or provider activation.
