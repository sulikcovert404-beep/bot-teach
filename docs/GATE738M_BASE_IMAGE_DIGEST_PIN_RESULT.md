# Gate738M — Official Base Image Digest Resolution and Pin

Date: 2026-10-04

## Verdict

`PASS`

The exact official `linux/amd64` child manifest for `docker.io/library/python:3.12-slim` was resolved and verified from Docker Hub registry metadata. The Dockerfile now pins that immutable digest, and only that exact digest was pulled into the local Docker image cache. The signed provenance for the previous operational runtime does not identify its base image, so the selected current base is recorded as `BASE_IMAGE_UPDATE=YES`; Gate738L must fully qualify the new candidate before any release claim.

## Pre-change candidate identity

- Worktree: `D:\project\ai-teacher-gate731-target`
- Branch: `codex/gate731-target`
- Base Git HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Source state: `UNCOMMITTED_CANDIDATE`
- Dockerfile SHA-256 before pin: `43344df307d45b6860ee1cb95053a3166240510decd63d5d13bd9dabf07af3e1`
- Deterministic pre-change candidate manifest SHA-256: `3872caa9dfb7902129f5607a0ac8af0459b6e9650d0b1ad83e390ee43d44b1ee`
- Candidate manifest entries: 403 files

The manifest covers the files copied by the Dockerfile (`app/`, `migrations/`, `web/`, `pyproject.toml`, and `alembic.ini`), plus `Dockerfile` and `.dockerignore`. Entries are sorted by repository-relative POSIX path and include each file's SHA-256 and byte length; the manifest digest is SHA-256 of canonical JSON (`sort_keys=true`, compact separators). Ignored caches, secrets, VCS metadata, and tests excluded by the Docker build context are not included.

## Previous runtime provenance review

The old runtime attestation was re-verified using the preinstalled GitHub CLI, with no installation or image pull for that artifact:

- Subject: `ghcr.io/sulikcovert404-beep/bot-teach`
- Subject digest: `sha256:9fa6fd7e95626bf2c60fb6a1dd1e13f64620eb50b0e7be9ea9ee90a92d24c462`
- Predicate: SLSA provenance v1
- Verified source: `77c3bbce0cd25a0b32f9c4bbea0e3c5611e5195a`
- Verified workflow/run: `.github/workflows/ci.yml`, run `35588891399`, attempt 1
- Resolved dependencies in the signed statement: source Git repository/commit only
- Base image digest or base-image material in the signed statement: `NOT PRESENT`
- Historical base digest: `NOT PROVEN`

Because the historical base is not proven by the signed statement, the Gate's explicit fallback was used: resolve and pin the current official base. The update is explicit; no claim is made that the old runtime used this base.

## Official registry evidence

Read-only requests were made to the Docker Hub Registry API for `docker.io/library/python`; no unrelated registry or image was queried.

| Check | Evidence | Result |
|---|---|---|
| Official tag index | `3.12-slim`; HTTP 200; OCI image index | PASS |
| Index digest | Header and recomputed body SHA-256: `sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016` | PASS |
| Platform child | Exactly one `linux/amd64` descriptor; OCI image manifest; `sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8` | PASS |
| Direct child fetch | HTTP 200; registry digest header and recomputed manifest-body SHA-256 both equal the child digest | PASS |
| Config blob | SHA-256 matches config descriptor `sha256:414a398990af718f018ff9c23cea0e7489b7986eb54f2b1d7cc874c99ebc7364` | PASS |
| Platform/config | `os=linux`, `architecture=amd64` | PASS |
| Python patch version | `3.12.15` from image config | RECORDED |
| Debian base family | Official image history records Debian `trixie`, `amd64` | RECORDED |

Index digest and platform child digest are intentionally recorded separately. The project release target is `linux/amd64`; the Dockerfile uses the platform-specific child digest so the selected runtime platform is directly bound to the immutable manifest.

## Pin and controlled pull

- Dockerfile line 1 before: `FROM python:3.12-slim`
- Dockerfile line 1 after: `FROM docker.io/library/python:3.12-slim@sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`
- No other Dockerfile line changed.
- Dockerfile SHA-256 after pin: `5ef8e40c25c080b69bf3b749babde554c8bcf81d6694449bd1ed8f1d1be9626f`
- Post-pin deterministic candidate manifest SHA-256: `9c6847cee8c46fc70f013ec9620bdcd56044628afbff5554326641c9fd87d8e1`
- Post-pin candidate manifest entries: 403 files
- Exact-digest pull: PASS; Docker reported `sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`
- Local inspect: image ID/repo digest match the pinned child digest; `OS=linux`, `ARCH=amd64`; image config reports Python 3.12.15.
- `git diff --check -- Dockerfile`: PASS.

## Migration identity snapshot

The base pin does not change application or migration files. Their snapshot hashes are:

| Migration | SHA-256 |
|---|---|
| `20261003_0027_submission_revision_parent_identity.py` | `da114ad085304c17842faab41382a51968a6fb4b6aeea524b2c405e4db95e76b` |
| `20261003_0028_submission_revision_expand.py` | `d06d6d3b99e5abdc97ed39dd681519e01c97933a1e26a210bc7125266e75720b` |
| `20261003_0029_submission_review_revision_index.py` | `c8d4a226649646dbb43a30bc59fb828564c2c111371a92c06aa16c690f8f957a` |
| `20261003_0030_submission_revision_contract.py` | `da81fcfe614ac036123cb48539084f13576ba7e5cc0c1a6c1595d9179dc3c32f` |
| `20261003_0031_submission_revision_compat_cleanup.py` | `c1c82f9c8a602651e5760221593754f1c49f18c957b8aab39cc45c6b64cfe6c6` |
| `20261004_0032_writer_admission_drain_control.py` | `3bd3b7dd16beb437c64b01ad08ffb2c819c25fb93108e872ccd392bd41174bfb` |

The workspace Alembic graph remains at one head, `20261004_0032`; the base pin did not edit migration files.

## Scope and next step

- Local Docker image cache: exact pinned base digest added.
- Candidate image build, application runtime, disposable database, test run: not performed in Gate738M.
- Production, staging, SSH, remote registry push, deployment, migration, commit, and other projects: untouched.
- Gate738L must resume from this new manifest and Dockerfile identity. Because `BASE_IMAGE_UPDATE=YES`, the full artifact, reproducibility, runtime/drain, security, regression, and IPv6 checks remain mandatory.

Next action: continue Gate738L from the post-pin frozen candidate snapshot; include base digest `sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8`, Python `3.12.15`, Debian `trixie`, the new manifest digest, and the explicit base-update finding in artifact provenance.
