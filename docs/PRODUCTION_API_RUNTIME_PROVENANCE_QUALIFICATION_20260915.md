# Production API Runtime Provenance Qualification — 2026-09-15

## Scope

Read-only qualification on `95.135.208.167`. No Docker lifecycle action, build, deploy, env read/edit, migration, rollback, or network change was performed.

## Candidate images

| Reference | Digest | Created |
|---|---|---|
| `staging-api:latest` | `sha256:f13e836c7500fb84eb856bbbd70f7e2ff4fed42c46a254b423c6faab72b16315` | 2026-09-12 17:33:54 +01:00 |
| `staging-api:canonical-0020` | `sha256:1b7bfe4558795d81e3357ab1316825a0c4db476df9937b6bd61e4c9406f1fdbb` | 2026-09-14 16:32:24 +01:00 |
| `staging-api:canonical-0021-candidate` | `sha256:24c0135f282415b90029d601c1ef941839ae7082c16c71c95778592e41a564fd` | 2026-09-14 17:44:58 +01:00 |
| `ai-teacher-staging-rc-api:latest` | `sha256:bfbb9100b2876bc638917a0a8d762323006193a7466e4e1cc8b29abaa13ac05b` | 2026-09-12 18:20:02 +01:00 |

All candidate metadata was inspected without reading container environment values. The canonical `latest` image history contains application, migration, and web assets and runs `uvicorn app.main:app`; the candidate images show distinct creation/build histories.

## Compose evidence

`/opt/apps/ai-teacher/deploy/staging/docker-compose.yml` defines `api` with `build: context=../.., dockerfile=Dockerfile`, not a pinned image reference. It uses `/etc/apps/ai-teacher/staging.env` via `env_file`. The same compose file defines `migrate`; no API container currently exists.

## Release/source references

The on-host release tree includes `releases/mvp-03e0300f/RELEASE_MANIFEST.txt`, canonical release archives, and a prior parity report referencing `staging-api:latest` at digest `sha256:17bb6c3af1a7d04c161ee8b508631a9be9453b846dd88a060168756fd11b925e`, which does **not** match the current `staging-api:latest` digest. No authoritative manifest mapping the current production target to one of the three staging API candidates was found in the bounded search.

## Compatibility assessment

- Runtime command shape is consistent across the `staging-api` candidates (`uvicorn app.main:app --host 0.0.0.0 --port 8000` observed in image history).
- Digest lineage is not established: current `latest`, canonical-0020, and canonical-0021-candidate are distinct; the only on-host parity document points to an older digest.
- Compose uses build semantics, so starting the service would not by itself prove which pre-existing image is authoritative.
- API container absence prevents runtime health/readiness or DB compatibility qualification.

## Verdict

**Canonical API image: UNKNOWN.**  
**API runtime provenance: OPEN.**  
**Recovery gate: HOLD.**

Recommendation: `RESTORE GATE NOT READY / HOLD`. Obtain an owner-approved release manifest or artifact digest that explicitly maps the production runtime to one candidate. Only after that evidence is recorded should a separate Commander gate consider creating/starting the API container. Do not select `canonical-0021-candidate` or rebuild based on tag names alone.

## Mutation audit

Docker start/stop/recreate: NONE  
Build/pull: NONE  
Env/config changes: NONE  
Migration/database changes: NONE  
Cloudflare/Webhook changes: NONE
