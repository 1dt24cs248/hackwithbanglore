"""Route tests use an isolated SQLite database and mocked provider services."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import DEFAULT_HINDSIGHT_BANK_ID
from app.database import create_database_engine, create_session_factory, get_db
from app.main import app
from app.models import Base, Incident, InvestigationFinding, InvestigationRun, MemoryOperationEvent
from app.schemas.ai import InvestigationAnalysis
from app.services.hindsight_service import HistoricalMemory, RecallResult, RetainResult
from app.services.investigation_service import InvestigationService


class FakeAI:
    model_identifier = "mock/model"

    def analyze_incident(self, context):
        return InvestigationAnalysis(
            incident_id=context.incident_id,
            summary="Synthetic incident summary.",
            analysis_provenance="ai_generated_hypothesis",
            current_evidence=[],
            historical_memories=context.historical_memories,
            engineer_verified_findings=context.engineer_verified_findings,
            potential_root_causes=[{
                "cause": "Possible pool saturation.", "confidence": 0.6,
                "rationale": "The metric is high.",
                "supporting_evidence":[{"reference":"current:incident_description","provenance":"current_incident_evidence","relevance":"Reported context."}],
            }],
            historical_similarities=[],
            recommended_steps=[{
                "step":"Compare connection utilization before and after deployment.",
                "rationale":"Validate temporal correlation.",
                "supporting_evidence":[{"reference":"current:incident_description","provenance":"current_incident_evidence","relevance":"Incident report."}],
                "requires_engineer_review":True,
            }],
            confidence={"score":0.6,"limitations":["Synthetic test output."]},
            information_still_required=["Connection utilization history."],
            model_identifier=self.model_identifier,
        )


class APIRouteTests(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["DATABASE_URL"] = "sqlite://"
        os.environ["HINDSIGHT_API_KEY"] = ""
        os.environ["GROQ_API_KEY"] = ""
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = create_session_factory(self.engine)

        def override_db():
            session = self.factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

        # Mock Hindsight service
        self.hindsight_service = AsyncMock()
        self.hindsight = self.hindsight_service
        self.hindsight_service.recall_incident_memories.return_value = RecallResult(
            status="success", bank_id=DEFAULT_HINDSIGHT_BANK_ID, recalled_at="2026-01-01T00:00:00Z",
            memories=(HistoricalMemory(id="mem-1", text="Prior verified pool issue", memory_type="verified_resolution", context="past incident", occurred_start=None, mentioned_at=None, tags=("verified-resolution",)),),
        )
        self.hindsight_service.retain_verified_resolution.return_value = RetainResult(
            status="success", bank_id=DEFAULT_HINDSIGHT_BANK_ID, memory_type="verified_resolution", recorded_at="2026-01-01T00:00:00Z", document_id="doc-1"
        )
        self.hindsight_service.retain_failed_approach.return_value = RetainResult(
            status="success", bank_id=DEFAULT_HINDSIGHT_BANK_ID, memory_type="failure", recorded_at="2026-01-01T00:00:00Z", document_id="doc-2"
        )

        app.state.hindsight_service = self.hindsight_service
        app.state.ai_service = FakeAI()
        self.incident_id = self._create_incident()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        os.environ.clear()
        os.environ.update(self.original_env)

    def _create_incident(self):
        response = self.client.post("/api/incidents", json={
            "title":"Payment API 503", "description":"Started after deployment.",
            "service_name":"payment-api", "environment":"production", "severity":"high",
            "error_messages":["HTTP 503"], "deployment":{"deployment_id":"DEP-921"},
            "system_metrics":{"db_utilization":98},
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["data"]["incident_id"]

    def test_incident_create_detail_list_and_pagination(self):
        second = self.client.post("/api/incidents", json={
            "title":"Worker warning", "description":"Queue delay.", "service_name":"worker",
            "environment":"staging", "severity":"low",
        })
        self.assertEqual(second.status_code, 201)
        page = self.client.get("/api/incidents?page=1&limit=1")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json()["data"]["total"], 2)
        self.assertEqual(len(page.json()["data"]["items"]), 1)
        detail = self.client.get(f"/api/incidents/{self.incident_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["service_name"], "payment-api")
        self.assertEqual(len(detail.json()["data"]["logs"]), 2)
        self.assertEqual(self.client.get("/api/incidents/00000000-0000-0000-0000-000000000001").status_code, 404)

    def test_memory_off_does_not_recall_and_investigation_can_be_retrieved(self):
        response = self.client.post(f"/api/incidents/{self.incident_id}/investigate", json={"memory_mode":"MEMORY_OFF"})
        self.assertEqual(response.status_code, 201, response.text)
        self.hindsight_service.recall_incident_memories.assert_not_called()
        run_id = response.json()["data"]["investigation_id"]
        result = self.client.get(f"/api/investigations/{run_id}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["data"]["execution_status"], "succeeded")
        self.assertEqual(result.json()["data"]["findings"][0]["provenance"], "ai_hypothesis")
        self.assertEqual(len(result.json()["data"]["hypotheses"]), 1)
        self.assertEqual(len(result.json()["data"]["recommendations"]), 1)
        self.assertTrue(result.json()["data"]["findings"][1]["requires_engineer_review"])

    def test_memory_on_calls_recall_and_preserves_historical_provenance(self):
        response = self.client.post(f"/api/incidents/{self.incident_id}/investigate", json={"memory_mode":"MEMORY_ON"})
        self.assertEqual(response.status_code, 201, response.text)
        self.hindsight_service.recall_incident_memories.assert_called_once()
        self.assertEqual(response.json()["data"]["analysis"]["historical_memories"][0]["provenance"], "historical_hindsight_memory")

    def test_feedback_resolution_verification_and_failed_approach(self):
        result = self.client.post(f"/api/incidents/{self.incident_id}/investigate", json={"memory_mode":"off"}).json()["data"]
        recommendation_id = result["recommendations"][0]["id"]
        feedback = self.client.post(f"/api/investigations/{result['investigation_id']}/feedback", json={
            "recommendation_id":recommendation_id,
            "feedback_type":"accepted", "created_by":"engineer",
        })
        self.assertEqual(feedback.status_code, 201, feedback.text)
        unverified = self.client.post(f"/api/incidents/{self.incident_id}/resolve", json={
            "root_cause_summary":"Hypothesis", "resolution_summary":"Try restart", "verified_by":"engineer", "confirmed":False,
        })
        self.assertEqual(unverified.status_code, 409)
        self.hindsight_service.retain_verified_resolution.assert_not_called()
        resolved = self.client.post(f"/api/incidents/{self.incident_id}/resolve", json={
            "root_cause_summary":"Confirmed pool saturation", "resolution_summary":"Adjusted pool limits", "verified_by":"engineer", "confirmed":True,
        })
        self.assertEqual(resolved.status_code, 201)
        self.hindsight_service.retain_verified_resolution.assert_called_once()
        failed = self.client.post(f"/api/incidents/{self.incident_id}/failed-approaches", json={
            "attempted_action":"Raised retry count", "outcome":"Increased load", "recorded_by":"engineer",
        })
        self.assertEqual(failed.status_code, 201)
        self.hindsight_service.retain_failed_approach.assert_called_once()

    def test_memory_endpoint_and_dashboard_statistics(self):
        memories = self.client.get(f"/api/incidents/{self.incident_id}/memories")
        self.assertEqual(memories.status_code, 200)
        entry = memories.json()["data"]["entries"][0]
        self.assertEqual(entry["provenance"], "historical_hindsight_memory")
        summary = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["data"]["total_incidents"], 1)
        self.assertEqual(summary.json()["data"]["severity_distribution"]["high"], 1)

        activity = self.client.get("/api/memory/activity?limit=8")
        self.assertEqual(activity.status_code, 200)
        self.assertTrue(activity.json()["data"]["items"])
        self.assertEqual(activity.json()["data"]["items"][0]["operation"], "recall")

    def test_memory_endpoint_returns_real_empty_recall_as_empty_state(self):
        self.hindsight.recall_incident_memories.return_value = RecallResult(
            status="success", bank_id=DEFAULT_HINDSIGHT_BANK_ID,
            recalled_at="2026-01-01T00:00:00Z", memories=(),
        )

        response = self.client.get(f"/api/incidents/{self.incident_id}/memories")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["entries"], [])

    def test_memory_endpoint_reports_safe_provider_failure_category(self):
        self.hindsight.recall_incident_memories.return_value = RecallResult(
            status="failed", bank_id=DEFAULT_HINDSIGHT_BANK_ID,
            recalled_at="2026-01-01T00:00:00Z", error_category="authentication_error",
        )

        response = self.client.get(f"/api/incidents/{self.incident_id}/memories")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["error_category"], "authentication_error")
        self.assertIn("authentication failed", response.json()["detail"]["message"])

    def test_frontend_origin_is_allowed_by_cors(self):
        response = self.client.options(
            "/api/dashboard/summary",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:5173")

    def test_external_failure_and_missing_investigation_are_safe(self):
        self.hindsight_service.recall_incident_memories.return_value = RecallResult(
            status="failed", bank_id=DEFAULT_HINDSIGHT_BANK_ID, recalled_at="2026-01-01T00:00:00Z", error_category="upstream_timeout"
        )
        failed = self.client.post(f"/api/incidents/{self.incident_id}/investigate", json={"memory_mode":"on"})
        self.assertEqual(failed.status_code, 503)
        self.assertNotIn("upstream_timeout", failed.text)
        missing = self.client.get("/api/investigations/00000000-0000-0000-0000-000000000001")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.client.get("/api/incidents/00000000-0000-0000-0000-000000000001/memories").status_code, 404)

    def test_groq_and_hindsight_unavailable_return_safe_errors(self):
        app.state.ai_service = None
        groq = self.client.post(f"/api/incidents/{self.incident_id}/investigate", json={"memory_mode":"off"})
        self.assertEqual(groq.status_code, 503)
        self.assertNotIn("api_key", groq.text.lower())
        app.state.hindsight_service = None
        memory = self.client.get(f"/api/incidents/{self.incident_id}/memories")
        self.assertEqual(memory.status_code, 503)
        self.assertNotIn("stack", memory.text.lower())

    def test_postmortem_endpoints_and_lifecycle(self):
        # 1. Unverified incident rejects postmortem generation
        unverified_resp = self.client.post(f"/api/incidents/{self.incident_id}/postmortem")
        self.assertEqual(unverified_resp.status_code, 400)
        self.assertEqual(unverified_resp.json()["detail"]["code"], "RESOLUTION_REQUIRED")

        # 2. Verify resolution
        resolve_resp = self.client.post(
            f"/api/incidents/{self.incident_id}/resolve",
            json={
                "root_cause_summary": "Pool connection leak.",
                "resolution_summary": "Applied patch to connection pool.",
                "verified_by": "Senior SRE",
                "confirmed": True,
            },
        )
        self.assertEqual(resolve_resp.status_code, 201)

        # 3. Generate postmortem
        gen_resp = self.client.post(f"/api/incidents/{self.incident_id}/postmortem")
        self.assertEqual(gen_resp.status_code, 200)
        data = gen_resp.json()["data"]
        pm_id = data["postmortem_id"]
        self.assertTrue(pm_id)
        self.assertIn("Pool connection leak.", data["body_markdown"])
        self.assertIn("Senior SRE", data["body_markdown"])

        # 4. List postmortems
        list_resp = self.client.get("/api/postmortems")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()["data"]["items"]
        self.assertTrue(any(item["id"] == pm_id for item in items))

        # 5. Get postmortem detail
        detail_resp = self.client.get(f"/api/postmortems/{pm_id}")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()["data"]["id"], pm_id)

        # 6. Download postmortem
        dl_resp = self.client.get(f"/api/postmortems/{pm_id}/download")
        self.assertEqual(dl_resp.status_code, 200)
        self.assertIn("text/markdown", dl_resp.headers["content-type"])
        self.assertIn("attachment", dl_resp.headers["content-disposition"])
        self.assertIn("# Incident Postmortem", dl_resp.text)

        # 7. Non-existent postmortem returns 404
        missing_resp = self.client.get("/api/postmortems/00000000-0000-0000-0000-000000000001")
        self.assertEqual(missing_resp.status_code, 404)



if __name__ == "__main__":
    unittest.main()
