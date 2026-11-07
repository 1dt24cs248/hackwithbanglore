"""Investigation executions and provenance-aware findings."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, JSON_VALUE
from app.models.validation import validate_safe_references


class InvestigationRun(Base):
    __tablename__ = "investigation_runs"
    __table_args__ = (
        CheckConstraint("memory_mode IN ('off', 'on')", name="ck_investigation_runs_memory_mode"),
        CheckConstraint(
            "execution_status IN ('queued', 'running', 'succeeded', 'failed', 'partial')",
            name="ck_investigation_runs_execution_status",
        ),
        UniqueConstraint("incident_id", "id", name="uq_investigation_runs_incident_id_id"),
        Index("ix_investigation_runs_incident_created", "incident_id", "created_at"),
        Index(
            "ix_investigation_runs_incident_mode_status",
            "incident_id",
            "memory_mode",
            "execution_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    memory_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    model_identifier: Mapped[str | None] = mapped_column(String(200))
    analysis_summary: Mapped[str | None] = mapped_column(Text)
    recalled_memory_refs: Mapped[dict[str, object] | list[object] | None] = mapped_column(JSON_VALUE)
    execution_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued", server_default="queued"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="investigation_runs")
    findings: Mapped[list["InvestigationFinding"]] = relationship(back_populates="investigation_run")
    feedback: Mapped[list["EngineerFeedback"]] = relationship(
        back_populates="investigation_run",
        foreign_keys="EngineerFeedback.investigation_run_id",
    )
    memory_events: Mapped[list["MemoryOperationEvent"]] = relationship(
        back_populates="investigation_run",
        foreign_keys="MemoryOperationEvent.investigation_run_id",
    )
    verified_resolutions: Mapped[list["VerifiedResolution"]] = relationship(
        back_populates="investigation_run",
        foreign_keys="VerifiedResolution.investigation_run_id",
    )

    @validates("recalled_memory_refs")
    def validate_recalled_memory_refs(self, _key: str, value: object) -> object:
        return validate_safe_references(value)


class InvestigationFinding(Base):
    __tablename__ = "investigation_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ('evidence', 'root_cause', 'recommendation')",
            name="ck_investigation_findings_type",
        ),
        CheckConstraint("length(trim(content)) > 0", name="ck_investigation_findings_content_nonempty"),
        CheckConstraint(
            "provenance IN ('current_incident_evidence', 'historical_memory', "
            "'ai_hypothesis', 'engineer_verified_root_cause')",
            name="ck_investigation_findings_provenance",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_investigation_findings_confidence",
        ),
        CheckConstraint(
            "(provenance = 'engineer_verified_root_cause' AND finding_type = 'root_cause' "
            "AND verified_by IS NOT NULL AND length(trim(verified_by)) > 0) OR "
            "(provenance <> 'engineer_verified_root_cause' AND verified_by IS NULL)",
            name="ck_investigation_findings_verification",
        ),
        CheckConstraint(
            "finding_type <> 'evidence' OR provenance = 'current_incident_evidence'",
            name="ck_investigation_findings_evidence_provenance",
        ),
        Index("ix_investigation_findings_run_created", "investigation_run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    evidence_refs: Mapped[list[object] | dict[str, object] | None] = mapped_column(JSON_VALUE)
    verified_by: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation_run: Mapped[InvestigationRun] = relationship(back_populates="findings")

    @validates("evidence_refs")
    def validate_evidence_refs(self, _key: str, value: object) -> object:
        return validate_safe_references(value)
