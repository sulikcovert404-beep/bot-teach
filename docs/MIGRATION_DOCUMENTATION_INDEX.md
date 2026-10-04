# Migration Documentation Index

**Classification date:** 2026-10-04
**Purpose:** prevent historical migration and recovery commands from being mistaken for current operational instructions.

## Current source of truth

- `docs/MIGRATIONS.md` — `ACTIVE_CANONICAL`; authoritative migration invocation policy.
- `docs/OPERATIONS.md` — `ACTIVE_CANONICAL`; current operational/restore boundaries.
- `README.md`, `.env.example`, and this index — `ACTIVE_REFERENCE`; current entry/configuration references; migration target defaults fail closed.
- Any action against Staging or Production still requires its own explicit Gate. This index grants no operational authorization.

Date-stamped Gate/BATCH/EXAM/review/evidence documents preserve the state recorded at their time. Embedded historical commands and revision values are evidence only; they do not supersede the canonical documents above.

## Classification totals

| Classification | Count | Meaning |
|---|---:|---|
| `ACTIVE_CANONICAL` | 2 | Current authoritative policy. |
| `ACTIVE_REFERENCE` | 3 | Current entry point or index; defer to canonical policy. |
| `HISTORICAL_ARCHIVE` | 8 | Superseded runbook/checklist/manifest; not executable guidance. |
| `GATE_EVIDENCE_ONLY` | 105 | Historical Gate or review record; preserve, do not execute as policy. |
| `STALE_UNCLASSIFIED` | 0 | Unresolved classification; acceptance requires zero. |
| **Total indexed** | **118** | Files matching the migration command/target query, plus the Gate738AB report. |

## Inventory

| Path | Classification | Basis |
|---|---|---|
| `.env.example` | `ACTIVE_REFERENCE` | Current entry/configuration point; refers to an explicit Gate-selected target and canonical policy. |
| `README.md` | `ACTIVE_REFERENCE` | Current entry/configuration point; refers to an explicit Gate-selected target and canonical policy. |
| `docs/ADAPTIVE_LESSON_PACK_HARDENING_REPORT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/ARTIFACT_DEPLOYMENT_GATE_PREPARATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH054_OPERATIONAL_CLOSURE_CHECKLIST.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH054_RELEASE_EVIDENCE_INDEX.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH055_RELEASE_MANIFEST_ROLLBACK_PACKAGE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH056_GO_LIVE_CLOSURE_PACKAGE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH058_RELEASE_BRANCH_INTEGRITY_AUDIT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH062_FINAL_OPERATIONAL_CLOSURE_VERIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH081_ALEMBIC_PATH_SEPARATOR_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH082_ALEMBIC_PATH_SEPARATOR_DISPOSABLE_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH083_ALEMBIC_PATH_SEPARATOR_APPLICATION_PLAN_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH084_ALEMBIC_PATH_SEPARATOR_APPLICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH086_QUALITY_CLOSURE_MANIFEST_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH087_RELEASE_BRANCH_FINAL_EVIDENCE_INDEX.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH088_REPOSITORY_BASELINE_INTEGRITY_AUDIT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH095_STORAGE_READ_ONLY_EVIDENCE_COLLECTION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH096_STORAGE_INCIDENT_EVIDENCE_CONSOLIDATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH097_STORAGE_ESCALATION_PACKAGE_PREPARATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH104_STORAGE_OBSERVATION_SNAPSHOT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH106_STORAGE_EVIDENCE_TREND_REPORT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH161_LOCAL_RELEASE_CANDIDATE_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH163_OFFSERVER_BACKUP_ARCHIVE_VALIDATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH164_BACKUP_ARCHIVE_VALIDATION_WITH_CLIENT_TOOLS_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH167_NEW_SERVER_MIGRATION_READINESS_CHECKLIST_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH168_NEW_SERVER_PREPARATION_PLAN_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH175_ENVIRONMENT_CONFIGURATION_PREPARATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH197B_NON_EXTERNAL_ENV_PROVISION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/BATCH230_OPERATIONAL_BASELINE_READINESS_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CANONICAL_RUNTIME_CONFIGURATION_FORENSIC_REVIEW_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CI_DETERMINISTIC_MIGRATION_HARDENING_IMPLEMENTATION_PLAN_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CI_DETERMINISTIC_MIGRATION_HARDENING_PROPOSAL_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CI_HARDENING_MERGE_READINESS_RECORD_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CI_HARDENING_POST_MERGE_VERIFICATION_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/CI_RELIABILITY_AUTOMATION_REVIEW_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/DEVELOPER_ONBOARDING_CONSISTENCY_REVIEW_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/DEVELOPMENT_QUALITY_GATE_INVENTORY_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/DOCUMENTATION_DRIFT_REMEDIATION_PLAN_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/EXAM_0021_APPLICATION_POSTGRES_QUALIFICATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/EXAM_0021_FINAL_RUNTIME_E2E_QUALIFICATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/EXAM_0021_PRE_IMPLEMENTATION_AUDIT_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/EXAM_0021_PRODUCTION_MIGRATION_READINESS_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/EXAM_0021_RELEASE_ARTIFACT_QUALIFICATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE733A_CANONICAL_TENANT_CONTEXT_FOUNDATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE736A_INTEGRATED_LOCAL_RELEASE_CANDIDATE_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE736B_REGRESSION_HARNESS_STABILIZATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE737A_RELEASE_COMPATIBILITY_PROVENANCE_READINESS_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE737B_RELEASE_EVIDENCE_CLOSURE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738AA_MIGRATION_SURFACE_REPAIR_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738AB_HISTORICAL_MIGRATION_DOCS_AND_CANDIDATE_REFREEZE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Gate738AB result record; evidence, not operational instruction. |
| `docs/GATE738B_SYNTHETIC_MIGRATION_LOCK_REHEARSAL_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738D_ONLINE_MIGRATION_REDESIGN_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738E_CANDIDATE_LINEAGE_RECONSTRUCTION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738F_ONLINE_MIGRATION_ROLLOUT_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738G_CANDIDATE_WORKSPACE_LINEAGE_PROVENANCE_RECOVERY_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738H_COMPATIBILITY_BRIDGE_REPAIR_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738K_WRITER_ADMISSION_DRAIN_CONTROL_PLANE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738L_IMMUTABLE_CANDIDATE_ARTIFACT_RUNTIME_QUALIFICATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738M_BASE_IMAGE_DIGEST_PIN_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738N_DOCKER_CANDIDATE_DEPENDENCY_REPAIR_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738O_BUILD_CONTEXT_HYGIENE_REPAIR_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738P_CONTRACT_GUARD_REPAIR_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738R_0022_PROVENANCE_LINEAGE_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738T_LEGACY_410_OPENAPI_CONTRACT_ALIGNMENT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738U_RELEASE_QUALIFICATION_ENVIRONMENT_HANDOFF.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738V_CANDIDATE_IDENTITY_RECONCILIATION_PHASE0_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738Y_LEGACY_QUALIFICATION_HARNESS_MODERNIZATION_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/GATE738Z_MIGRATION_INVOCATION_SURFACE_AUDIT_RESULT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/HISTORICAL_MIGRATION_HARDENING_EXCEPTION.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/INDEPENDENT_SENSITIVE_REVIEW_MIGRATION_CONVERGENCE.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/INFRASTRUCTURE_IO_INCIDENT_EVIDENCE_PACK_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/INFRASTRUCTURE_RECOVERY_DECISION_MATRIX_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/LOCAL_ENVIRONMENT_RECOVERY_PROCEDURE_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/MIGRATIONS.md` | `ACTIVE_CANONICAL` | Current source of truth for migration policy/operations. |
| `docs/MIGRATION_DOCUMENTATION_INDEX.md` | `ACTIVE_REFERENCE` | Current entry/configuration point; refers to an explicit Gate-selected target and canonical policy. |
| `docs/MIGRATION_EXECUTION_SIMULATION_REVIEW_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/OPERATIONS.md` | `ACTIVE_CANONICAL` | Current source of truth for migration policy/operations. |
| `docs/OPERATIONS_DOCUMENTATION_HARDENING_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/POST_MIGRATION_OPERATIONAL_RUNBOOK_20260914.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/POST_MIGRATION_RECOVERY_VALIDATION_CHECKLIST.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/POST_MIGRATION_SCHEMA_INTEGRITY_REVIEW_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/POST_MIGRATION_SECURITY_EVIDENCE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/POST_MIGRATION_VALIDATION_PLAN_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRE_CUTOVER_PROVENANCE_AND_FRESH_BACKUP.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/PRODUCTION_ACCESS_RECOVERY_RECORD_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_CONFIG_OWNER_ESCALATION_PACKAGE_20260915.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_CUTOVER_READINESS_RUNBOOK.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/PRODUCTION_MIGRATION_DECISION_BUNDLE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_MIGRATION_EVIDENCE_ARCHIVE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_MIGRATION_INCIDENT_CLOSURE_REPORT_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_MIGRATION_PACKAGE_FINAL_REVIEW_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_MIGRATION_PREFLIGHT_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_OPERATIONAL_HANDOFF.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/PRODUCTION_RECOVERY_ARTIFACT_EVIDENCE_ARCHIVE_VALIDATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_COMMUNICATION_PACKAGE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_DECISION_CLOSURE_RECORD_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_ESCALATION_TRACKER_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_EVIDENCE_BUNDLE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_EXIT_CRITERIA_REVIEW_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_HANDOFF_CHECKLIST_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_HANDOFF_FINAL_INDEX_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_STATE_FREEZE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_STATUS_RECORD_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_WAITING_STATE_REPORT_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RECOVERY_WATCH_BASELINE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/PRODUCTION_RUNTIME_CONFIG_RECOVERY_ESCALATION_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/QUALITY_SECURITY_PERFORMANCE_HARDENING_MILESTONE_REPORT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RAG_STAGING_VALIDATION_REPORT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RECOVERY_MONITORING_BASELINE_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RECOVERY_OPERATOR_ACTION_SHEET_20260914.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/RECOVERY_READINESS_FINAL_CHECKLIST_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RECOVERY_STATE_DELTA_LOG_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RELEASE_BOUNDARY_COMPLETENESS_REVIEW_EXAM_0021_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/RELEASE_CANDIDATE_0021_MANIFEST.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/STAGING_ARTIFACT_PARITY_REPOSITORY_SYNC_REPORT.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |
| `docs/STAGING_CHECKLIST.md` | `HISTORICAL_ARCHIVE` | Superseded runbook/checklist/provenance or 0021 artifact; retained for history and excluded from current operational use. |
| `docs/TENANT_IDENTITY_MIGRATION_IMPLEMENTATION_READINESS_20260914.md` | `GATE_EVIDENCE_ONLY` | Historical Gate/report/proposal/review record; preserve its claims; embedded commands are not current procedure. |

## Search and disposition

The inventory searched `docs/`, `README.md`, and `.env.example` for executable migration/restore commands and known current/historical targets: `alembic upgrade`, `alembic downgrade`, `alembic stamp`, `alembic current`, `alembic heads`, `pg_restore`, `pg_dump`, `migration-gate`, `restore-drill`, `EXPECTED_MIGRATION_HEAD`, `upgrade head`, and revisions `20260912_0021`, `20261003_0029`, `20261003_0030`, `20261003_0031`, `20261004_0032`, `20261004_0033`.

The active set is limited to `docs/MIGRATIONS.md`, `docs/OPERATIONS.md`, `README.md`, `.env.example`, and this index. Old operator-facing documents whose names could imply current use carry a prominent historical banner. Historical content was not rewritten, so records remain faithful to the event.

The Gate738AA report is indexed as evidence. Gate738V manifest `e7720c946f0d84f683dadbf344346779E8DE2DA6E5B5E21DE77858C0B9CAB378` is `HISTORICAL PRE-GATE738AA` only. Gate738AB writes a new uncommitted candidate manifest after all documentation edits.
