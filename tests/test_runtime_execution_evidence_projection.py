import pytest

from app.services.runtime_execution_evidence_projection import (
 EvidenceValidityStatus,
 build_evidence_projection,
 validate_evidence_projection,
)
from app.services.runtime_execution_result import ExecutionResultStatus
from tests.test_runtime_execution_result import ref, result


def projection(status=EvidenceValidityStatus.VALID,result_ref=None):
 item,_,_=result(ExecutionResultStatus.SUCCEEDED); return build_evidence_projection(projection_id="p",execution_reference=ref("exec"),result_reference=result_ref or ref("exec",digest=item.result_digest),evidence_type="validation",evidence_payload_reference=ref("payload"),validity_status=status,trace_reference=ref("trace")),item

def test_valid_projection():
 p,r=projection(); assert validate_evidence_projection(p,r)
def test_invalid_result_cannot_create_valid_evidence():
 p,r=projection(result_ref=ref("wrong",digest=r"sha256:"+"0"*64)); assert not validate_evidence_projection(p,r)
def test_nonvalid_statuses_and_digest():
 for status in (EvidenceValidityStatus.INVALID,EvidenceValidityStatus.EXPIRED,EvidenceValidityStatus.UNKNOWN):
  p,_=projection(status); assert validate_evidence_projection(p)
 p,_=projection(); object.__setattr__(p,"projection_digest","sha256:"+"0"*64); assert not validate_evidence_projection(p)
def test_trace_and_reference_binding():
 p,r=projection(); bad=build_evidence_projection(projection_id="p",execution_reference=ref("exec"),result_reference=ref("exec",digest=r.result_digest),evidence_type="validation",evidence_payload_reference=ref("payload",status=__import__('app.services.runtime_admission_bundle',fromlist=['ReferenceStatus']).ReferenceStatus.INVALID),validity_status=EvidenceValidityStatus.UNKNOWN,trace_reference=ref("trace")); assert not validate_evidence_projection(bad)
def test_deterministic_unicode_and_secret_rejection():
 a,r=projection(); b,_=projection(); assert a.canonical_bytes()==b.canonical_bytes() and a.projection_digest==b.projection_digest
 with pytest.raises(ValueError): projection(result_ref=ref("token=secret"))

