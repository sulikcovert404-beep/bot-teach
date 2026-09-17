from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_entry_preparation_handoff import *


def refs(status=ReferenceStatus.VALID):
    return [ReferenceToken(f"r{i}", f"sha256:{i:064x}", status) for i in range(5)]
def make(status=ReferenceStatus.VALID):
    a=refs(status); return RuntimeEntryPreparationHandoff("h1", *a)
def test_valid_and_deterministic():
    h=make(); assert evaluate_runtime_entry_preparation_handoff(h) is HandoffOutcome.TRANSFERRED; assert h.compute_digest()==h.handoff_digest
def test_warning_is_unknown_until_review():
    assert evaluate_runtime_entry_preparation_handoff(make(ReferenceStatus.REQUIRES_REVIEW)) is HandoffOutcome.UNKNOWN
def test_blocked_and_invalid():
    assert evaluate_runtime_entry_preparation_handoff(make(ReferenceStatus.BLOCKED)) is HandoffOutcome.BLOCKED
    assert evaluate_runtime_entry_preparation_handoff(make(ReferenceStatus.INVALID)) is HandoffOutcome.REJECTED
def test_digest_mismatch():
    h=make(); object.__setattr__(h,"handoff_digest","sha256:"+"0"*64); assert evaluate_runtime_entry_preparation_handoff(h) is HandoffOutcome.REJECTED
def test_persian_canonicalization():
    h=RuntimeEntryPreparationHandoff("می‌شود", *refs()); assert h.digest_matches()
