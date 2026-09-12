"""Validated, provider-neutral commands for the admin content boundary."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .curriculum_pipeline_adapters import serialize_payload
from .curriculum_pipeline_api import ContentValidationError


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentValidationError(f"{field} must be a non-empty string")
    return value


def _id(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContentValidationError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True)
class _Command:
    idempotency_key: str
    request_hash: str

    def __post_init__(self) -> None:
        _text(self.idempotency_key, "idempotency_key")
        _text(self.request_hash, "request_hash")

    def to_payload(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def serialize(self) -> str:
        return serialize_payload(self.to_payload())


@dataclass(frozen=True)
class CreateContentVersionCommand(_Command):
    source_document_id: int
    digest: str

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.source_document_id, "source_document_id"); _text(self.digest, "digest")


@dataclass(frozen=True)
class UpdateContentMetadataCommand(_Command):
    content_version_id: int
    metadata: Mapping[str, Any]
    expected_version: int

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.content_version_id, "content_version_id"); _id(self.expected_version, "expected_version")
        if not self.metadata:
            raise ContentValidationError("metadata must not be empty")


@dataclass(frozen=True)
class SubmitProcessingCommand(_Command):
    content_version_id: int

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.content_version_id, "content_version_id")


@dataclass(frozen=True)
class ApproveContentVersionCommand(_Command):
    content_version_id: int
    digest: str
    expected_version: int

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.content_version_id, "content_version_id"); _id(self.expected_version, "expected_version"); _text(self.digest, "digest")


@dataclass(frozen=True)
class RejectContentVersionCommand(_Command):
    content_version_id: int
    reason: str
    expected_version: int

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.content_version_id, "content_version_id"); _id(self.expected_version, "expected_version"); _text(self.reason, "reason")


@dataclass(frozen=True)
class PublishRequestContract(_Command):
    content_version_id: int
    expected_version: int

    def __post_init__(self) -> None:
        super().__post_init__(); _id(self.content_version_id, "content_version_id"); _id(self.expected_version, "expected_version")
