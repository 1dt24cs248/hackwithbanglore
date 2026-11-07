"""Incident and operational context records."""

import re
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|password|secret|authorization)\s*[:=]\s*(?:bearer\s+)?\S+"
)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_incidents_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'closed')",
            name="ck_incidents_status",
        ),
        CheckConstraint("created_at <= updated_at", name="ck_incidents_timestamp_order"),
        CheckConstraint(
            "synthetic_data = is_demo",
            name="ck_incidents_synthetic_demo_flags_match",
        ),
        CheckConstraint("length(trim(title)) > 0", name="ck_incidents_title_nonempty"),
        CheckConstraint("length(trim(description)) > 0", name="ck_incidents_description_nonempty"),
        Index("ix_incidents_status_severity_created", "status", "severity", "created_at"),
        Index(
            "ix_incidents_service_environment_created",
            "service_name",
            "environment",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", server_default="open")
    owner: Mapped[str | None] = mapped_column(String(150))
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="api", server_default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    root_cause_summary: Mapped[str | None] = mapped_column(Text)
    synthetic_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    investigation_runs: Mapped[list["InvestigationRun"]] = relationship(back_populates="incident")
    logs: Mapped[list["IncidentLog"]] = relationship(back_populates="incident")
    deployments: Mapped[list["Deployment"]] = relationship(back_populates="incident")
    feedback: Mapped[list["EngineerFeedback"]] = relationship(back_populates="incident")
    verified_resolutions: Mapped[list["VerifiedResolution"]] = relationship(back_populates="incident")
    postmortems: Mapped[list["Postmortem"]] = relationship(back_populates="incident")
    memory_events: Mapped[list["MemoryOperationEvent"]] = relationship(back_populates="incident")


class IncidentLog(Base):
    __tablename__ = "incident_logs"
    __table_args__ = (
        CheckConstraint(
            "log_type IN ('error', 'warning', 'deployment', 'note')",
            name="ck_incident_logs_type",
        ),
        CheckConstraint(
            "lower(log_text) NOT LIKE '%api_key=%' AND "
            "lower(log_text) NOT LIKE '%api-key=%' AND "
            "lower(log_text) NOT LIKE '%password=%' AND "
            "lower(log_text) NOT LIKE '%secret=%' AND "
            "lower(log_text) NOT LIKE '%authorization:%' AND "
            "lower(log_text) NOT LIKE '%bearer %'",
            name="ck_incident_logs_no_common_credentials",
        ),
        Index("ix_incident_logs_incident_created", "incident_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    log_type: Mapped[str] = mapped_column(String(40), nullable=False)
    log_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    author: Mapped[str | None] = mapped_column(String(150))

    incident: Mapped[Incident] = relationship(back_populates="logs")

    @validates("log_text")
    def reject_common_credentials(self, _key: str, value: str) -> str:
        if _CREDENTIAL_PATTERN.search(value):
            raise ValueError("Incident logs must not contain credential-shaped values.")
        return value


class Deployment(Base):
    __tablename__ = "deployments"
    __table_args__ = (
        Index("ix_deployments_incident_deployed", "incident_id", "deployed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False
    )
    deployment_id: Mapped[str | None] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100))
    deployed_by: Mapped[str | None] = mapped_column(String(150))
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    incident: Mapped[Incident] = relationship(back_populates="deployments")
