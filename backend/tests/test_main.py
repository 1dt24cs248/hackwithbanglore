"""Basic HTTP endpoint checks using only Python's standard library."""

import asyncio
import json
import os
import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from app.config import BACKEND_DIR, DEFAULT_HINDSIGHT_BANK_ID, ENV_FILE, Settings
from app.main import app


async def request_json(path: str) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    raw_path = path.encode("ascii")

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": raw_path,
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async with app.router.lifespan_context(app):
        await app(scope, receive, send)

    response_start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = next(message for message in messages if message["type"] == "http.response.body")
    return response_start["status"], json.loads(response_body["body"])


class BackendEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_environment = os.environ.copy()
        os.environ["HINDSIGHT_API_KEY"] = ""
        os.environ["GROQ_API_KEY"] = ""
        os.environ["DATABASE_URL"] = ""

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_environment)

    def test_homepage_response(self) -> None:
        status, body = asyncio.run(request_json("/"))

        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {
                "message": "Welcome to IncidentIQ",
                "status": "running",
                "project": "IncidentIQ",
            },
        )

    def test_health_response(self) -> None:
        os.environ["HINDSIGHT_API_KEY"] = "test-hindsight-secret"
        os.environ["HINDSIGHT_BANK_ID"] = "incidentiq-hackathon-demo"
        hindsight_client = patch("app.main.Hindsight").start()
        hindsight_client.return_value.arecall = AsyncMock()
        self.addCleanup(patch.stopall)

        status, body = asyncio.run(request_json("/health"))

        self.assertEqual(status, 200)
        dependencies = body["data"]["dependencies"]
        self.assertEqual(dependencies["hindsight"]["status"], "reachable")
        self.assertTrue(dependencies["hindsight"]["configured"])
        self.assertEqual(dependencies["hindsight"]["bank_id"], "incidentiq-hackathon-demo")
        self.assertEqual(dependencies["groq"]["status"], "not_configured")
        self.assertEqual(dependencies["database"]["status"], "not_configured")
        hindsight_client.return_value.arecall.assert_awaited_once()

    def test_health_provider_authentication_failure_is_safe(self) -> None:
        os.environ["HINDSIGHT_API_KEY"] = "secret-hindsight-key"
        os.environ["GROQ_API_KEY"] = "secret-groq-key"
        hindsight_client = patch("app.main.Hindsight").start()
        hindsight_client.return_value.arecall = AsyncMock()
        groq_client = patch("app.main.create_groq_client").start()
        self.addCleanup(patch.stopall)
        error = RuntimeError("private auth response and credentials")
        error.status_code = 401
        hindsight_client.return_value.arecall.side_effect = error
        groq_client.return_value.models.list.side_effect = error

        status, body = asyncio.run(request_json("/health"))

        payload = json.dumps(body)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["dependencies"]["hindsight"]["status"], "unavailable")
        self.assertEqual(body["data"]["dependencies"]["hindsight"]["error_category"], "authentication_error")
        self.assertEqual(body["data"]["dependencies"]["groq"]["status"], "unavailable")
        self.assertEqual(body["data"]["dependencies"]["groq"]["error_category"], "authentication_error")
        self.assertNotIn("private auth response", payload)
        self.assertNotIn("secret-hindsight-key", payload)
        self.assertNotIn("secret-groq-key", payload)

    def test_optional_configuration_may_be_missing(self) -> None:
        os.environ["GROQ_API_KEY"] = ""
        os.environ["DATABASE_URL"] = ""

        status, body = asyncio.run(request_json("/health"))

        self.assertEqual(status, 200)
        dependencies = body["data"]["dependencies"]
        self.assertEqual(dependencies["groq"]["status"], "not_configured")
        self.assertEqual(dependencies["database"]["status"], "not_configured")
        self.assertFalse(dependencies["hindsight"]["configured"])

    def test_database_health_reports_connected_and_unavailable(self) -> None:
        os.environ["DATABASE_URL"] = "sqlite://"
        status, body = asyncio.run(request_json("/health"))
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["dependencies"]["database"]["status"], "connected")

        with patch("app.main.check_database", return_value=False), patch("app.main.Hindsight"), patch("app.main.create_groq_client"):
            status, body = asyncio.run(request_json("/health"))
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["dependencies"]["database"]["status"], "unavailable")

    def test_settings_loads_the_backend_environment_file(self) -> None:
        self.assertEqual(ENV_FILE, (BACKEND_DIR / ".env").resolve())
        self.assertEqual(BACKEND_DIR.name, "backend")

    def test_hindsight_bank_id_is_configurable_with_demo_default(self) -> None:
        os.environ["HINDSIGHT_BANK_ID"] = "incidentiq-isolated-demo"
        self.assertEqual(Settings.load().hindsight_bank_id, "incidentiq-isolated-demo")
        os.environ["HINDSIGHT_BANK_ID"] = ""
        self.assertEqual(Settings.load().hindsight_bank_id, DEFAULT_HINDSIGHT_BANK_ID)
        self.assertEqual(DEFAULT_HINDSIGHT_BANK_ID, "incidentiq-hackathon-demo")

    def test_health_response_never_contains_secret_values(self) -> None:
        secret_values = (
            "hindsight-test-secret-do-not-return",
            "groq-test-secret-do-not-return",
            "postgresql://private-user:private-password@db.invalid/app",
        )
        os.environ["HINDSIGHT_API_KEY"] = secret_values[0]
        os.environ["GROQ_API_KEY"] = secret_values[1]
        os.environ["DATABASE_URL"] = secret_values[2]

        with patch("app.main.check_database", return_value=False), patch("app.main.Hindsight"), patch("app.main.create_groq_client"):
            status, body = asyncio.run(request_json("/health"))
        response_text = json.dumps(body)

        self.assertEqual(status, 200)
        for secret in secret_values:
            self.assertNotIn(secret, response_text)


if __name__ == "__main__":
    unittest.main()
