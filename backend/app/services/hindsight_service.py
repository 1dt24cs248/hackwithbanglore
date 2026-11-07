"""Safe, reusable operations for IncidentIQ's Hindsight memory bank."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from hindsight_client import Hindsight

logger = logging.getLogger(__name__)
MEMORY_PROVENANCE = "historical_hindsight_memory"

OperationStatus = Literal["success", "failed", "skipped_duplicate"]


@dataclass(frozen=True)
class HistoricalMemory:
    """A Hindsight result kept distinct from current incident evidence."""

    id: str
    text: str
    memory_type: str | None
    context: str | None
    occurred_start: str | None
    mentioned_at: str | None
    tags: tuple[str, ...]
    provenance: Literal["historical_hindsight_memory"] = MEMORY_PROVENANCE


@dataclass(frozen=True)
class RecallResult:
    status: OperationStatus
    bank_id: str
    recalled_at: str
    memories: tuple[HistoricalMemory, ...] = ()
    error_category: str | None = None


@dataclass(frozen=True)
class RetainResult:
    status: OperationStatus
    bank_id: str
    memory_type: str
    recorded_at: str
    document_id: str | None = None
    error_category: str | None = None


@dataclass(frozen=True)
class AvailabilityResult:
    available: bool
    configured: bool
    status: Literal["not_configured", "reachable", "unavailable"]
    bank_id: str
    checked_at: str
    error_category: str | None = None


class HindsightMemoryService:
    """Uses the lifespan-managed SDK client; this class never creates clients."""

    def __init__(self, client: Hindsight | None, bank_id: str) -> None:
        self._client = client
        self._bank_id = bank_id
        self._completed_documents: set[str] = set()
        self._retain_lock = asyncio.Lock()

    @property
    def bank_id(self) -> str:
        """Configured bank identifier; safe to expose, unlike credentials."""
        return self._bank_id

    async def check_availability(self) -> AvailabilityResult:
        """Perform a real, read-only recall to check bank/API availability."""
        checked_at = _now()
        if self._client is None:
            self._audit("availability_check", "failed", checked_at, "client_unavailable")
            return AvailabilityResult(
                False, False, "not_configured", self._bank_id, checked_at,
                "client_unavailable",
            )

        try:
            # An empty result is still a successful availability check.
            await self._client.arecall(
                bank_id=self._bank_id,
                query="IncidentIQ Hindsight service availability check",
                budget="low",
            )
        except Exception as error:
            category = _safe_error_category(error)
            self._audit("availability_check", "failed", checked_at, category)
            return AvailabilityResult(
                False, True, "unavailable", self._bank_id, checked_at, category
            )

        self._audit("availability_check", "success", checked_at)
        return AvailabilityResult(True, True, "reachable", self._bank_id, checked_at)

    async def recall_incident_memories(
        self,
        incident_description: str,
        technical_context: str | None = None,
    ) -> RecallResult:
        """Recall historical memories relevant to an incident description."""
        recalled_at = _now()
        query_parts = [_clean_text(incident_description)]
        if technical_context and technical_context.strip():
            query_parts.append(_clean_text(technical_context))
        query = "\nTechnical context: ".join(part for part in query_parts if part)

        if not query:
            self._audit("recall", "failed", recalled_at, "invalid_input")
            return RecallResult(
                "failed", self._bank_id, recalled_at, error_category="invalid_input"
            )
        if self._client is None:
            self._audit("recall", "failed", recalled_at, "client_unavailable")
            return RecallResult(
                "failed", self._bank_id, recalled_at, error_category="client_unavailable"
            )

        try:
            response = await self._client.arecall(
                bank_id=self._bank_id,
                query=query,
                budget="low",
            )
            memories = tuple(
                HistoricalMemory(
                    id=result.id,
                    text=result.text,
                    memory_type=result.type,
                    context=result.context,
                    occurred_start=result.occurred_start,
                    mentioned_at=result.mentioned_at,
                    tags=tuple(result.tags or ()),
                )
                for result in response.results
            )
        except Exception as error:
            category = _safe_error_category(error)
            self._audit("recall", "failed", recalled_at, category)
            return RecallResult(
                "failed", self._bank_id, recalled_at, error_category=category
            )

        self._audit("recall", "success", recalled_at)
        return RecallResult("success", self._bank_id, recalled_at, memories=memories)

    async def retain_incident_experience(
        self,
        incident_description: str,
        technical_context: str | None = None,
        incident_id: str | None = None,
        occurred_at: datetime | str | None = None,
    ) -> RetainResult:
        """Retain reported incident observations without asserting a cause."""
        if not incident_description.strip():
            return self._rejected_retain("incident", "invalid_input", incident_id)
        content = _compose_content(
            "Incident experience (reported symptoms; root cause not asserted)",
            incident_description,
            technical_context,
        )
        if incident_id:
            content = f"{content}\nIncident: {_clean_text(incident_id)}"
        return await self._retain(
            memory_type="incident",
            content=content,
            context="IncidentIQ incident observation",
            incident_id=incident_id,
            occurred_at=occurred_at,
            tags=("incident", "incident-observation"),
        )

    async def retain_verified_resolution(
        self,
        root_cause: str,
        resolution: str,
        verified_by: str,
        verified: bool,
        incident_id: str | None = None,
        verified_at: datetime | str | None = None,
        technical_context: str | None = None,
    ) -> RetainResult:
        """Retain a resolution only after an explicit engineer verification."""
        if not verified:
            return self._rejected_retain("resolution", "unverified_resolution")
        if not verified_by.strip():
            return self._rejected_retain("resolution", "missing_verifier")
        if not root_cause.strip() or not resolution.strip():
            return self._rejected_retain("resolution", "invalid_input")

        content_parts = [
            "Engineer-verified resolution",
            f"Verified by: {_clean_text(verified_by)}",
            f"Verified root cause: {_clean_text(root_cause)}",
            f"Resolution: {_clean_text(resolution)}",
        ]
        if incident_id:
            content_parts.append(f"Incident: {_clean_text(incident_id)}")
        if technical_context and technical_context.strip():
            content_parts.append(f"Technical context: {_clean_text(technical_context)}")
        return await self._retain(
            memory_type="verified_resolution",
            content="\n".join(content_parts),
            context="Engineer-verified IncidentIQ resolution",
            incident_id=incident_id,
            occurred_at=verified_at,
            tags=("incident", "verified-resolution"),
        )

    async def retain_failed_approach(
        self,
        attempted_action: str,
        outcome: str,
        incident_id: str | None = None,
        failed_at: datetime | str | None = None,
        technical_context: str | None = None,
    ) -> RetainResult:
        """Retain a documented unsuccessful troubleshooting approach."""
        if not attempted_action.strip() or not outcome.strip():
            return self._rejected_retain("failed_approach", "invalid_input")
        content_parts = [
            "Previously unsuccessful troubleshooting approach",
            f"Attempted action: {_clean_text(attempted_action)}",
            f"Observed outcome: {_clean_text(outcome)}",
        ]
        if incident_id:
            content_parts.append(f"Incident: {_clean_text(incident_id)}")
        if technical_context and technical_context.strip():
            content_parts.append(f"Technical context: {_clean_text(technical_context)}")
        return await self._retain(
            memory_type="failed_approach",
            content="\n".join(content_parts),
            context="IncidentIQ failed troubleshooting experience",
            incident_id=incident_id,
            occurred_at=failed_at,
            tags=("incident", "failed-approach"),
        )

    async def _retain(
        self,
        memory_type: str,
        content: str,
        context: str,
        incident_id: str | None,
        occurred_at: datetime | str | None,
        tags: tuple[str, ...],
    ) -> RetainResult:
        recorded_at = _now()
        if self._client is None:
            self._audit(
                "retain", "failed", recorded_at, "client_unavailable", incident_id,
                memory_type=memory_type,
            )
            return RetainResult(
                "failed", self._bank_id, memory_type, recorded_at,
                error_category="client_unavailable",
            )
        if not content.strip():
            return self._rejected_retain(memory_type, "invalid_input", incident_id)

        document_id = _stable_document_id(memory_type, incident_id, content)
        async with self._retain_lock:
            if document_id in self._completed_documents:
                self._audit(
                    "retain", "skipped_duplicate", recorded_at,
                    incident_id=incident_id, memory_type=memory_type,
                )
                return RetainResult(
                    "skipped_duplicate", self._bank_id, memory_type, recorded_at, document_id
                )
            try:
                response = await self._client.aretain(
                    bank_id=self._bank_id,
                    content=content,
                    context=context,
                    tags=list(tags),
                    document_id=document_id,
                    timestamp=_format_timestamp(occurred_at),
                    update_mode="replace",
                )
            except Exception as error:
                category = _safe_error_category(error)
                self._audit(
                    "retain", "failed", recorded_at, category, incident_id,
                    memory_type=memory_type,
                )
                return RetainResult(
                    "failed", self._bank_id, memory_type, recorded_at,
                    document_id=document_id, error_category=category,
                )

            if not response.success:
                self._audit(
                    "retain", "failed", recorded_at, "sdk_rejected", incident_id,
                    memory_type=memory_type,
                )
                return RetainResult(
                    "failed", self._bank_id, memory_type, recorded_at,
                    document_id=document_id, error_category="sdk_rejected",
                )

            self._completed_documents.add(document_id)

        self._audit(
            "retain", "success", recorded_at,
            incident_id=incident_id, memory_type=memory_type,
        )
        return RetainResult(
            "success", self._bank_id, memory_type, recorded_at, document_id=document_id
        )

    def _rejected_retain(
        self,
        memory_type: str,
        error_category: str,
        incident_id: str | None = None,
    ) -> RetainResult:
        recorded_at = _now()
        self._audit(
            "retain", "failed", recorded_at, error_category, incident_id,
            memory_type=memory_type,
        )
        return RetainResult(
            "failed", self._bank_id, memory_type, recorded_at,
            error_category=error_category,
        )

    def _audit(
        self,
        operation_type: str,
        status: OperationStatus,
        timestamp: str,
        error_category: str | None = None,
        incident_id: str | None = None,
        memory_type: str | None = None,
    ) -> None:
        # Keep logs to safe metadata only: never include queries, memory text,
        # exception messages, credentials, or authorization headers.
        logger.log(
            logging.WARNING if status == "failed" else logging.INFO,
            "Hindsight operation audit",
            extra={
                "operation_type": operation_type,
                "memory_type": memory_type,
                "bank_id": self._bank_id,
                "timestamp": timestamp,
                "status": status,
                "error_category": error_category,
                "incident_id": incident_id,
                "memory_type": memory_type,
            },
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_timestamp(value: datetime | str | None) -> str:
    if value is None:
        return _now()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return value


def _stable_document_id(memory_type: str, incident_id: str | None, content: str) -> str:
    identity = "\0".join((memory_type, incident_id or "", content))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    return f"incidentiq-{memory_type}-{digest}"


def _compose_content(
    heading: str,
    incident_description: str,
    technical_context: str | None,
) -> str:
    parts = [heading]
    if incident_description.strip():
        parts.append(f"Incident description: {_clean_text(incident_description)}")
    if technical_context and technical_context.strip():
        parts.append(f"Technical context: {_clean_text(technical_context)}")
    return "\n".join(parts)


def _clean_text(value: str) -> str:
    """Redact common credential-shaped values before queries or retention."""
    value = re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
    value = re.sub(
        r"(?i)\b(api[_-]?key|access[_-]?token|token|password|secret|authorization)\b\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        value,
    )
    return value.strip()


def _safe_error_category(error: Exception) -> str:
    name = type(error).__name__.lower()
    status_code = getattr(error, "status_code", getattr(error, "status", None))
    if status_code in {401, 403} or "auth" in name or "permission" in name:
        return "authentication_error"
    if status_code == 429 or "rate" in name:
        return "rate_limited"
    if isinstance(status_code, int) and status_code >= 500:
        return "provider_error"
    if status_code == 404:
        return "provider_error"
    if "timeout" in name:
        return "timeout"
    if "connection" in name or "connect" in name or "network" in name:
        return "network_error"
    return "sdk_error"
