import pytest
from app.services.runtime_admission_bundle import ReferenceStatus
from app.services.runtime_contract_integration_review import IntegrationOutcome,build_integration_review,validate_integration_review
from tests.test_runtime_execution_result import ref

def review(violations=(),risk=''):
 refs=(ref('admission'),ref('boundary'),ref('result')); return build_integration_review(review_id='r',contract_references=refs,dependency_map={'admission':(),'boundary':('admission',),'result':('boundary',)},compatibility_summary='ok',violations=tuple(violations),risk_summary=risk,trace_reference=ref('trace'))
def test_compatible_chain_and_warning():
 assert validate_integration_review(review()) is IntegrationOutcome.COMPATIBLE
 assert validate_integration_review(review(risk='future version')) is IntegrationOutcome.COMPATIBLE_WITH_WARNINGS
def test_incompatible_and_blocked_graph():
 assert validate_integration_review(review(violations=('edge mismatch',))) is IntegrationOutcome.INCOMPATIBLE
 assert validate_integration_review(build_integration_review(review_id='r',contract_references=(ref('a'),),dependency_map={'a':('missing',)},compatibility_summary='x',violations=(),risk_summary='',trace_reference=ref('t'))) is IntegrationOutcome.INCOMPATIBLE
 x=review(); object.__setattr__(x,'review_digest','sha256:'+'0'*64); assert validate_integration_review(x) is IntegrationOutcome.BLOCKED
def test_reference_trace_unicode_and_secret():
 with pytest.raises(ValueError): review(risk='token=secret')
 with pytest.raises(ValueError): build_integration_review(review_id='',contract_references=(ref('a'),),dependency_map={},compatibility_summary='x',violations=(),risk_summary='',trace_reference=ref('t'))
 a=review(); b=review(); assert a.canonical_bytes()==b.canonical_bytes() and a.review_digest==b.review_digest
