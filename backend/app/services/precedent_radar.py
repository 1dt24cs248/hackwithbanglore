"""Deterministic, explainable lexical ranking for IncidentIQ precedents.

Scores are TF-IDF cosine similarity percentages over the current incident's
reported evidence. The small synonym table normalizes common SRE vocabulary;
it does not infer causes or use an embedding/model.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable


TOKEN_RE = re.compile(r"[a-z][a-z0-9_+-]{1,}")
STOPWORDS = frozenset(
    "a about after all also an and are as at be been before being between by can "
    "caused cause causes customer customers during each from had has have in into "
    "is it its may more most not of on or other outage outages over reported "
    "service services some than that the their them then there these this through "
    "to under was were when where which while with without incident incidents "
    "issue issues failure failures error errors system systems production affected "
    "impact impacted users user company from due following overall global only "
    "high low medium critical actual using use several multiple new existing "
    "disruption disruptions experienced experience recovered recovery available availability "
    "across related current historical unknown data source verified reported company "
    "cloudflare github google amazon aws meta atlassian discord dropbox fastly".split()
)

# Small, explicit normalization set for common infrastructure terminology.
TECHNICAL_SYNONYMS = {
    "db": "database", "postgres": "database", "postgresql": "database",
    "mysql": "database", "sql": "database", "k8s": "kubernetes",
    "conn": "connection", "conns": "connection", "connections": "connection",
    "pooling": "pool", "pools": "pool", "route": "routing", "routes": "routing",
    "router": "routing", "routers": "routing", "routed": "routing",
    "rollout": "deployment", "rollouts": "deployment", "deploy": "deployment",
    "release": "deployment", "releases": "deployment", "config": "configuration",
    "configs": "configuration", "configured": "configuration",
    "auth": "authentication", "login": "authentication", "oauth": "authentication",
    "processor": "cpu", "cores": "cpu", "ram": "memory", "mem": "memory",
    "disk": "storage", "volume": "storage", "filesystem": "storage",
    "cert": "tls", "certificate": "tls", "certificates": "tls",
    "timeout": "timeout", "timeouts": "timeout", "slow": "latency",
    "slowness": "latency", "kafka": "queue", "pubsub": "queue",
    "packetloss": "packet_loss",
}


def tokenize(value: str | None) -> list[str]:
    """Lowercase, normalize selected synonyms, and remove stopwords."""
    if not value:
        return []
    tokens = (TECHNICAL_SYNONYMS.get(token, token) for token in TOKEN_RE.findall(value.lower()))
    return [token for token in tokens if token not in STOPWORDS]


def incident_query_text(incident: Any) -> str:
    """Use observed incident evidence only; intentionally omit root-cause fields."""
    parts = [incident.title, incident.description, incident.service_name]
    parts.extend(log.log_text for log in getattr(incident, "logs", ()))
    for deployment in getattr(incident, "deployments", ()):
        parts.extend((deployment.version or "", deployment.change_summary or ""))
    return " ".join(part for part in parts if part)


def rank_documents(query: str, documents: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Rank documents with binary-query, log-TF, smoothed-IDF cosine similarity."""
    query_counts = Counter(tokenize(query))
    if not query_counts or not documents:
        return []

    document_counts = [Counter(tokenize(item["_search_text"])) for item in documents]
    document_frequency = Counter(
        token for counts in document_counts for token in counts.keys()
    )
    corpus_size = len(document_counts)

    def idf(token: str) -> float:
        return math.log((1 + corpus_size) / (1 + document_frequency[token])) + 1.0

    query_weights = {token: idf(token) for token in query_counts}
    query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
    scored: list[tuple[float, str, dict[str, Any], list[str]]] = []
    for item, counts in zip(documents, document_counts):
        shared = set(query_counts).intersection(counts)
        if not shared:
            continue
        candidate_weights = {
            token: (1.0 + math.log(counts[token])) * idf(token)
            for token in counts
        }
        candidate_norm = math.sqrt(sum(weight * weight for weight in candidate_weights.values()))
        if not candidate_norm or not query_norm:
            continue
        cosine = sum(query_weights[token] * candidate_weights[token] for token in shared)
        score = cosine / (query_norm * candidate_norm)
        if score <= 0:
            continue
        signals = sorted(shared, key=lambda token: (-query_weights[token] * candidate_weights[token], token))
        scored.append((score, str(item.get("id", "")), item, signals[:6]))

    scored.sort(key=lambda row: (-row[0], row[1]))
    results = []
    for score, _identity, item, signals in scored[:limit]:
        result = {key: value for key, value in item.items() if not key.startswith("_")}
        result["relevance_score"] = round(score * 100, 1)
        result["matching_signals"] = signals
        results.append(result)
    return results


def public_documents(records: Iterable[dict[str, Any]], exclude_library_id: str | None = None) -> list[dict[str, Any]]:
    documents = []
    for record in records:
        if exclude_library_id and record.get("id") == exclude_library_id:
            continue
        source = next(iter(record.get("sources") or []), {})
        search_fields = [
            record.get("title", ""), record.get("company", ""),
            record.get("category", ""), record.get("incident_type", ""),
            record.get("investigation_summary", ""), record.get("technical_root_cause", ""),
            *record.get("affected_services", []), *record.get("symptoms", []),
            *record.get("reported_errors", []), *record.get("infrastructure", []),
            *record.get("dependencies", []), *record.get("tags", []),
        ]
        documents.append({
            "id": record.get("id"),
            "title": record.get("title"),
            "company": record.get("company"),
            "incident_date": record.get("incident_date"),
            "category": record.get("category"),
            "technical_root_cause": record.get("technical_root_cause"),
            "recovery_actions": record.get("recovery_actions", []),
            "preventive_actions": record.get("preventive_actions", []),
            "source_url": source.get("url"),
            "_search_text": " ".join(str(field) for field in search_fields if field),
        })
    return documents

def workspace_documents(incidents: Iterable[Any], current_incident_id: Any) -> list[dict[str, Any]]:
    documents = []
    for incident in incidents:
        if incident.id == current_incident_id or incident.status != "resolved":
            continue
        resolutions = sorted(
            getattr(incident, "verified_resolutions", ()),
            key=lambda item: (
                item.verified_at.replace(tzinfo=timezone.utc)
                if item.verified_at and item.verified_at.tzinfo is None
                else item.verified_at.astimezone(timezone.utc)
                if item.verified_at else datetime.min.replace(tzinfo=timezone.utc),
                str(item.id),
            ),
            reverse=True,
        )
        if not resolutions:
            continue
        resolution = resolutions[0]
        root_cause = resolution.root_cause_summary
        resolution_summary = resolution.resolution_summary
        search_fields = [
            incident.title, incident.description, incident.service_name,
            root_cause, resolution_summary,
            *(log.log_text for log in getattr(incident, "logs", ())),
            *(deployment.change_summary or "" for deployment in getattr(incident, "deployments", ())),
        ]
        documents.append({
            "id": str(incident.id),
            "title": incident.title,
            "incident_number": incident.incident_number,
            "verified_root_cause": root_cause,
            "verified_resolution": resolution_summary,
            "verification_status": "verified",
            "verified_at": resolution.verified_at.isoformat() if resolution.verified_at else None,
            "memory_retention_status": None,
            "_resolution_id": resolution.id,
            "_resolution_count": len(resolutions),
            "_search_text": " ".join(str(field) for field in search_fields if field),
        })
    return documents
