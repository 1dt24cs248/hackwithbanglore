"""Typed service inputs and results for incident investigation workflows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.ai import InvestigationAnalysis


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class MemoryMode(str, Enum):
    MEMORY_OFF = "off"
    MEMORY_ON = "on"

    @classmethod
    def parse(cls, value: object) -> "MemoryMode":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"memory_off", "off"}:
                return cls.MEMORY_OFF
            if normalized in {"memory_on", "on"}:
                return cls.MEMORY_ON
        raise ValueError("memory_mode must be MEMORY_OFF or MEMORY_ON.")


class IncidentLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    log_type: Literal["error", "warning", "deployment", "note"] = "note"
    log_text: str = Field(min_length=1, max_length=50_000)
    source_system: str | None = Field(default=None, max_length=100)
    author: str | None = Field(default=None, max_length=150)


class DeploymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    deployment_id: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=100)
    deployed_by: str | None = Field(default=None, max_length=150)
    deployed_at: datetime | None = None
    change_summary: str | None = Field(default=None, max_length=20_000)


class IncidentSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=20_000)
    severity: Severity
    service_name: str = Field(min_length=1, max_length=150)
    environment: str = Field(min_length=1, max_length=50)
    owner: str | None = Field(default=None, max_length=150)
    source: str = Field(default="api", min_length=1, max_length=50)
    error_messages: list[str] = Field(default_factory=list, max_length=100)
    logs: list[IncidentLogInput] = Field(default_factory=list, max_length=100)
    deployment: DeploymentInput | None = None
    system_metrics: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=100
    )


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_mode: MemoryMode

    @field_validator("memory_mode", mode="before")
    @classmethod
    def normalize_memory_mode(cls, value: object) -> MemoryMode:
        return MemoryMode.parse(value)


class EngineerFeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    investigation_run_id: UUID
    recommendation_id: UUID
    feedback_type: Literal["accepted", "rejected", "corrected"]
    comment: str | None = Field(default=None, max_length=5_000)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    created_by: str = Field(min_length=1, max_length=150)

    @model_validator(mode="after")
    def require_correction_detail(self) -> "EngineerFeedbackInput":
        if self.feedback_type == "corrected" and not (self.comment or "").strip():
            raise ValueError("Corrected feedback requires a comment.")
        return self


class VerifiedResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    root_cause_summary: str = Field(min_length=1, max_length=20_000)
    resolution_summary: str = Field(min_length=1, max_length=20_000)
    verified_by: str = Field(min_length=1, max_length=150)
    confirmed: bool
    investigation_run_id: UUID | None = None


class FailedApproachInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    attempted_action: str = Field(min_length=1, max_length=10_000)
    outcome: str = Field(min_length=1, max_length=10_000)
    recorded_by: str = Field(min_length=1, max_length=150)
    investigation_run_id: UUID | None = None


class IncidentSubmissionResult(BaseModel):
    incident_id: UUID
    incident_number: str
    status: str


class RecommendationReference(BaseModel):
    id: UUID
    index: int = Field(ge=0)
    step: str
    requires_engineer_review: Literal[True] = True


class InvestigationExecutionResult(BaseModel):
    investigation_id: UUID
    incident_id: UUID
    memory_mode: MemoryMode
    execution_status: Literal["succeeded"]
    model_identifier: str
    analysis: InvestigationAnalysis
    recommendations: list[RecommendationReference]


class EngineerFeedbackResult(BaseModel):
    feedback_id: UUID
    investigation_run_id: UUID
    recommendation_id: UUID
    feedback_type: Literal["accepted", "rejected", "corrected"]


class VerifiedResolutionResult(BaseModel):
    resolution_id: UUID
    incident_id: UUID
    status: Literal["resolved"]
    memory_retention_status: Literal["success", "failed", "skipped_duplicate"]
    memory_error_category: str | None = None


class FailedApproachResult(BaseModel):
    incident_id: UUID
    memory_retention_status: Literal["success", "failed", "skipped_duplicate"]
    memory_error_category: str | None = None
