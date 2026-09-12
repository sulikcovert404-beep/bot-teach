"""Pure environment evidence contracts; no live probes or infrastructure access."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Any


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_CAPABILITIES = {"database", "migration", "vector", "runtime_service"}
_SECRET_PATTERN = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|credential|://[^\s:@]+:[^\s@]+@)")


@dataclass(frozen=True, slots=True)
class EnvironmentCapability:
    capability_name: str
    status: CapabilityStatus
    evidence_reference: str
    probe_version_reference: str
    timestamp_reference: str
    digest: str
    dependency_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.capability_name not in _CAPABILITIES:
            raise ValueError("unknown capability name")
        if any(name not in _CAPABILITIES for name in self.dependency_names):
            raise ValueError("unknown dependency name")
        if self.status is CapabilityStatus.AVAILABLE and not self.digest:
            raise ValueError("AVAILABLE requires evidence digest")
        for value in (self.evidence_reference, self.probe_version_reference, self.timestamp_reference, self.digest):
            if _SECRET_PATTERN.search(value):
                raise ValueError("secret-like value is not allowed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "status": self.status.value,
            "evidence_reference": self.evidence_reference,
            "probe_version_reference": self.probe_version_reference,
            "timestamp_reference": self.timestamp_reference,
            "digest": self.digest,
            "dependency_names": list(self.dependency_names),
        }


@dataclass(frozen=True, slots=True)
class EnvironmentReadinessReport:
    environment_identifier: str
    capabilities: tuple[EnvironmentCapability, ...]
    blockers: tuple[str, ...]
    evidence_digest: str
    readiness_summary: str

    def __post_init__(self) -> None:
        names = [item.capability_name for item in self.capabilities]
        if len(names) != len(set(names)):
            raise ValueError("duplicate capability")
        if any(_SECRET_PATTERN.search(value) for value in (self.environment_identifier, *self.blockers, self.readiness_summary)):
            raise ValueError("secret-like value is not allowed")
        if not self.evidence_digest:
            raise ValueError("evidence digest is required")

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "environment_identifier": self.environment_identifier,
            "capabilities": [item.to_dict() for item in sorted(self.capabilities, key=lambda item: item.capability_name)],
            "blockers": sorted(self.blockers),
            "readiness_summary": self.readiness_summary,
        }
        if include_digest:
            value["evidence_digest"] = self.evidence_digest
        return value

    def canonical_bytes(self) -> bytes:
        payload = json.dumps(self.to_dict(include_digest=False), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return unicodedata.normalize("NFC", payload).encode("utf-8")

    @property
    def computed_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.evidence_digest == self.computed_digest

    @property
    def is_ready(self) -> bool:
        return self.digest_matches() and all(item.status is CapabilityStatus.AVAILABLE for item in self.capabilities)
