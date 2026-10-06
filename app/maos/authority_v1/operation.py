"""Deterministic, secret-aware canonical binding for MAOS operations."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

OPERATION_DOMAIN_V1 = "maos.operation.v1"
_SENSITIVE_KEY_PARTS = frozenset(
    {"secret", "token", "password", "passwd", "credential", "authorization", "privatekey", "apikey"}
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)^bearer\s+\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)^sk-[a-z0-9_-]{16,}$"),
)


@dataclass(frozen=True, slots=True)
class OperationBinding:
    canonical_json: str
    digest: str
    domain: str = OPERATION_DOMAIN_V1

    def __post_init__(self) -> None:
        if self.domain != OPERATION_DOMAIN_V1:
            raise ValueError("unsupported operation digest domain")
        if len(self.digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.digest):
            raise ValueError("operation digest must be a lowercase SHA-256 hex digest")
        expected = hashlib.sha256(
            OPERATION_DOMAIN_V1.encode("ascii") + b"\x00" + self.canonical_json.encode("utf-8")
        ).hexdigest()
        if self.digest != expected:
            raise ValueError("operation digest does not match canonical operation identity")


def bind_operation(
    *,
    principal_id: str,
    tenant_id: str,
    action: str,
    resource_ref: str,
    parameters: Mapping[str, object] | None = None,
) -> OperationBinding:
    """Canonicalize a bounded JSON value set and bind it with a domain-separated digest.

    Floats and unsupported Python objects are rejected rather than silently coerced.
    Callers must put only non-secret identifiers/parameters in this identity; keys
    conventionally carrying secrets and recognizable credential values are rejected.
    """
    normalized_identity: dict[str, str] = {}
    for name, value in (
        ("principal_id", principal_id),
        ("tenant_id", tenant_id),
        ("action", action),
        ("resource_ref", resource_ref),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
        normalized = unicodedata.normalize("NFC", value)
        if any(pattern.search(normalized) for pattern in _SECRET_VALUE_PATTERNS):
            raise ValueError(f"credential-like raw values are not allowed in {name}")
        normalized_identity[name] = normalized
    normalized_parameters = _normalize(parameters or {})
    document = {
        "action": normalized_identity["action"],
        "domain": OPERATION_DOMAIN_V1,
        "parameters": normalized_parameters,
        "principal_id": normalized_identity["principal_id"],
        "resource_ref": normalized_identity["resource_ref"],
        "tenant_id": normalized_identity["tenant_id"],
    }
    canonical = json.dumps(
        document, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    )
    digest = hashlib.sha256(
        OPERATION_DOMAIN_V1.encode("ascii") + b"\x00" + canonical.encode("utf-8")
    ).hexdigest()
    return OperationBinding(canonical_json=canonical, digest=digest)


def _normalize(value: object) -> object:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floating-point operation parameters are unsupported")
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        if any(pattern.search(normalized) for pattern in _SECRET_VALUE_PATTERNS):
            raise ValueError("credential-like raw values are not allowed in operation identity")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("operation parameter object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            compact_key = re.sub(r"[^a-z0-9]", "", normalized_key.casefold())
            if any(part in compact_key for part in _SENSITIVE_KEY_PARTS):
                raise ValueError("secret-bearing operation parameter keys are not allowed")
            if normalized_key in result:
                raise ValueError("operation parameter keys collide after Unicode normalization")
            result[normalized_key] = _normalize(item)
        return result
    raise TypeError(f"unsupported canonical operation value type: {type(value).__name__}")
