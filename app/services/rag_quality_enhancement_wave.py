"""Pure quality contract for conflict-aware, calibrated RAG grounding."""
from dataclasses import dataclass
from enum import StrEnum


class QualityOutcome(StrEnum):
    ENHANCED = "RAG_QUALITY_ENHANCED"
    ENHANCED_WITH_WARNINGS = "RAG_QUALITY_ENHANCED_WITH_WARNINGS"
    INCOMPLETE = "RAG_QUALITY_INCOMPLETE"
    BLOCKED = "RAG_QUALITY_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RAGQualityEnhancementWave:
    conflict_categories: tuple[str, ...] = ()
    resolution_rules: tuple[str, ...] = ()
    precedence_model: tuple[str, ...] = ()
    threshold_strategy: tuple[str, ...] = ()
    confidence_levels: tuple[str, ...] = ()
    scoring_interpretation: tuple[str, ...] = ()
    grounding_state_rules: tuple[str, ...] = ()
    explainability_metadata: tuple[str, ...] = ()
    compatibility_rules: tuple[str, ...] = ()
    validation_scenarios: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    trace_reference: str = ""
    rag_quality_design_and_contract_only: bool = True
    runtime_execution: bool = False
    deployment: bool = False
    database_change: bool = False
    infrastructure_change: bool = False
    credential_change: bool = False

    def outcome(self) -> QualityOutcome:
        if not self.trace_reference:
            return QualityOutcome.BLOCKED
        if not self.rag_quality_design_and_contract_only or any((self.runtime_execution, self.deployment, self.database_change, self.infrastructure_change, self.credential_change)):
            return QualityOutcome.INCOMPLETE
        required=(self.conflict_categories,self.resolution_rules,self.precedence_model,self.threshold_strategy,self.confidence_levels,self.scoring_interpretation,self.grounding_state_rules,self.explainability_metadata,self.compatibility_rules,self.validation_scenarios)
        if any(not x for x in required):
            return QualityOutcome.INCOMPLETE
        return QualityOutcome.ENHANCED_WITH_WARNINGS if self.blockers else QualityOutcome.ENHANCED
