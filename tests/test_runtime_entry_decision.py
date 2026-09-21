from app.services.readiness_evidence_gate import *
from app.services.runtime_entry_decision import *


def make_evidence(status=GateStatus.PASSED):
    return {g.value.lower(): EvidenceReference(g.value.lower(), "test", "sha256:" + g.value, "V1", "اکنون", g.value, EvidenceKind.STATIC, status) for g in GateName}


def report(values):
    defs = tuple(GateDefinition(g, (g.value.lower(),), required_kind=EvidenceKind.STATIC) for g in GateName)
    return evaluate_readiness(defs, values)


def test_all_required_gates_allow_runtime():
    values = make_evidence(); r = report(values)
    d = resolve_stage_admission(RuntimeStage.RUNTIME_STAGE, r, values, timestamp_reference="ثابت")
    assert d.outcome is AdmissionOutcome.ALLOWED
    assert d.decision_digest == resolve_stage_admission(RuntimeStage.RUNTIME_STAGE, r, values, timestamp_reference="ثابت").decision_digest


def test_missing_and_unknown_require_evidence():
    values = make_evidence(); values.pop("audit_ready")
    d = resolve_stage_admission(RuntimeStage.RUNTIME_STAGE, report(values), values)
    assert d.outcome is AdmissionOutcome.REQUIRES_EVIDENCE
    values = make_evidence(GateStatus.UNKNOWN)
    assert resolve_stage_admission(RuntimeStage.RUNTIME_STAGE, report(values), values).outcome is AdmissionOutcome.REQUIRES_EVIDENCE


def test_blocked_dependency_blocks_admission():
    values = make_evidence(); values["migration_ready"] = EvidenceReference("migration_ready", "pg", "sha256:x", "V1", "اکنون", "migration", EvidenceKind.LIVE, GateStatus.BLOCKED)
    defs = tuple(GateDefinition(g, (g.value.lower(),), (GateName.MIGRATION_READY,) if g is GateName.TRANSACTION_READY else (), EvidenceKind.LIVE if g is GateName.MIGRATION_READY else EvidenceKind.STATIC) for g in GateName)
    r = evaluate_readiness(defs, values)
    assert resolve_stage_admission(RuntimeStage.PERSISTENCE_STAGE, r, values).outcome is AdmissionOutcome.BLOCKED


def test_digest_and_version_mismatch_not_allowed():
    values = make_evidence(); r = report(values)
    assert resolve_stage_admission(RuntimeStage.CONTRACT_STAGE, r, values, expected_readiness_digest="bad").outcome is AdmissionOutcome.NOT_ALLOWED
    assert resolve_stage_admission(RuntimeStage.CONTRACT_STAGE, r, values, expected_gate_versions={"CONTRACT_READY":"V2"}).outcome is AdmissionOutcome.NOT_ALLOWED


def test_persian_nfc_zwnj_rtl_survives_canonical_serialization():
    values = make_evidence(); values["contract_ready"] = EvidenceReference("می‌شود", "منبع \u200fRTL", "sha256:x", "V1", "اکنون", "تأیید‌شده")
    r = report(values); d = resolve_stage_admission(RuntimeStage.CONTRACT_STAGE, r, values, timestamp_reference="می‌شود")
    assert "می‌شود" in d.canonical_bytes().decode("utf-8")
    assert "\u200c" in d.canonical_bytes().decode("utf-8")
