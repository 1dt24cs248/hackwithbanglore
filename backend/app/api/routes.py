"""REST endpoints for the IncidentIQ incident lifecycle."""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    Incident,
    InvestigationRun,
    MemoryOperationEvent,
    Postmortem,
    VerifiedResolution,
)
from app.schemas.investigation import (
    FailedApproachInput,
    IncidentSubmission,
    InvestigationRequest,
    EngineerFeedbackInput,
    VerifiedResolutionInput,
)
from app.services.hindsight_service import HindsightMemoryService
from app.services.investigation_service import InvestigationService, InvestigationServiceError

router = APIRouter(prefix="/api", tags=["IncidentIQ"])


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recommendation_id: uuid.UUID
    feedback_type: Literal["accepted", "rejected", "corrected"]
    comment: str | None = None
    confidence: Decimal | None = None
    created_by: str


def get_investigation_service(
    request: Request, session: Session = Depends(get_db)
) -> InvestigationService:
    return InvestigationService(
        session=session,
        hindsight_service=getattr(request.app.state, "hindsight_service", None),
        ai_service=getattr(request.app.state, "ai_service", None),
    )


def _fail(error: InvestigationServiceError) -> HTTPException:
    category = error.category
    if category in {"incident_not_found", "investigation_not_found", "recommendation_not_found"}:
        return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Requested resource was not found."})
    if category in {"hindsight_client_unavailable", "groq_not_configured", "groq_error"} or category.startswith(("hindsight_", "groq_")):
        return HTTPException(status_code=503, detail={"code": "DEPENDENCY_UNAVAILABLE", "message": "An investigation dependency is unavailable."})
    if category == "database_error":
        return HTTPException(status_code=503, detail={"code": "DATABASE_UNAVAILABLE", "message": "The database operation could not be completed."})
    if category == "engineer_confirmation_required":
        return HTTPException(status_code=409, detail={"code": "VERIFICATION_REQUIRED", "message": "Explicit engineer verification is required."})
    if category in {"invalid_input", "invalid_incident_id", "sensitive_input_rejected"}:
        return HTTPException(status_code=422, detail={"code": "INVALID_INPUT", "message": "The request contains invalid or sensitive input."})
    return HTTPException(status_code=500, detail={"code": "REQUEST_FAILED", "message": "The request could not be completed."})


def _envelope(data: Any) -> dict[str, Any]:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    return {"success": True, "data": data}


@router.post("/incidents", status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentSubmission,
    service: InvestigationService = Depends(get_investigation_service),
) -> dict[str, Any]:
    try:
        return _envelope(service.submit_incident(payload))
    except InvestigationServiceError as error:
        raise _fail(error) from None


@router.get("/incidents")
def list_incidents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    service_name: str | None = None,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(Incident)
    count_query = select(func.count(Incident.id))
    filters = []
    if status_filter:
        filters.append(Incident.status == status_filter)
    if severity:
        filters.append(Incident.severity == severity)
    if service_name:
        filters.append(Incident.service_name == service_name)
    query = query.where(*filters)
    count_query = count_query.where(*filters)
    try:
        total = session.scalar(count_query) or 0
        items = session.scalars(
            query.order_by(Incident.created_at.desc(), Incident.id).offset((page - 1) * limit).limit(limit)
        ).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "The database operation could not be completed."}) from None
    return _envelope({"items": [_incident_summary(i) for i in items], "total": total, "page": page, "limit": limit})


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    incident = session.scalar(
        select(Incident).options(selectinload(Incident.logs), selectinload(Incident.deployments), selectinload(Incident.verified_resolutions)).where(Incident.id == incident_id)
    )
    if incident is None:
        raise _fail(InvestigationServiceError("incident_not_found"))

    # Resolve the latest Hindsight retention status for the demo learning loop
    retention_status = None
    latest_event = session.scalar(
        select(MemoryOperationEvent)
        .where(
            MemoryOperationEvent.incident_id == incident_id,
            MemoryOperationEvent.operation_name == "retain",
            MemoryOperationEvent.memory_type == "resolution",
        )
        .order_by(MemoryOperationEvent.created_at.desc(), MemoryOperationEvent.id.desc())
    )

    if latest_event:
        summary = latest_event.payload_summary or ""
        if "Verified resolution retained." in summary:
            retention_status = "success"
        elif "Verified resolution retention skipped as duplicate." in summary:
            retention_status = "skipped_duplicate"
        elif "Verified resolution retention failed." in summary:
            retention_status = "failed"

    return _envelope({
        **_incident_summary(incident),
        "description": incident.description,
        "environment": incident.environment,
        "owner": incident.owner,
        "source": incident.source,
        "root_cause_summary": incident.root_cause_summary,
        "resolved_at": _iso(incident.resolved_at),
        "memory_retention_status": retention_status,
        "logs": [{"id": str(x.id), "log_type": x.log_type, "log_text": x.log_text, "source_system": x.source_system, "created_at": _iso(x.created_at)} for x in incident.logs],
        "deployments": [{"id": str(x.id), "deployment_id": x.deployment_id, "version": x.version, "environment": x.environment, "service_name": x.service_name, "deployed_by": x.deployed_by, "deployed_at": _iso(x.deployed_at), "change_summary": x.change_summary} for x in incident.deployments],
        "verified_resolutions": [{"id": str(x.id), "root_cause_summary": x.root_cause_summary, "resolution_summary": x.resolution_summary, "verified_by": x.verified_by, "verified_at": _iso(x.verified_at), "provenance": "engineer_verified_root_cause"} for x in incident.verified_resolutions],
    })


@router.post("/incidents/{incident_id}/investigate", status_code=status.HTTP_201_CREATED)
async def investigate(
    incident_id: uuid.UUID,
    payload: InvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> dict[str, Any]:
    try:
        return _envelope(await service.run_investigation(incident_id, payload))
    except InvestigationServiceError as error:
        raise _fail(error) from None


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    run = session.scalar(
        select(InvestigationRun).options(selectinload(InvestigationRun.findings), selectinload(InvestigationRun.feedback)).where(InvestigationRun.id == investigation_id)
    )
    if run is None:
        raise _fail(InvestigationServiceError("investigation_not_found"))
    findings = [{
        "id": str(f.id), "finding_type": f.finding_type, "content": f.content,
        "provenance": f.provenance, "confidence": float(f.confidence) if f.confidence is not None else None,
        "evidence_refs": f.evidence_refs or [], "requires_engineer_review": f.finding_type == "recommendation",
    } for f in run.findings]
    hypotheses = [item for item in findings if item["finding_type"] == "root_cause"]
    recommendations = [item for item in findings if item["finding_type"] == "recommendation"]
    return _envelope({
        "id": str(run.id), "incident_id": str(run.incident_id), "memory_mode": run.memory_mode,
        "execution_status": run.execution_status, "model_identifier": run.model_identifier,
        "summary": run.analysis_summary, "historical_memory_refs": run.recalled_memory_refs or [],
        "findings": findings, "hypotheses": hypotheses,
        "recommendations": recommendations, "created_at": _iso(run.created_at),
    })


@router.post("/investigations/{investigation_id}/feedback", status_code=status.HTTP_201_CREATED)
async def feedback(
    investigation_id: uuid.UUID,
    payload: FeedbackRequest,
    session: Session = Depends(get_db),
    service: InvestigationService = Depends(get_investigation_service),
) -> dict[str, Any]:
    run = session.get(InvestigationRun, investigation_id)
    if run is None:
        raise _fail(InvestigationServiceError("investigation_not_found"))
    feedback_payload = EngineerFeedbackInput(
        investigation_run_id=investigation_id,
        recommendation_id=payload.recommendation_id,
        feedback_type=payload.feedback_type,
        comment=payload.comment,
        confidence=payload.confidence,
        created_by=payload.created_by,
    )
    try:
        return _envelope(await service.record_feedback(run.incident_id, feedback_payload))
    except InvestigationServiceError as error:
        raise _fail(error) from None


@router.post("/incidents/{incident_id}/resolve", status_code=status.HTTP_201_CREATED)
async def resolve_incident(
    incident_id: uuid.UUID,
    payload: VerifiedResolutionInput,
    service: InvestigationService = Depends(get_investigation_service),
) -> dict[str, Any]:
    try:
        return _envelope(await service.record_verified_resolution(incident_id, payload))
    except InvestigationServiceError as error:
        raise _fail(error) from None


@router.post("/incidents/{incident_id}/failed-approaches", status_code=status.HTTP_201_CREATED)
async def failed_approach(
    incident_id: uuid.UUID,
    payload: FailedApproachInput,
    service: InvestigationService = Depends(get_investigation_service),
) -> dict[str, Any]:
    try:
        return _envelope(await service.record_failed_approach(incident_id, payload))
    except InvestigationServiceError as error:
        raise _fail(error) from None


@router.get("/incidents/{incident_id}/memories")
async def incident_memories(
    incident_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    incident = session.scalar(select(Incident).where(Incident.id == incident_id))
    if incident is None:
        raise _fail(InvestigationServiceError("incident_not_found"))
    hindsight: HindsightMemoryService | None = getattr(request.app.state, "hindsight_service", None)
    if hindsight is None:
        raise HTTPException(503, detail={
            "code": "MEMORY_UNAVAILABLE",
            "message": "Hindsight memory service is not configured.",
            "error_category": "service_unavailable",
        })
    result = await hindsight.recall_incident_memories(
        f"{incident.title}\n{incident.description}",
        f"Incident: {incident.incident_number}; Service: {incident.service_name}; Environment: {incident.environment}; Severity: {incident.severity}",
    )
    try:
        session.add(MemoryOperationEvent(
            incident_id=incident.id, operation_name="recall", memory_type="incident",
            status="success" if result.status == "success" else "failed",
            payload_summary=f"Memory endpoint recall; result_count={len(result.memories)}." if result.status == "success" else "Memory endpoint recall failed.",
            error_message=result.error_category,
        ))
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "The memory audit could not be saved."}) from None
    if result.status != "success":
        category = _safe_provider_error_category(result.error_category)
        raise HTTPException(503, detail={
            "code": "MEMORY_UNAVAILABLE",
            "message": _memory_error_message(category),
            "error_category": category,
        })
    return _envelope({"entries": [{
        "id": item.id, "memory_type": item.memory_type, "summary": item.text,
        "context": item.context, "occurred_start": item.occurred_start,
        "mentioned_at": item.mentioned_at, "tags": list(item.tags),
        "provenance": "historical_hindsight_memory",
    } for item in result.memories]})


@router.get("/dashboard/summary")
def dashboard_summary(session: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        total = session.scalar(select(func.count(Incident.id))) or 0
        open_count = session.scalar(select(func.count(Incident.id)).where(Incident.status.in_(["open", "investigating"]))) or 0
        resolved = session.scalar(select(func.count(Incident.id)).where(Incident.status == "resolved")) or 0
        severity_counts = dict(session.execute(select(Incident.severity, func.count(Incident.id)).group_by(Incident.severity)).all())
        statuses = dict(session.execute(select(Incident.status, func.count(Incident.id)).group_by(Incident.status)).all())
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Dashboard data is unavailable."}) from None
    return _envelope({"total_incidents": total, "open_incidents": open_count, "resolved_incidents": resolved,
                      "critical_incidents": severity_counts.get("critical", 0),
                      "severity_distribution": {key: severity_counts.get(key, 0) for key in ("critical", "high", "medium", "low")},
                      "status_distribution": statuses})


@router.get("/memory/activity")
def memory_activity(
    limit: int = Query(default=8, ge=1, le=50),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return safe operation metadata from the existing memory audit table."""
    try:
        events = session.scalars(
            select(MemoryOperationEvent)
            .order_by(MemoryOperationEvent.created_at.desc(), MemoryOperationEvent.id)
            .limit(limit)
        ).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Memory activity is unavailable."}) from None
    return _envelope({"items": [{
        "id": str(event.id),
        "operation": event.operation_name,
        "memory_type": event.memory_type,
        "status": event.status,
        "incident_id": str(event.incident_id) if event.incident_id else None,
        "created_at": _iso(event.created_at),
    } for event in events]})


@router.get("/postmortems")
def list_postmortems(
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """List all generated postmortems across incidents."""
    try:
        postmortems = session.scalars(
            select(Postmortem)
            .options(selectinload(Postmortem.incident))
            .order_by(Postmortem.created_at.desc())
        ).all()
    except SQLAlchemyError:
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Postmortems are unavailable."}) from None

    return _envelope({"items": [{
        "id": str(pm.id),
        "incident_id": str(pm.incident_id),
        "incident_number": pm.incident.incident_number if pm.incident else "—",
        "incident_title": pm.incident.title if pm.incident else "—",
        "title": pm.title,
        "status": pm.status,
        "revision_number": pm.revision_number,
        "downloaded_count": pm.downloaded_count,
        "created_at": _iso(pm.created_at),
        "updated_at": _iso(pm.updated_at),
    } for pm in postmortems]})


@router.get("/postmortems/{postmortem_id}")
def get_postmortem(
    postmortem_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve a postmortem document by ID."""
    pm = session.scalar(
        select(Postmortem)
        .options(selectinload(Postmortem.incident))
        .where(Postmortem.id == postmortem_id)
    )
    if pm is None:
        raise HTTPException(404, detail={"code": "POSTMORTEM_NOT_FOUND", "message": "Postmortem not found."})

    return _envelope({
        "id": str(pm.id),
        "incident_id": str(pm.incident_id),
        "incident_number": pm.incident.incident_number if pm.incident else "—",
        "incident_title": pm.incident.title if pm.incident else "—",
        "title": pm.title,
        "body_markdown": pm.body_markdown,
        "status": pm.status,
        "generated_by": pm.generated_by,
        "revision_number": pm.revision_number,
        "downloaded_count": pm.downloaded_count,
        "created_at": _iso(pm.created_at),
        "updated_at": _iso(pm.updated_at),
    })


@router.post("/incidents/{incident_id}/postmortem")
@router.post("/incidents/{incident_id}/postmortems")
def generate_incident_postmortem(
    incident_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generate or retrieve a structured markdown postmortem for an incident with a verified resolution."""
    incident = session.scalar(
        select(Incident)
        .options(
            selectinload(Incident.logs),
            selectinload(Incident.deployments),
            selectinload(Incident.verified_resolutions),
            selectinload(Incident.investigation_runs).selectinload(InvestigationRun.findings),
        )
        .where(Incident.id == incident_id)
    )
    if incident is None:
        raise _fail(InvestigationServiceError("incident_not_found"))

    if not incident.verified_resolutions:
        raise HTTPException(400, detail={
            "code": "RESOLUTION_REQUIRED",
            "message": "A postmortem can only be generated after an engineer explicitly confirms a verified resolution. Unverified incidents cannot produce a postmortem.",
        })

    resolution = incident.verified_resolutions[0]
    existing = session.scalar(
        select(Postmortem).where(Postmortem.incident_id == incident_id, Postmortem.status == "final")
    )
    if existing is not None:
        return _envelope({
            "postmortem_id": str(existing.id),
            "incident_id": str(incident.id),
            "incident_number": incident.incident_number,
            "title": existing.title,
            "status": existing.status,
            "body_markdown": existing.body_markdown,
            "revision_number": existing.revision_number,
            "downloaded_count": existing.downloaded_count,
            "created_at": _iso(existing.created_at),
        })

    settings = getattr(request.app.state, "settings", None)
    bank_id = settings.hindsight_bank_id if settings else "incidentiq-hackathon-demo"
    body = _build_postmortem_markdown(incident, resolution, incident.investigation_runs, bank_id)

    pm = Postmortem(
        incident_id=incident.id,
        verified_resolution_id=resolution.id,
        revision_number=1,
        title=f"Postmortem: {incident.title}",
        body_markdown=body,
        status="final",
        generated_by="IncidentIQ Engine",
    )
    try:
        session.add(pm)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Could not persist postmortem."}) from None

    return _envelope({
        "postmortem_id": str(pm.id),
        "incident_id": str(incident.id),
        "incident_number": incident.incident_number,
        "title": pm.title,
        "status": pm.status,
        "body_markdown": pm.body_markdown,
        "revision_number": pm.revision_number,
        "downloaded_count": pm.downloaded_count,
        "created_at": _iso(pm.created_at),
    })


@router.get("/postmortems/{postmortem_id}/download")
def download_postmortem(
    postmortem_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> Response:
    """Download postmortem as a markdown file."""
    pm = session.scalar(
        select(Postmortem)
        .options(selectinload(Postmortem.incident))
        .where(Postmortem.id == postmortem_id)
    )
    if pm is None:
        raise HTTPException(404, detail={"code": "POSTMORTEM_NOT_FOUND", "message": "Postmortem not found."})

    try:
        pm.downloaded_count += 1
        session.commit()
    except SQLAlchemyError:
        session.rollback()

    ref = pm.incident.incident_number if pm.incident else str(pm.id)[:8]
    filename = f"postmortem-{ref}.md"
    return Response(
        content=pm.body_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_postmortem_markdown(
    incident: Incident,
    resolution: VerifiedResolution,
    runs: list[InvestigationRun],
    bank_id: str,
) -> str:
    md_lines = [
        f"# Incident Postmortem: {incident.title}",
        "",
        f"**Incident Reference:** `{incident.incident_number}`  ",
        f"**Service:** `{incident.service_name}`  ",
        f"**Environment:** `{incident.environment}`  ",
        f"**Severity:** `{incident.severity.upper()}`  ",
        f"**Status:** `{incident.status.upper()}`  ",
        f"**Reported Date:** `{_iso(incident.created_at) or 'Unknown'}`  ",
        f"**Resolution Confirmed:** `{_iso(resolution.verified_at) or 'Unknown'}`  ",
        "",
        "---",
        "",
        "## 1. Confirmed Incident Facts & Telemetry",
        "",
        "### Incident Description",
        incident.description,
        "",
    ]

    deployment = incident.deployments[0] if getattr(incident, 'deployments', None) else None
    if deployment:
        md_lines.extend([
            "### Deployment Context",
            f"- **Deployment ID:** `{deployment.deployment_id}`",
            f"- **Version:** `{deployment.version or 'N/A'}`",
            f"- **Change Summary:** {deployment.change_summary or 'None'}",
            "",
        ])

    if incident.logs:
        md_lines.append("### Incident Evidence & Error Logs")
        for log in incident.logs:
            md_lines.append(f"- `[{log.log_type.upper()}]` ({log.source_system}): {log.log_text}")
        md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "## 2. Engineer-Verified Root Cause",
        "",
        f"> **Explicitly verified by:** `{resolution.verified_by}` on `{_iso(resolution.verified_at) or 'Unknown'}`",
        "",
        resolution.root_cause_summary,
        "",
        "---",
        "",
        "## 3. Applied Resolution & Corrective Actions",
        "",
        resolution.resolution_summary,
        "",
        "---",
        "",
        "## 4. Operational Impact Assessment",
        "",
        f"- **Affected Service:** `{incident.service_name}`",
        f"- **Environment:** `{incident.environment}`",
        f"- **Severity Classification:** `{incident.severity.upper()}`",
        "",
        "---",
        "",
        "## 5. Lessons Learned & Retained Hindsight Memory",
        "",
        f"- **Memory Bank:** `{bank_id}`",
        "- **Retained Artifacts:** Verified resolution stored with persistent tags `['incident', 'verified-resolution']`.",
        "- **Future Benefit:** Subsequent investigations in the same service/domain recall this verified pattern automatically during `MEMORY_ON` investigations.",
        "",
        "---",
        "",
        "## 6. Unverified AI Suggestions & Initial Hypotheses (Audit Reference Only)",
        "",
        "> [!WARNING]",
        "> **AUDIT REFERENCE ONLY · NOT CONFIRMED FACTS**  ",
        "> The following items were hypotheses and recommendations generated by the AI model during initial investigation runs before human verification. They are recorded here strictly for audit provenance and must not be cited as verified conclusions.",
        "",
    ])

    ai_found = False
    for r in runs:
        findings = r.findings or []
        if findings or r.analysis_summary:
            ai_found = True
            md_lines.append(f"### Investigation Run `{str(r.id)[:8].upper()}` (Mode: `MEMORY_{r.memory_mode.upper()}`)")
            if r.analysis_summary:
                md_lines.append(f"**Model Summary:** {r.analysis_summary}")
                md_lines.append("")
            for f in findings:
                conf_str = f" (Confidence: {int(f.confidence * 100)}%)" if f.confidence is not None else ""
                md_lines.append(f"- **[{f.provenance.upper()} - UNVERIFIED]{conf_str}:** {f.content}")
            md_lines.append("")

    if not ai_found:
        md_lines.append("No prior AI investigation findings recorded.")
        md_lines.append("")

    return "\n".join(md_lines)


def _incident_summary(incident: Incident) -> dict[str, Any]:
    return {"id": str(incident.id), "incident_number": incident.incident_number, "title": incident.title,
            "status": incident.status, "severity": incident.severity, "service_name": incident.service_name,
            "created_at": _iso(incident.created_at)}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _safe_provider_error_category(value: str | None) -> str:
    allowed = {
        "authentication_error", "network_error", "connection_error", "timeout",
        "rate_limited", "provider_error", "sdk_error", "client_unavailable",
        "invalid_input", "service_unavailable", "service_error",
    }
    return value if value in allowed else "provider_error"


def _memory_error_message(category: str) -> str:
    messages = {
        "authentication_error": "Hindsight authentication failed. Check the backend credentials.",
        "network_error": "Hindsight could not be reached. Check backend network connectivity.",
        "connection_error": "Hindsight could not be reached. Check backend network connectivity.",
        "timeout": "The Hindsight recall request timed out. Retry shortly.",
        "rate_limited": "Hindsight rate limit reached. Retry shortly.",
        "client_unavailable": "Hindsight is not configured on the backend.",
        "invalid_input": "The incident context could not be used for Hindsight recall.",
    }
    return messages.get(category, "Historical memory is temporarily unavailable. Retry or check provider status.")
