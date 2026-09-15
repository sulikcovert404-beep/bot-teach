# Production Image Provenance Gap Report — 2026-09-15

## Current chain

The host has a verified canonical release archive and several API image candidates, but the chain is incomplete:

`release archive → source commit → CI build → image digest → registry/reference → runtime container`

The archive checksum is known and verified. Current image digests are present locally. The compose file uses a Dockerfile build context and `env_file`, and no API container currently exists.

## Missing evidence

- No signed release manifest binds the production release identifier to a source commit and current image digest.
- CI Docker builds use `push: false` and publish no digest or attestation artifact.
- No registry reference or immutable tag is recorded for the candidate images.
- Existing parity documentation references an obsolete image digest.
- No runtime container metadata can confirm the selected artifact because `staging-api-1` is absent.

## Risk

Selecting an image by `latest`, local tag, creation time, or filename could start an unapproved or incompatible application against the existing database. The risk includes schema/runtime drift, untraceable rollback, and inability to reproduce the deployed artifact.

## Required future controls (design only; not implemented here)

1. Pin deployment to an immutable image digest.
2. Generate CI build provenance containing release ID, commit SHA, digest, build timestamp, and workflow run ID.
3. Publish SBOM and signed attestation for the image.
4. Store a release manifest as a protected artifact and verify it before lifecycle actions.
5. Record the selected digest in deployment metadata and health/readiness evidence.
6. Make staging-smoke emit the built image digest and associate it with the tested commit.

## Decision

`API-RUNTIME-PROVENANCE-001 = OPEN`  
`RESTORE GATE = HOLD / NOT READY`

The safe next action is to obtain an owner/CI-signed manifest for an existing candidate. If no such evidence can be produced, report STOP and keep the API absent. No image selection, build, push, deploy, start, migration, environment change, Cloudflare change, or webhook change was performed.
