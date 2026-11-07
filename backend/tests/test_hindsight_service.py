"""Mocked Hindsight service tests; no test contacts the Hindsight API."""

import asyncio
import queue
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from hindsight_client_api.models.recall_response import RecallResponse
from hindsight_client_api.models.recall_result import RecallResult
from hindsight_client_api.models.retain_response import RetainResponse

from app.config import DEFAULT_HINDSIGHT_BANK_ID
from app.services.hindsight_service import (
    HindsightMemoryService,
)

class HindsightMemoryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = AsyncMock()
        self.bank_id = DEFAULT_HINDSIGHT_BANK_ID
        self.service = HindsightMemoryService(self.client, self.bank_id)

    async def test_successful_recall_preserves_historical_provenance(self) -> None:
        self.client.arecall.return_value = RecallResponse(
            results=[
                RecallResult(
                    id="memory-1",
                    text="A previous incident recovered after reducing worker concurrency.",
                    type="fact",
                    context="Engineer-verified IncidentIQ resolution",
                    occurred_start="2026-10-20T10:00:00Z",
                    mentioned_at="2026-10-20T11:00:00Z",
                    tags=["verified-resolution"],
                )
            ]
        )

        result = await self.service.recall_incident_memories(
            "Payment API latency after deployment",
            "Database connection usage high",
        )

        self.client.arecall.assert_called_once_with(
            bank_id=self.bank_id,
            query=(
                "Payment API latency after deployment\n"
                "Technical context: Database connection usage high"
            ),
            budget="low",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.memories), 1)
        self.assertEqual(result.memories[0].id, "memory-1")
        self.assertEqual(result.memories[0].provenance, "historical_hindsight_memory")
        self.assertEqual(result.memories[0].tags, ("verified-resolution",))

    async def test_empty_recall_is_success_with_no_fabricated_memories(self) -> None:
        self.client.arecall.return_value = RecallResponse(results=[])

        result = await self.service.recall_incident_memories("No matching memory expected")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.memories, ())

    async def test_unavailable_client_is_reported_without_fallback(self) -> None:
        service = HindsightMemoryService(None, self.bank_id)

        availability = await service.check_availability()
        recall = await service.recall_incident_memories("Current incident")

        self.assertFalse(availability.available)
        self.assertEqual(availability.error_category, "client_unavailable")
        self.assertEqual(availability.status, "not_configured")
        self.assertEqual(recall.status, "failed")
        self.assertEqual(recall.error_category, "client_unavailable")

    async def test_availability_check_uses_real_read_only_recall(self) -> None:
        self.client.arecall.return_value = RecallResponse(results=[])

        result = await self.service.check_availability()

        self.client.arecall.assert_called_once_with(
            bank_id=self.bank_id,
            query="IncidentIQ Hindsight service availability check",
            budget="low",
        )
        self.assertTrue(result.available)

    async def test_hindsight_authentication_failure_has_safe_category(self) -> None:
        error = RuntimeError("secret provider response")
        error.status_code = 401
        self.client.arecall.side_effect = error

        result = await self.service.check_availability()

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.error_category, "authentication_error")
        self.assertNotIn("secret provider response", repr(result))

    async def test_successful_retention_uses_category_tags_timestamp_and_stable_document(self) -> None:
        self.client.aretain.return_value = RetainResponse(
            success=True,
            bank_id=self.bank_id,
            items_count=1,
            var_async=False,
        )
        occurred_at = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

        result = await self.service.retain_incident_experience(
            "Payment API returned HTTP 503",
            technical_context="Database pool saturated",
            incident_id="INC-20261105-0001",
            occurred_at=occurred_at,
        )

        self.assertEqual(result.status, "success")
        kwargs = self.client.aretain.call_args.kwargs
        self.assertEqual(kwargs["bank_id"], self.bank_id)
        self.assertIn("Incident: INC-20261105-0001", kwargs["content"])
        self.assertIn("root cause not asserted", kwargs["content"])
        self.assertEqual(kwargs["tags"], ["incident", "incident-observation"])
        self.assertEqual(kwargs["timestamp"], "2026-11-05T12:00:00+00:00")
        self.assertEqual(kwargs["update_mode"], "replace")

    async def test_successful_verified_resolution_is_tagged_and_recorded(self) -> None:
        self.client.aretain.return_value = RetainResponse(
            success=True,
            bank_id=self.bank_id,
            items_count=1,
            var_async=False,
        )

        result = await self.service.retain_verified_resolution(
            root_cause="Worker concurrency exhausted the database pool",
            resolution="Reduced concurrency from 24 to 8",
            verified_by="on-call engineer",
            verified=True,
            incident_id="INC-17",
        )

        self.assertEqual(result.status, "success")
        kwargs = self.client.aretain.call_args.kwargs
        self.assertIn("Engineer-verified resolution", kwargs["content"])
        self.assertEqual(kwargs["tags"], ["incident", "verified-resolution"])

    async def test_unverified_resolution_is_never_sent_to_hindsight(self) -> None:
        result = await self.service.retain_verified_resolution(
            root_cause="Likely connection pool exhaustion",
            resolution="Restarted workers",
            verified_by="",
            verified=False,
            incident_id="INC-18",
        )

        self.client.aretain.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_category, "unverified_resolution")

    async def test_failed_retention_returns_safe_error_category(self) -> None:
        self.client.aretain.side_effect = RuntimeError("private SDK detail and token")

        with self.assertLogs("app.services.hindsight_service", level="WARNING") as captured:
            result = await self.service.retain_failed_approach(
                attempted_action="Restart workers",
                outcome="Latency returned immediately",
                incident_id="INC-19",
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_category, "sdk_error")
        self.assertNotIn("private SDK detail", repr(result))
        self.assertNotIn("private SDK detail", " ".join(captured.output))
        record = captured.records[0]
        self.assertEqual(record.operation_type, "retain")
        self.assertEqual(record.bank_id, self.bank_id)
        self.assertEqual(record.status, "failed")
        self.assertEqual(record.error_category, "sdk_error")
        self.assertTrue(record.timestamp)

    async def test_retry_uses_idempotent_document_and_skips_duplicate_call(self) -> None:
        self.client.aretain.return_value = RetainResponse(
            success=True,
            bank_id=self.bank_id,
            items_count=1,
            var_async=False,
        )
        kwargs = {
            "incident_description": "Queue backlog after deploy",
            "technical_context": "Payment workers",
            "incident_id": "INC-20",
        }

        first = await self.service.retain_incident_experience(**kwargs)
        second = await self.service.retain_incident_experience(**kwargs)

        self.client.aretain.assert_called_once()
        self.assertEqual(first.document_id, second.document_id)
        self.assertEqual(second.status, "skipped_duplicate")

    async def test_concurrent_duplicate_retention_does_not_block_event_loop(self) -> None:
        completed = threading.Event()
        result_queue: queue.Queue[object] = queue.Queue()

        async def exercise_concurrent_retention() -> tuple[
            str, str, str | None, str | None, int, str
        ]:
            client = AsyncMock()
            first_call_started = asyncio.Event()
            allow_first_call_to_finish = asyncio.Event()

            async def slow_aretain(**_kwargs: object) -> RetainResponse:
                first_call_started.set()
                await allow_first_call_to_finish.wait()
                return RetainResponse(
                    success=True,
                    bank_id=self.bank_id,
                    items_count=1,
                    var_async=False,
                )

            client.aretain.side_effect = slow_aretain
            service = HindsightMemoryService(client, self.bank_id)
            retention = {
                "incident_description": "Queue backlog after deploy",
                "technical_context": "Payment workers",
                "incident_id": "INC-CONCURRENT-1",
            }
            first_task = asyncio.create_task(
                service.retain_incident_experience(**retention)
            )
            await first_call_started.wait()
            second_task = asyncio.create_task(
                service.retain_incident_experience(**retention)
            )

            event_loop_responsive = asyncio.Event()

            async def mark_event_loop_responsive() -> None:
                await asyncio.sleep(0)
                event_loop_responsive.set()

            asyncio.create_task(mark_event_loop_responsive())
            try:
                await asyncio.wait_for(event_loop_responsive.wait(), timeout=0.5)
            finally:
                allow_first_call_to_finish.set()

            first, second = await asyncio.gather(first_task, second_task)
            retained_kwargs = client.aretain.call_args.kwargs
            return (
                first.status,
                second.status,
                first.document_id,
                second.document_id,
                client.aretain.await_count,
                retained_kwargs["update_mode"],
            )

        def run_in_isolated_loop() -> None:
            try:
                result_queue.put(asyncio.run(exercise_concurrent_retention()))
            except BaseException as error:
                result_queue.put(error)
            finally:
                completed.set()

        # Isolate the watchdog from a regression that blocks its own event loop.
        worker = threading.Thread(target=run_in_isolated_loop, daemon=True)
        worker.start()
        finished = await asyncio.to_thread(completed.wait, 1.5)
        self.assertTrue(finished, "concurrent retention blocked its event loop")

        result = result_queue.get_nowait()
        if isinstance(result, BaseException):
            raise result
        first_status, second_status, first_id, second_id, call_count, update_mode = result
        self.assertEqual((first_status, second_status), ("success", "skipped_duplicate"))
        self.assertEqual(first_id, second_id)
        self.assertEqual(call_count, 1)
        self.assertEqual(update_mode, "replace")

    async def test_incident_memory_redacts_credential_shaped_text(self) -> None:
        self.client.aretain.return_value = RetainResponse(
            success=True,
            bank_id=self.bank_id,
            items_count=1,
            var_async=False,
        )

        await self.service.retain_incident_experience(
            "Request failed with api_key=super-secret-value and "
            "Authorization: Bearer abc.def"
        )

        retained_content = self.client.aretain.call_args.kwargs["content"]
        self.assertNotIn("super-secret-value", retained_content)
        self.assertNotIn("abc.def", retained_content)

    async def test_safe_error_category_handles_api_exception_status(self) -> None:
        from hindsight_client_api.exceptions import ApiException
        from app.services.hindsight_service import _safe_error_category

        self.assertEqual(_safe_error_category(ApiException(status=401)), "authentication_error")
        self.assertEqual(_safe_error_category(ApiException(status=403)), "authentication_error")
        self.assertEqual(_safe_error_category(ApiException(status=429)), "rate_limited")
        self.assertEqual(_safe_error_category(ApiException(status=500)), "provider_error")
        self.assertEqual(_safe_error_category(ApiException(status=503)), "provider_error")
        self.assertEqual(_safe_error_category(ApiException(status=404)), "provider_error")


if __name__ == "__main__":
    unittest.main()
