"""Pure, provider-neutral configuration contracts for the admin pipeline."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

CONFIG_VERSION = "1.0.0"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    return value


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, frozenset)):
        items = [_plain(v) for v in value]
        return sorted(items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True)) if isinstance(value, frozenset) else items
    return value


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    enable_vector_sync: bool = True
    enable_audit_projection: bool = True
    enable_observability: bool = True


@dataclass(frozen=True, slots=True)
class LifecyclePolicy:
    require_approval: bool = True
    require_vector_sync: bool = True
    allowed_transitions: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("DRAFT", ("IN_REVIEW",)),
        ("IN_REVIEW", ("APPROVED", "CHANGES_REQUESTED")),
        ("APPROVED", ("PUBLISHED",)),
    )


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    strict: bool = True
    required_checks: tuple[str, ...] = ("schema", "provenance", "digest")
    fail_closed: bool = True


@dataclass(frozen=True, slots=True)
class ObservabilityOptions:
    enabled_metrics: tuple[str, ...] = ("command_received", "command_completed", "command_rejected")
    include_payloads: bool = False
    include_sensitive_fields: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowLimits:
    max_steps: int = 32
    max_batch_size: int = 100
    timeout_seconds: int = 300


@dataclass(frozen=True, slots=True)
class PipelineConfiguration:
    version: str = CONFIG_VERSION
    feature_flags: FeatureFlags = FeatureFlags()
    lifecycle: LifecyclePolicy = LifecyclePolicy()
    validation: ValidationPolicy = ValidationPolicy()
    observability: ObservabilityOptions = ObservabilityOptions()
    workflow_limits: WorkflowLimits = WorkflowLimits()

    def __post_init__(self) -> None:
        for name in ("feature_flags", "lifecycle", "validation", "observability", "workflow_limits"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        if not self.version or not isinstance(self.version, str):
            raise ValueError("configuration version is required")

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()


def validate_configuration(config: PipelineConfiguration) -> ValidationResult:
    errors: list[str] = []
    if not isinstance(config, PipelineConfiguration):
        return ValidationResult(False, ("configuration_type",))
    if not config.version:
        errors.append("version_required")
    limits = config.workflow_limits
    if limits.max_steps <= 0:
        errors.append("max_steps_positive")
    if limits.max_batch_size <= 0:
        errors.append("max_batch_size_positive")
    if limits.timeout_seconds <= 0:
        errors.append("timeout_positive")
    if config.observability.include_payloads or config.observability.include_sensitive_fields:
        errors.append("sensitive_observability_forbidden")
    if config.lifecycle.require_vector_sync and not config.feature_flags.enable_vector_sync:
        errors.append("vector_sync_required_but_disabled")
    if not config.validation.fail_closed:
        errors.append("fail_closed_required")
    return ValidationResult(not errors, tuple(sorted(errors)))


def resolve_configuration(context: Mapping[str, Any] | None = None) -> PipelineConfiguration:
    """Resolve immutable configuration from explicit data only; never reads process state."""
    context = {} if context is None else context
    unknown = set(context) - {"version", "feature_flags", "lifecycle", "validation", "observability", "workflow_limits"}
    if unknown:
        raise ValueError("unknown configuration fields: " + ", ".join(sorted(unknown)))
    base = PipelineConfiguration()
    values = base.to_dict()
    for section, override in context.items():
        if section == "version":
            values[section] = override
            continue
        if not isinstance(override, Mapping):
            raise ValueError(f"{section} must be an object")
        allowed = set(values[section])
        extra = set(override) - allowed
        if extra:
            raise ValueError(f"unknown {section} fields: " + ", ".join(sorted(extra)))
        values[section] = {**values[section], **override}
    config = PipelineConfiguration(
        version=values["version"],
        feature_flags=FeatureFlags(**values["feature_flags"]),
        lifecycle=LifecyclePolicy(**values["lifecycle"]),
        validation=ValidationPolicy(**values["validation"]),
        observability=ObservabilityOptions(**values["observability"]),
        workflow_limits=WorkflowLimits(**values["workflow_limits"]),
    )
    result = validate_configuration(config)
    if not result.valid:
        raise ValueError("invalid configuration: " + ", ".join(result.errors))
    return config
