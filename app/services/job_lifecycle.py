"""Provider-neutral asynchronous job lifecycle contracts."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class JobStatus(StrEnum):
    CREATED='CREATED'; QUEUED='QUEUED'; RUNNING='RUNNING'; COMPLETED='COMPLETED'; FAILED='FAILED'; CANCELLED='CANCELLED'; BLOCKED='BLOCKED'; AMBIGUOUS='AMBIGUOUS'

TERMINAL_STATES=frozenset({JobStatus.COMPLETED,JobStatus.FAILED,JobStatus.CANCELLED})
TRANSITIONS={
 JobStatus.CREATED:frozenset({JobStatus.QUEUED,JobStatus.BLOCKED}),
 JobStatus.QUEUED:frozenset({JobStatus.RUNNING,JobStatus.BLOCKED,JobStatus.CANCELLED}),
 JobStatus.RUNNING:frozenset({JobStatus.COMPLETED,JobStatus.FAILED,JobStatus.CANCELLED,JobStatus.AMBIGUOUS}),
 JobStatus.BLOCKED:frozenset({JobStatus.QUEUED,JobStatus.CANCELLED}),
 JobStatus.AMBIGUOUS:frozenset({JobStatus.COMPLETED,JobStatus.FAILED,JobStatus.CANCELLED}),
 JobStatus.COMPLETED:frozenset(), JobStatus.FAILED:frozenset(), JobStatus.CANCELLED:frozenset(),
}
TRANSITION_MATRIX_VERSION='1.0'
class InvalidJobTransition(ValueError): pass

def _nfc(v:str)->str:return unicodedata.normalize('NFC',v)
def _canon(v:object)->str:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))

@dataclass(frozen=True,slots=True)
class JobRequest:
 job_id:str; execution_reference:str; command_reference:str; job_type:str; trace_context:tuple[tuple[str,str],...]; created_reference:str
 @classmethod
 def create(cls, *, job_id:str, execution_reference:str, command_reference:str, job_type:str, trace_context:Mapping[str,str], created_reference:str)->'JobRequest':
  return cls(_nfc(job_id),_nfc(execution_reference),_nfc(command_reference),_nfc(job_type),tuple(sorted((_nfc(str(k)),_nfc(str(v))) for k,v in trace_context.items())),_nfc(created_reference))
 def canonical_json(self)->str:return _canon({'command_reference':self.command_reference,'created_reference':self.created_reference,'execution_reference':self.execution_reference,'job_id':self.job_id,'job_type':self.job_type,'trace_context':dict(self.trace_context)})

@dataclass(frozen=True,slots=True)
class JobResult:
 job_id:str; status:JobStatus; result_reference:str|None=None; reason_code:str|None=None; started_at:str|None=None; completed_at:str|None=None
 def canonical_json(self)->str:return _canon({'completed_at':self.completed_at,'job_id':self.job_id,'reason_code':self.reason_code,'result_reference':self.result_reference,'started_at':self.started_at,'status':self.status.value})

@dataclass(frozen=True,slots=True)
class CancellationRequest:
 job_id:str; reason_code:str='CANCELLATION_REQUESTED'

def validate_transition(current:JobStatus, target:JobStatus)->None:
 if target not in TRANSITIONS.get(current,frozenset()): raise InvalidJobTransition(f'{current.value}->{target.value}')

def request_cancel(job_id:str)->CancellationRequest:return CancellationRequest(_nfc(job_id))

def get_job_status(job_id:str)->None:
 """Future reconciliation port; persistence/runtime intentionally absent."""
 raise NotImplementedError('job status reconciliation is a future runtime concern')
