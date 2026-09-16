from app.services.job_lifecycle import (
    InvalidJobTransition,
    JobRequest,
    JobResult,
    JobStatus,
    request_cancel,
    validate_transition,
)


def test_valid_transitions():
    for current, target in ((JobStatus.CREATED, JobStatus.QUEUED), (JobStatus.QUEUED, JobStatus.RUNNING), (JobStatus.RUNNING, JobStatus.COMPLETED), (JobStatus.RUNNING, JobStatus.AMBIGUOUS), (JobStatus.BLOCKED, JobStatus.QUEUED), (JobStatus.AMBIGUOUS, JobStatus.CANCELLED)):
        validate_transition(current, target)


def test_invalid_and_terminal_transitions_fail_closed():
    for current, target in ((JobStatus.COMPLETED, JobStatus.QUEUED), (JobStatus.FAILED, JobStatus.RUNNING), (JobStatus.CANCELLED, JobStatus.COMPLETED), (JobStatus.CREATED, JobStatus.COMPLETED)):
        try:
            validate_transition(current, target)
        except InvalidJobTransition:
            pass
        else:
            raise AssertionError((current, target))


def test_request_and_result_are_deterministic_and_preserve_zwnj():
    req = JobRequest.create(job_id='j۱', execution_reference='e', command_reference='c', job_type='ingest', trace_context={'b':'می‌شود', 'a':'x'}, created_reference='2026-01-01T00:00:00Z')
    assert req.canonical_json() == req.canonical_json()
    assert '\u200c' in req.canonical_json()
    result = JobResult('j۱', JobStatus.COMPLETED, result_reference='r', started_at='t')
    assert result.canonical_json() == result.canonical_json()


def test_cancellation_is_contract_only():
    assert request_cancel('j-1').reason_code == 'CANCELLATION_REQUESTED'
