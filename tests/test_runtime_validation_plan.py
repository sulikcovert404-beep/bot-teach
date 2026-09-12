from app.services.runtime_validation_plan import *

def req(i='e',v='1',d='d',r='ttl'): return EvidenceRequirement(i,v,d,r)
def plan():
 s=tuple(ValidationStep(x,i,tuple([('a','b','c')[i-2]] if i>1 else []),(),('database',),(),(req(x),),f'd{i}','ttl','FAIL_CLOSED') for i,x in enumerate(('a','b','c'),1))
 return RuntimeValidationPlan('p','1',s,(),('database',),(req('root'),),'FAIL_CLOSED','none',(('a',('b','c')),))
def test_order_and_digest_are_deterministic():
 p=plan(); assert [x.validation_id for x in p.ordered_steps()]==['a','b','c']; assert p.plan_digest()==plan().plan_digest()
def test_failure_propagates_as_not_run():
 p=plan(); out=propagate_outcome(p,{'a':ValidationOutcome.FAILED}); assert out['b'] is ValidationOutcome.NOT_RUN and out['c'] is ValidationOutcome.NOT_RUN
def test_missing_dependency_is_not_run():
 p=plan(); assert propagate_outcome(p,{'a': ValidationOutcome.PASSED})['b'] is ValidationOutcome.NOT_RUN
def test_reverse_graph_and_provider_neutrality():
 p=plan(); assert p.reverse_invalidations()['a']==('b','c'); assert all('PGVector' not in s.required_capabilities for s in p.validation_steps)
def test_persian_nfc_zwnj_round_trip():
 p=RuntimeValidationPlan('پ','۱',(),(),('پایگاه‌داده',),(), 'رد', 'بازگشت'); assert 'پایگاه‌داده'.encode('utf8') in p.canonical_bytes()


