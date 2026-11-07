# IncidentIQ — Comprehensive System Audit Report

**Audit Date:** 2026-11-06  
**Auditor Roles:** Principal Full-Stack Engineer, Senior QA Automation Architect, SRE Engineer, Security Reviewer  
**Target Environment:** Local Developer & Demonstration Environment  
**Frontend URL:** `http://localhost:5173` (Vite dev server)  
**Backend URL:** `http://127.0.0.1:8001` (FastAPI / Uvicorn)  
**Database:** PostgreSQL (Operational Store)  
**AI Reasoning:** Groq API (`openai/gpt-oss-20b`)  
**Persistent Memory Layer:** Hindsight SDK (`incidentiq-hackathon-demo`)  

---

## 1. Executive Summary

IncidentIQ was audited end-to-end to verify system completeness, architectural integrity, frontend interaction behavior, database schemas, and live integrations with Groq and Hindsight.

The core premise of IncidentIQ is **learning from operational experience**: investigating an incident without prior memory (`MEMORY_OFF`), allowing an engineer to review and explicitly confirm a root cause and resolution, retaining that verified knowledge in Hindsight, and then recalling it in subsequent related investigations (`MEMORY_ON`) so Groq can reason over historical context alongside current evidence.

### Key Audit Findings:
1. **Core Learning Loop Status (Operational & Verified):**
   - The end-to-end learning loop was executed and verified live against the real PostgreSQL database, live Groq API, and live Hindsight bank `incidentiq-hackathon-demo`.
   - Incident A (`INC-20261106-5097574F`) was investigated under `MEMORY_OFF` (0 historical memories recalled).
   - An engineer resolution was confirmed and verified, persisting to PostgreSQL and retaining to Hindsight.
   - Incident B (`0179d48c-ae07-4aba-8ec4-530cd2d0d38f`) was investigated under `MEMORY_ON`. Real Hindsight recall successfully retrieved 6 historical memory records from Incident A.
   - Groq synthesized both current telemetry (connection pool at 95%, Redis p95 latency 360 ms) and historical memories, correctly highlighting the prior worker concurrency exhaustion pattern.
2. **Defect in Hindsight Error Extraction Discovered & Fixed:**
   - In `backend/app/services/hindsight_service.py`, `_safe_error_category()` attempted to extract HTTP status via `getattr(error, "status_code", None)`. However, `hindsight_client_api.exceptions.ApiException` uses `.status` (not `.status_code`). This caused every API error from Hindsight (401, 403, 404, 429, 500) to fall through to `"sdk_error"`.
   - Fixed to inspect both `.status` and `.status_code`.
3. **Running Uvicorn Process Investigation:**
   - Process `42208` (parent monitor) and `43152` (child worker bound to port 8001) were inspected non-destructively.
   - Both belong to the current IncidentIQ backend (`app.main:app --reload --host 127.0.0.1 --port 8001`).
   - When `hindsight_service.py` was updated, Uvicorn's hot reloader reloaded the application, and the live `/health` endpoint immediately switched from `unavailable (sdk_error)` to `reachable (reachable=True)`.
4. **Postmortem Feature Completed (Phase 7):**
   - The Postmortem page was previously an unimplemented static placeholder stating `"Postmortem API is not connected yet"`.
   - The backend database model `Postmortem` existed with 11 columns, but had zero API routes or generation logic.
   - Designed and implemented complete postmortem lifecycle: `POST /api/incidents/{id}/postmortem`, `GET /api/postmortems`, `GET /api/postmortems/{id}`, and `GET /api/postmortems/{id}/download`.
   - Enforced strict safety: Postmortems reject unverified incidents (HTTP 400 `RESOLUTION_REQUIRED`) and strictly isolate unverified AI hypotheses in audit callouts.

---

## 2. Architecture Assessment

```
                      +-----------------------------+
                      | React 18 + Vite (Port 5173) |
                      |    (Tailwind / Custom CSS)   |
                      +--------------+--------------+
                                     |  REST API / CORS
                                     v
                      +-----------------------------+
                      |  FastAPI Monolith (Port 8001)|
                      +-------+------+-------+------+
                              |      |       |
              +---------------+      |       +----------------+
              |                      v                        |
              v             +-----------------+               v
     +-----------------+    | Hindsight Cloud |      +-----------------+
     |   PostgreSQL    |    |   Memory SDK    |      |    Groq Cloud   |
     | (Operational DB)|    | (Persistent KB) |      | (LLM Inference) |
     +-----------------+    +-----------------+      +-----------------+
```

### Architecture Strengths:
- **Clean Separation of Concerns:** PostgreSQL serves as the authoritative operational source of truth; Hindsight acts as contextual associative memory; Groq acts strictly as a reasoning engine.
- **Strict Evidence Provenance:** The codebase explicitly tags every piece of data: `current_incident_evidence`, `historical_hindsight_memory`, `ai_generated_hypothesis`, and `engineer_verified_root_cause`.
- **Human-in-the-Loop Gate:** AI suggestions are never automatically promoted to verified root causes. Confirmation requires explicit human confirmation.

### Architectural Risks & Limitations:
- **Missing Authentication & Authorization:** All endpoints currently accept client-supplied identifiers (`verified_by`, `recorded_by`). There is no JWT/OAuth/session mechanism. (Appropriate for local demonstration, but must be gated before any production deployment).
- **Synchronous Execution:** While FastAPI is async, the routes wrap synchronous database and SDK operations in AnyIO worker threads. Under high concurrency, thread pool limits could cause queuing.

---

## 3. Comprehensive Frontend Interaction Audit

Every visible page and interaction was audited against backend routes and database state.

### Page 1: Command Center (`/` or `page = 'dashboard'`)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Top Metric: Total Incidents | Stat card | `dashboard?.total_incidents` | `GET /api/dashboard/summary` | Displays live count of total incidents | PASS |
| Top Metric: Open Incidents | Stat card | `dashboard?.open_incidents` | `GET /api/dashboard/summary` | Displays count of active open incidents | PASS |
| Top Metric: Resolved | Stat card | `dashboard?.resolved_incidents` | `GET /api/dashboard/summary` | Displays verified resolved incidents | PASS |
| Top Metric: Critical | Stat card | `dashboard?.critical_incidents` | `GET /api/dashboard/summary` | Displays critical incidents count | PASS |
| Button: "New investigation" | Navigates to investigations | `onClick={() => onNavigate('investigate')}` | None | Switches view to Investigations | PASS |
| Chart: Severity Distribution | SVG Donut + bar tracks | Computes percentages from `severity_distribution` | `GET /api/dashboard/summary` | Correctly renders proportional tracks | PASS |
| Platform Status: Hindsight | Service status row | Reads `health.dependencies.hindsight` | `GET /health` | Displays "Reachable" with pulse indicator | PASS |
| Platform Status: Groq | Service status row | Reads `health.dependencies.groq` | `GET /health` | Displays "Reachable" with pulse indicator | PASS |
| Platform Status: Database | Service status row | Reads `health.dependencies.database` | `GET /health` | Displays "Connected" | PASS |
| Table: Recent Incidents | Row selection | `onClick={() => onOpenIncident(incident.id)}` | `GET /api/incidents/{id}` | Navigates to Investigations and loads incident | PASS |
| Button: "View investigations"| Action link | `onClick={() => onNavigate('investigate')}` | None | Navigates to Investigations tab | PASS |
| Button: Topbar Refresh | Refresh icon | `reload()` | Concurrent GETs to summary, incidents, activity, health | Refreshes all metrics and status | PASS |

### Page 2: Investigations (`page = 'investigate'`)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Dropdown: Incident Select | Context selector | `<select>` bound to `selectedIncidentId` | `GET /api/incidents` & `GET /api/incidents/{id}` | Loads full incident evidence, logs, metrics | PASS |
| Mode Toggle: MEMORY_OFF | Radio/segmented button | Sets mode to `'off'` | None | Sets run flag to skip Hindsight recall | PASS |
| Mode Toggle: MEMORY_ON | Radio/segmented button | Sets mode to `'on'` | None | Sets run flag to recall Hindsight memories | PASS |
| Button: "Run investigation" | Dispatches AI analysis | `runInvestigation()` | `POST /api/incidents/{id}/investigate` | Triggers Groq analysis; shows loading ring; renders findings | PASS |
| Button: "Submit incident" | Opens modal form | `setShowForm(true)` | None | Displays incident creation form | PASS |
| Form: "Create incident" | Form submit | Validates and formats JSON payload | `POST /api/incidents` | Successfully persists new incident in PostgreSQL | PASS |
| Form: Engineer Review | Form submit | `submitResolution()` | `POST /api/incidents/{id}/resolve` | Requires confirmed checkbox; saves resolution & retains to Hindsight | PASS |
| Form: Failed Approach | Optional details form | `submitFailedApproach()` | `POST /api/incidents/{id}/failed-approaches` | Retains separate failed troubleshooting memory | PASS |

### Page 3: Guided Hindsight Learning Loop (on Investigations page)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Button: "Create / load historical sample" | Fixture setup | `openSyntheticHistory()` | `GET /api/incidents` & `POST /api/incidents` if missing | Loads Incident A fixture; switches to MEMORY_OFF | PASS |
| Step 01 Pill: Historical incident | Progress indicator | Checks `demo.historicalIncidentId` | Local state | Turns green upon sample creation/load | PASS |
| Step 02 Pill: MEMORY_OFF | Progress indicator | Checks `demo.historicalOffRunId` | Local state | Turns green once MEMORY_OFF investigation finishes | PASS |
| Step 03 Pill: Engineer review | Progress indicator | Checks `demo.historicalRetentionStatus` | `POST /api/incidents/{id}/resolve` response | Turns green upon Hindsight retain success | PASS |
| Button: "Create & investigate related sample" | Follow-up action | `createAndInvestigateFollowUp()` | Creates Incident B & runs `POST .../investigate` (MEMORY_ON) | Disabled until retain succeeds; runs memory recall | PASS |
| Step 04 Pill: Follow-up | Progress indicator | Checks `demo.followUpIncidentId` | Local state | Turns green upon successful MEMORY_ON run | PASS |

### Page 4: Memory Explorer (`page = 'memory'`)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Dropdown: Select Incident | Incident selector | Updates `selectedIncidentId` | None | Triggers memory retrieval hook | PASS |
| Bank Status Badge | Bank badge in header | `hindsightBankLabel(health)` | `GET /health` | Renders `incidentiq-hackathon-demo bank` | PASS |
| Memory Card Grid | Recalled cards | Maps `data.entries` | `GET /api/incidents/{id}/memories` | Renders all 6 recalled memories with tags and IDs | PASS |
| Empty State | Empty display | Rendered when `entries.length === 0` | None | "No relevant memories returned" with no fake memories | PASS |

### Page 5: Memory Comparison (`page = 'compare'`)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Dropdown: Select Incident | Incident selector | Updates `selectedIncidentId` | None | Prepares incident for dual run | PASS |
| Button: "Run comparison" | Dual investigation run | `compare()` | Sequential `POST .../investigate` (MEMORY_OFF then MEMORY_ON) | Executes both runs; displays side-by-side comparison | PASS |
| Footnote Disclaimer | Honesty banner | Static disclaimer text | None | Explicitly states comparison does not claim MTTR reduction | PASS |

### Page 6: Postmortem Center (`page = 'postmortem'`)
| Element / Control | Label / Action | Implementation | API Request | Observed Result | Status |
|---|---|---|---|---|---|
| Button: "Generate postmortem" | Action on eligible incident | `generatePostmortem(id)` | `POST /api/incidents/{id}/postmortem` | Generates structured markdown document in PostgreSQL | PASS |
| Table: Postmortem Archive | Archive listing | Maps `postmortems` | `GET /api/postmortems` | Displays document title, incident, downloads count | PASS |
| Button: "View" | Document viewer | `openPostmortem(id)` | `GET /api/postmortems/{id}` | Opens full document viewer with formatted sections | PASS |
| Toggle: Formatted / Raw | View toggle | `setViewMode()` | None | Switches between styled sections and raw Markdown | PASS |
| Button: "Download .md" | File download | `downloadPostmortem()` | `GET /api/postmortems/{id}/download` | Downloads markdown file attachment with proper filename | PASS |
| Button: "Close" | Closes viewer | `setSelectedPm(null)` | None | Returns to postmortem list | PASS |

---

## 4. Groq & AI Service Audit

- **Configured Model:** `openai/gpt-oss-20b` (fallback: default model in `DEFAULT_GROQ_MODEL`).
- **Structured Output Validation:** AI responses are strictly validated through Pydantic models (`InvestigationAnalysis`, `RootCauseHypothesis`, `RecommendedInvestigationStep`).
- **Prompt Isolation:** Prompts enforce that current incident evidence and historical Hindsight memories are passed as separate tagged sections.
- **Fail-Safe Categorization:** AIServiceError categorizes errors into `authentication_error`, `rate_limited`, `provider_error`, `timeout`, `network_error`, and `malformed_response` without leaking raw keys or tracebacks.

---

## 5. Security & SRE Review

1. **Secret Redaction:**
   - Text redaction regex filters common API key shapes (`gsk_*`, `AKIA*`, `Bearer ...`) before sending to Groq, persisting to audit logs, or retaining in Hindsight.
2. **CORS:**
   - Restricted to `http://localhost:5173`, `http://127.0.0.1:5173`, `http://127.0.0.1:5174`, `http://127.0.0.1:5175`.
3. **Authentication Limitation:**
   - The application does not authenticate users. The `verified_by` field is client-provided. This is documented in the UI and README.
4. **SQL Injection Safety:**
   - All queries use SQLAlchemy 2.0 type-safe expressions and parameterized queries. No raw string interpolation is used.

