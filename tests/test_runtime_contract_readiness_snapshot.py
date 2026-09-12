import pytest
from app.services.runtime_admission_bundle import ReferenceStatus
from app.services.runtime_contract_readiness_snapshot import SnapshotStatus,build_snapshot,validate_snapshot
from tests.test_runtime_execution_result import ref

def snap():return build_snapshot(snapshot_id='s',evaluated_contracts=(ref('c1'),),integration_review_reference=ref('i'),release_readiness_reference=ref('r'),evidence_references=(ref('e'),),trace_reference=ref('t'),snapshot_timestamp_reference=ref('ts'))
def test_ready_and_statuses():
 s=snap(); assert validate_snapshot(s,SnapshotStatus.READY); assert validate_snapshot(s,SnapshotStatus.READY_WITH_WARNINGS); assert validate_snapshot(s,SnapshotStatus.NOT_READY)
def test_digest_and_missing_refs():
 s=snap(); object.__setattr__(s,'snapshot_digest','sha256:'+'0'*64); assert not validate_snapshot(s,SnapshotStatus.READY)
 bad=build_snapshot(snapshot_id='b',evaluated_contracts=(ref('c',status=ReferenceStatus.INVALID),),integration_review_reference=ref('i'),release_readiness_reference=ref('r'),evidence_references=(ref('e'),),trace_reference=ref('t'),snapshot_timestamp_reference=ref('ts')); assert validate_snapshot(bad,SnapshotStatus.BLOCKED)
def test_deterministic_unicode_and_secret():
 a=snap(); b=snap(); assert a.canonical_bytes()==b.canonical_bytes() and a.snapshot_digest==b.snapshot_digest
 with pytest.raises(ValueError): build_snapshot(snapshot_id='token=secret',evaluated_contracts=(ref('c'),),integration_review_reference=ref('i'),release_readiness_reference=ref('r'),evidence_references=(ref('e'),),trace_reference=ref('t'),snapshot_timestamp_reference=ref('ts'))
