import pytest

from app.services.runtime_execution_completion import (
 CompletionStatus,
 build_completion,
 validate_completion,
)
from tests.test_runtime_execution_result import ref


def test_completion_contract_is_immutable_and_deterministic():
 a=build_completion(completion_id="c",execution_reference=ref("e"),lifecycle_reference=ref("l"),result_reference=ref("r"),attestation_reference=ref("a"),evidence_references=(ref("ev"),),trace_reference=ref("t")); b=build_completion(completion_id="c",execution_reference=ref("e"),lifecycle_reference=ref("l"),result_reference=ref("r"),attestation_reference=ref("a"),evidence_references=(ref("ev"),),trace_reference=ref("t")); assert a.canonical_bytes()==b.canonical_bytes() and a.completion_digest==b.completion_digest

def test_unknown_without_runtime_inputs_and_digest_failure():
 a=build_completion(completion_id="c",execution_reference=ref("e"),lifecycle_reference=ref("l"),result_reference=ref("r"),attestation_reference=ref("a"),evidence_references=(ref("ev"),),trace_reference=ref("t")); assert validate_completion(a) is CompletionStatus.UNKNOWN; object.__setattr__(a,"completion_digest","sha256:"+"0"*64); assert validate_completion(a) is CompletionStatus.FAILED_COMPLETION

def test_required_fields_and_secret_rejection():
 with pytest.raises(ValueError): build_completion(completion_id="",execution_reference=ref("e"),lifecycle_reference=ref("l"),result_reference=ref("r"),attestation_reference=ref("a"),evidence_references=(ref("ev"),),trace_reference=ref("t"))
 with pytest.raises(ValueError): build_completion(completion_id="token=secret",execution_reference=ref("e"),lifecycle_reference=ref("l"),result_reference=ref("r"),attestation_reference=ref("a"),evidence_references=(ref("ev"),),trace_reference=ref("t"))
