import json

from app.services.readiness_evidence_gate import *

GATES = tuple(GateDefinition(g, (g.value.lower(),), required_kind=EvidenceKind.STATIC)
              for g in GateName)


def evidence(status=GateStatus.PASSED, kind=EvidenceKind.STATIC):
    return {g.value.lower(): EvidenceReference(g.value.lower(), "pytest", "sha256:x", "V1",
                                                "2026-09-03T00:00:00Z", g.value, kind, status)
            for g in GateName}


def test_all_gates_pass_and_report_is_deterministic():
    r = evaluate_readiness(GATES, evidence())
    assert r.decision is ReadinessDecision.READY_FOR_NEXT_STAGE
    assert r.digest == evaluate_readiness(tuple(reversed(GATES)), evidence()).digest


def test_missing_and_unknown_evidence_fail_closed():
    values = evidence(); values.pop("contract_ready")
    assert evaluate_readiness(GATES, values).decision is ReadinessDecision.NOT_READY
    values = evidence("UNKNOWN")
    assert evaluate_readiness(GATES, values).decision is ReadinessDecision.NOT_READY


def test_blocked_postgresql_evidence_and_dependency_failure():
    values = evidence(); values["migration_ready"] = EvidenceReference("migration_ready", "docker",
        "sha256:x", "V1", "now", "migration", EvidenceKind.LIVE, GateStatus.BLOCKED)
    defs = tuple(GateDefinition(g, (g.value.lower(),), (GateName.MIGRATION_READY,) if g is GateName.TRANSACTION_READY else (),
                                EvidenceKind.LIVE if g is GateName.MIGRATION_READY else EvidenceKind.STATIC) for g in GateName)
    assert evaluate_readiness(defs, values).decision is ReadinessDecision.BLOCKED


def test_persian_nfc_zwnj_rtl_round_trip():
    values = evidence(); values["contract_ready"] = EvidenceReference("می‌شود", "منبع ‏RTL", "sha256:x", "V1", "اکنون", "تأیید‌شده")
    r = evaluate_readiness(GATES, values)
    encoded = json.dumps(r.to_dict(), ensure_ascii=False)
    assert "می‌شود" not in encoded  # IDs are structural and remain separate from payload text
    assert "READY_FOR_NEXT_STAGE" in encoded
