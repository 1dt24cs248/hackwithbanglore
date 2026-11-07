"""Incident submission, investigation orchestration, and engineer learning flow."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Deployment,
    EngineerFeedback,
    Incident,
    IncidentLog,
    InvestigationFinding,
    InvestigationRun,
    MemoryOperationEvent,
    VerifiedResolution,
)
from app.schemas.ai import IncidentContext, InvestigationAnalysis
from app.schemas.investigation import (
    FailedApproachInput,
    FailedApproachResult,
    IncidentSubmission,
    IncidentSubmissionResult,
    InvestigationExecutionResult,
    InvestigationRequest,
    MemoryMode,
    RecommendationReference,
    EngineerFeedbackInput,
    EngineerFeedbackResult,
    VerifiedResolutionInput,
    VerifiedResolutionResult,
)
from app.services.ai_service import AIServiceError, GroqAIService
from app.services.hindsight_service import (
    HindsightMemoryService,
    RecallResult,
    RetainResult,
)

logger = logging.getLogger(__name__)

_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|authorization)"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+|\bbearer\s+[A-Za-z0-9._~+/=-]+"
)
_GROQ_KEY_PATTERN = re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b")
_AWS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|credential|authorization)"
)

MemoryStatus = Literal["success", "failed", "skipped_duplicate"]


class InvestigationServiceError(RuntimeError):
    """Safe, stable service failure without provider or database details."""

    def __init__(self, category: str, run_id: uuid.UUID | None = None) -> None:
        self.category = category
        self.run_id = run_id
        super().__init__(f"Incident investigation failed ({category}).")


class InvestigationService:
    """Coordinate existing persistence, Hindsight, and Groq services."""

    def __init__(
        self,
        session: Session,
        hindsight_service: HindsightMemoryService | None,
        ai_service: GroqAIService | None,
    ) -> None:
        self._session = session
        self._hindsight = hindsight_service
        self._ai = ai_service

    def submit_incident(
        self, payload: IncidentSubmission | dict[str, Any]
    ) -> IncidentSubmissionResult:
        """Validate and persist an incident and its submitted evidence."""
        data = _parse(IncidentSubmission, payload)
        _ensure_submission_safe(data)
        incident_id = uuid.uuid4()
        incident_number = _incident_number(incident_id)
        now = _now()
        try:
            incident = Incident(
                id=incident_id,
                incident_number=incident_number,
                title=data.title,
                description=data.description,
                service_name=data.service_name,
                environment=data.environment,
                severity=data.severity.value,
                owner=data.owner,
                source=data.source,
                status="open",
            )
            self._session.add(incident)
            self._session.flush()

            for message in data.error_messages:
                self._session.add(
                    IncidentLog(
                        incident_id=incident.id,
                        log_type="error",
                        log_text=message,
                        source_system="incident_submission",
                    )
                )
            for log in data.logs:
                self._session.add(
                    IncidentLog(
                        incident_id=incident.id,
                        log_type=log.log_type,
                        log_text=log.log_text,
                        source_system=log.source_system,
                        author=log.author,
                    )
                )
            if data.system_metrics:
                metrics_json = json.dumps(
                    data.system_metrics, ensure_ascii=False, separators=(",", ":")
                )
                self._session.add(
                    IncidentLog(
                        incident_id=incident.id,
                        log_type="note",
                        log_text=metrics_json,
                        source_system="system_metrics",
                        created_at=now,
                    )
                )
            if data.deployment is not None:
                deployment = data.deployment
                deployed_at = deployment.deployed_at or now
                if deployed_at.tzinfo is None:
                    deployed_at = deployed_at.replace(tzinfo=timezone.utc)
                self._session.add(
                    Deployment(
                        incident_id=incident.id,
                        deployment_id=deployment.deployment_id,
                        environment=data.environment,
                        service_name=data.service_name,
                        version=deployment.version,
                        deployed_by=deployment.deployed_by,
                        deployed_at=deployed_at,
                        change_summary=deployment.change_summary,
                    )
                )
            self._session.commit()
        except ValueError:
            self._session.rollback()
            raise InvestigationServiceError("invalid_input") from None
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error") from None

        return IncidentSubmissionResult(
            incident_id=incident_id,
            incident_number=incident_number,
            status="open",
        )

    async def run_investigation(
        self,
        incident_id: uuid.UUID | str,
        request: InvestigationRequest | dict[str, Any],
    ) -> InvestigationExecutionResult:
        """Run MEMORY_OFF or MEMORY_ON, persist findings, and preserve failure state."""
        incident_uuid = _uuid(incident_id, "invalid_incident_id")
        data = _parse(InvestigationRequest, request)
        mode = data.memory_mode

        try:
            incident = self._load_incident(incident_uuid)
            if incident is None:
                raise InvestigationServiceError("incident_not_found")
            context_without_memory = _incident_context(incident)
            run = InvestigationRun(
                incident_id=incident.id,
                memory_mode=mode.value,
                model_identifier=(
                    self._ai.model_identifier if self._ai is not None else None
                ),
                recalled_memory_refs=[],
                execution_status="queued",
            )
            self._session.add(run)
            self._session.flush()
            run_id = run.id
            self._session.commit()
            run.execution_status = "running"
            self._session.commit()
        except InvestigationServiceError:
            self._session.rollback()
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error") from None

        historical_memories = []
        if mode is MemoryMode.MEMORY_ON:
            recall_result = await self._recall(context_without_memory)
            if recall_result.status != "success":
                category = _safe_category(
                    recall_result.error_category or "recall_failed"
                )
                self._finish_failed_run(
                    run_id,
                    f"hindsight_{category}",
                    memory_event=_memory_event_values(
                        operation="recall",
                        memory_type="incident",
                        status="failed",
                        error_category=category,
                        summary="Hindsight recall failed.",
                    ),
                )
                raise InvestigationServiceError(f"hindsight_{category}", run_id)

            historical_memories = list(recall_result.memories)
            try:
                self._session.add(
                    _memory_event(
                        incident_id=incident_uuid,
                        run_id=run_id,
                        values=_memory_event_values(
                            operation="recall",
                            memory_type="incident",
                            status="success",
                            summary=f"Hindsight recall succeeded; result_count={len(historical_memories)}.",
                        ),
                    )
                )
                self._session.commit()
            except SQLAlchemyError:
                self._session.rollback()
                self._finish_failed_run(run_id, "database_error")
                raise InvestigationServiceError("database_error", run_id) from None

        if self._ai is None:
            self._finish_failed_run(run_id, "groq_not_configured")
            raise InvestigationServiceError("groq_not_configured", run_id)

        ai_context = context_without_memory.model_copy(
            update={"historical_memories": historical_memories}
        )
        try:
            analysis = await asyncio.to_thread(self._ai.analyze_incident, ai_context)
        except AIServiceError as error:
            category = f"groq_{error.category}"
            self._finish_failed_run(run_id, category)
            raise InvestigationServiceError(category, run_id) from None
        except Exception:
            self._finish_failed_run(run_id, "groq_error")
            raise InvestigationServiceError("groq_error", run_id) from None

        try:
            run = self._session.get(InvestigationRun, run_id)
            if run is None:
                raise SQLAlchemyError("run disappeared")
            run.model_identifier = analysis.model_identifier
            run.analysis_summary = analysis.summary
            run.recalled_memory_refs = _memory_references(historical_memories)
            recommendation_records: list[InvestigationFinding] = []
            for item in analysis.potential_root_causes:
                self._session.add(
                    InvestigationFinding(
                        investigation_run_id=run_id,
                        finding_type="root_cause",
                        content=f"Potential cause: {item.cause}\nRationale: {item.rationale}",
                        provenance="ai_hypothesis",
                        confidence=item.confidence,
                        evidence_refs=_finding_evidence_refs(item.supporting_evidence),
                        verified_by=None,
                    )
                )
            for item in analysis.recommended_steps:
                finding = InvestigationFinding(
                    investigation_run_id=run_id,
                    finding_type="recommendation",
                    content=f"{item.step}\nRationale: {item.rationale}",
                    provenance="ai_hypothesis",
                    evidence_refs=_finding_evidence_refs(item.supporting_evidence),
                    verified_by=None,
                )
                self._session.add(finding)
                recommendation_records.append(finding)
            run.execution_status = "succeeded"
            self._session.flush()
            recommendation_refs = [
                RecommendationReference(
                    id=finding.id,
                    index=index,
                    step=analysis.recommended_steps[index].step,
                )
                for index, finding in enumerate(recommendation_records)
            ]
            self._session.commit()
        except (ValueError, ValidationError):
            self._session.rollback()
            self._finish_failed_run(run_id, "result_persistence_error")
            raise InvestigationServiceError("result_persistence_error", run_id) from None
        except SQLAlchemyError:
            self._session.rollback()
            self._finish_failed_run(run_id, "database_error")
            raise InvestigationServiceError("database_error", run_id) from None

        return InvestigationExecutionResult(
            investigation_id=run_id,
            incident_id=incident_uuid,
            memory_mode=mode,
            execution_status="succeeded",
            model_identifier=analysis.model_identifier,
            analysis=analysis,
            recommendations=recommendation_refs,
        )

    async def record_feedback(
        self,
        incident_id: uuid.UUID | str,
        payload: EngineerFeedbackInput | dict[str, Any],
    ) -> EngineerFeedbackResult:
        """Persist feedback against a recommendation without changing AI findings."""
        incident_uuid = _uuid(incident_id, "invalid_incident_id")
        data = _parse(EngineerFeedbackInput, payload)
        _ensure_safe_texts(data.created_by, data.comment or "")
        try:
            run = self._session.scalar(
                select(InvestigationRun).where(
                    InvestigationRun.id == data.investigation_run_id,
                    InvestigationRun.incident_id == incident_uuid,
                )
            )
            if run is None:
                raise InvestigationServiceError("investigation_not_found")
            finding = self._session.scalar(
                select(InvestigationFinding).where(
                    InvestigationFinding.id == data.recommendation_id,
                    InvestigationFinding.investigation_run_id == run.id,
                    InvestigationFinding.finding_type == "recommendation",
                )
            )
            if finding is None:
                raise InvestigationServiceError("recommendation_not_found")
            feedback = EngineerFeedback(
                incident_id=incident_uuid,
                investigation_run_id=run.id,
                recommendation_id=str(finding.id),
                feedback_type=data.feedback_type,
                comment=data.comment,
                confidence=data.confidence,
                created_by=data.created_by,
            )
            self._session.add(feedback)
            self._session.commit()
        except InvestigationServiceError:
            self._session.rollback()
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error") from None
        return EngineerFeedbackResult(
            feedback_id=feedback.id,
            investigation_run_id=run.id,
            recommendation_id=finding.id,
            feedback_type=data.feedback_type,
        )

    async def record_verified_resolution(
        self,
        incident_id: uuid.UUID | str,
        payload: VerifiedResolutionInput | dict[str, Any],
    ) -> VerifiedResolutionResult:
        """Persist an engineer-confirmed resolution, then retain it in Hindsight."""
        incident_uuid = _uuid(incident_id, "invalid_incident_id")
        data = _parse(VerifiedResolutionInput, payload)
        if not data.confirmed:
            raise InvestigationServiceError("engineer_confirmation_required")
        _ensure_safe_texts(
            data.root_cause_summary,
            data.resolution_summary,
            data.verified_by,
        )
        verified_at = _now()
        try:
            incident = self._load_incident(incident_uuid)
            if incident is None:
                raise InvestigationServiceError("incident_not_found")
            if data.investigation_run_id is not None:
                run = self._session.scalar(
                    select(InvestigationRun).where(
                        InvestigationRun.id == data.investigation_run_id,
                        InvestigationRun.incident_id == incident_uuid,
                    )
                )
                if run is None:
                    raise InvestigationServiceError("investigation_not_found")
            resolution = VerifiedResolution(
                incident_id=incident_uuid,
                investigation_run_id=data.investigation_run_id,
                root_cause_summary=data.root_cause_summary,
                resolution_summary=data.resolution_summary,
                verified_by=data.verified_by,
                verified_at=verified_at,
            )
            self._session.add(resolution)
            incident.root_cause_summary = data.root_cause_summary
            incident.status = "resolved"
            incident.resolved_at = verified_at
            self._session.flush()
            resolution_id = resolution.id
            incident_number = incident.incident_number
            technical_context = f"Service: {incident.service_name}; Environment: {incident.environment}"
            self._session.commit()
        except InvestigationServiceError:
            self._session.rollback()
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error") from None

        retention = await self._retain_verified_resolution(
            root_cause=data.root_cause_summary,
            resolution=data.resolution_summary,
            verified_by=data.verified_by,
            incident_id=incident_number,
            verified_at=verified_at,
            technical_context=technical_context,
        )
        self._audit_retention(
            incident_id=incident_uuid,
            run_id=data.investigation_run_id,
            memory_type="resolution",
            retention=retention,
            payload_summary=(
                "Verified resolution retained."
                if retention.status == "success"
                else "Verified resolution retention skipped as duplicate."
                if retention.status == "skipped_duplicate"
                else "Verified resolution retention failed."
            ),
        )
        return VerifiedResolutionResult(
            resolution_id=resolution_id,
            incident_id=incident_uuid,
            status="resolved",
            memory_retention_status=retention.status,
            memory_error_category=retention.error_category,
        )

    async def record_failed_approach(
        self,
        incident_id: uuid.UUID | str,
        payload: FailedApproachInput | dict[str, Any],
    ) -> FailedApproachResult:
        """Retain an engineer-reported failed path under failure memory only."""
        incident_uuid = _uuid(incident_id, "invalid_incident_id")
        data = _parse(FailedApproachInput, payload)
        _ensure_safe_texts(data.attempted_action, data.outcome, data.recorded_by)
        try:
            incident = self._load_incident(incident_uuid)
            if incident is None:
                raise InvestigationServiceError("incident_not_found")
            if data.investigation_run_id is not None:
                run = self._session.scalar(
                    select(InvestigationRun).where(
                        InvestigationRun.id == data.investigation_run_id,
                        InvestigationRun.incident_id == incident_uuid,
                    )
                )
                if run is None:
                    raise InvestigationServiceError("investigation_not_found")
            incident_number = incident.incident_number
            technical_context = f"Service: {incident.service_name}; Environment: {incident.environment}"
            self._session.commit()
        except InvestigationServiceError:
            self._session.rollback()
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error") from None

        if self._hindsight is None:
            retention = _failed_retention("service_unavailable", "failed_approach", "unconfigured")
        else:
            try:
                retention = await self._hindsight.retain_failed_approach(
                    attempted_action=data.attempted_action,
                    outcome=data.outcome,
                    incident_id=incident_number,
                    failed_at=_now(),
                    technical_context=technical_context,
                )
            except Exception:
                retention = _failed_retention("service_error", "failed_approach", self._hindsight.bank_id)
        self._audit_retention(
            incident_id=incident_uuid,
            run_id=data.investigation_run_id,
            memory_type="failure",
            retention=retention,
            payload_summary=(
                "Failed troubleshooting approach retained."
                if retention.status == "success"
                else "Failed troubleshooting retention skipped as duplicate."
                if retention.status == "skipped_duplicate"
                else "Failed troubleshooting retention failed."
            ),
        )
        return FailedApproachResult(
            incident_id=incident_uuid,
            memory_retention_status=retention.status,
            memory_error_category=retention.error_category,
        )

    async def _recall(self, context: IncidentContext) -> RecallResult:
        if self._hindsight is None:
            return RecallResult(
                status="failed",
                bank_id="unconfigured",
                recalled_at=_now().isoformat(),
                error_category="service_unavailable",
            )
        try:
            return await self._hindsight.recall_incident_memories(
                context.incident_description,
                _technical_context(context),
            )
        except Exception:
            return RecallResult(
                status="failed",
                bank_id=self._hindsight.bank_id,
                recalled_at=_now().isoformat(),
                error_category="service_error",
            )

    def _finish_failed_run(
        self,
        run_id: uuid.UUID,
        category: str,
        memory_event: dict[str, str] | None = None,
    ) -> None:
        logger.warning(
            "Investigation run failed",
            extra={
                "operation": "investigate",
                "investigation_id": str(run_id),
                "failure_category": category,
            },
        )
        try:
            run = self._session.get(InvestigationRun, run_id)
            if run is not None:
                run.execution_status = "failed"
            if memory_event is not None:
                self._session.add(
                    _memory_event(
                        incident_id=run.incident_id if run is not None else None,
                        run_id=run_id,
                        values=memory_event,
                    )
                )
            self._session.commit()
        except Exception as error:
            self._session.rollback()
            logger.warning(
                "Investigation failure state could not be persisted",
                extra={
                    "operation": "mark_investigation_failed",
                    "error_category": type(error).__name__,
                    "failure_category": category,
                },
            )

    def _load_incident(self, incident_id: uuid.UUID) -> Incident | None:
        return self._session.scalar(
            select(Incident)
            .options(
                selectinload(Incident.logs),
                selectinload(Incident.deployments),
                selectinload(Incident.verified_resolutions),
            )
            .where(Incident.id == incident_id)
        )

    def _retain_verified_resolution(
        self,
        *,
        root_cause: str,
        resolution: str,
        verified_by: str,
        incident_id: str,
        verified_at: datetime,
        technical_context: str,
    ) -> RetainResult:
        if self._hindsight is None:
            return _failed_retention("service_unavailable", "verified_resolution", "unconfigured")
        try:
            return self._hindsight.retain_verified_resolution(
                root_cause=root_cause,
                resolution=resolution,
                verified_by=verified_by,
                verified=True,
                incident_id=incident_id,
                verified_at=verified_at,
                technical_context=technical_context,
            )
        except Exception:
            return _failed_retention("service_error", "verified_resolution", self._hindsight.bank_id)

    def _audit_retention(
        self,
        *,
        incident_id: uuid.UUID,
        run_id: uuid.UUID | None,
        memory_type: str,
        retention: RetainResult,
        payload_summary: str,
    ) -> None:
        status = "failed" if retention.status == "failed" else "success"
        values = _memory_event_values(
            operation="retain",
            memory_type=memory_type,
            status=status,
            summary=payload_summary,
            error_category=retention.error_category,
        )
        try:
            self._session.add(
                _memory_event(incident_id=incident_id, run_id=run_id, values=values)
            )
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise InvestigationServiceError("database_error", run_id) from None


def _parse(model: type, payload: Any) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError:
        raise InvestigationServiceError("invalid_input") from None


def _uuid(value: uuid.UUID | str, error_category: str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise InvestigationServiceError(error_category) from None


def _ensure_submission_safe(payload: IncidentSubmission) -> None:
    values = [
        payload.title,
        payload.description,
        payload.service_name,
        payload.environment,
        payload.owner or "",
        payload.source,
    ]
    values.extend(payload.error_messages)
    values.extend(log.log_text for log in payload.logs)
    values.extend(
        value
        for log in payload.logs
        for value in (log.source_system or "", log.author or "")
    )
    if payload.deployment is not None:
        values.extend(
            (
                payload.deployment.deployment_id or "",
                payload.deployment.version or "",
                payload.deployment.deployed_by or "",
                payload.deployment.change_summary or "",
            )
        )
    metrics = json.dumps(payload.system_metrics, ensure_ascii=False)
    values.append(metrics)
    _ensure_safe_texts(*values)
    if any(_SENSITIVE_KEY_PATTERN.search(key) for key in payload.system_metrics):
        raise InvestigationServiceError("sensitive_input_rejected")


def _ensure_safe_texts(*values: str) -> None:
    for value in values:
        if _contains_sensitive(value):
            raise InvestigationServiceError("sensitive_input_rejected")


def _contains_sensitive(value: str) -> bool:
    return bool(
        _CREDENTIAL_PATTERN.search(value)
        or _GROQ_KEY_PATTERN.search(value)
        or _AWS_KEY_PATTERN.search(value)
        or re.search(r"(?i)(://[^:/\s]+:)[^@/\s]+@", value)
    )


def _incident_number(incident_id: uuid.UUID) -> str:
    return f"INC-{_now():%Y%m%d}-{incident_id.hex[:8].upper()}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _incident_context(incident: Incident) -> IncidentContext:
    metrics: dict[str, str | int | float | bool | None] = {}
    ordinary_logs: list[str] = []
    error_messages: list[str] = []
    for log in sorted(incident.logs, key=lambda item: (str(item.created_at), str(item.id))):
        if log.source_system == "system_metrics":
            try:
                parsed = json.loads(log.log_text)
                if isinstance(parsed, dict):
                    metrics.update(parsed)
            except (TypeError, ValueError):
                ordinary_logs.append(log.log_text)
        elif log.log_type == "error":
            error_messages.append(log.log_text)
        else:
            ordinary_logs.append(log.log_text)

    deployments = [
        {
            "deployment_id": deployment.deployment_id,
            "service_name": deployment.service_name,
            "environment": deployment.environment,
            "version": deployment.version,
            "deployed_by": deployment.deployed_by,
            "deployed_at": deployment.deployed_at,
            "change_summary": deployment.change_summary,
        }
        for deployment in sorted(
            incident.deployments,
            key=lambda item: (str(item.deployed_at), str(item.id)),
        )
    ]
    verified_findings = [
        {
            "finding_id": str(resolution.id),
            "statement": (
                f"Verified root cause: {resolution.root_cause_summary}; "
                f"verified resolution: {resolution.resolution_summary}"
            ),
            "verified_by": resolution.verified_by,
            "verified_at": resolution.verified_at,
        }
        for resolution in sorted(
            incident.verified_resolutions,
            key=lambda item: (str(item.verified_at), str(item.id)),
        )
    ]
    return IncidentContext(
        incident_id=incident.incident_number,
        service_name=incident.service_name,
        environment=incident.environment,
        severity=incident.severity,
        incident_description=f"{incident.title}\n{incident.description}",
        error_messages=error_messages,
        logs=ordinary_logs,
        deployments=deployments,
        system_metrics=metrics,
        engineer_verified_findings=verified_findings,
    )


def _technical_context(context: IncidentContext) -> str:
    parts = [
        f"Incident: {context.incident_id or 'unknown incident'}",
        f"Service: {context.service_name or 'unspecified'}",
        f"Environment: {context.environment or 'unspecified'}",
        f"Severity: {context.severity or 'unspecified'}",
        *(f"Error: {item}" for item in context.error_messages[:20]),
        *(f"Log: {item}" for item in context.logs[:20]),
        *(f"Deployment: {json.dumps(item.model_dump(mode='json', exclude_none=True))}" for item in context.deployments),
        f"System metrics: {json.dumps(context.system_metrics, ensure_ascii=False)}",
    ]
    return "\n".join(parts)[:10_000]


def _finding_evidence_refs(citations: list[Any]) -> list[dict[str, str]]:
    provenance_map = {
        "current_incident_evidence": "current_incident_evidence",
        "historical_hindsight_memory": "historical_memory",
        "engineer_verified_root_cause": "engineer_verified_root_cause",
    }
    refs: list[dict[str, str]] = []
    for citation in citations:
        if len(citation.reference) > 255:
            raise ValueError("evidence reference is too long")
        refs.append(
            {
                "source_id": citation.reference,
                "provenance": provenance_map[citation.provenance],
            }
        )
    return refs


def _memory_references(memories: list[Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for memory in memories:
        if len(memory.id) > 255:
            raise ValueError("memory reference is too long")
        refs.append(
            {
                "memory_id": memory.id,
                "provenance": "historical_memory",
                "type": memory.memory_type or "incident",
            }
        )
    return refs


def _memory_event_values(
    *,
    operation: str,
    memory_type: str,
    status: str,
    summary: str,
    error_category: str | None = None,
) -> dict[str, str]:
    values = {
        "operation_name": operation,
        "memory_type": memory_type,
        "status": status,
        "payload_summary": summary,
    }
    if error_category:
        values["error_message"] = _safe_category(error_category)
    return values


def _memory_event(
    *,
    incident_id: uuid.UUID | None,
    run_id: uuid.UUID | None,
    values: dict[str, str],
) -> MemoryOperationEvent:
    return MemoryOperationEvent(
        incident_id=incident_id,
        investigation_run_id=run_id,
        **values,
    )


def _failed_retention(category: str, memory_type: str, bank_id: str) -> RetainResult:
    return RetainResult(
        status="failed",
        bank_id=bank_id,
        memory_type=memory_type,
        recorded_at=_now().isoformat(),
        error_category=category,
    )


def _safe_category(value: str) -> str:
    if re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value):
        return value
    return "external_service_error"
