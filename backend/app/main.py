"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from hindsight_client import Hindsight

from app.config import Settings
from app.api.routes import router as api_router
from app.database import check_database, create_database_engine, create_session_factory
from app.services.ai_service import GroqAIService, create_groq_client
from app.services.hindsight_service import HindsightMemoryService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Load settings and own the optional Hindsight client's lifetime."""
    settings = Settings.load()
    application.state.settings = settings
    application.state.hindsight_client = None
    application.state.groq_client = None
    application.state.database_engine = None
    application.state.session_factory = None
    application.state.ai_service = None
    application.state.hindsight_service = None

    try:
        if settings.database_url:
            application.state.database_engine = create_database_engine(settings.database_url)
            application.state.session_factory = create_session_factory(
                application.state.database_engine
            )

        if settings.hindsight_api_key:
            base_url, api_key = settings.require_hindsight()
            application.state.hindsight_client = Hindsight(
                base_url=base_url,
                api_key=api_key,
            )
        application.state.hindsight_service = HindsightMemoryService(
            application.state.hindsight_client,
            bank_id=settings.hindsight_bank_id,
        )

        application.state.groq_client = create_groq_client(settings)
        application.state.ai_service = GroqAIService.from_settings(
            settings, application.state.groq_client
        )

        yield
    finally:
        try:
            for client_attr in ("groq_client", "hindsight_client"):
                client = getattr(application.state, client_attr, None)
                if client is not None:
                    try:
                        client.close()
                    except Exception as error:
                        logger.warning(
                            "External client close failed",
                            extra={
                                "resource": client_attr,
                                "error_category": type(error).__name__,
                            },
                        )
                    finally:
                        setattr(application.state, client_attr, None)
        finally:
            engine = application.state.database_engine
            if engine is not None:
                engine.dispose()
                application.state.database_engine = None
            application.state.session_factory = None
            application.state.hindsight_service = None
            application.state.ai_service = None


app = FastAPI(
    title="IncidentIQ API",
    description="Self-Learning AI Agent for Production Incident Investigation",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(api_router)


@app.get("/")
def home() -> dict[str, str]:
    return {
        "message": "Welcome to IncidentIQ",
        "status": "running",
        "project": "IncidentIQ",
    }


@app.get("/health")
async def health_check(request: Request) -> dict[str, object]:
    """Report liveness and perform safe, read-only provider readiness checks."""
    settings: Settings = request.app.state.settings
    database_configured = bool(settings.database_url)
    database_connected = check_database(request.app.state.database_engine)
    hindsight_service: HindsightMemoryService | None = getattr(
        request.app.state, "hindsight_service", None
    )
    ai_service: GroqAIService | None = getattr(request.app.state, "ai_service", None)

    if hindsight_service is None:
        hindsight = {
            "configured": bool(settings.hindsight_api_key),
            "reachable": False,
            "status": "unavailable" if settings.hindsight_api_key else "not_configured",
            "bank_id": settings.hindsight_bank_id,
            "error_category": "service_unavailable" if settings.hindsight_api_key else None,
        }
    else:
        check = await hindsight_service.check_availability()
        hindsight = {
            "configured": check.configured,
            "reachable": check.available,
            "status": check.status,
            "bank_id": check.bank_id,
            "checked_at": check.checked_at,
            "error_category": check.error_category,
        }

    if ai_service is None:
        groq = {
            "configured": bool(settings.groq_api_key),
            "reachable": False,
            "status": "unavailable" if settings.groq_api_key else "not_configured",
            "error_category": "service_unavailable" if settings.groq_api_key else None,
        }
    else:
        check = ai_service.check_availability()
        groq = {
            "configured": check.configured,
            "reachable": check.reachable,
            "status": check.status,
            "checked_at": check.checked_at,
            "error_category": check.error_category,
        }

    return {
        "success": True,
        "data": {
            "status": "ok",
            "application": "available",
            "dependencies": {
                "hindsight": hindsight,
                "groq": groq,
                "database": {
                    "configured": database_configured,
                    "status": (
                        "not_configured"
                        if not database_configured
                        else "connected" if database_connected else "unavailable"
                    ),
                },
            },
        },
    }
