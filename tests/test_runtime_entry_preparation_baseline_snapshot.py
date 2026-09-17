from dataclasses import replace

import pytest

from app.services.runtime_admission_bundle import ReferenceStatus, ReferenceToken
from app.services.runtime_entry_preparation_baseline_snapshot import *


def ref(i, status=ReferenceStatus.VALID): return ReferenceToken(i, 'sha256:'+i, status)
def make(**kw):
    args=dict(snapshot_id='s1',preparation_review_reference=ref('p'),reconciliation_reference=ref('r'),freeze_reference=ref('f'),baseline_reference=ref('b'),trace_reference=ref('t'))
    args.update(kw); return RuntimeEntryPreparationBaselineSnapshot(**args)
def test_valid_and_deterministic():
    s=make(); assert evaluate_runtime_entry_preparation_baseline_snapshot(s) is SnapshotOutcome.CAPTURED; assert s.snapshot_digest==s.compute_digest(); assert s.canonical_bytes()==make().canonical_bytes()
def test_warning_invalid_blocked_unknown():
    assert evaluate_runtime_entry_preparation_baseline_snapshot(make(captured_findings=({'code':'DRIFT'},))) is SnapshotOutcome.CAPTURED_WITH_WARNINGS
    assert evaluate_runtime_entry_preparation_baseline_snapshot(make(preparation_review_reference=ref('p',ReferenceStatus.INVALID))) is SnapshotOutcome.INVALID
    assert evaluate_runtime_entry_preparation_baseline_snapshot(make(preparation_review_reference=ref('p',ReferenceStatus.BLOCKED))) is SnapshotOutcome.BLOCKED
    assert evaluate_runtime_entry_preparation_baseline_snapshot(make(preparation_review_reference=ref('p',ReferenceStatus.REQUIRES_REVIEW))) is SnapshotOutcome.UNKNOWN
def test_digest_tamper_and_trace_required():
    s=make(); object.__setattr__(s,'snapshot_digest','sha256:bad'); assert evaluate_runtime_entry_preparation_baseline_snapshot(s) is SnapshotOutcome.INVALID
    with pytest.raises(ValueError): make(trace_reference=None)
def test_persian_and_secret_rejected():
    s=make(captured_findings=({'note':'می\u200cشود'},)); assert 'می\u200cشود'.encode() in s.canonical_bytes()
    with pytest.raises(ValueError): make(captured_findings=({'api_key':'x'},))
