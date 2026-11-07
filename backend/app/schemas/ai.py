"""Validated request and response schemas for AI incident analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EvidenceProvenance = Literal[
    "current_incident_evidence",
    "historical_hindsight_memory",
    "engineer_verified_root_cause",
]


class DeploymentContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    deployment_id: str | None = Field(default=None, max_length=200)
    service_name: str | None = Field(default=None, max_length=200)
    environment: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=200)
    deployed_by: str | None = Field(default=None, max_length=200)
    deployed_at: datetime | None = None
    change_summary: str | None = Field(default=None, max_length=5_000)


class HistoricalMemoryInput(BaseModel):
    """A memory returned by Hindsight, kept explicitly historical."""

    model_config = ConfigDict(
        extra="ignore", str_strip_whitespace=True, from_attributes=True
    )

    id: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=10_000)
    tags: list[str] = Field(default_factory=list, max_length=30)
    provenance: Literal["historical_hindsight_memory"] = (
        "historical_hindsight_memory"
    )


class EngineerVerifiedFindingInput(BaseModel):
    """An engineer-verified finding supplied separately from model output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    finding_id: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=5_000)
    verified_by: str = Field(min_length=1, max_length=200)
    verified_at: datetime | None = None
    provenance: Literal["engineer_verified_root_cause"] = (
        "engineer_verified_root_cause"
    )


class IncidentContext(BaseModel):
    """Current evidence and separately sourced historical/verified context."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    incident_id: str | None = Field(default=None, max_length=200)
    service_name: str | None = Field(default=None, max_length=150)
    environment: str | None = Field(default=None, max_length=50)
    severity: str | None = Field(default=None, max_length=20)
    incident_description: str = Field(min_length=1, max_length=20_000)
    error_messages: list[str] = Field(default_factory=list, max_length=100)
    logs: list[str] = Field(default_factory=list, max_length=100)
    deployments: list[DeploymentContext] = Field(default_factory=list, max_length=30)
    system_metrics: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=100
    )
    historical_memories: list[HistoricalMemoryInput] = Field(
        default_factory=list, max_length=50
    )
    engineer_verified_findings: list[EngineerVerifiedFindingInput] = Field(
        default_factory=list, max_length=50
    )


class EvidenceItem(BaseModel):
    reference: str
    provenance: EvidenceProvenance
    summary: str


class EvidenceCitation(BaseModel):
    reference: str = Field(min_length=1)
    provenance: EvidenceProvenance
    relevance: str = Field(min_length=1)


class RootCauseHypothesis(BaseModel):
    cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    supporting_evidence: list[EvidenceCitation] = Field(min_length=1)
    provenance: Literal["ai_generated_hypothesis"] = "ai_generated_hypothesis"


class HistoricalSimilarity(BaseModel):
    memory_reference: str = Field(min_length=1)
    similarity_summary: str = Field(min_length=1)
    relevance: str = Field(min_length=1)
    provenance: Literal["historical_hindsight_memory"] = (
        "historical_hindsight_memory"
    )


class RecommendedInvestigationStep(BaseModel):
    step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    supporting_evidence: list[EvidenceCitation] = Field(min_length=1)
    provenance: Literal["ai_generated_hypothesis"] = "ai_generated_hypothesis"
    requires_engineer_review: Literal[True] = True


class ConfidenceAssessment(BaseModel):
    score: float = Field(ge=0, le=1)
    limitations: list[str] = Field(min_length=1)


class InvestigationAnalysis(BaseModel):
    """Full analysis with current, historical, and verified sources separated."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str | None
    summary: str = Field(min_length=1)
    analysis_provenance: Literal["ai_generated_hypothesis"] = (
        "ai_generated_hypothesis"
    )
    current_evidence: list[EvidenceItem]
    historical_memories: list[HistoricalMemoryInput]
    engineer_verified_findings: list[EngineerVerifiedFindingInput]
    potential_root_causes: list[RootCauseHypothesis]
    historical_similarities: list[HistoricalSimilarity]
    recommended_steps: list[RecommendedInvestigationStep]
    confidence: ConfidenceAssessment
    information_still_required: list[str]
    model_identifier: str


class _ModelCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=1)
    relevance: str = Field(min_length=1)


class _ModelHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)
    supporting_evidence: list[_ModelCitation] = Field(min_length=1)


class _ModelSimilarity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_reference: str = Field(min_length=1)
    similarity_summary: str = Field(min_length=1)
    relevance: str = Field(min_length=1)


class _ModelRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    supporting_evidence: list[_ModelCitation] = Field(min_length=1)


class _ModelConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=1)
    limitations: list[str] = Field(min_length=1)


class _ModelAnalysis(BaseModel):
    """Only fields produced by Groq; provenance labels are assigned locally."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    potential_root_causes: list[_ModelHypothesis]
    historical_similarities: list[_ModelSimilarity]
    recommended_steps: list[_ModelRecommendation]
    confidence: _ModelConfidence
    information_still_required: list[str]
