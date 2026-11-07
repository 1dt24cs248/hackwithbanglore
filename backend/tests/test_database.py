"""Isolated SQLAlchemy/Alembic tests; no PostgreSQL credentials are required."""

import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import check_database, create_database_engine, create_session_factory
from app.models import (
    Base,
    Deployment,
    EngineerFeedback,
    Incident,
    IncidentLog,
    InvestigationFinding,
    InvestigationRun,
    MemoryOperationEvent,
    Postmortem,
    VerifiedResolution,
)


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_database_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.factory = create_session_factory(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _incident(self, number: str = "INC-TEST-1") -> Incident:
        return Incident(
            incident_number=number,
            title="Payment API latency",
            description="Latency increased after a deployment.",
            service_name="payment-api",
            environment="production",
            severity="high",
            source="api",
        )

    def test_crud_relationships_and_verified_postmortem_revisions(self) -> None:
        with self.factory() as session:
            incident = self._incident()
            session.add(incident)
            session.flush()
            run = InvestigationRun(
                incident_id=incident.id,
                memory_mode="on",
                execution_status="succeeded",
                recalled_memory_refs=[{"id": "memory-17", "memory_type": "resolution"}],
            )
            session.add(run)
            session.flush()
            finding = InvestigationFinding(
                investigation_run_id=run.id,
                finding_type="root_cause",
                content="Possible worker pool exhaustion.",
                provenance="ai_hypothesis",
                confidence=0.72,
                evidence_refs=[{"source": "current_incident", "id": "log-1"}],
            )
            session.add(finding)
            session.add(
                IncidentLog(
                    incident_id=incident.id,
                    log_type="error",
                    log_text="Synthetic timeout after 4s",
                    source_system="api",
                )
            )
            session.add(
                Deployment(
                    incident_id=incident.id,
                    environment="production",
                    service_name="payment-api",
                    deployed_at=datetime.now(timezone.utc),
                    version="v1.2.3",
                )
            )
            feedback = EngineerFeedback(
                incident_id=incident.id,
                investigation_run_id=run.id,
                recommendation_id="recommendation-1",
                feedback_type="accepted",
                created_by="engineer-1",
                confidence=0.9,
            )
            session.add(feedback)
            resolution = VerifiedResolution(
                incident_id=incident.id,
                investigation_run_id=run.id,
                root_cause_summary="Worker concurrency exhausted the database pool.",
                resolution_summary="Reduced worker concurrency from 24 to 8.",
                verified_by="engineer-1",
                verified_at=datetime.now(timezone.utc),
            )
            session.add(resolution)
            session.flush()
            session.add(
                MemoryOperationEvent(
                    incident_id=incident.id,
                    investigation_run_id=run.id,
                    operation_name="recall",
                    memory_type="resolution",
                    status="success",
                    payload_summary="Retrieved 1 reference.",
                )
            )
            draft = Postmortem(
                incident_id=incident.id,
                verified_resolution_id=resolution.id,
                revision_number=1,
                title="Payment API latency",
                body_markdown="# Draft",
                status="draft",
            )
            final = Postmortem(
                incident_id=incident.id,
                verified_resolution_id=resolution.id,
                revision_number=2,
                title="Payment API latency",
                body_markdown="# Final",
                status="final",
            )
            session.add_all([draft, final])
            session.commit()

            loaded = session.scalar(select(Incident).where(Incident.id == incident.id))
            self.assertEqual(loaded.investigation_runs[0].findings[0].provenance, "ai_hypothesis")
            self.assertEqual(len(loaded.postmortems), 2)
            self.assertEqual(final.verified_resolution.id, resolution.id)

    def test_foreign_keys_prevent_orphan_runs_and_cross_incident_feedback(self) -> None:
        with self.factory() as session:
            orphan_run = InvestigationRun(
                incident_id=uuid.uuid4(), memory_mode="off", execution_status="queued"
            )
            session.add(orphan_run)
            with self.assertRaises(SQLAlchemyError):
                session.commit()
            session.rollback()

            first = self._incident("INC-TEST-2")
            second = self._incident("INC-TEST-3")
            session.add_all([first, second])
            session.flush()
            run = InvestigationRun(
                incident_id=first.id, memory_mode="off", execution_status="queued"
            )
            session.add(run)
            session.flush()
            feedback = EngineerFeedback(
                incident_id=second.id,
                investigation_run_id=run.id,
                feedback_type="rejected",
                created_by="engineer-1",
            )
            session.add(feedback)
            with self.assertRaises(SQLAlchemyError):
                session.commit()

    def test_provenance_and_verification_constraints(self) -> None:
        with self.factory() as session:
            incident = self._incident("INC-TEST-4")
            session.add(incident)
            session.flush()
            run = InvestigationRun(
                incident_id=incident.id, memory_mode="off", execution_status="succeeded"
            )
            session.add(run)
            session.flush()

            invalid = InvestigationFinding(
                investigation_run_id=run.id,
                finding_type="root_cause",
                content="Unconfirmed model guess.",
                provenance="ai_hypothesis",
                verified_by="engineer-1",
            )
            session.add(invalid)
            with self.assertRaises(SQLAlchemyError):
                session.commit()
            session.rollback()

            verified_without_reviewer = InvestigationFinding(
                investigation_run_id=run.id,
                finding_type="root_cause",
                content="Claimed verified root cause.",
                provenance="engineer_verified_root_cause",
            )
            session.add(verified_without_reviewer)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_final_postmortem_is_unique_and_must_match_verified_resolution(self) -> None:
        with self.factory() as session:
            incident = self._incident("INC-TEST-5")
            other_incident = self._incident("INC-TEST-6")
            session.add_all([incident, other_incident])
            session.flush()
            resolution = VerifiedResolution(
                incident_id=incident.id,
                root_cause_summary="Verified cause.",
                resolution_summary="Verified repair.",
                verified_by="engineer-1",
                verified_at=datetime.now(timezone.utc),
            )
            session.add(resolution)
            session.flush()
            session.add(
                Postmortem(
                    incident_id=incident.id,
                    verified_resolution_id=resolution.id,
                    revision_number=1,
                    title="First final",
                    body_markdown="# Final",
                    status="final",
                )
            )
            session.commit()

            session.add(
                Postmortem(
                    incident_id=incident.id,
                    verified_resolution_id=resolution.id,
                    revision_number=2,
                    title="Second final",
                    body_markdown="# Final",
                    status="final",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

            mismatched = Postmortem(
                incident_id=other_incident.id,
                verified_resolution_id=resolution.id,
                revision_number=1,
                title="Mismatched report",
                body_markdown="# Draft",
                status="draft",
            )
            session.add(mismatched)
            with self.assertRaises(SQLAlchemyError):
                session.commit()

    def test_safe_reference_and_audit_metadata_validation(self) -> None:
        with self.assertRaises(ValueError):
            InvestigationRun(
                incident_id=uuid.uuid4(),
                memory_mode="on",
                recalled_memory_refs=[{"id": "m-1", "text": "full memory payload"}],
            )
        with self.assertRaises(ValueError):
            MemoryOperationEvent(
                operation_name="recall",
                memory_type="incident",
                status="success",
                payload_summary="api_key=do-not-store",
            )

    def test_incident_log_rejects_common_credentials(self) -> None:
        with self.assertRaises(ValueError):
            IncidentLog(log_type="error", log_text="Authorization: Bearer private-token")

    def test_database_health_reports_available_and_unavailable(self) -> None:
        self.assertTrue(check_database(self.engine))
        self.assertFalse(check_database(None))
        unreachable = Mock()
        unreachable.connect.side_effect = OperationalError("SELECT 1", {}, Exception())
        self.assertFalse(check_database(unreachable))

    def test_postgresql_urls_use_psycopg_driver_without_connecting(self) -> None:
        engine = create_database_engine(
            "postgresql://placeholder:placeholder@127.0.0.1:5432/incidentiq"
        )
        try:
            self.assertEqual(engine.dialect.name, "postgresql")
            self.assertEqual(engine.dialect.driver, "psycopg")
        finally:
            engine.dispose()

    def test_alembic_upgrade_creates_all_tables_in_isolated_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="incidentiq-alembic-") as temp_dir:
            db_path = Path(temp_dir) / "migrations.sqlite3"
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
            command.upgrade(config, "head")

            migrated_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
            try:
                table_names = set(inspect(migrated_engine).get_table_names())
            finally:
                migrated_engine.dispose()

            self.assertTrue(
                {
                    "incidents",
                    "investigation_runs",
                    "investigation_findings",
                    "incident_logs",
                    "deployments",
                    "engineer_feedback",
                    "verified_resolutions",
                    "postmortems",
                    "memory_operation_events",
                }.issubset(table_names)
            )


if __name__ == "__main__":
    unittest.main()
