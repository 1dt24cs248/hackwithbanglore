# IncidentIQ API

This document describes the FastAPI routes currently implemented in `backend/app/api/routes.py`.

## Base URLs and responses

- Local API base: `http://127.0.0.1:8000`
- JSON API prefix: `/api`
- Health and home routes are outside the `/api` prefix.
- JSON success responses use `{"success": true, "data": ...}`.
- Most errors use FastAPI's `{"detail": {"code": "...", "message": "..."}}` shape. Request validation errors use FastAPI's standard validation details.
- Timestamps are ISO 8601 strings.

## Health and home

### `GET /`

Returns basic application identity and liveness.

### `GET /health`

Returns application status and dependency configuration/connectivity. The health check performs a read-only Hindsight recall and a Groq model-list request. It does not run an AI investigation or retain memory.

Provider errors are returned as safe categories; credentials and raw exception details are not returned.

## Incidents

### `POST /api/incidents`

Creates an incident and submitted evidence. Required fields are `title`, `description`, `severity`, `service_name`, and `environment`.

Optional fields include `owner`, `source`, `error_messages`, `logs`, `deployment`, and `system_metrics`. Log and severity values are validated by the request schema. Common credential-shaped values are rejected.

The response contains `incident_id`, `incident_number`, and `status`.

### `GET /api/incidents`

Lists incidents. Query parameters:

- `page` (default 1, minimum 1)
- `limit` (default 20, range 1–100)
- `status`
- `severity`
- `service_name`

Returns `items`, `total`, `page`, and `limit`.

### `GET /api/incidents/{incident_id}`

Returns incident details, evidence logs, deployments, investigation runs, verified resolutions, and the latest recorded Hindsight retention status for the latest verified resolution. If there is no corresponding retention event, the status is `null`.

## Investigations and engineer review

### `POST /api/incidents/{incident_id}/investigate`

Creates and executes an investigation.

Request:

```json
{"memory_mode": "MEMORY_OFF"}
```

`memory_mode` accepts `MEMORY_OFF`/`off` or `MEMORY_ON`/`on`. MEMORY_OFF skips Hindsight recall. MEMORY_ON must complete Hindsight recall before AI analysis; provider failure is returned as an error rather than a successful empty-memory result.

The response includes the run and incident IDs, memory mode, execution status, model identifier, structured analysis, and recommendation references. AI causes remain hypotheses and recommendations require engineer review.

### `GET /api/investigations/{investigation_id}`

Returns the persisted investigation run, findings and their provenance, historical memory references, and recommendation details.

### `POST /api/investigations/{investigation_id}/feedback`

Records engineer feedback for a recommendation. Required fields: `recommendation_id`, `feedback_type` (`accepted`, `rejected`, or `corrected`), and `created_by`. `comment` is optional except that corrected feedback requires a non-empty comment. `confidence` is optional and must be between 0 and 1.

### `POST /api/incidents/{incident_id}/resolve`

Records an explicitly confirmed engineer-verified resolution, then requests Hindsight retention.

```json
{
  "root_cause_summary": "Verified root cause",
  "resolution_summary": "Applied and verified correction",
  "verified_by": "Engineer display name",
  "confirmed": true,
  "investigation_run_id": "optional-run-uuid"
}
```

The `confirmed` field is mandatory and must be `true`; otherwise the request is rejected. Repeating the same root cause, resolution, and verifier for an incident reuses the existing resolution record. Different verified details create a new resolution revision. Retention status is one of `success`, `skipped_duplicate`, or `failed`.

This endpoint does not authenticate the supplied verifier. The application must remain local and synthetic-data-only until authentication and authorization are implemented.

### `POST /api/incidents/{incident_id}/resolution/retain`

Retries Hindsight retention for the latest resolution already stored as engineer-verified. It does not create another resolution record or accept replacement verification text. Returns the resolution ID and retention status.

### `POST /api/incidents/{incident_id}/failed-approaches`

Requests retention of a separate unsuccessful troubleshooting approach. Required fields: `attempted_action`, `outcome`, and `recorded_by`. `investigation_run_id` is optional.

This route does not create a verified-resolution record. The attempt content is retained by Hindsight; PostgreSQL stores operation metadata, not the failed-approach text. If retention fails, the operation must be retried while the form values remain available; failed-approach content is not durable locally.

## Hindsight memory

### `GET /api/incidents/{incident_id}/memories`

Performs a real Hindsight recall using incident description and technical context. Returns `entries`, including memory ID, type, text summary, context, timestamps, tags, and `historical_hindsight_memory` provenance. A successful empty recall returns an empty list; a provider failure is an error.

### `GET /api/memory/activity?limit=8`

Lists safe memory-operation metadata. `limit` is between 1 and 50. It does not return retained incident or memory text.

Recall results use Hindsight's provider ranking and are passed through as returned; the application does not currently apply a separate score threshold or duplicate filter.

## Dashboard

### `GET /api/dashboard/summary`

Returns incident counts, severity distribution, and status distribution.

## Postmortems

### `POST /api/incidents/{incident_id}/postmortem`

Generates or retrieves a Markdown postmortem from the latest verified resolution. The alias `POST /api/incidents/{incident_id}/postmortems` is also available. A revision is created when the verified resolution or generated document changes; the previous final record is archived rather than deleted.

The Markdown distinguishes engineer-verified facts from unverified AI suggestions. The Hindsight section reports the stored retention status; failed or missing retention is not represented as a successful learning event.

### `GET /api/postmortems`

Lists generated postmortem metadata, including revision and download counts.

### `GET /api/postmortems/{postmortem_id}`

Returns postmortem metadata and `body_markdown`.

### `GET /api/postmortems/{postmortem_id}/download`

Returns the Markdown document as `text/markdown` with an attachment filename and increments the persisted download count. Failure to record the count is reported as an error.

## Error categories and limitations

Expected application error codes include `NOT_FOUND`, `INVALID_INPUT`, `VERIFICATION_REQUIRED`, `HINDSIGHT_UNAVAILABLE`, `GROQ_UNAVAILABLE`, and `DATABASE_UNAVAILABLE`.

The API currently has no authentication or authorization. CORS is not an access-control boundary. Do not expose it publicly or send sensitive production incident data. Automated tests use provider doubles; they do not prove live Groq or Hindsight availability.
