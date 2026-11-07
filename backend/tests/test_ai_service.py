"""Mocked Groq service tests; no test makes a Groq API request."""

from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.config import DEFAULT_GROQ_MODEL, Settings
from app.schemas.ai import IncidentContext
from app.services.ai_service import AIServiceError, GroqAIService
from app.services.hindsight_service import HistoricalMemory


def _completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _model_result(**overrides: object) -> str:
    data: dict[str, object] = {
        "summary": "A latency increase coincides with a recent deployment.",
        "potential_root_causes": [
            {
                "cause": "The deployment may have increased database pool usage.",
                "confidence": 0.62,
                "rationale": "The current log reports pool timeouts after deployment.",
                "supporting_evidence": [
                    {
                        "reference": "current:log:0",
                        "relevance": "The log is contemporaneous with the symptoms.",
                    }
                ],
            }
        ],
        "historical_similarities": [
            {
                "memory_reference": "historical:0",
                "similarity_summary": "A prior incident had related symptoms.",
                "relevance": "This is context only and does not prove the cause.",
            }
        ],
        "recommended_steps": [
            {
                "step": "Compare pool usage before and after the deployment.",
                "rationale": "This can test whether the change correlates with current symptoms.",
                "supporting_evidence": [
                    {
                        "reference": "current:log:0",
                        "relevance": "The timeout is the observed symptom.",
                    }
                ],
            }
        ],
        "confidence": {
            "score": 0.55,
            "limitations": ["Metrics from before the deployment are not supplied."],
        },
        "information_still_required": ["Database pool utilization over time."],
    }
    data.update(overrides)
    return json.dumps(data)


class GroqAIServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Mock()
        self.client.models.list.return_value = SimpleNamespace(
            data=[SimpleNamespace(id=DEFAULT_GROQ_MODEL)]
        )
        self.service = GroqAIService(self.client)
        self.context = IncidentContext(
            incident_id="INC-42",
            incident_description="Payment API latency increased after deployment.",
            logs=["pool timeout observed"],
            historical_memories=[
                HistoricalMemory(
                    id="memory-42",
                    text="Prior pool issue after a release.",
                    memory_type="fact",
                    context="Engineer-verified resolution",
                    occurred_start=None,
                    mentioned_at=None,
                    tags=("verified-resolution",),
                )
            ],
            engineer_verified_findings=[
                {
                    "finding_id": "finding-1",
                    "statement": "The previous incident was caused by worker saturation.",
                    "verified_by": "on-call engineer",
                }
            ],
        )

    def test_provider_availability_uses_model_list_without_inference(self) -> None:
        result = self.service.check_availability()

        self.assertTrue(result.configured)
        self.assertTrue(result.reachable)
        self.assertEqual(result.status, "reachable")
        self.client.models.list.assert_called_once_with()
        self.client.chat.completions.create.assert_not_called()

    def test_unconfigured_groq_is_reported_without_provider_call(self) -> None:
        result = GroqAIService(None).check_availability()

        self.assertFalse(result.configured)
        self.assertFalse(result.reachable)
        self.assertEqual(result.status, "not_configured")

    def test_groq_authentication_failure_is_safely_classified(self) -> None:
        error = RuntimeError("private response with credential")
        error.status_code = 401
        self.client.models.list.side_effect = error

        result = self.service.check_availability()

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error_category, "authentication_error")
        self.assertNotIn("private response", repr(result))

    def test_groq_provider_failures_distinguish_network_rate_limit_and_timeout(self) -> None:
        from app.services.ai_service import _classify_provider_error

        rate_error = RuntimeError("limited")
        rate_error.status_code = 429
        auth_error = RuntimeError("unauthorized")
        auth_error.status_code = 403
        network_error = ConnectionError("private network detail")
        timeout_error = TimeoutError("private timeout detail")

        self.assertEqual(_classify_provider_error(auth_error), "authentication_error")
        self.assertEqual(_classify_provider_error(rate_error), "rate_limited")
        self.assertEqual(_classify_provider_error(network_error), "network_error")
        self.assertEqual(_classify_provider_error(timeout_error), "timeout")

    def test_valid_structured_analysis_keeps_provenance_separate(self) -> None:
        payload = json.loads(_model_result())
        payload["potential_root_causes"][0]["supporting_evidence"].extend(
            [
                {
                    "reference": "historical:0",
                    "relevance": "This prior memory has related symptoms only.",
                },
                {
                    "reference": "verified:0",
                    "relevance": "An engineer verified this fact for its original incident.",
                },
            ]
        )
        self.client.chat.completions.create.return_value = _completion(
            json.dumps(payload)
        )

        result = self.service.analyze_incident(self.context)

        self.assertEqual(result.summary, "A latency increase coincides with a recent deployment.")
        self.assertEqual(result.current_evidence[0].provenance, "current_incident_evidence")
        self.assertEqual(result.historical_memories[0].provenance, "historical_hindsight_memory")
        self.assertEqual(
            result.engineer_verified_findings[0].provenance,
            "engineer_verified_root_cause",
        )
        self.assertEqual(
            result.potential_root_causes[0].provenance,
            "ai_generated_hypothesis",
        )
        self.assertEqual(
            result.potential_root_causes[0].supporting_evidence[0].provenance,
            "current_incident_evidence",
        )
        self.assertEqual(
            {item.provenance for item in result.potential_root_causes[0].supporting_evidence},
            {
                "current_incident_evidence",
                "historical_hindsight_memory",
                "engineer_verified_root_cause",
            },
        )
        self.assertEqual(
            result.recommended_steps[0].supporting_evidence[0].provenance,
            "current_incident_evidence",
        )
        self.assertTrue(result.recommended_steps[0].requires_engineer_review)
        self.assertEqual(result.historical_similarities[0].memory_reference, "memory-42")
        self.assertEqual(result.model_identifier, DEFAULT_GROQ_MODEL)

        kwargs = self.client.chat.completions.create.call_args.kwargs
        self.client.models.list.assert_called_once_with()
        self.assertEqual(kwargs["model"], DEFAULT_GROQ_MODEL)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertNotIn("tools", kwargs)

    def test_configured_model_must_be_in_the_account_model_list(self) -> None:
        self.client.models.list.return_value = SimpleNamespace(
            data=[SimpleNamespace(id="openai/gpt-oss-20b")]
        )
        service = GroqAIService(self.client, model="private/unavailable-model")

        with self.assertRaises(AIServiceError) as caught:
            service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "model_unavailable")
        self.client.chat.completions.create.assert_not_called()

    def test_empty_historical_context_cannot_gain_fabricated_memories(self) -> None:
        self.client.chat.completions.create.return_value = _completion(
            _model_result(historical_similarities=[])
        )
        context = self.context.model_copy(update={"historical_memories": []})

        result = self.service.analyze_incident(context)

        self.assertEqual(result.historical_memories, [])
        self.assertEqual(result.historical_similarities, [])

    def test_malformed_response_fails_without_fabricated_fallback(self) -> None:
        self.client.chat.completions.create.return_value = _completion("not json")

        with self.assertRaises(AIServiceError) as caught:
            self.service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "malformed_response")

    def test_unknown_evidence_reference_is_rejected(self) -> None:
        altered = _model_result().replace("current:log:0", "current:invented")
        self.client.chat.completions.create.return_value = _completion(altered)

        with self.assertRaises(AIServiceError) as caught:
            self.service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "malformed_response")

    def test_historical_similarity_must_reference_supplied_memory(self) -> None:
        altered = _model_result().replace("historical:0", "historical:invented")
        self.client.chat.completions.create.return_value = _completion(altered)

        with self.assertRaises(AIServiceError) as caught:
            self.service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "malformed_response")

    def test_missing_api_key_is_graceful_until_analysis_is_requested(self) -> None:
        service = GroqAIService.from_settings(Settings(groq_api_key=None), Mock())

        with self.assertRaises(AIServiceError) as caught:
            service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "not_configured")

    def test_groq_model_is_configurable_and_defaults_when_unset(self) -> None:
        with patch.dict(os.environ, {"GROQ_MODEL": "openai/gpt-oss-120b"}):
            configured = Settings.load()
        self.assertEqual(configured.groq_model, "openai/gpt-oss-120b")

        with patch.dict(os.environ, {"GROQ_MODEL": ""}):
            defaulted = Settings.load()
        self.assertEqual(defaulted.groq_model, DEFAULT_GROQ_MODEL)

    def test_rate_limit_and_timeout_have_safe_categories(self) -> None:
        class RateLimitError(Exception):
            pass

        for error, category in (
            (RateLimitError("private response body"), "rate_limited"),
            (TimeoutError("private timeout detail"), "timeout"),
        ):
            with self.subTest(category=category):
                self.client.chat.completions.create.side_effect = error
                with self.assertRaises(AIServiceError) as caught:
                    self.service.analyze_incident(self.context)
                self.assertEqual(caught.exception.category, category)
                self.assertNotIn("private", str(caught.exception))

    def test_provider_api_error_does_not_leak_exception_details(self) -> None:
        self.client.chat.completions.create.side_effect = RuntimeError(
            "private body Authorization: Bearer do-not-log"
        )

        with self.assertRaises(AIServiceError) as caught:
            self.service.analyze_incident(self.context)

        self.assertEqual(caught.exception.category, "api_error")
        self.assertNotIn("do-not-log", str(caught.exception))

    def test_credentials_are_redacted_from_prompt_and_generated_text(self) -> None:
        self.context.logs = ["Authorization: Bearer super-secret-token"]
        response = _model_result().replace(
            "A latency increase coincides with a recent deployment.",
            "A request included api_key=another-secret-value.",
        )
        self.client.chat.completions.create.return_value = _completion(response)

        result = self.service.analyze_incident(self.context)

        prompt = self.client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertNotIn("super-secret-token", prompt)
        self.assertNotIn("another-secret-value", result.summary)
        self.assertIn("[REDACTED]", result.summary)


if __name__ == "__main__":
    unittest.main()
