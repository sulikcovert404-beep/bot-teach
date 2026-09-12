from app.services.operational_readiness_decision_review_framework import *
def make(**k):
 d=dict(review_framework_id='r',decision_framework_reference='d',review_roles={'reviewer':'owner'},review_criteria=('complete',),review_checks=('trace',),challenge_rules=('challenge',),escalation_rules=('commander',),review_constraints=('separate',),scope_exclusions=('approval',),boundary_assertions={'approval_authority':False,'execution':False},trace_reference='t',review_digest='h'); d.update(k); return OperationalReadinessDecisionReviewFramework(**d)
def test_defined(): assert make().outcome() is ReviewOutcome.REVIEW_FRAMEWORK_DEFINED
def test_blocked(): assert make(review_digest='').outcome() is ReviewOutcome.REVIEW_FRAMEWORK_BLOCKED
def test_incomplete(): assert make(review_roles={}).outcome() is ReviewOutcome.REVIEW_FRAMEWORK_INCOMPLETE
