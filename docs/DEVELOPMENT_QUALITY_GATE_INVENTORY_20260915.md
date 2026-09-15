# Development Quality Gate Inventory — 2026-09-15

| Gate | Purpose | Command / Location | Status | Owner | Failure impact |
|---|---|---|---|---|---|
| Static lint | Python style and common defects | `ruff check app tests migrations scripts`; `.github/workflows/ci.yml` | Active CI gate | CI | Quality job fails |
| Type safety | Strict application typing | `mypy app`; `.github/workflows/ci.yml` | Active CI gate | CI | Quality job fails |
| Full regression | Application behavior coverage | `pytest -q`; `.github/workflows/ci.yml` | Active CI gate | CI | Quality job fails |
| Secret scan | Prevent tracked credentials | `python scripts/secret_scan.py` | Active CI gate | CI | Quality job fails |
| Config contract | Validate required production-shaped settings without real secrets | CI inline `Settings()` check | Active CI gate | CI | Quality job fails |
| Migration qualification | Explicit revision upgrade/current assertion | `tests/test_migration_roundtrip_qualification.py`; CI target `20260912_0021` | Active; 2 local tests passed | CI / DB maintainers | Migration confidence reduced |
| Migration rollback | Downgrade and explicit re-upgrade | CI `Verify migration rollback and re-upgrade` | Active CI gate | CI | Quality job fails |
| Health/readiness | API health and expected migration contract | `tests/test_health.py`, `tests/test_environment_readiness.py`; staging smoke | Local collection currently blocked by missing venv dependency | Runtime maintainers | Readiness evidence incomplete |
| Retrieval evaluation | Dataset/metric correctness | `tests/test_retrieval_evaluation.py`, `tests/test_retrieval_dataset.py` | Active test gate | RAG maintainers | Retrieval quality regression |
| Vector store | Vector persistence and scope behavior | `tests/test_vector_store.py`, persisted retrieval qualification | Active test gate | RAG maintainers | Retrieval/runtime risk |
| Tenant isolation | Context, resolver, and concurrency isolation | `tests/test_tenant_context.py`, `test_tenant_resolver.py`, `test_tenant_concurrency_qualification.py` | Active test gate | Security maintainers | Confidentiality risk |
| Docker build | Reproducible image build | CI `docker` job | Active CI gate | CI / Runtime | Artifact unavailable |
| Staging smoke | Disposable Compose, readiness, backup archive | `.github/workflows/ci.yml` `staging-smoke` | Active CI gate | Runtime | Staging qualification fails |
| Dependency audit | Known vulnerable package detection | CI `pip-audit` job | Active CI gate | Security / CI | Security gate fails |

## Cross-gate rules

- CI migration targets are explicit (`20260912_0021`); do not use `alembic upgrade head` for qualification.
- Local, disposable, staging, and Production evidence are separate; a local pass cannot be promoted to live readiness.
- Secrets and real provider credentials are never required for static qualification and must not appear in reports.
- Recovery remains Safe Hold; no runtime, database, migration, Cloudflare, Telegram, or deployment action is implied by this inventory.

## Open improvements

- Refresh the local `.venv` with the documented procedure so health/environment collection can run locally.
- Keep CI and staging smoke expected-head sources aligned as the release lineage changes.
- Add a visible marker or index for historical operational documents to reduce confusion with current gates.
