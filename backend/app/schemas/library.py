"""Validated public-source incident catalog records."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class LibraryMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    value: str | int | float | bool | None
    unit: str | None = Field(default=None, max_length=40)
    scope: str = Field(min_length=1, max_length=200)
    evidence: str = Field(min_length=1, max_length=1000)


class IncidentSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    source_type: Literal["postmortem", "status_report", "engineering_report", "official_update"]
    publication_date: date | None = None
    status_url: HttpUrl | None = None
    evidence_notes: str = Field(min_length=1, max_length=3000)
    verified_at: date


class IncidentLibraryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=3, max_length=80)
    company: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    incident_date: date
    start_time: str | None = Field(default=None, max_length=80)
    end_time: str | None = Field(default=None, max_length=80)
    duration: str | None = Field(default=None, max_length=120)
    affected_products: list[str] = Field(min_length=1, max_length=30)
    affected_services: list[str] = Field(min_length=1, max_length=30)
    category: str = Field(min_length=1, max_length=100)
    incident_type: str = Field(min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=20)
    severity: Literal["critical", "high", "medium", "low"]
    severity_basis: str = Field(min_length=1, max_length=500)
    environment: str | None = Field(default=None, max_length=50)
    investigation_summary: str = Field(min_length=1, max_length=4000)
    symptoms: list[str] = Field(min_length=1, max_length=30)
    reported_errors: list[str] = Field(default_factory=list, max_length=20)
    documented_metrics: list[LibraryMetric] = Field(default_factory=list, max_length=60)
    technical_root_cause: str | None = Field(default=None, max_length=5000)
    infrastructure: list[str] = Field(default_factory=list, max_length=30)
    dependencies: list[str] = Field(default_factory=list, max_length=30)
    trigger: str | None = Field(default=None, max_length=3000)
    customer_impact: str = Field(min_length=1, max_length=4000)
    business_impact: str = Field(min_length=1, max_length=4000)
    customers_affected: str | None = Field(default=None, max_length=300)
    financial_impact: str | None = Field(default=None, max_length=500)
    sla_impact: str | None = Field(default=None, max_length=1000)
    recovery_actions: list[str] = Field(min_length=1, max_length=30)
    preventive_actions: list[str] = Field(min_length=1, max_length=40)
    data_gaps: list[str] = Field(default_factory=list, max_length=40)
    sources: list[IncidentSource] = Field(min_length=1, max_length=10)
    verification_status: Literal["verified", "partially_verified", "needs_review", "rejected"]
    source_publication_date: date | None = None
    last_verified_at: date

    @field_validator("documented_metrics")
    @classmethod
    def reject_non_finite_metric(cls, metrics: list[LibraryMetric]) -> list[LibraryMetric]:
        for metric in metrics:
            if isinstance(metric.value, float) and (metric.value != metric.value or abs(metric.value) == float("inf")):
                raise ValueError("Metric values must be finite numbers.")
        return metrics
