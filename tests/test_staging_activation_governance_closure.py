from app.services.staging_activation_governance_closure import *


def refs():return tuple(f'ref-{i}' for i in range(5))
def test_digest():
 x=StagingActivationGovernanceClosure('c',*refs(),('STAGING_ACTIVATION=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE','DEPLOYMENT=PROHIBITED'),(),'trace');assert len(x.closure_digest)==64
def test_precedence():
 assert StagingActivationGovernanceClosure.evaluate(references=('CONFLICT',)) is ClosureOutcome.STAGING_GOVERNANCE_BLOCKED
 assert StagingActivationGovernanceClosure.evaluate(references=refs(),findings=('warn',)) is ClosureOutcome.STAGING_GOVERNANCE_CLOSED_WITH_WARNINGS
def test_unknown_guard():
 assert StagingActivationGovernanceClosure.evaluate(references=('UNKNOWN',)) is ClosureOutcome.UNKNOWN
 assert StagingActivationGovernanceClosure.evaluate(references=refs(),assertions=('staging_activation=allowed',)) is ClosureOutcome.STAGING_GOVERNANCE_OPEN
