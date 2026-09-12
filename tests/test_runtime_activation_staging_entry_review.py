from app.services.runtime_activation_staging_entry_review import *
def refs(): return tuple(f'ref-{i}' for i in range(5))
def test_digest_and_guards():
    r=RuntimeActivationStagingEntryReview('r',*refs(),('ok',),('STAGING_ENTRY=REVIEW_ONLY',),'trace')
    assert r.review_digest==r.canonical_digest() and r.payload()['execution'] is False
def test_outcomes():
    assert RuntimeActivationStagingEntryReview.evaluate(references=refs())==StagingEntryOutcome.STAGING_ENTRY_APPROVED
    assert RuntimeActivationStagingEntryReview.evaluate(references=('BLOCKED',)+refs())==StagingEntryOutcome.STAGING_ENTRY_BLOCKED
    assert RuntimeActivationStagingEntryReview.evaluate(references=refs(),assertions=('BAD',))==StagingEntryOutcome.STAGING_ENTRY_NOT_APPROVED
def test_secret_rejected():
    try: RuntimeActivationStagingEntryReview('secret',*refs(),(),(),'trace')
    except ValueError: pass
    else: raise AssertionError
