# Gate 088 — Repository Baseline Integrity Audit

Status: QUALIFICATION COMPLETE / COMMIT HOLD
Date: 2026-09-17
Mode: Read-only; no repository or operational mutation

## Git integrity

- Branch: `master`
- HEAD: `b13e37ffe7bc153e26e53aba7e82c99ebcca74e1`
- Recent quality/release commits: `842326e`, `e31281c`, `574aa67`, `b13e37f`
- Working tree contains pre-existing modified and untracked artifacts; all were left untouched.
- No cleanup, reset, stash, formatting, dependency, test, server, Docker, deployment, migration, environment, or database action was performed.

## Documentation consistency

- Gate 074 records the earlier 955-test baseline and 1,550 Ruff findings.
- Gate 086 supersedes that count with the authoritative controlled Gate 084 run: **958 passed, 0 failed, exit 0**, one upstream Starlette/httpx warning, and Alembic warnings resolved.
- Gate 087 correctly indexes the 958-test baseline and deferred register.
- Release/migration references remain consistent within the quality evidence chain: target `20260912_0021`.
- The older Gate 074 955 count is historical and is explicitly superseded by Gate 086; this is documented drift, not an untracked contradiction.

## Reproducibility markers

- Python: 3.13.14
- FastAPI: 0.141.1
- Starlette: 1.6.0
- httpx: 0.28.1
- pytest: 9.1.1
- Ruff: 0.16.6
- Alembic: 1.19.1
- Controlled test command and `--basetemp` procedure are recorded in Gate 086.
- No new regression run was started because this gate is read-only and the latest authoritative controlled run is already recorded.

## Operational anomaly history — OPEN INVESTIGATION

Gate 044 Storage Recovery Revalidation on `95.135.208.167` found severe I/O recurrence while application containers remained running:

- I/O PSI: `some avg10=93.59%`, `full avg10=85.99%`
- vmstat iowait reached approximately 97%
- iostat iowait 96.5–96.8%; vda write await peaked at 3748 ms
- API, PostgreSQL, Redis were running and local `/health` returned `{"status":"ok"}`

This is an operational storage observability concern. Application health alone is insufficient evidence of host stability. The anomaly remains **OPEN INVESTIGATION** and must not be represented as operational closure. No remediation was performed.

## Acceptance

- HEAD and recent evidence chain verified: PASS
- Documentation cross-check: PASS with historical 955→958 supersession documented
- Reproducibility markers present: PASS
- Storage recurrence captured as OPEN INVESTIGATION: PASS
- Repository mutation: NONE

## Commit boundary

Commit remains **HOLD** pending Commander review. This report itself has not been committed.
