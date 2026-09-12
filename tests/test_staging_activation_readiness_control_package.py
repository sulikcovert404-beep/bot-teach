from app.services.staging_activation_readiness_control_package import *
def refs(): return tuple(f'ref-{i}' for i in range(7))
def test_digest():
    x=StagingActivationReadinessControlPackage('p',*refs(),(),('STAGING_ACTIVATION=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE','DEPLOYMENT=PROHIBITED'),'trace'); assert len(x.package_digest)==64
def test_outcomes():
    assert StagingActivationReadinessControlPackage.evaluate(references=('DIGEST_MISMATCH',)) is StagingControlOutcome.STAGING_CONTROL_BLOCKED
    assert StagingActivationReadinessControlPackage.evaluate(references=refs(),findings=('warn',)) is StagingControlOutcome.STAGING_CONTROL_READY_WITH_WARNINGS
def test_unknown_guard():
    assert StagingActivationReadinessControlPackage.evaluate(references=('UNKNOWN',)) is StagingControlOutcome.UNKNOWN
    assert StagingActivationReadinessControlPackage.evaluate(references=refs(),assertions=('staging_activation=allowed',)) is StagingControlOutcome.STAGING_CONTROL_NOT_READY
