"""Provider-neutral contract conformance utilities."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json, unicodedata
from typing import Any, Iterable

@dataclass(frozen=True, slots=True)
class ContractSpec:
    identifier: str
    version: str
    outcomes: tuple[str, ...]
    invariants: tuple[str, ...]

CONTRACT_REGISTRY: tuple[ContractSpec, ...] = (
    ContractSpec("control_plane", "1.0", ("APPROVED","DENIED","BLOCKED","REQUIRES_REVIEW","CONFLICT","INTERNAL_FAILURE"), ("projection_isolation","unknown_fail_closed")),
    ContractSpec("execution_contract", "1.0", ("NOT_EXECUTED","STARTED","COMPLETED","FAILED","CANCELLED","AMBIGUOUS"), ("approved_only_execution",)),
    ContractSpec("job_lifecycle", "1.0", ("CREATED","QUEUED","RUNNING","COMPLETED","FAILED","CANCELLED","BLOCKED","AMBIGUOUS"), ("valid_transitions",)),
    ContractSpec("retry_recovery", "1.0", ("TRANSIENT","PERMANENT","AMBIGUOUS","POLICY_BLOCKED"), ("ambiguous_reconcile","policy_blocked_no_retry")),
    ContractSpec("failure_matrix", "1.0", ("TRANSIENT","PERMANENT","AMBIGUOUS","POLICY_BLOCKED"), ("derived_mapping","fail_closed")),
    ContractSpec("configuration", "1.0", (), ("cannot_bypass_policy",)),
    ContractSpec("audit", "1.0", (), ("observer_isolation",)),
    ContractSpec("observability", "1.0", (), ("observer_isolation",)),
)

GOLDEN_VECTORS = (
    {"name":"approved", "decision":"APPROVED", "execution":"STARTED"},
    {"name":"denied", "decision":"DENIED", "execution":"NOT_EXECUTED"},
    {"name":"blocked", "decision":"BLOCKED", "execution":"NOT_EXECUTED"},
    {"name":"ambiguous", "decision":"AMBIGUOUS", "execution":"AMBIGUOUS"},
    {"name":"policy_blocked", "decision":"POLICY_BLOCKED", "execution":"NOT_EXECUTED"},
    {"name":"cancelled", "decision":"CANCELLED", "execution":"CANCELLED"},
)

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value)

def assert_closed_vocabulary(value: Enum | str, allowed: Iterable[str]) -> None:
    actual = value.value if isinstance(value, Enum) else value
    if actual not in frozenset(allowed):
        raise ValueError(f"unknown contract vocabulary: {actual}")

def assert_deeply_immutable(value: Any) -> None:
    if isinstance(value, (dict, list, set)):
        raise AssertionError("mutable nested value in contract")
    if hasattr(value, "__dataclass_fields__"):
        for name in value.__dataclass_fields__:
            assert_deeply_immutable(getattr(value, name))

def validate_registry() -> None:
    ids = [s.identifier for s in CONTRACT_REGISTRY]
    if len(ids) != len(set(ids)) or any(not s.version for s in CONTRACT_REGISTRY):
        raise AssertionError("invalid contract registry")
    for spec in CONTRACT_REGISTRY:
        if len(spec.outcomes) != len(set(spec.outcomes)):
            raise AssertionError(f"duplicate outcomes: {spec.identifier}")
