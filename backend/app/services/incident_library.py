"""Read-only, version-controlled catalog of verified production incidents."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from app.schemas.library import IncidentLibraryRecord


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "real_incidents.json"
CATEGORY_PATH = CATALOG_PATH.parent / "incident_categories.json"
OFFICIAL_SOURCE_DOMAINS = {
    "Cloudflare": ("cloudflare.com",), "GitHub": ("github.blog",),
    "Google Cloud": ("status.cloud.google.com",), "AWS": ("aws.amazon.com",),
    "Meta": ("engineering.fb.com",), "Fastly": ("fastly.com",),
    "Dropbox": ("dropbox.tech",), "Atlassian": ("atlassian.com",),
    "Discord": ("discord.com",),
}


class IncidentLibraryError(ValueError):
    """Invalid catalog data or unknown library incident."""


@lru_cache(maxsize=1)
def _load_records() -> tuple[IncidentLibraryRecord, ...]:
    try:
        raw: Any = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise IncidentLibraryError("Catalog must contain a JSON array.")
        records = tuple(IncidentLibraryRecord.model_validate(item) for item in raw)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise IncidentLibraryError("Incident library data is unavailable or invalid.") from error

    seen_ids: set[str] = set()
    seen_identity: set[tuple[str, date, str]] = set()
    verified: list[IncidentLibraryRecord] = []
    for record in records:
        if record.id in seen_ids:
            raise IncidentLibraryError("Catalog contains duplicate incident IDs.")
        identity = (record.company.casefold(), record.incident_date, record.title.casefold())
        if identity in seen_identity:
            raise IncidentLibraryError("Catalog contains duplicate incident identities.")
        seen_ids.add(record.id)
        seen_identity.add(identity)
        for source in record.sources:
            parsed = urlparse(str(source.url))
            if parsed.scheme != "https" or not parsed.netloc:
                raise IncidentLibraryError("Catalog sources must use HTTPS URLs.")
            if record.verification_status == "verified":
                allowed = OFFICIAL_SOURCE_DOMAINS.get(record.company, ())
                hostname = (parsed.hostname or "").lower()
                if not any(hostname == domain or hostname.endswith("." + domain) for domain in allowed):
                    raise IncidentLibraryError("Verified catalog sources must use the company's official domain.")
        if record.verification_status == "verified":
            verified.append(record)
    return tuple(verified)


def clear_catalog_cache() -> None:
    """Clear cached JSON between tests and after local catalog updates."""
    _load_records.cache_clear()
    library_categories.cache_clear()


@lru_cache(maxsize=1)
def library_categories() -> list[str]:
    try:
        categories = json.loads(CATEGORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IncidentLibraryError("Incident category taxonomy is unavailable or invalid.") from error
    if not isinstance(categories, list) or not categories or any(not isinstance(item, str) or not item.strip() for item in categories) or len(set(categories)) != len(categories):
        raise IncidentLibraryError("Incident category taxonomy is invalid.")
    return categories


def list_incidents(
    *,
    page: int = 1,
    limit: int = 12,
    search: str | None = None,
    company: str | None = None,
    category: str | None = None,
    year: int | None = None,
    severity: str | None = None,
    service: str | None = None,
    incident_type: str | None = None,
    verification_status: str = "verified",
) -> dict[str, Any]:
    records = list(_load_records())
    if verification_status != "verified":
        # Non-verified records are intentionally absent from the public catalog.
        return {"items": [], "total": 0, "page": page, "limit": limit}
    normalized_search = (search or "").strip().casefold()
    filters = (
        (company, lambda item: item.company.casefold()),
        (category, lambda item: item.category.casefold()),
        (severity, lambda item: item.severity.casefold()),
        (service, lambda item: " ".join(item.affected_services).casefold()),
        (incident_type, lambda item: item.incident_type.casefold()),
    )
    for expected, getter in filters:
        if expected:
            needle = expected.strip().casefold()
            records = [item for item in records if needle in getter(item)]
    if year is not None:
        records = [item for item in records if item.incident_date.year == year]
    if normalized_search:
        records = [
            item for item in records
            if normalized_search in " ".join((item.title, item.company, item.investigation_summary, *item.symptoms, *item.affected_services)).casefold()
        ]
    records.sort(key=lambda item: (item.incident_date, item.company.casefold(), item.id), reverse=True)
    total = len(records)
    start = (page - 1) * limit
    return {"items": [item.model_dump(mode="json") for item in records[start:start + limit]], "total": total, "page": page, "limit": limit}


def get_incident(incident_id: str) -> IncidentLibraryRecord | None:
    return next((item for item in _load_records() if item.id == incident_id), None)


def catalog_summary(categories: list[str]) -> dict[str, Any]:
    records = _load_records()
    company_counts = Counter(item.company for item in records)
    category_counts = Counter(item.category for item in records)
    year_counts = Counter(item.incident_date.year for item in records)
    years = sorted(year_counts, reverse=True)
    services = sorted({service for item in records for service in item.affected_services}, key=str.casefold)
    incident_types = sorted({item.incident_type for item in records}, key=str.casefold)
    metric_count = sum(bool(item.documented_metrics) for item in records)
    return {
        "verified_incidents": len(records),
        "companies": dict(sorted(company_counts.items())),
        "categories": dict(sorted(category_counts.items())),
        "incidents_with_documented_metrics": metric_count,
        "years": years,
        "year_counts": dict(sorted(year_counts.items(), reverse=True)),
        "services": services,
        "incident_types": incident_types,
        "taxonomy": [
            {"category": category, "verified_incidents": category_counts.get(category, 0), "covered": category_counts.get(category, 0) > 0}
            for category in categories
        ],
    }


def investigation_submission(record: IncidentLibraryRecord) -> dict[str, Any]:
    """Build evidence-only operational incident data; never return the published answer in this payload."""
    metrics: dict[str, str | int | float | bool | None] = {}
    for metric in record.documented_metrics:
        if isinstance(metric.value, (int, float)) and not isinstance(metric.value, bool):
            key = metric.name
            if metric.unit:
                key = f"{key}_{metric.unit}".replace("%", "percent").replace(" ", "_").lower()
            metrics[key] = metric.value
    description = record.investigation_summary
    if record.symptoms:
        description += "\nReported symptoms: " + "; ".join(record.symptoms)
    evidence_text = " ".join((record.title, description, *record.reported_errors)).casefold()
    if record.technical_root_cause and record.technical_root_cause.casefold() in evidence_text:
        raise IncidentLibraryError("Published root cause must not be included in blind investigation evidence.")
    return {
        "title": record.title,
        "description": description,
        "severity": record.severity,
        "service_name": record.affected_services[0],
        "environment": record.environment or "unknown",
        "source": f"real_library:{record.id}"[:50],
        "error_messages": list(record.reported_errors),
        "system_metrics": metrics,
    }
