from app.services.runtime_activation_pre_staging_governance_package import *


def refs(): return tuple(f'ref-{i}' for i in range(9))
def test_digest_is_deterministic_and_immutable():
    p=RuntimeActivationPreStagingGovernancePackage('p',*refs())
    assert p.package_digest==p.canonical_digest(); assert p.payload()['execution'] is False
def test_precedence_and_warnings():
    assert RuntimeActivationPreStagingGovernancePackage.evaluate(references=refs())==PreStagingOutcome.PRE_STAGING_READY
    assert RuntimeActivationPreStagingGovernancePackage.evaluate(references=refs(),findings=('note',))==PreStagingOutcome.PRE_STAGING_READY_WITH_WARNINGS
    assert RuntimeActivationPreStagingGovernancePackage.evaluate(references=('BLOCKED',)+refs())==PreStagingOutcome.PRE_STAGING_BLOCKED
def test_secrets_and_digest_rejected():
    try: RuntimeActivationPreStagingGovernancePackage('secret',*refs())
    except ValueError: pass
    else: raise AssertionError
