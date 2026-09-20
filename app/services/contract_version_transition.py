"""Pure contract version transition model (no persistence or runtime upgrades)."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompatibilityClass(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    REQUIRES_REVALIDATION = "REQUIRES_REVALIDATION"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class TransitionError(ValueError):
    """Invalid or unsafe transition contract."""


def _clean(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise TransitionError(f"{name} must be non-empty text")
    normalized = unicodedata.normalize("NFC", value)
    if re.search(r"(?:api[_ -]?key|password|token|secret)\s*[:=]", normalized, re.IGNORECASE):
        raise TransitionError("secret values are forbidden")
    return normalized


def _tuple(values: Iterable[str], name: str) -> tuple[str, ...]:
    return tuple(sorted({_clean(v, name) for v in values}))


@dataclass(frozen=True, slots=True)
class ContractVersionRecord:
    contract_id: str
    contract_type: str
    previous_version: str | None
    current_version: str
    change_reference: str
    compatibility_class: CompatibilityClass
    affected_components: tuple[str, ...] = field(default_factory=tuple)
    trace_reference: str = ""
    digest: str = ""

    def __post_init__(self) -> None:
        for n in ("contract_id", "contract_type", "current_version", "change_reference"):
            object.__setattr__(self, n, _clean(getattr(self, n), n))
        if self.previous_version is not None:
            object.__setattr__(self, "previous_version", _clean(self.previous_version, "previous_version"))
        object.__setattr__(self, "affected_components", _tuple(self.affected_components, "affected_component"))
        object.__setattr__(self, "trace_reference", _clean(self.trace_reference, "trace_reference"))
        if self.digest and self.digest != self.compute_digest():
            raise TransitionError("digest mismatch")
        if not self.digest:
            object.__setattr__(self, "digest", self.compute_digest())

    def _payload(self) -> dict[str, Any]:
        return {"contract_id": self.contract_id, "contract_type": self.contract_type,
                "previous_version": self.previous_version, "current_version": self.current_version,
                "change_reference": self.change_reference, "compatibility_class": self.compatibility_class.value,
                "affected_components": self.affected_components, "trace_reference": self.trace_reference}

    def canonical_bytes(self) -> bytes:
        return json.dumps(self._payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def verify_digest(self) -> bool:
        return self.digest == self.compute_digest()


@dataclass(frozen=True, slots=True)
class ContractTransitionDecision:
    source_version: str
    target_version: str
    compatibility_result: CompatibilityClass
    invalidated_evidence_references: tuple[str, ...] = field(default_factory=tuple)
    required_validations: tuple[str, ...] = field(default_factory=tuple)
    decision_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_version", _clean(self.source_version, "source_version"))
        object.__setattr__(self, "target_version", _clean(self.target_version, "target_version"))
        object.__setattr__(self, "invalidated_evidence_references", _tuple(self.invalidated_evidence_references, "evidence_reference"))
        object.__setattr__(self, "required_validations", _tuple(self.required_validations, "validation"))
        if self.decision_digest and self.decision_digest != self.compute_digest():
            raise TransitionError("digest mismatch")
        if not self.decision_digest:
            object.__setattr__(self, "decision_digest", self.compute_digest())

    def _payload(self) -> dict[str, Any]:
        return {"source_version": self.source_version, "target_version": self.target_version,
                "compatibility_result": self.compatibility_result.value,
                "invalidated_evidence_references": self.invalidated_evidence_references,
                "required_validations": self.required_validations}

    def canonical_bytes(self) -> bytes:
        return json.dumps(self._payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class VersionGraph:
    parents: Mapping[str, str | None]
    superseded: Mapping[str, str | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        p = { _clean(k, "version"): (None if v is None else _clean(v, "parent")) for k, v in self.parents.items() }
        s = { _clean(k, "version"): (None if v is None else _clean(v, "superseded")) for k, v in self.superseded.items() }
        object.__setattr__(self, "parents", p); object.__setattr__(self, "superseded", s)
        for parent in p.values():
            if parent is not None and parent not in p: raise TransitionError("broken version graph")
        for version in p:
            seen: set[str] = set(); cur: str | None = version
            while cur is not None:
                if cur in seen: raise TransitionError("cycle in version graph")
                seen.add(cur); cur = p[cur]

    def ancestors(self, version: str) -> tuple[str, ...]:
        version = _clean(version, "version")
        if version not in self.parents: raise TransitionError("broken version graph")
        out: list[str] = []; cur: str | None = version
        while cur is not None:
            out.append(cur); cur = self.parents[cur]
        return tuple(out)

    def successors(self, version: str) -> tuple[str, ...]:
        version = _clean(version, "version")
        return tuple(sorted(child for child, parent in self.parents.items() if parent == version))


def promotion_allowed(compatibility: CompatibilityClass) -> bool:
    return compatibility is CompatibilityClass.COMPATIBLE
