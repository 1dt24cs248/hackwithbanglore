# API Contract

## 1. API conventions
- Base URL: `http://localhost:8000/api/v1`
- Format: JSON
- Content-type: `application/json`
- Timestamps: ISO 8601 with timezone
- Errors returned with standard error envelope

## 2. Health endpoint
### GET /health
Purpose: verify backend and dependency health.

Response:
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": "connected",
    "hindsight": "connected",
    "groq": "available"
  }
}
```

## 3. Incident submission
### POST /incidents
Purpose: create a new incident record.

Request body:
```json
{
  "title": "Payment API latency spike",
  "description": "Request latency increased after deployment.",
  "service_name": "payment-api",
  "environment": "production",
  "severity": "high",
  "owner": "maya",
  "source": "web",
  "logs": [
    {"log_type": "error", "log_text": "timeout after 4s", "source_system": "api"}
  ],
  "deployment": {
    "deployment_id": "deploy-1048",
    "version": "v2.7.1",
    "deployed_by": "eng-team",
    "deployed_at": "2026-11-05T10:15:00Z"
  }
}
```

Response:
```json
{
  "success": true,
  "data": {
    "incident_id": "uuid",
    "incident_number": "INC-20261105-0001",
    "status": "open"
  }
}
```

Validation:
- required title, description, service_name, environment, severity
- severity must be one of critical, high, medium, low

## 4. Investigation run creation
### POST /incidents/{incident_id}/investigations
Purpose: create a new investigation execution for an incident.

Request body:
```json
{
  "memory_mode": "on",
  "model_identifier": "openai/gpt-oss-120b",
  "include_historical_matches": true
}
```

Response:
```json
{
  "success": true,
  "data": {
    "id": "inv-run-uuid",
    "incident_id": "incident-uuid",
    "memory_mode": "on",
    "execution_status": "running",
    "created_at": "2026-11-05T10:20:00Z"
  }
}
```

Relevant behaviour:
- memory_mode must be `off` or `on`
- the backend creates an `investigation_runs` row before executing analysis
- `memory_mode=on` executes real Hindsight recall
- `memory_mode=off` skips Hindsight recall

## 5. Investigation run retrieval
### GET /incidents/{incident_id}/investigations
Purpose: retrieve historical investigation runs for an incident.

Query params:
- page
- limit
- execution_status

Response:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "inv-run-uuid",
        "memory_mode": "on",
        "model_identifier": "openai/gpt-oss-120b",
        "execution_status": "succeeded",
        "created_at": "2026-11-05T10:20:00Z"
      }
    ],
    "total": 1
  }
}
```

## 6. Incident analysis
### POST /incidents/{incident_id}/investigations/{investigation_id}/analyse
Purpose: run the investigation logic for a specific incident and recorded investigation execution.

Request body:
```json
{
  "memory_mode": "on",
  "include_historical_matches": true
}
```

Response:
```json
{
  "success": true,
  "data": {
    "investigation_id": "inv-run-uuid",
    "incident_id": "incident-uuid",
    "memory_mode": "on",
    "execution_status": "succeeded",
    "summary": "Database latency increased after deployment and queue backlogs suggest connection pool exhaustion.",
    "current_evidence": ["error:timeout after 4s", "deploy-1048"],
    "historical_memory_refs": ["hindsight:incident-201", "hindsight:resolution-77"],
    "likely_root_causes": [
      {
        "rank": 1,
        "cause": "Connection pool exhaustion after deployment",
        "confidence": 0.87,
        "provenance": "AI_GENERATED_HYPOTHESIS",
        "evidence": ["current_evidence:timeout after 4s", "historical_memory:incident-201"]
      }
    ],
    "recommendations": [
      {
        "title": "Scale worker pool and validate timeout thresholds",
        "source": "historical_memory",
        "confidence": 0.83,
        "provenance": "HISTORICAL_MEMORY",
        "supporting_evidence": ["hindsight:incident-201", "hindsight:resolution-77"]
      }
    ]
  }
}
```

Relevant behaviour:
- the system stores a new investigation run record before the execution starts
- memory_mode `off` never executes Hindsight `recall()`
- memory_mode `on` executes real Hindsight `recall()` and passes those references to the LLM
- recommendation provenance must indicate whether it is based on current evidence, historical memory, AI hypothesis, or verified root cause

## 7. Incident resolution
### POST /incidents/{incident_id}/resolve
Purpose: finalise a verified resolution.

Request body:
```json
{
  "root_cause_summary": "Worker pool saturation caused queue backlog after deployment.",
  "resolution_summary": "Scaled workers and rolled back incompatible change.",
  "verification_status": "verified",
  "engineer": "maya"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "incident_id": "uuid",
    "status": "resolved",
    "resolved_at": "2026-11-05T11:45:00Z"
  }
}
```

Relevant operations:
- retains verified resolution in Hindsight
- stores memory event in PostgreSQL

## 6. Incident listing
### GET /incidents
Purpose: list incidents with optional filters.

Query params:
- status
- severity
- service_name
- page
- limit

Response:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "incident_number": "INC-20261105-0001",
        "title": "Payment API latency spike",
        "status": "resolved",
        "severity": "high",
        "service_name": "payment-api",
        "created_at": "2026-11-05T09:12:00Z"
      }
    ],
    "total": 1
  }
}
```

## 7. Incident detail
### GET /incidents/{incident_id}
Purpose: return the full incident record and context.

Response:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Payment API latency spike",
    "status": "resolved",
    "root_cause_summary": "Worker pool saturation caused queue backlog after deployment.",
    "logs": [
      {"log_type": "error", "log_text": "timeout after 4s"}
    ]
  }
}
```

## 8. Hindsight memory recall
### GET /memory/recall
Purpose: return recalled Hindsight memories for a context.

Query parameters:
- service_name
- incident_summary
- memory_types

Response:
```json
{
  "success": true,
  "data": {
    "entries": [
      {
        "memory_type": "resolution",
        "summary": "Increase worker pool before retrying a deploy with incompatible timeouts.",
        "related_incident": "INC-20251111-0020",
        "confidence": 0.91
      }
    ]
  }
}
```

## 9. Memory operation history
### GET /memory/history
Purpose: show memory operations for an incident or service.

Response:
```json
{
  "success": true,
  "data": {
    "entries": [
      {"operation_name": "recall", "status": "success", "memory_type": "failure"},
      {"operation_name": "retain", "status": "success", "memory_type": "resolution"}
    ]
  }
}
```

## 10. Memory Off vs Memory On
### POST /incidents/{incident_id}/compare-memory
Purpose: compare analysis executed without Hindsight against the same incident analysed with Hindsight.

Request body:
```json
{
  "service_name": "payment-api",
  "include_historical_matches": true
}
```

Response:
```json
{
  "success": true,
  "data": {
    "memory_off": {
      "investigation_id": "off-run-uuid",
      "summary": "Observations point to deployment-induced timeout saturation.",
      "recommendations": [{"title": "Check DB timeout threshold", "provenance": "AI_GENERATED_HYPOTHESIS"}]
    },
    "memory_on": {
      "investigation_id": "on-run-uuid",
      "summary": "Historical memory shows a previous deployment with similar symptoms and a verified resolution involving worker pool scaling.",
      "recommendations": [{"title": "Scale worker pool and verify rollback path", "provenance": "HISTORICAL_MEMORY"}],
      "historical_memory_refs": ["hindsight:incident-201"]
    },
    "delta_summary": "The memory-on path includes documented historical evidence and matches a previous verified pattern; the comparison is descriptive only and does not claim a measured performance improvement."
  }
}
```

This comparison must use the same incident context, the same model configuration, and separate investigation runs. It must not claim improved confidence or MTTR without a measured benchmark.

## 11. Recurrence detection
### GET /incidents/recurrence
Purpose: identify possible recurring incident patterns.

Response:
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "service_name": "payment-api",
        "risk_level": "moderate",
        "similar_incidents": ["INC-20261103-0009", "INC-20260921-0082"],
        "summary": "Similar latency spikes occurred after deployment changes."
      }
    ]
  }
}
```

## 12. Learning timeline
### GET /incidents/{incident_id}/timeline
Purpose: show a timeline of events and memory operations.

Response:
```json
{
  "success": true,
  "data": {
    "timeline": [
      {"time": "2026-11-05T09:10:00Z", "type": "incident_created", "detail": "Incident submitted."},
      {"time": "2026-11-05T10:05:00Z", "type": "memory_recall", "detail": "Retrieved 3 relevant entries."},
      {"time": "2026-11-05T11:40:00Z", "type": "resolution_verified", "detail": "Root cause confirmed."}
    ]
  }
}
```

## 13. Analytics
### GET /analytics/dashboard
Purpose: provide summary metrics for dashboard cards.

Response:
```json
{
  "success": true,
  "data": {
    "total_incidents": 124,
    "open_incidents": 18,
    "resolved_incidents": 98,
    "critical_incidents": 8,
    "severity_distribution": {"critical": 8, "high": 20, "medium": 34, "low": 62}
  }
}
```

## 14. Guided demo
### GET /demo/session
Purpose: start a demo flow with synthetic data.

Response:
```json
{
  "success": true,
  "data": {
    "mode": "synthetic",
    "incident_id": "demo-001",
    "steps": ["submit", "analyse", "compare-memory", "retain", "review"]
  }
}
```

## 15. Postmortem generation
### POST /incidents/{incident_id}/postmortem
Purpose: generate markdown postmortem for a validated incident.

Response:
```json
{
  "success": true,
  "data": {
    "postmortem_id": "uuid",
    "title": "Payment API Latency Spike",
    "status": "draft"
  }
}
```

## 16. Postmortem download
### GET /postmortems/{postmortem_id}/download
Purpose: download markdown output.

Response headers:
- `Content-Type: text/markdown`

## 17. External contract details
### Groq contract
- input: structured prompt with incident and evidence context
- output: summary, likely causes, and recommendations
- failure modes: request timeout, malformed JSON, rate limit

### Hindsight contract
- input: `retain()` or `recall()` with context and memory payload
- output: memory entry or list of entries
- failure modes: empty result, API error, invalid memory type

## 18. Error envelope
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Severity must be one of critical, high, medium, low.",
    "details": ["severity"]
  }
}
```

## 19. Authentication
The MVP and local demo can operate without formal auth. If auth is added later, the backend must enforce it and the frontend must never receive raw credentials or secret material.

## 20. Summary
The API design keeps the incident lifecycle explicit and the memory layer separate. PostgreSQL stores structured operational history, while Hindsight provides persistent recall and reasoning context. All outputs remain evidence-backed and user-verifiable.
