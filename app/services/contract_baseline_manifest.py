"""Pure, immutable baseline manifest for the administrative contract surface."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from collections.abc import Iterable, Mapping
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class BaselineOutcome(StrEnum):
    FROZEN = "FROZEN"
    FROZEN_WITH_WARNINGS = "FROZEN_WITH_WARNINGS"
    NOT_FROZEN = "NOT_FROZEN"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        items = [_clean(v) for v in value]
        return sorted(items, key=lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True))
    return value


def _reject_secrets(value: Any) -> None:
    if isinstance(value, str) and _SECRET.search(value):
        raise ValueError("secret-like content is not permitted")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET.search(str(key)):
                raise ValueError("secret-like field is not permitted")
            _reject_secrets(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _reject_secrets(item)


def _canonical(value: Any) -> bytes:
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ContractBaselineManifest:
    baseline_id: str
    contract_inventory: tuple[str, ...]
    contract_versions: Mapping[str, str]
    dependency_summary: Mapping[str, tuple[str, ...]]
    authority_summary: Mapping[str, str]
    digest_summary: Mapping[str, str]
    closure_reference: ReferenceToken
    trace_reference: ReferenceToken
    warnings: tuple[str, ...] = ()
    baseline_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.baseline_id or not self.closure_reference or not self.trace_reference:
            raise ValueError("baseline identity and references are required")
        inventory = tuple(sorted(set(self.contract_inventory)))
        if any(not name for name in inventory):
            raise ValueError("contract inventory entries must be non-empty")
        object.__setattr__(self, "contract_inventory", inventory)
        object.__setattr__(self, "contract_versions", dict(self.contract_versions))
        object.__setattr__(self, "dependency_summary", {str(k): tuple(sorted(v)) for k, v in self.dependency_summary.items()})
        object.__setattr__(self, "authority_summary", dict(self.authority_summary))
        object.__setattr__(self, "digest_summary", dict(self.digest_summary))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        _reject_secrets(self.payload())
        if self.baseline_digest and self.baseline_digest != self.compute_digest():
            raise ValueError("baseline digest mismatch")
        if not self.baseline_digest:
            object.__setattr__(self, "baseline_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "contract_inventory": self.contract_inventory,
            "contract_versions": self.contract_versions,
            "dependency_summary": self.dependency_summary,
            "authority_summary": self.authority_summary,
            "digest_summary": self.digest_summary,
            "closure_reference": self.closure_reference.to_dict(),
            "trace_reference": self.trace_reference.to_dict(),
            "warnings": self.warnings,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical(self.payload())

    def compute_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def digest_matches(self) -> bool:
        return self.baseline_digest == self.compute_digest()


REQUIRED_CONTRACTS: frozenset[str] = frozenset()


def evaluate_baseline(manifest: ContractBaselineManifest, *, required_contracts: Iterable[str] = REQUIRED_CONTRACTS) -> BaselineOutcome:
    """Evaluate only declarative invariants; this function performs no I/O or mutation."""
    if not manifest.contract_inventory:
        return BaselineOutcome.NOT_FROZEN
    if not manifest.digest_matches():
        return BaselineOutcome.NOT_FROZEN
    if manifest.closure_reference.status is not ReferenceStatus.VALID:
        return BaselineOutcome.NOT_FROZEN
    if manifest.trace_reference.status is ReferenceStatus.REQUIRES_REVIEW:
        return BaselineOutcome.UNKNOWN
    if manifest.trace_reference.status is not ReferenceStatus.VALID:
        return BaselineOutcome.BLOCKED
    required = set(required_contracts)
    if required - set(manifest.contract_inventory):
        return BaselineOutcome.BLOCKED
    names = set(manifest.contract_inventory)
    if any(dep not in names for deps in manifest.dependency_summary.values() for dep in deps):
        return BaselineOutcome.BLOCKED
    if set(manifest.contract_versions) - names or set(manifest.digest_summary) - names:
        return BaselineOutcome.NOT_FROZEN
    if any(not manifest.contract_versions.get(name) or not manifest.digest_summary.get(name) for name in names):
        return BaselineOutcome.NOT_FROZEN
    if len(set(manifest.authority_summary.values())) != len(manifest.authority_summary):
        return BaselineOutcome.BLOCKED
    return BaselineOutcome.FROZEN_WITH_WARNINGS if manifest.warnings else BaselineOutcome.FROZEN


def build_baseline_manifest(**kwargs: Any) -> ContractBaselineManifest:
    return ContractBaselineManifest(**kwargs)
