import pytest

from app.services.runtime_execution_attestation import (
 AttestationStatus,
 build_attestation,
 validate_attestation,
)
from app.services.runtime_execution_evidence_projection import (
 EvidenceValidityStatus,
 build_evidence_projection,
)
from app.services.runtime_execution_result import ExecutionResultStatus
from tests.test_runtime_execution_result import ref, result


def att(status=EvidenceValidityStatus.VALID):
 r,_,b=result(ExecutionResultStatus.SUCCEEDED); p=build_evidence_projection(projection_id="p",execution_reference=ref("exec"),result_reference=ref("exec",digest=r.result_digest),evidence_type="validation",evidence_payload_reference=ref("payload"),validity_status=status,trace_reference=ref("trace")); a=build_attestation(attestation_id="a",execution_reference=ref("exec"),result_reference=ref("exec",digest=r.result_digest),projection_references=(ref("p",digest=p.projection_digest),),boundary_reference=ref("boundary"),trace_reference=ref("trace"),validity_period_reference=ref("period")); return a,r,p

def test_valid_attestation():
 a,r,p=att(); assert validate_attestation(a,r,(p,)) is AttestationStatus.VALID
def test_invalid_result_or_projection():
 a,r,p=att(); assert validate_attestation(a,None,(p,)) is AttestationStatus.UNKNOWN
 x,_,_=result(ExecutionResultStatus.FAILED); assert validate_attestation(a,x,(p,)) is AttestationStatus.INVALID
 bad,_,_=att(EvidenceValidityStatus.EXPIRED); assert validate_attestation(bad,r,(p,)) is AttestationStatus.INVALID
def test_digest_and_trace_linkage():
 a,r,p=att(); object.__setattr__(a,"attestation_digest","sha256:"+"0"*64); assert validate_attestation(a,r,(p,)) is AttestationStatus.INVALID
 with pytest.raises(ValueError): build_attestation(attestation_id="",execution_reference=ref("e"),result_reference=ref("r"),projection_references=(ref("p"),),boundary_reference=ref("b"),trace_reference=ref("t"),validity_period_reference=ref("v"))
def test_deterministic_unicode_and_secret_rejection():
 a,r,p=att(); b,_,_=att(); assert a.canonical_bytes()==b.canonical_bytes() and a.attestation_digest==b.attestation_digest
 with pytest.raises(ValueError): build_attestation(attestation_id="token=secret",execution_reference=ref("e"),result_reference=ref("r"),projection_references=(ref("p"),),boundary_reference=ref("b"),trace_reference=ref("t"),validity_period_reference=ref("v"))
