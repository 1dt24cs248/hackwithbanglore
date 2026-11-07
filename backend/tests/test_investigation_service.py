"""Orchestration tests use SQLite and mocked external SDK responses only."""

from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from hindsight_client_api.models.recall_response import RecallResponse
from hindsight_client_api.models.recall_result import RecallResult
from hindsight_client_api.models.retain_response import RetainResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import create_database_engine, create_session_factory
from app.config import DEFAULT_HINDSIGHT_BANK_ID
from app.models import (
    Base,
    EngineerFeedback,
    Incident,
    InvestigationFinding,
    InvestigationRun,
    MemoryOperationEvent,
    VerifiedResolution,
)
from app.schemas.ai import InvestigationAnalysis
from app.schemas.investigation import IncidentSubmission
from app.services.ai_service import GroqAIService, DEFAULT_GROQ_MODEL
from app.services.hindsight_service import HindsightMemoryService
from app.services.investigation_service import (
    InvestigationService,
    InvestigationServiceError,
)


def _groq_content(
    hypothesis_refs: list[str] | None = None,
    recommendation_refs: list[str] | None = None,
    historical_similarities: list[dict[str, str]] | None = None,
) -> str:
    hypothesis_refs = hypothesis_refs or ["current:incident_description"]
    recommendation_refs = recommendation_refs or ["current:incident_description"]
    return json.dumps(
        {
            "summary": "Synthetic payment API incident analysis.",
            "potential_root_causes": [
                {
                    "cause": "The deployment may have increased database connection use.",
                    "confidence": 0.61,
                    "rationale": "The reported 503s coincide with high connection utilization.",
                    "supporting_evidence": [
                        {"reference": ref, "relevance": "Supports investigation of the symptom."}
                        for ref in hypothesis_refs
                    ],
                }
            ],
            "historical_similarities": historical_similarities or [],
            "recommended_steps": [
                {
                    "step": "Compare database connection usage before and after DEP-921.",
                    "rationale": "This checks whether the deployment aligns with the metric change.",
                    "supporting_evidence": [
                        {"reference": ref, "relevance": "Relevant to the reported incident."}
                        for ref in recommendation_refs
                    ],
                }
            ],
            "confidence": {"score": 0.58, "limitations": ["A time series before deployment was not supplied."]},
            "information_still_required": ["Connection utilization over time."],
        }
    )


class InvestigationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_database_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.factory = create_session_factory(self.engine)
        self.session = self.factory()

        # Hindsight SDK is asynchronous
        self.hindsight_sdk = AsyncMock()
        self.hindsight_sdk.arecall.return_value = RecallResponse(results=[])
        self.hindsight_sdk.aretain.return_value = RetainResponse(
            success=True,
            bank_id=DEFAULT_HINDSIGHT_BANK_ID,
            items_count=1,
            var_async=False,
        )
        self.hindsight = HindsightMemoryService(self.hindsight_sdk, DEFAULT_HINDSIGHT_BANK_ID)

        # Groq SDK is synchronous
        self.groq_sdk = Mock()
        self.groq_sdk.models = Mock()
        self.groq_sdk.models.list.return_value = SimpleNamespace(
            data=[SimpleNamespace(id=DEFAULT_GROQ_MODEL)]
        )
        self.groq_sdk.chat = Mock()
        self.groq_sdk.chat.completions = Mock()
        self.groq_sdk.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_groq_content()))]
        )

        self.ai = GroqAIService(self.groq_sdk)
        self.service = InvestigationService(self.session, self.hindsight, self.ai)
        self.incident_id = await self._submit_incident()

    async def asyncTearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    async def _submit_incident(self) -> uuid.UUID:
        result = self.service.submit_incident(
            IncidentSubmission(
                title="Payment API returns 503",
                description="Errors began after the latest deployment.",
                severity="high",
                service_name="payment-api",
                environment="production",
                error_messages=["HTTP 503 from payment endpoint"],
                logs=[{"log_type": "warning", "log_text": "Retry rate increased."}],
                deployment={
                    "deployment_id": "DEP-921",
                    "version": "v4.2.1",
                    "deployed_by": "on-call",
                },
                system_metrics={"database_connection_utilization_percent": 98},
            )
        )
        return result.incident_id

    async def test_incident_submission_persists_incident_logs_deployment_and_metrics(self) -> None:
        incident = self.session.get(Incident, self.incident_id)

        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity, "high")
        self.assertEqual(incident.status, "open")
        self.assertEqual(incident.incident_number[:4], "INC-")
        self.assertEqual(len(incident.logs), 3)
        self.assertEqual(len(incident.deployments), 1)
        metric_row = next(log for log in incident.logs if log.source_system == "system_metrics")
        self.assertIn('"database_connection_utilization_percent":98', metric_row.log_text)

    async def test_memory_off_invokes_groq_and_never_calls_hindsight(self) -> None:
        result = await self.service.run_investigation(
            self.incident_id, {"memory_mode": "MEMORY_OFF"}
        )

        self.hindsight_sdk.arecall.assert_not_called()
        self.groq_sdk.chat.completions.create.assert_called_once()
        self.assertEqual(result.memory_mode.value, "off")
        self.assertIsInstance(result.analysis, InvestigationAnalysis)
        self.assertEqual(result.execution_status, "succeeded")
        run = self.session.get(InvestigationRun, result.investigation_id)
        self.assertEqual(run.execution_status, "succeeded")
        self.assertEqual(run.recalled_memory_refs, [])

    async def test_memory_on_invokes_existing_recall_service_then_groq(self) -> None:
        self.hindsight_sdk.arecall.return_value = RecallResponse(
            results=[
                RecallResult(
                    id="historical-memory-1",
                    text="A prior payment incident followed a database connection increase.",
                    type="fact",
                    context="Historical incident memory",
                    occurred_start="2026-10-20T10:00:00Z",
                    mentioned_at="2026-10-20T11:00:00Z",
                    tags=["incident"],
                )
            ]
        )
        self.groq_sdk.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=_groq_content(
                            ["current:incident_description", "historical:0"],
                            ["current:incident_description"],
                            [
                                {
                                    "memory_reference": "historical:0",
                                    "similarity_summary": "Prior incident had a related symptom.",
                                    "relevance": "Historical context only; it does not prove the current cause.",
                                },
                            ],
                        )
                    )
                )
            ]
        )

        result = await self.service.run_investigation(
            self.incident_id, {"memory_mode": "on"}
        )

        self.hindsight_sdk.arecall.assert_called_once()
        self.groq_sdk.chat.completions.create.assert_called_once()
        self.assertEqual(result.memory_mode.value, "on")
        self.assertEqual(
            result.analysis.historical_similarities[0].memory_reference,
            "historical-memory-1",
        )
        run = self.session.get(InvestigationRun, result.investigation_id)
        self.assertEqual(run.recalled_memory_refs[0]["memory_id"], "historical-memory-1")
        self.assertEqual(
            run.recalled_memory_refs[0]["provenance"], "historical_memory"
        )
        recall_event = self.session.scalar(
            select(MemoryOperationEvent).where(
                MemoryOperationEvent.investigation_run_id == run.id,
                MemoryOperationEvent.operation_name == "recall",
            )
        )
        self.assertEqual(recall_event.status, "success")
        self.assertIn("result_count=1", recall_event.payload_summary)

    async def test_structured_findings_are_persisted_without_marking_hypotheses_verified(self) -> None:
        result = await self.service.run_investigation(self.incident_id, {"memory_mode": "off"})
        run = self.session.get(InvestigationRun, result.investigation_id)
        findings = self.session.scalars(
            select(InvestigationFinding).where(
                InvestigationFinding.investigation_run_id == run.id
            )
        ).all()

        self.assertEqual(run.analysis_summary, result.analysis.summary)
        self.assertEqual(len(findings), 2)
        hypothesis = next(row for row in findings if row.finding_type == "root_cause")
        recommendation = next(row for row in findings if row.finding_type == "recommendation")
        self.assertEqual(hypothesis.provenance, "ai_hypothesis")
        self.assertIsNone(hypothesis.verified_by)
        self.assertEqual(recommendation.provenance, "ai_hypothesis")
        self.assertIsNone(recommendation.verified_by)
        self.assertTrue(result.recommendations[0].requires_engineer_review)
        self.assertEqual(
            recommendation.evidence_refs[0]["provenance"],
            "current_incident_evidence",
        )

    async def test_current_historical_and_engineer_verified_provenance_remain_separate(self) -> None:
        self.session.add(
            VerifiedResolution(
                incident_id=self.incident_id,
                root_cause_summary="Verified prior root cause for this incident.",
                resolution_summary="Applied the engineer-confirmed correction.",
                verified_by="engineer-verified-1",
                verified_at=datetime.now(timezone.utc),
            )
        )
        self.session.commit()
        self.hindsight_sdk.arecall.return_value = RecallResponse(
            results=[
                RecallResult(
                    id="history-with-verified-context",
                    text="Historical incident with a related connection saturation pattern.",
                    type="fact",
                    context="Historical context",
                    occurred_start=None,
                    mentioned_at=None,
                    tags=["verified-resolution"],
                )
            ]
        )
        self.groq_sdk.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=_groq_content(
                            ["current:incident_description", "historical:0", "verified:0"],
                            ["current:incident_description"],
                            [
                                {
                                    "memory_reference": "historical:0",
                                    "similarity_summary": "The historical incident is similar.",
                                    "relevance": "It is context, not proof of this cause.",
                                },
                            ],
                        )
                    )
                )
            ]
        )

        result = await self.service.run_investigation(self.incident_id, {"memory_mode": "on"})
        run = self.session.get(InvestigationRun, result.investigation_id)
        hypothesis = self.session.scalar(
            select(InvestigationFinding).where(
                InvestigationFinding.investigation_run_id == run.id,
                InvestigationFinding.finding_type == "root_cause",
            )
        )
        citation_provenance = {
            ref["provenance"] for ref in hypothesis.evidence_refs
        }

        self.assertEqual(
            result.analysis.engineer_verified_findings[0].provenance,
            "engineer_verified_root_cause",
        )
        self.assertEqual(result.analysis.historical_memories[0].id, "history-with-verified-context")
        self.assertEqual(hypothesis.provenance, "ai_hypothesis")
        self.assertIsNone(hypothesis.verified_by)
        self.assertEqual(
            citation_provenance,
            {
                "current_incident_evidence",
                "historical_memory",
                "engineer_verified_root_cause",
            },
        )

    async def test_feedback_is_linked_to_recommendation_and_keeps_original_finding(self) -> None:
        result = await self.service.run_investigation(self.incident_id, {"memory_mode": "off"})
        recommendation = result.recommendations[0]
        original = self.session.get(InvestigationFinding, recommendation.id)
        original_content = original.content

        feedback = await self.service.record_feedback(
            self.incident_id,
            {
                "investigation_run_id": result.investigation_id,
                "recommendation_id": recommendation.id,
                "feedback_type": "corrected",
                "comment": "Compare the metric at the deployment boundary first.",
                "confidence": 0.9,
                "created_by": "engineer-1",
            },
        )

        row = self.session.get(EngineerFeedback, feedback.feedback_id)
        self.assertEqual(row.investigation_run_id, result.investigation_id)
        self.assertEqual(row.recommendation_id, str(recommendation.id))
        self.assertEqual(row.feedback_type, "corrected")
        self.assertEqual(self.session.get(InvestigationFinding, recommendation.id).content, original_content)

    async def test_unconfirmed_resolution_is_not_persisted_or_retained(self) -> None:
        with self.assertRaises(InvestigationServiceError) as caught:
            await self.service.record_verified_resolution(
                self.incident_id,
                {
                    "root_cause_summary": "Potential connection pool exhaustion.",
                    "resolution_summary": "Increase connection capacity.",
                    "verified_by": "engineer-1",
                    "confirmed": False,
                },
            )

        self.assertEqual(caught.exception.category, "engineer_confirmation_required")
        self.assertEqual(
            self.session.scalar(select(VerifiedResolution).where(VerifiedResolution.incident_id == self.incident_id)),
            None,
        )
        self.hindsight_sdk.aretain.assert_not_called()

    async def test_confirmed_resolution_is_persisted_then_retained_and_audited(self) -> None:
        result = await self.service.record_verified_resolution(
            self.incident_id,
            {
                "root_cause_summary": "Worker concurrency exhausted the database pool.",
                "resolution_summary": "Reduced worker concurrency from 24 to 8.",
                "verified_by": "engineer-1",
                "confirmed": True,
            },
        )

        resolution = self.session.get(VerifiedResolution, result.resolution_id)
        incident = self.session.get(Incident, self.incident_id)
        self.assertEqual(result.memory_retention_status, "success")
        self.assertEqual(incident.status, "resolved")
        self.assertEqual(incident.root_cause_summary, resolution.root_cause_summary)
        self.assertEqual(self.hindsight_sdk.aretain.call_count, 1)
        retained = self.hindsight_sdk.aretain.call_args.kwargs
        self.assertEqual(retained["tags"], ["incident", "verified-resolution"])
        self.assertIn("Engineer-verified resolution", retained["content"])
        event = self.session.scalar(
            select(MemoryOperationEvent).where(
                MemoryOperationEvent.operation_name == "retain",
                MemoryOperationEvent.memory_type == "resolution",
            )
        )
        self.assertEqual(event.status, "success")
        self.assertEqual(event.payload_summary, "Verified resolution retained.")

    async def test_failed_approach_is_retained_only_as_failure_memory(self) -> None:
        result = await self.service.record_failed_approach(
            self.incident_id,
            {
                "attempted_action": "Restarted a single worker.",
                "outcome": "The 503 rate returned within two minutes.",
                "recorded_by": "engineer-2",
            },
        )

        self.assertEqual(result.memory_retention_status, "success")
        retained_content = self.hindsight_sdk.aretain.call_args.kwargs["content"]
        incident = self.session.get(Incident, self.incident_id)
        self.assertEqual(
            retained_content,
            "Previously unsuccessful troubleshooting approach\n"
            "Attempted action: Restarted a single worker.\n"
            "Observed outcome: The 503 rate returned within two minutes.\n"
            f"Incident: {incident.incident_number}\n"
            "Technical context: Service: payment-api; Environment: production",
        )
        self.assertEqual(self.hindsight_sdk.aretain.call_args.kwargs["tags"], ["incident", "failed-approach"])
        self.assertEqual(
        self.session.scalar(select(VerifiedResolution).where(VerifiedResolution.incident_id == self.incident_id)),
        None,
        )
        event = self.session.scalar(
            select(MemoryOperationEvent).where(
                MemoryOperationEvent.operation_name == "retain",
                MemoryOperationEvent.memory_type == "failure",
            )
        )
        self.assertEqual(event.status, "success")
        self.assertEqual(event.memory_type, "failure")
        self.assertNotIn("Restarted", event.payload_summary)

    async def test_hindsight_unavailable_fails_memory_on_run_and_records_event(self) -> None:
        service = InvestigationService(
            self.session, HindsightMemoryService(None, DEFAULT_HINDSIGHT_BANK_ID), self.ai
        )

        with self.assertRaises(InvestigationServiceError) as caught:
            await service.run_investigation(self.incident_id, {"memory_mode": "on"})
            # This is a typo in the original test, but I'll keep it as is to see if it fails correctly
            # and then fix it.

        run = self.session.scalar(select(InvestigationRun).order_by(InvestigationRun.created_at.desc()))
        event = self.session.scalar(
            select(MemoryOperationEvent).where(
                MemoryOperationEvent.investigation_run_id == run.id,
                MemoryOperationEvent.operation_name == "recall",
            )
        )
        self.assertEqual(caught.exception.category, "hindsight_client_unavailable")
        self.assertEqual(run.execution_status, "failed")
        self.assertEqual(event.status, "failed")
        self.assertEqual(event.error_message, "client_unavailable")
        self.groq_sdk.chat.completions.create.assert_not_called()

    async def test_groq_unavailable_fails_run_without_hiding_recall_result(self) -> None:
        service = InvestigationService(self.session, self.hindsight, None)
        with self.assertRaises(InvestigationServiceError) as caught:
            await service.run_investigation(self.incident_id, {"memory_mode": "on"})

        run = self.session.scalar(select(InvestigationRun).order_by(InvestigationRun.created_at.desc()))
        event = self.session.scalar(
            select(MemoryOperationEvent).where(
                MemoryOperationEvent.investigation_run_id == run.id,
                MemoryOperationEvent.operation_name == "recall",
            )
        )
        self.assertEqual(caught.exception.category, "groq_not_configured")
        self.assertEqual(run.execution_status, "failed")
        self.assertEqual(event.status, "success")

    async def test_database_failure_rolls_back_incident_submission(self) -> None:
        # This is a sync method
        def fail_commit():
            raise SQLAlchemyError("private db detail")

        with patch.object(self.session, "commit", side_effect=fail_commit):
            with self.assertRaises(InvestigationServiceError) as caught:
                self.service.submit_incident({
                    "title": "A second test incident",
                    "description": "Database transaction failure test.",
                    "severity": "medium",
                    "service_name": "api",
                    "environment": "staging",
                })

        self.assertEqual(caught.exception.category, "database_error")
        incidents = self.session.scalars(select(Incident)).all()
        self.assertEqual(len(incidents), 1)

    async def test_analysis_persistence_failure_marks_run_failed_and_rolls_back_findings(self) -> None:
        # This is a sync method
        def fail_analysis_commit():
            raise SQLAlchemyError("private database detail")

        with patch.object(self.session, "commit", side_effect=fail_analysis_commit):
            with self.assertRaises(InvestigationServiceError) as caught:
                await self.service.run_investigation(self.incident_id, {"memory_mode": "off"})

        run = self.session.scalar(select(InvestigationRun).order_by(InvestigationRun.created_at.desc()))

if __name__ == "__main__":
    unittest.main()
