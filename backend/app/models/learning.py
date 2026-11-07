"""Verified resolutions, engineer review, postmortems, and memory audit rows."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class VerifiedResolution(Base):
    __tablename__ = "verified_resolutions"
    __table_args__ = (
        CheckConstraint("length(trim(root_cause_summary)) > 0", name="ck_verified_resolutions_root_cause_nonempty"),
        CheckConstraint("length(trim(resolution_summary)) > 0", name="ck_verified_resolutions_summary_nonempty"),
        CheckConstraint("length(trim(verified_by)) > 0", name="ck_verified_resolutions_verifier_nonempty"),
        ForeignKeyConstraint(
            ["incident_id", "investigation_run_id"],
            ["investigation_runs.incident_id", "investigation_runs.id"],
            name="fk_verified_resolutions_run_incident",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "investigation_run_id IS NULL OR incident_id IS NOT NULL",
            name="ck_verified_resolutions_run_requires_incident",
        ),
        UniqueConstraint("incident_id", "id", name="uq_verified_resolutions_incident_id_id"),
        Index("ix_verified_resolutions_incident_verified", "incident_id", "verified_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    investigation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigation_runs.id", ondelete="RESTRICT")
    )
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_summary: Mapped[str] = mapped_column(Text, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(150), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="verified_resolutions")
    investigation_run: Mapped["InvestigationRun | None"] = relationship(
        back_populates="verified_resolutions", foreign_keys=[investigation_run_id]
    )
    postmortems: Mapped[list["Postmortem"]] = relationship(viewonly=True)


class EngineerFeedback(Base):
    __tablename__ = "engineer_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('accepted', 'rejected', 'corrected')",
            name="ck_engineer_feedback_type",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_engineer_feedback_confidence",
        ),
        ForeignKeyConstraint(
            ["incident_id", "investigation_run_id"],
            ["investigation_runs.incident_id", "investigation_runs.id"],
            name="fk_engineer_feedback_run_incident",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "investigation_run_id IS NULL OR incident_id IS NOT NULL",
            name="ck_engineer_feedback_run_requires_incident",
        ),
        Index("ix_engineer_feedback_incident_created", "incident_id", "created_at"),
        Index("ix_engineer_feedback_run_created", "investigation_run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    investigation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigation_runs.id", ondelete="RESTRICT")
    )
    recommendation_id: Mapped[str | None] = mapped_column(String(100))
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(150), nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="feedback")
    investigation_run: Mapped["InvestigationRun | None"] = relationship(
        back_populates="feedback", foreign_keys=[investigation_run_id]
    )


class Postmortem(Base):
    __tablename__ = "postmortems"
    __table_args__ = (
        CheckConstraint("length(trim(body_markdown)) > 0", name="ck_postmortems_body_nonempty"),
        CheckConstraint(
            "status IN ('draft', 'final', 'archived')", name="ck_postmortems_status"
        ),
        CheckConstraint("revision_number > 0", name="ck_postmortems_revision_positive"),
        ForeignKeyConstraint(
            ["incident_id", "verified_resolution_id"],
            ["verified_resolutions.incident_id", "verified_resolutions.id"],
            name="fk_postmortems_verified_resolution_same_incident",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("incident_id", "revision_number", name="uq_postmortems_incident_revision"),
        Index("ix_postmortems_incident_created", "incident_id", "created_at"),
        Index(
            "uq_postmortems_one_final_per_incident",
            "incident_id",
            unique=True,
            postgresql_where=text("status = 'final'"),
            sqlite_where=text("status = 'final'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    verified_resolution_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", server_default="draft")
    generated_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    downloaded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    incident: Mapped["Incident"] = relationship(
        back_populates="postmortems", foreign_keys=[incident_id]
    )
    verified_resolution: Mapped[VerifiedResolution] = relationship(
        viewonly=True, foreign_keys=[incident_id, verified_resolution_id]
    )


class MemoryOperationEvent(Base):
    __tablename__ = "memory_operation_events"
    __table_args__ = (
        CheckConstraint(
            "operation_name IN ('retain', 'recall', 'conflict_detected')",
            name="ck_memory_events_operation",
        ),
        CheckConstraint(
            "memory_type IN ('incident', 'resolution', 'failure')",
            name="ck_memory_events_memory_type",
        ),
        CheckConstraint(
            "status IN ('success', 'failed', 'partial')",
            name="ck_memory_events_status",
        ),
        ForeignKeyConstraint(
            ["incident_id", "investigation_run_id"],
            ["investigation_runs.incident_id", "investigation_runs.id"],
            name="fk_memory_events_run_incident",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "investigation_run_id IS NULL OR incident_id IS NOT NULL",
            name="ck_memory_events_run_requires_incident",
        ),
        Index("ix_memory_events_incident_operation_created", "incident_id", "operation_name", "created_at"),
        Index("ix_memory_events_run_created", "investigation_run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT")
    )
    investigation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigation_runs.id", ondelete="RESTRICT")
    )
    operation_name: Mapped[str] = mapped_column(String(50), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payload_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    error_message: Mapped[str | None] = mapped_column(String(500))

    incident: Mapped["Incident | None"] = relationship(back_populates="memory_events")
    investigation_run: Mapped["InvestigationRun | None"] = relationship(
        back_populates="memory_events", foreign_keys=[investigation_run_id]
    )

    @validates("payload_summary", "error_message")
    def validate_audit_text(self, _key: str, value: str | None) -> str | None:
        if value and _contains_credential(value):
            raise ValueError("Memory operation audit text must not contain credentials.")
        return value


def _contains_credential(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "api_key=",
            "api-key=",
            "password=",
            "secret=",
            "authorization:",
            "bearer ",
        )
    )
