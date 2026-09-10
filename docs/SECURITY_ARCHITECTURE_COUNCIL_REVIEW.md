# Security Architecture Council Review

## Scope
Milestone 3 security hardening review, evidence-only. Production remains unchanged. Agent recommendations are advisory.

## Agent responses

### Claude Sonnet 5
Complete. Confirmed from sanitized evidence that `scope` is declared but omitted from `PgVectorStore.search` filtering; tenant tables use plain `tenant_id` strings without visible FK/RLS; `data_isolation_verified` defaults true without enforcement; retrieval does not demonstrate a `PublicationPointer` join. It also flagged that the auth excerpt sanitization corrupted Python structure, so JWT secret validation remains unverified. Recommended `RLS_SELECTED_TABLES`, pending Commander decision and migration review.

### GLM
Complete from prior review. Raised cross-tenant IDOR, role escalation, stale session, class/grade ownership, request-controlled tenant resolution, entitlement/quota bypass, RAG leakage, direct-service exposure, auditability, and RLS pooling/session-state risks. Findings were advisory and required direct validation.

### Qwen
No new security handoff response recorded in this round. Existing Qwen response is from a separate implementation diagnosis and is not treated as evidence for this security council.

## Common points
- Tenant and retrieval scope must be enforced server-side before ranking or response generation.
- Agent claims require direct Codex validation; no provider recommendation authorizes implementation by itself.
- RLS would be defense in depth and has connection-pool/background-job implications.
- Critical-path authorization, entitlement, audit, and regression tests are required.

## Conflicts and limits
- Claude recommends `RLS_SELECTED_TABLES`; GLM identified RLS as a risk-control option. Neither supplied a migration-ready policy. Commander must decide before any RLS migration.
- Claude confirmed gaps from excerpts, but malformed sanitization and omitted `admin_authorization.py` limit conclusions about JWT validation and teacher tenant authorization.
- Qwen was not routed for this exact security handoff in this round; no consensus is claimed.

## Codex validation
Direct repository search confirms `RetrievalRequest.scope` exists and the current `PgVectorStore` path must be inspected before any fix is classified. The working tree contains extensive pre-existing/uncommitted changes; no broad cleanup or production mutation is safe without isolating the requested slice. Current handoff scan found no credential values.

## Recommended disposition
- FIX NOW only after Codex tests confirm: mandatory scope filtering, no optimistic success/error swallowing, and safe logging.
- COMMANDER DECISION: choose one RLS classification (`RLS_NOT_REQUIRED_NOW`, `RLS_SELECTED_TABLES`, or `RLS_BROADLY_REQUIRED`) before schema/migration work; provide/approve review of `admin_authorization.py` and the actual migration lineage.
- DEFER: broad RLS migration, FK backfill, immutable publication refactor, and provider abstraction until scope and migration evidence are complete.

## Commander decision required
No RLS or schema change has been implemented. Commander approval is required for any such change.
