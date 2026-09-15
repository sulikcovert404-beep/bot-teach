# Development Quality Gate Execution Matrix — 2026-09-15

| Gate | Trigger | Owner | Required before | Failure action | Automation |
|---|---|---|---|---|---|
| Static lint | Every change / PR | CI | Merge | Block quality gate | Automated |
| Type safety | Every change / PR | CI | Merge | Block quality gate | Automated |
| Full regression | Every change / PR | CI | Merge/release review | Block quality gate | Automated |
| Secret scan | Every change / PR | CI/Security | Merge | Block and investigate | Automated |
| Config contract | Every CI run | CI/Runtime | Release qualification | Block | Automated |
| Migration qualification | Release candidate | CI/DB maintainers | Any migration decision | Block; preserve evidence | Automated disposable |
| Migration rollback | Release candidate | CI/DB maintainers | Migration approval | Block; do not touch live DB | Automated disposable |
| Health/readiness | Smoke or runtime candidate | Runtime maintainers | Release/cutover | Block; diagnose environment | Automated + manual runtime |
| Retrieval/vector | Retrieval changes | RAG maintainers | RAG release | Block affected release | Automated tests |
| Tenant isolation | Auth/tenant changes | Security maintainers | Merge and release | Block; security review | Automated tests + targeted review |
| Docker build | Every release candidate | CI/Runtime | Artifact promotion | Block artifact | Automated |
| Staging smoke | Disposable staging candidate | Runtime maintainers | Staging decision | Block; preserve logs | Automated |
| Dependency audit | Every CI run / scheduled | Security/CI | Release | Warn or block per severity | Automated |

## Manual decision gates

- Production recovery, runtime configuration restoration, live database or migration actions, Cloudflare, webhook, and Telegram changes require a separate Commander gate.
- Merge requires an explicit destination and merge authorization; the current CI hardening merge to `master` is complete.
- Agent recommendations are advisory and require Codex validation plus Commander decision before consequential changes.

## Evidence and failure handling

- Record command, revision, environment class (local/disposable/staging/live), result, and relevant logs without secrets.
- A failed gate blocks only its dependent path; continue independent development work.
- Never convert a blocked credential, unavailable provider, or local dependency problem into a fabricated PASS.
- Keep historical qualification records immutable and label them as historical.

## Current open items

- Refresh the local `.venv` to run health/environment tests.
- Keep expected migration head references aligned as releases advance.
- Recovery remains Safe Hold with RUNTIME-CONFIG-001 open and HOST-IO-002 on watch.
