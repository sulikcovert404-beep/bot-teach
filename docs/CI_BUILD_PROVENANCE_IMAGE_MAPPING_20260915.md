# CI Build Provenance and Image Mapping — 2026-09-15

## Scope

Read-only review of repository workflows, GitHub Actions run metadata, and on-host release/image evidence. No build, push, deploy, secret access, or production mutation occurred.

## CI workflow evidence

`.github/workflows/ci.yml` defines a Docker job using `docker/build-push-action@v6` with `push: false` and tag `ai-education-platform-iran:ci`. It does not publish an image, record a digest artifact, or bind a release identifier to a registry digest. The staging-smoke job builds locally with `docker compose up -d --build` and likewise emits no durable image provenance record.

Recent CI runs for commits `105ab13`, `6b6c6e7`, `38317b1`, `242bd65`, and `6d0629e` completed with quality failure; Docker and staging-smoke were skipped because they require the quality job. Browser E2E is independent and passed in its qualifying run, but it does not build the production API image.

## Mapping findings

- Canonical release archive `canonical-release-prod-convergence-00c8fb7.tar.gz` checksum was verified separately as `e897693b...`; this confirms artifact integrity, not an image mapping.
- No GitHub workflow artifact, release asset, tag, or build log binds the production release commit to `staging-api` digest `sha256:f13e836c...`, `sha256:1b7bfe45...`, or `sha256:24c0135f...`.
- The only on-host parity report references obsolete digest `sha256:17bb6c3a...`, which matches none of the current candidates.
- The current compose file uses a Dockerfile build context and does not pin an image digest.

## Confidence and recommendation

| Item | Result | Confidence |
|---|---|---|
| CI workflow inspected | PASS | High |
| CI publishes production image digest | NO | High |
| Release → commit mapping | Partial (archive name/checksum only) | Medium |
| Commit → image digest mapping | NOT FOUND | High |
| Authoritative API image | UNKNOWN | High |

**RESTORE GATE: HOLD / NOT READY.** A signed or CI-generated provenance record is required containing release ID, commit SHA, Docker image digest, build timestamp, and (if applicable) registry reference. Until then, do not infer identity from tags, local creation times, or archive names and do not start/recreate/rebuild the API.

## Mutation audit

No image build/push/pull, container lifecycle operation, deployment, migration, environment/configuration change, Cloudflare change, or webhook change was performed.
