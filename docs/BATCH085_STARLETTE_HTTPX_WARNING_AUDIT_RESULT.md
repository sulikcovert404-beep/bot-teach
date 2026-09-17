# Gate 085 — Starlette/httpx Warning Ownership & Compatibility Audit

Status: COMPLETE (read-only)

## Exact warning

`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

Observed at `fastapi/testclient.py:1` while importing Starlette's TestClient.

## Dependency chain

- FastAPI: 0.141.1
- Starlette: 1.6.0
- httpx: 0.28.1
- pytest: 9.1.1
- Project constraint: `httpx>=0.27,<1.0`

## Ownership

The warning is emitted by the FastAPI/Starlette TestClient compatibility layer during import. It is dependency interaction, not application runtime code. Existing tests use `fastapi.testclient.TestClient`; selected async tests already use `httpx.ASGITransport`.

## Classification

`UPSTREAM-WAIT` / `NO-LOCAL-ACTION`.

The warning recommends the future `httpx2` package. No supported local package change was authorized or validated in this gate. Suppression, fixture changes, and dependency edits were explicitly excluded.

## Future action boundary

Revisit only when the project's supported FastAPI/Starlette/httpx2 compatibility and lockfile policy are defined. A future dependency migration must be a separate reviewed gate with a full regression run.

## Validation

Constructing `TestClient(FastAPI())` with warnings enabled reproduced exactly one warning. No source, test, fixture, requirements, lockfile, server, Docker, database, migration, or environment changes were made.

## Acceptance

- warning fully traced: PASS
- owner identified: PASS
- future action boundary defined: PASS
- zero mutation: PASS
