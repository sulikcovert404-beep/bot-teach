# Browser E2E Implementation Decision Matrix — 2026-09-15

| Decision | Options | Selected | Owner | Impact |
|---|---|---|---|---|
| Package owner | Platform maintainers / CI maintainers / shared ownership | **Pending** | Commander | Defines upgrades and security response |
| Node strategy | Repository-pinned LTS / runner default / container-only | **Pending** | CI | Reproducibility and support window |
| Package manager | npm / pnpm / yarn | **Pending** | Package owner | Lockfile and cache behavior |
| Lockfile | `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` | **Pending** | Package owner | Deterministic dependency resolution |
| Runner image | Playwright pinned image / custom image / hosted browser | **Pending** | CI/Runtime | Browser availability and build time |
| Browser matrix | Chromium only / Chromium + Firefox / full supported matrix | **Pending** | QA | Coverage versus runtime cost |
| Trace retention | Failure-only short retention / all runs / external store | **Pending** | Security/QA | Evidence value versus data exposure |
| Fixture ownership | Test module seed / disposable service / CI script | **Pending** | QA/Backend | Isolation and teardown reliability |
| CI trigger | Pull request only / push and pull request / scheduled | **Pending** | CI | Feedback speed and compute cost |

## Decision constraints

- Use synthetic identities and disposable data only.
- Redact cookies, authorization headers, tokens, personal data, and provider output from traces.
- Keep browser E2E in a separate job with explicit timeout and unconditional cleanup.
- Do not call Production, live Telegram, Cloudflare, or real providers.
- Any selected dependency or workflow change requires a new Commander Implementation Gate.

## Recommendation for the next gate

Choose one pinned Node LTS plus a repository lockfile, a Playwright pinned runner image, Chromium-first coverage, failure-only redacted traces with short retention, and a disposable fixture seed owned by QA/Backend. These are recommendations only; no option is selected by this document.

## Status

**DECISION MATRIX READY / IMPLEMENTATION NOT AUTHORIZED.** Production, runtime, secrets, database, migrations, Cloudflare, Telegram, and deployment remain unchanged.
