# Production Release Artifact Digest Reconciliation — 2026-09-15

## Scope

Read-only reconciliation on `95.135.208.167`. No image pull/build, container lifecycle action, deploy, migration, config/secret access, rollback, or network change was performed.

## Release artifacts

| Artifact | SHA256 | Evidence |
|---|---|---|
| `canonical-release-prod-convergence-00c8fb7.tar.gz` | `e897693bbafd2390954e26cb75972f612a2e841565d4984f41141329a303e1ee` | On-host checksum matches the previously recorded canonical artifact SHA. |
| `canonical-release-exam-0021-assembly-21c905a.tar` | `1384bdf915db1052116ce2ff77813c9dea09887107371a1d81c2fcb58f80aa37` | On-host checksum; archive contains 0021 migration and application tree. |

The only standalone release manifest found is `releases/mvp-03e0300f/RELEASE_MANIFEST.txt`; it is a file hash list for an older packaged tree and does not contain a current Docker image digest mapping.

## Image mapping evidence

Current image candidates are distinct:

- `staging-api:latest` → `sha256:f13e836c7500fb84eb856bbbd70f7e2ff4fed42c46a254b423c6faab72b16315`
- `staging-api:canonical-0020` → `sha256:1b7bfe4558795d81e3357ab1316825a0c4db476df9937b6bd61e4c9406f1fdbb`
- `staging-api:canonical-0021-candidate` → `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd`
- `ai-teacher-staging-rc-api:latest` → `sha256:bfbb9100b2876bc638917a0a8d762323006193a7466e4e1cc8b29abaa13ac05b`

The current compose file uses `build` context rather than an image digest. Existing on-host parity documentation references an older `staging-api:latest` digest (`sha256:17bb6c3a...`), which matches none of the current candidates. Image labels identify the `staging` project for `latest`, but do not establish release identity.

## Release association and confidence

- Artifact checksum association to `canonical-release-prod-convergence-00c8fb7`: **HIGH** (checksum matches recorded value).
- Mapping that artifact to any current API image digest: **NONE FOUND**.
- Mapping `canonical-release-exam-0021-assembly-21c905a` to `canonical-0021-candidate`: **UNPROVEN**; name similarity is insufficient.
- Current authoritative production API image: **UNKNOWN**.

## Recommendation

`RESTORE GATE: HOLD / NOT READY`. Obtain an owner-signed or CI-generated manifest that explicitly binds release identifier, source commit, image digest, and build timestamp. Until then, do not choose by tag, creation time, or archive filename; do not start/recreate the API or rebuild an image.

## Mutation audit

No Docker lifecycle action, build/pull, environment/config change, database/migration change, Cloudflare change, or webhook change occurred.
