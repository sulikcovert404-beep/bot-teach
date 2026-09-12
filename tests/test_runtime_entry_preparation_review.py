import pytest
from app.services.runtime_entry_preparation_review import *
from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken

def make(status=ReferenceStatus.VALID, findings=()):
    def r(n): return ReferenceToken(n,"sha256:"+n,status)
    return RuntimeEntryPreparationReview("r-1",r("freeze"),r("base"),r("close"),r("handoff"),r("consistency"),r("ready"),tuple(findings),r("trace"))

def test_ready_and_deterministic():
    x=make(); assert evaluate_runtime_entry_preparation(x) is PreparationOutcome.READY_FOR_PREPARATION; assert x.canonical_bytes()==make().canonical_bytes()
def test_outcomes():
    assert evaluate_runtime_entry_preparation(make(findings=("warning",))) is PreparationOutcome.READY_WITH_WARNINGS
    assert evaluate_runtime_entry_preparation(make(ReferenceStatus.INVALID)) is PreparationOutcome.NOT_READY
    assert evaluate_runtime_entry_preparation(make(ReferenceStatus.BLOCKED)) is PreparationOutcome.BLOCKED
    assert evaluate_runtime_entry_preparation(make(ReferenceStatus.REQUIRES_REVIEW)) is PreparationOutcome.UNKNOWN
def test_tamper_and_persian_and_secret():
    x=make(findings=("یادداشت‌ فارسی",)); object.__setattr__(x,"review_digest","sha256:bad"); assert evaluate_runtime_entry_preparation(x) is PreparationOutcome.BLOCKED
    with pytest.raises(ValueError, match="secret"): make(findings=("api_key",))
