"""Stable identities for effect-bearing operations; no idempotency store."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperationId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("operation id is required")


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("idempotency key is required")
