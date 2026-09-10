# Claude Sonnet 5 — Security Hardening Review

- Status: COMPLETE
- Model: Claude Sonnet 5 (Low)
- Evidence read: 7 of 8 fetchable files; relevant_security_tests.md contained paths only.

## Confirmed findings
- Sanitization corrupted auth_identity_excerpt.md/tokens.py syntax, so secret validation cannot be verified; regenerate a structurally valid secret-free excerpt.
- RetrievalRequest/SourceChunk `scope` is defined but omitted from PgVectorStore.search filtering; non-public scope would not be enforced at that layer. Fix now.
- Multi-tenant tables use bare tenant_id strings without visible foreign keys or RLS; database-level isolation backstop is absent. Classify RLS as RLS_SELECTED_TABLES, pending Commander decision and migration review.
- data_isolation_verified defaults true without visible enforcement, creating false audit confidence.
- Retrieval evidence queries SourceChunk directly and does not demonstrate use of PublicationPointer; verify/fix before claiming version-safe retrieval.
- Destructive re-ingestion and leaked-credential rotation remain blocked items based on prior confirmed evidence.

## Positive controls
- Role claim validation rejects missing/malformed claims.
- Identity relink guard prevents assigning an external identity to another user.
- ContentVersion/PublicationPointer/outbox/idempotency schema supports immutable publication design.

## Verification gaps / Commander decisions
- Actual admin_authorization.authorize() tenant/scope enforcement was not included.
- Identity.verified persistence and webhook signature enforcement need direct verification.
- Actual migration 20260909_0015 was not included.
- Do not implement RLS or schema changes without Commander approval.
