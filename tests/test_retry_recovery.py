from app.services.retry_recovery import *

def c(cat): return FailureClassification(cat,"ERR_TEST","commit","publish",metadata=(("fa","می‌شود"),))

def test_categories_and_actions():
 assert decide_retry(c(FailureCategory.TRANSIENT),attempt_reference="a").outcome is RetryOutcome.RETRY_ALLOWED
 assert decide_retry(c(FailureCategory.PERMANENT),attempt_reference="a").outcome is RetryOutcome.RETRY_DENIED
 assert decide_retry(c(FailureCategory.AMBIGUOUS),attempt_reference="a").outcome is RetryOutcome.RETRY_DEFERRED
 assert recovery_action(c(FailureCategory.AMBIGUOUS)) is RecoveryAction.RECONCILE
 assert decide_retry(c(FailureCategory.POLICY_BLOCKED),attempt_reference="a").outcome is RetryOutcome.MANUAL_REVIEW

def test_immutable_and_deterministic_persian():
 x=c(FailureCategory.TRANSIENT); y=c(FailureCategory.TRANSIENT)
 assert x.canonical_json()==y.canonical_json(); assert "می‌شود" in x.canonical_json()
 try: x.phase="x"; assert False
 except AttributeError: pass

def test_budget_validation():
 try: RetryDecision(RetryOutcome.RETRY_ALLOWED,"E","S","A",max_attempts=0); assert False
 except ValueError: pass
