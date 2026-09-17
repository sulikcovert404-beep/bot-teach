from app.services.staging_readiness_governance_finalization import *


def refs(): return tuple(f'ref-{i}' for i in range(7))
def test_digest_and_immutability():
    x=StagingReadinessGovernanceFinalization('f',*refs(),(),('STAGING_EXECUTION=PROHIBITED','DEPLOYMENT=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE'),'trace')
    assert len(x.finalization_digest)==64
def test_precedence():
    assert StagingReadinessGovernanceFinalization.evaluate(references=('ref','DIGEST_MISMATCH')) is FinalizationOutcome.STAGING_GOVERNANCE_BLOCKED
    assert StagingReadinessGovernanceFinalization.evaluate(references=refs(),findings=('warn',)) is FinalizationOutcome.STAGING_GOVERNANCE_FINALIZED_WITH_WARNINGS
def test_unknown_and_guard():
    assert StagingReadinessGovernanceFinalization.evaluate(references=('UNKNOWN',)) is FinalizationOutcome.UNKNOWN
    assert StagingReadinessGovernanceFinalization.evaluate(references=refs(),assertions=('runtime_activation=allowed',)) is FinalizationOutcome.STAGING_GOVERNANCE_NOT_FINALIZED
