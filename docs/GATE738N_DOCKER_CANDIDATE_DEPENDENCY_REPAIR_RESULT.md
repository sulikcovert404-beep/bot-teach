# Gate738N — Docker Candidate Dependency Repair and Runtime Qualification

Date: 2026-10-04

## Verdict

**GATE738N = PASS — DEPENDENCY REPAIR RUNTIME QUALIFIED (LOCAL CANDIDATE ONLY)**

This qualifies the current uncommitted workspace candidate for local review. It does not authorize deployment or any staging/production action.

## Scope and provenance

- Branch: `codex/gate731-target`
- Base Git HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Source state: `UNCOMMITTED_CANDIDATE`
- Pinned base: `docker.io/library/python:3.12-slim@sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`
- Candidate manifest: `docs/GATE738N_CANDIDATE_FREEZE_MANIFEST.json`
- Candidate image-input manifest SHA-256: `sha256:49bcac4f00e1d6643e4569c799acefa5b220bac9dbfdbacd5c09c4fe8a763d9b`
- Freeze manifest file SHA-256: `bb25bb9dd5f10f7ee474ca7ad1cea604d4226a0786826dc3c8a5af4e3f89a878`
- Dockerfile SHA-256: `4bb2ff74177a6c97c2c44b5aeefd7476c894d4af08f9cc7fac839a15b2d94045`
- pyproject.toml SHA-256: `eac92d268175c3fe88167336eac588530189cf84a7aa843e90ec3d908e3c86d3`

## Repair

`pyproject.toml` now declares `sqlalchemy[asyncio]>=2.0,<3.0` and explicitly pins `greenlet==3.5.4`. The Dockerfile installs the canonical project dependency groups with `pip install --no-cache-dir ".[dev]"`, replacing its separate manually maintained package list. This addresses the previous image failure where SQLAlchemy's async path could not import because greenlet was absent, and keeps installation subject to the project's declared constraints.

A preliminary resolver experiment selected greenlet 3.5.6 and was stopped before image creation. The qualified candidate uses the explicit 3.5.4 pin. No external runtime was modified.

## Independent candidate builds

Two `--no-cache` local builds completed with Gate738N provenance labels:

| Build | Tag | Image ID |
|---|---|---|
| A | `codex-gate738n-qualified-a-20261004` | `sha256:38285ebd56de395e92760aba8c9bd423beb0faeeb12a9f256ab5d0c69bed1bcd` |
| B | `codex-gate738n-qualified-b-20261004` | `sha256:b8a64cae9442a58bb8bb86dd247c3991e6e552a8dda10942a19983bc2fda2a03` |

Both images carry matching labels for Gate738N, base Git HEAD, uncommitted source state, candidate manifest SHA, and pinned base digest. The image IDs differ. The container-visible `pip freeze` inventories match (SHA-256 `338c7a5aebdd121bff576a0244370530cd0c5d1c2218d53f4da440331f49c06c`); content hashes for `app/`, `migrations/`, and `web/` match (SHA-256 of the comparison listing: `bde0fd15e17f26c712c46a6c8d280b1d7c98f6d218cfe318e5278a08641b1531`). Thus source payload and resolved package inventory match, while full image-byte identity is not established.

## Artifact checks

The following passed independently in both candidate images:

- `import app.main`; SQLAlchemy `2.1.3`; greenlet `3.5.4`.
- `python -m pip check`: no broken requirements.
- `alembic heads`: `20261004_0032 (head)`.

On a new, disposable PostgreSQL container on a private Docker network with no published host port:

- `pg_isready`: accepting connections.
- `alembic upgrade 20261004_0032`: completed successfully.
- `alembic current` and direct `alembic_version` query: `20261004_0032`.
- A separately named disposable Redis returned `PONG`.
- API containers from both candidate images started, with restart count `0` and no published ports.
- From within the private Docker network, each image returned HTTP 200 for `/health` and `/health/ready`; readiness reported migration head `20261004_0032`.

No staging or production services, databases, secrets, ports, or projects were involved.

## Workspace validation

- Full workspace regression: **1003 passed, 14 skipped, 1 warning** (`python -m pytest -q`).
- `python -m compileall -q app migrations tests scripts`: PASS.
- `git diff --check`: PASS (only Git line-ending notices).
- Ruff over `app migrations tests scripts`: 626 diagnostics currently present. Gate738N changed only `Dockerfile` and `pyproject.toml`, with no Python source edits; therefore no Gate738N Python diagnostic delta was introduced. Ruff was not applied to Dockerfile/TOML as those are not Python inputs.

## Safety and retained state

- No SSH connection, staging/production operation, registry push, deployment, migration commit, or secret read occurred.
- Migration DDL was run only against the newly created disposable local PostgreSQL used for this qualification.
- Gate738N disposable containers and network are removed after evidence collection; the two qualified image tags are retained for reviewer inspection.
- Pre-existing containers and networks belonging to other Gates/projects were not changed.
- No source changes were committed. Existing unrelated worktree modifications remain untouched.

## Follow-up

Review the exact Dockerfile and `pyproject.toml` diff before any separately authorized deployment Gate. The differing final image IDs should remain visible in release provenance; this report does not claim byte-identical builds.
