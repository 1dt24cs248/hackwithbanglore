"""Read-only, version-controlled catalog of verified production incidents."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
import re
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


def relationship_graph(max_patterns: int = 8) -> dict[str, Any]:
    """Build evidence-backed bipartite links from exact infrastructure/category fields."""
    records = _load_records()
    pattern_records: dict[tuple[str, str], dict[str, Any]] = {}
    record_patterns: dict[str, list[tuple[str, str]]] = {}

    for record in records:
        keys: list[tuple[str, str]] = []
        for component in record.infrastructure:
            label = component.strip()
            key = ("infrastructure", label.casefold())
            if label and key not in keys:
                keys.append(key)
                pattern_records.setdefault(key, {"label": label, "records": []})["records"].append(record)
        category_label = record.category.strip()
        category_key = ("category", category_label.casefold())
        if category_label:
            keys.append(category_key)
            pattern_records.setdefault(category_key, {"label": category_label, "records": []})["records"].append(record)
        record_patterns[record.id] = keys

    patterns = [
        (key, entry)
        for key, entry in pattern_records.items()
        if len(entry["records"]) >= 2
    ]
    patterns.sort(key=lambda item: (
        -len(item[1]["records"]),
        0 if item[0][0] == "infrastructure" else 1,
        item[1]["label"].casefold(),
        item[1]["label"],
    ))
    patterns = patterns[:max_patterns]

    def slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unnamed"

    pattern_nodes: list[dict[str, Any]] = []
    pattern_ids: dict[tuple[str, str], str] = {}
    for key, entry in patterns:
        pattern_type, _normalized = key
        label = entry["label"]
        node_id = f"{'infra' if pattern_type == 'infrastructure' else 'cat'}:{slug(label)}"
        pattern_ids[key] = node_id
        infrastructure = pattern_type == "infrastructure"
        pattern_nodes.append({
            "id": node_id,
            "node_type": "pattern",
            "label": label,
            "pattern_type": pattern_type,
            "incident_count": len(entry["records"]),
            "relation": "shared_infrastructure" if infrastructure else "same_category",
            "evidence_basis": "documented_infrastructure" if infrastructure else "library_category",
        })

    selected_keys = set(pattern_ids)
    related_by_incident: dict[str, list[dict[str, Any]]] = {record.id: [] for record in records}
    edges: list[dict[str, str]] = []
    for key, entry in patterns:
        pattern_type, _normalized = key
        label = entry["label"]
        related_records = sorted(
            entry["records"],
            key=lambda record: (record.incident_date, record.company.casefold(), record.id),
        )
        relation = "shared_infrastructure" if pattern_type == "infrastructure" else "same_category"
        evidence_basis = "documented_infrastructure" if pattern_type == "infrastructure" else "library_category"
        if pattern_type == "infrastructure":
            evidence = f"Both reports list '{label}' as affected infrastructure."
        else:
            evidence = f"Both incidents are filed under the library category '{label}'."
        related_ids = [record.id for record in related_records]
        for record in related_records:
            related_by_incident[record.id].append({
                "relation": relation,
                "pattern_label": label,
                "evidence": evidence,
                "related_incident_ids": [item for item in related_ids if item != record.id][:5],
            })
            edges.append({
                "source": record.id,
                "target": pattern_ids[key],
                "relation": relation,
                "evidence": evidence,
                "evidence_basis": evidence_basis,
            })

    connected_records = [record for record in records if related_by_incident[record.id]]
    pattern_order = {key: index for index, (key, _entry) in enumerate(patterns)}
    connected_records.sort(key=lambda record: (
        min(pattern_order[key] for key in record_patterns[record.id] if key in selected_keys),
        record.title.casefold(),
        record.id,
    ))
    incident_nodes = []
    for record in connected_records:
        source = next(iter(record.sources), None)
        incident_nodes.append({
            "id": record.id,
            "node_type": "incident",
            "title": record.title,
            "company": record.company,
            "incident_date": record.incident_date.isoformat(),
            "category": record.category,
            "technical_root_cause": record.technical_root_cause or None,
            "source_url": str(source.url) if source else None,
            "relationships": related_by_incident[record.id],
        })

    return {
        "nodes": [*pattern_nodes, *incident_nodes],
        "edges": edges,
        "patterns_shown": len(pattern_nodes),
        "incidents_shown": len(incident_nodes),
        "total_library_incidents": len(records),
        "legend_note": "Relationships come from documented infrastructure and library categories, not from similar wording. Root causes are shown for reading, not used to link incidents.",
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
