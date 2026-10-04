"""DB-free model for the current staged migration release boundary.

This is an orchestration contract test only. It does not connect to PostgreSQL
and is not evidence of database locking, migration execution, or crash safety.
"""

from __future__ import annotations

from dataclasses import dataclass

PRE_CONTRACT_TARGET = "20261004_0032"
CONTRACT_TARGETS = (
    "20261003_0030",
    "20261003_0031",
    "20261004_0033",
)
FINAL_TARGET = "20261004_0033"


@dataclass(frozen=True)
class ContractEvidence:
    candidate_eligible: bool | None
    old_generation_state: str | None
    active_old_writers: int | None
    database_quiescent: bool | None


def may_request_contract(evidence: ContractEvidence) -> bool:
    """Fail closed unless all independent candidate and OLD-writer guards pass."""
    return (
        evidence.candidate_eligible is True
        and evidence.old_generation_state == "FENCED"
        and evidence.active_old_writers == 0
        and evidence.database_quiescent is True
    )
