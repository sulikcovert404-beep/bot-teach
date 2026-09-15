# Browser E2E Tooling & Disposable Environment Design — 2026-09-15

## 1. Tool selection

The repository already contains a Node-based browser-like qualification harness (`scripts/browser-runtime-qualification.mjs`) and Python/CUA helpers for manual Telegram inspection. Use Playwright-compatible automation for a true browser runner when available; retain the Node harness for client lifecycle checks that do not require network access. Do not introduce a new framework until the runner and dependency budget are confirmed.

## 2. Disposable environment

Each run should use an isolated Compose project or CI service with:

- a throwaway database and Redis namespace;
- a pinned commit and explicit migration revision;
- seeded synthetic identities for all four roles and at least two tenants;
- deterministic setup and teardown, including volume cleanup after evidence capture;
- a dedicated base URL unavailable from public DNS.

No production environment, live Telegram account, real provider credential, or persistent user data may be used.

## 3. Test data rules

Seed only synthetic records: Student, Teacher, School Admin, Super Admin, two tenants, classrooms, published/pending content, and exam/assignment fixtures. Include Persian NFC/ZWNJ variants and mixed RTL/LTR formula samples. Record opaque fixture IDs only; never include personal data or secrets in traces.

## 4. CI execution path

Add a separate browser job only after the repository has a supported browser dependency and runner image. The job must install pinned dependencies, start the disposable stack, wait for readiness, execute the focused matrix, upload redacted traces on failure, and tear down with `if: always()`. It must not call live URLs or use production secrets.

## 5. Qualification gate

Before implementation or CI wiring, confirm:

- Tool selected and reproducibly installable.
- Disposable environment setup/teardown defined.
- Test data strategy approved and synthetic.
- Critical scenario matrix from `BROWSER_E2E_QUALIFICATION_PLAN_20260915.md` mapped to test IDs.
- Trace redaction and retention policy defined.
- CI execution path has an explicit timeout and cleanup step.

Current status: **PLANNING COMPLETE / IMPLEMENTATION NOT AUTHORIZED**. Production, runtime recovery, secrets, database mutation, migrations, Cloudflare, Telegram, and deployment remain out of scope.
