# IncidentIQ Comprehensive Repository Audit

**Audit date:** 2026-11-06  
**Scope:** Read-only review of the frontend, backend, configuration, persistence, integrations, documentation, and existing automated tests. No application source, environment configuration, or Git history was changed. The requested report is the only authored project document; Vite emitted its normal `frontend/dist` build output.

**Follow-up status:** This report records the findings before the subsequent configuration and provider-diagnostics implementation. The bank label/default and unchecked provider-health findings below are historical audit observations; they have since been addressed in application code and `project-docs/API.md`.

## Executive summary

The central incident learning loop is substantially implemented: incidents and evidence are persisted in PostgreSQL; separate `MEMORY_OFF` and `MEMORY_ON` investigation runs are recorded; the memory-on path calls Hindsight before Groq; generated causes remain hypotheses; an explicit confirmation workflow stores a verified resolution and requests Hindsight retention; and synthetic demo fixtures are labeled and reused rather than seeded automatically.

The most visible reported defect is a **frontend-only Hindsight bank label**. Current backend settings load `incidentiq-hackathon-demo`, and the running API reports Hindsight configured. The Memory Explorer hard-codes `incidentiq-demo` in its display. The actual Hindsight service receives the configured bank ID from the FastAPI lifespan, so the label does not prove that requests are using the wrong bank. A default/fallback of `incidentiq-demo` remains in backend code and documentation, which is a separate drift risk if configuration is absent or a service is instantiated without an explicit bank.

Memory Explorer's error is generated when its real recall call fails. Memory Comparison's generic dependency message is returned for Hindsight or Groq failures. The live `/health` response says both credentials are configured but their services are `not_checked`; database connectivity is confirmed. Because the audit was required to be read-only, no memory recall or investigation was triggered to probe provider state: the memory route writes an audit event and investigation would create a run. The exact live provider failure cause therefore remains unverified.

Postmortems are not connected because the backend has a postmortem table/model but no postmortem routes or service, and the page is an intentional placeholder. The project API documentation is stale and does not match the implemented route paths or payloads. Authentication is absent; the verified-resolution request's checkbox and typed verifier name are client-supplied and do not establish identity. Keep this application local and use synthetic data only.

Backend tests passed in the repository virtual environment (**58 passed, 2 subtests, 1 deprecation warning**). The Vite production build passed. No Playwright setup or frontend tests are present.

## 1. Architecture overview

| Layer | Current implementation | Assessment |
|---|---|---|
| Frontend | Single-page React application in `frontend/src/App.jsx`, Vite, Lucide icons, hand-authored CSS in `styles.css` | All requested screens are client-side views controlled by `page` state; no router or separate page/component tree. No Tailwind dependency or configuration is present despite the stated stack. |
| API | FastAPI app in `backend/app/main.py`; routes in `backend/app/api/routes.py`, prefix `/api` | Modular monolith with synchronous SQLAlchemy service calls. CORS is limited to several localhost origins. |
| Operational store | SQLAlchemy models and one Alembic initial migration; PostgreSQL URL support, with SQLite for isolated tests | Incidents, evidence, investigations, findings, feedback, verified resolutions, memory operation metadata, and postmortem records have models/tables. |
| AI | `GroqAIService` with injected lifespan-managed Groq client and Pydantic structured-output validation | Calls Groq after checking the configured model against the account model list. Failure categories are intentionally sanitized. |
| Memory | `HindsightMemoryService` around `hindsight-client`; configured bank injected by app lifespan | Real `recall()` and `retain()` calls are present. Memory OFF bypasses recall. Verified resolution and failed approach are distinct retain categories. |
| Tests | pytest/unittest tests for services, API, database, configuration, and integrations using mocks | Useful backend coverage; no browser/UI automation. Tests do not establish live Groq/Hindsight availability. |

The Vite config sets port `5174` with `strictPort: true`; the reported frontend URL is `localhost:5173`. CORS allows both `5173` and `5174`. The frontend API base defaults to `http://127.0.0.1:8001/api`, matching the reported backend port.

## 2. Feature implementation matrix

| Screen / feature | Current implementation | Status / gap |
|---|---|---|
| Command Center | Fetches dashboard summary, incident list, memory activity and health; shows metrics, severity distribution, recent incidents, session runs, memory activity and service state | Implemented. Run history is only in React session state; refresh loses it even though a run retrieval API exists. Health is liveness/configuration oriented, not a live Groq or Hindsight readiness check. |
| Investigations | Incident selector, incident form, evidence display, MEMORY_OFF/ON switch, investigation action, findings/provenance, recommendation list, review and resolution workflow | Core path implemented. A real dependency failure returns an error; no mock findings are fabricated. Frontend selects MEMORY_ON by default. |
| Memory Explorer | Selects an incident and calls `GET /api/incidents/{id}/memories`; renders actual Hindsight results or error/empty state | Recall path is connected. Displayed bank name is stale/hard-coded. No retry control is shown after a recall failure beyond reselecting an incident. |
| Postmortems | Static “Postmortem API is not connected yet” placeholder | Not implemented end-to-end. Models/table exist; no service, routes, list/detail/generate/download endpoints, or UI actions. |
| Memory Comparison | Runs one MEMORY_OFF request followed by one MEMORY_ON request for the same incident; displays both outputs if both succeed | Implemented as two sequential actual runs; no result is shown until both succeed. Error explicitly explains the partial case. Does not claim accuracy or MTTR gains. |
| Guided Hindsight Learning Loop | Creates/reuses exact synthetic historical fixture; guides MEMORY_OFF, engineer review/retain, then creates/reuses follow-up and runs MEMORY_ON | Core path implemented and clearly synthetic. Follow-up is disabled until an off run and successful or duplicate-skipped retain are recorded. Local browser storage is convenience state, not source of truth. |

### Reported UI errors

| UI message | Source and explanation |
|---|---|
| Memory Explorer: “Historical memory could not be retrieved.” | The `GET /api/incidents/{incident_id}/memories` route calls real Hindsight recall. If `RecallResult.status != "success"`, it returns HTTP 503 with this generic message. The service safely stores an error category in `memory_operation_events`, but the UI/API response does not expose that category. The actual current provider error cannot be determined from `/health`, which only reports Hindsight as configured/not checked. |
| Memory Comparison: “An investigation dependency is unavailable.” | `_fail()` maps `hindsight_*` and `groq_*` service categories to HTTP 503 and this message. The route itself is present and correctly addressed. Current `/health` does not check either provider, so this generic response does not identify which dependency or failure class. |
| Postmortems: “Postmortem API is not connected yet.” | This is literal placeholder UI. No backend Postmortem endpoints are registered. The database model is not an API implementation. |

## 3. Complete visible button functionality matrix

Locations refer to `frontend/src/App.jsx`. Repeated calls to the same page/navigation action are grouped where they share one handler.

| Visible button label | Component / location | Handler and expected action | API | Current status |
|---|---|---|---|---|
| Close navigation (icon) | App sidebar | `setMobileNav(false)` | None | Works; UI-only. |
| Command center; Investigations; Memory explorer; Postmortems; Memory comparison | App navigation | Sets current page and closes mobile navigation | Page-specific requests on page render/selection | Works; memory comparison is the `compare` view. |
| Close navigation (scrim) | App mobile overlay | `setMobileNav(false)` | None | Works; UI-only. |
| Open navigation (icon) | App top bar | `setMobileNav(true)` | None | Works; UI-only. |
| Refresh data (icon) | App top bar | `reload()` | GET dashboard summary, incidents, memory activity, health | Works; concurrent fetch. Errors in summary/list surface; memory/health failures do not produce the global load error. |
| Retry | App global error banner | `reload()` | Same as Refresh data | Works. |
| Dismiss (toast icon) | App toast | Clears toast state | None | Works; UI-only. |
| New investigation; Submit your first incident; View investigations; Create incident; Start an investigation; Start an investigation (placeholder); Explore memory; Continue investigation | Dashboard / Investigation empty or ready states / Memory Explorer | Navigates to investigations, opens form, or opens Memory Explorer as labelled | May cause page-load GETs; no immediate write | Works as navigation affordances. |
| Incident table row | Dashboard (clickable `<tr>`, not a `<button>`) | Selects incident and opens Investigations | GET incident detail on selection | Works with mouse; not keyboard-semantic as a button/interactive row. |
| Submit incident | Investigations heading | Toggles incident form visibility | None until form submit | Works. |
| Create / load historical sample | Guided demo | `openSyntheticHistory()`; reuses stored or exact server-confirmed synthetic record, otherwise creates it; selects MEMORY_OFF | GET incidents/detail; POST `/api/incidents` only if no matching fixture | Works; real writes are explicitly initiated and synthetic. |
| Create & investigate related sample | Guided demo | `createAndInvestigateFollowUp()` after verified retention gate | GET/POST incident as needed; POST `/api/incidents/{id}/investigate` MEMORY_ON | Works when prerequisites succeed; button is correctly disabled before retain. |
| MEMORY_OFF; MEMORY_ON | Investigation mode selector | Changes local mode | None | Works; mode label maps to backend enum values. |
| Run investigation | Investigation toolbar | `runInvestigation()` for selected incident/mode | POST `/api/incidents/{id}/investigate` | Works when DB, configured Groq, and (for ON) Hindsight are available. Errors are surfaced. |
| Submit incident (empty state) | Investigation empty state | Opens incident form | None | Works. |
| Close form (icon); Cancel | Incident form | `onCancel`, closes form | None | Works. |
| Create incident | Incident form submit | Validates metrics JSON, submits payload and selects new incident | POST `/api/incidents` | Works; service, severity and environment defaults are provided. No client-side sensitive-text scan; backend performs validation. |
| Confirm verified resolution | Engineer Review form submit | Sends root cause, resolution, typed name, checkbox confirmation, run ID; updates detail and dashboard | POST `/api/incidents/{id}/resolve` | Works functionally; critical trust limitation: name/confirmation are caller-controlled and API has no authentication. Backend persists resolution before attempting retain; a retain failure still leaves the resolution recorded and is shown accurately. |
| Record an unsuccessful troubleshooting approach | Engineer Review optional form submit | Sends action, outcome, typed name and run ID | POST `/api/incidents/{id}/failed-approaches` | Works; retains separately as failure memory. Name also unauthenticated. |
| Run comparison | Memory Comparison | Runs OFF then ON sequentially; only sets visible comparison after both succeed | Two POSTs to `/api/incidents/{id}/investigate` | Works; if second request fails, first run remains persisted but UI reports incomplete comparison. |
| Dismiss toast / Close navigation / Refresh controls | Shared chrome | Local state or reload | As above | No dead button handlers found. |

Other controls: incident and memory selectors update selected IDs; form fields update component state; confirmation checkbox gates resolution submission; `<details>` expands failed-approach form. Postmortems has no action buttons. Memory Explorer has no retry button. No visible button submits feedback even though a feedback API route exists.

## 4. Frontend API call vs backend route audit

All API calls made by the current frontend map to a registered backend route and use the expected method. No frontend call targets a missing route. `api()` unwraps the standard `{success, data}` envelope and parses safe error details.

| Frontend call | Backend route | Method / payload | Assessment |
|---|---|---|---|
| `/health` (special-cased to API origin) | `/health` | GET | Matches. Liveness and dependency configuration only; not provider readiness. |
| `/dashboard/summary` | `/api/dashboard/summary` | GET | Matches. |
| `/incidents?page=1&limit=30` (other pages use 100) | `/api/incidents` | GET, query `page`, `limit` | Matches. Backend max limit 100. |
| `/incidents` | `/api/incidents` | POST `IncidentSubmission` | Matches form and synthetic fixture fields; unsupported fields are forbidden. |
| `/incidents/{id}` | `/api/incidents/{incident_id}` | GET | Matches. |
| `/incidents/{id}/investigate` | `/api/incidents/{incident_id}/investigate` | POST `{memory_mode: MEMORY_OFF|MEMORY_ON}` | Matches; schema accepts those values and normalizes them. |
| `/incidents/{id}/resolve` | `/api/incidents/{incident_id}/resolve` | POST `root_cause_summary`, `resolution_summary`, `verified_by`, `confirmed`, optional `investigation_run_id` | Matches request schema. Trust concern is authorization, not payload shape. |
| `/incidents/{id}/failed-approaches` | `/api/incidents/{incident_id}/failed-approaches` | POST `attempted_action`, `outcome`, `recorded_by`, optional run ID | Matches. |
| `/incidents/{id}/memories` | `/api/incidents/{incident_id}/memories` | GET | Matches; makes a new real recall and records a metadata event. |
| `/memory/activity?limit=8` | `/api/memory/activity` | GET | Matches. |

### Backend routes with no current frontend consumer

| Backend route | Status |
|---|---|
| `GET /` | Simple API welcome/status response; no frontend consumer. |
| `GET /api/investigations/{investigation_id}` | Implemented, but dashboard/reload does not use it; runs are not recovered after a browser refresh. |
| `POST /api/investigations/{investigation_id}/feedback` | Implemented, but there is no feedback UI control. |

### Missing backend capabilities documented or implied elsewhere

There are no routes for postmortem generation/list/detail/download, incident investigation-run listing, recurrence, timeline, or postmortem editing. The documented API in `project-docs/API.md` describes a different contract in multiple areas: it says `/api/v1`, uses alternate investigation path names and payloads, and describes memory/analytics/demo/postmortem endpoints that are not registered. The real route prefix is `/api` and the route inventory is the OpenAPI inventory at audit time.

## 5. Hindsight integration assessment

- The backend settings loader in this workspace resolves to bank ID **`incidentiq-hackathon-demo`**. The running `/health` endpoint says the Hindsight credential is configured, but does not expose bank metadata; the already-running process's exact bank value is therefore not independently attested by an endpoint.
- `main.py` constructs `HindsightMemoryService(..., bank_id=settings.hindsight_bank_id)`. Actual recall/retain calls use `self._bank_id`; therefore the active settings value is passed to SDK calls.
- `frontend/src/App.jsx` hard-codes **`incidentiq-demo bank`** for the Memory Explorer display. This is a frontend presentation defect, not evidence that the configured request bank is wrong.
- `backend/app/config.py`, `.env.example`, README, service `BANK_ID`, and a few fallback result constructors still default/report `incidentiq-demo`. The explicit live setting currently overrides the service constructor default, but fallback/default drift should be cleaned up and the bank name should be exposed safely from backend configuration rather than duplicated in UI code.
- MEMORY_OFF creates and persists a run but does not call recall. MEMORY_ON calls real recall before Groq; recall failure marks the run failed and is not passed off as empty successful memory.
- Memory Explorer independently calls real recall and distinguishes success with no results from failed recall. Errors are generic to the frontend; safe error categories are recorded in metadata where possible.
- Verified-resolution retain requires `confirmed=True` at service level, a non-empty verifier display name, and non-empty root cause/resolution. Hindsight retain is only attempted in that workflow. The API does **not** authenticate the confirmer, so this is an explicit workflow safeguard, not trustworthy identity verification.
- Stable document IDs and an in-process duplicate guard are used. Idempotency protection is process-local; concurrent workers/restarts may still rely on Hindsight's document ID semantics, and the same in-memory set does not provide a database-backed cross-process lock.
- The Hindsight smoke test is opt-in for retain and does not run with normal pytest collection due provider dependencies; no live provider operation was run during this audit.

## 6. Groq integration assessment

- Groq client is created and owned by FastAPI lifespan; missing credentials do not break API startup, but investigation returns a dependency error.
- The service checks the selected model against the account's live model list on first use and validates returned JSON against Pydantic models. It rejects malformed output and unknown evidence/memory references rather than inventing fallback content.
- Prompts separate current evidence, historical memories, and engineer-verified findings; generated root causes are explicitly hypotheses. Common credential patterns are redacted before prompt submission and from model output.
- Provider error categories are sanitized; no raw provider exception text is returned to clients.
- Health only reports configured/not configured, not current network/model readiness. The live response showed Groq configured but not checked. No live Groq investigation was triggered.
- Test coverage mocks the SDK; it verifies service logic but cannot claim provider access or model availability.

## 7. Database and migration assessment

- Models include `incidents`, `incident_logs`, `deployments`, `investigation_runs`, `investigation_findings`, `engineer_feedback`, `verified_resolutions`, `memory_operation_events`, and `postmortems`.
- The single initial Alembic migration creates these tables with useful foreign keys, check constraints, indexes, provenance and verification constraints, and safe-reference metadata fields. Migration tests apply it against isolated SQLite; live backend health confirms configured DB connection (`SELECT 1`).
- Incident creation commits incident, logs, metrics, and optional deployment in one transaction. Investigation runs are created before provider calls, updated to running/failed/succeeded, and findings are committed after successful analysis. Verified resolution is committed before the external Hindsight retain call, which is necessary to preserve the engineer record if memory is down; the outcome is then recorded as a memory event.
- Memory audit rows store summary/count and safe error category rather than raw memory content; model validation and database checks reject common credential markers. Memory Explorer results themselves are returned to the caller, as expected for inspection.
- Postmortem persistence is schema-only. No business logic or routes manage revisions or downloads despite the schema supporting revisions and a single final postmortem.
- Live production database schema version/migration head and data quality were not inspected; no migration command was run. Health confirms connectivity only.

## 8. Security findings

| Severity | Finding | Evidence / impact |
|---|---|---|
| Critical before public deployment | No authentication or authorization on incident, investigation, feedback, resolution, memory, and dashboard routes | Any network-reachable caller can read incident data, create incidents/runs, trigger provider costs, and submit resolution/retention requests. |
| High | Engineer identity and confirmation are caller-supplied | `verified_by` and `confirmed` fields plus a checkbox do not authenticate the engineer. A caller can mark an arbitrary resolution verified, causing PostgreSQL resolution and Hindsight retain. |
| High | API accepts raw incident evidence into PostgreSQL and sends sanitized evidence/memory to third-party services | Common secret patterns are blocked/redacted, but redaction is heuristic and incomplete; project README correctly warns against real sensitive incidents. |
| Medium | Dependency health can be misread | `/health` says application available even if DB is not configured; provider states are not checked. UI has a “PRODUCTION” chrome label regardless of local synthetic/demo mode. |
| Medium | CORS is defense in depth only | CORS allows a fixed localhost list, but it is not an authentication boundary; API has no auth. |
| Low | Frontend bank label and repository defaults are stale | Could mislead demo reviewers about which Hindsight bank is queried; actual active bank currently comes from settings. |

The README's current security limitation correctly warns to run locally only and not expose the app or use sensitive production data. This warning matches the code assessment.

## 9. Test and build results

| Check | Result | Notes |
|---|---|---|
| Backend suite, repository `.venv`: `..\\.venv\\Scripts\\python.exe -m pytest -q` from `backend` | **Passed: 58 tests, 2 subtests** | One `StarletteDeprecationWarning`: `httpx` with `starlette.testclient` is deprecated; recommendation says install `httpx2`. No dependency changes were made. |
| Frontend production build: `npm run build` from `frontend` | **Passed** | Vite 6.4.5; 1,577 modules transformed; output generated successfully. |
| First generic `python -m pytest -q` attempt | Environment mismatch; collection failed | Invoked global Python, which lacks `hindsight_client`. Re-running with the repository virtual environment passed. |
| First sandboxed build attempt | Sandbox process-spawn failure (`spawn EPERM`) | Re-run of the requested build with execution permission succeeded; not an application build error. |
| Frontend UI tests | **Absent** | No Playwright dependency, configuration, or browser tests. |
| Live Groq/Hindsight integration | **Not tested** | Normal tests use mocks; provider calls were not issued during the read-only audit. |
| PostgreSQL migrations against live DB | **Not tested** | Existing isolated migration tests pass as part of pytest; live migration state was not queried. |

There is a root-level `backend/test_hindsight.py` smoke script that imports the Hindsight SDK and can optionally retain synthetic memory. It is not a normal mock-only integration test and must not be enabled against an unintended bank.

## 10. Prioritized bug and risk list

1. **P0 — Add authenticated identity and authorization before any non-local use.** Derive verifier identity from a validated principal; protect all data and write endpoints. The current confirmation/name fields do not prove engineer verification.
2. **P1 — Correct and centralize the bank label/default.** Render configured bank metadata from the backend or remove the label. Align fallback/default docs/code with the intended bank without exposing credentials. Verify using safe bank metadata before a demo.
3. **P1 — Improve safe provider diagnostics/readiness.** Expose non-secret provider operation state/error category and an explicit read-only readiness check; show which dependency failed in Memory Explorer and comparison without revealing provider messages. Ensure health labels distinguish configured, checked, and operational.
4. **P1 — Reconcile API documentation with OpenAPI and implementation.** `project-docs/API.md` describes numerous absent routes and incorrect paths/payloads; this makes the contract unreliable for frontend/demo work.
5. **P2 — Implement or explicitly defer postmortems.** Add generation/retrieval/revision/download API and UI backed only by verified resolutions, or mark the capability as deferred consistently across plans and demo claims.
6. **P2 — Add browser coverage for the core learning loop.** Add Playwright tests for synthetic create/reuse, MEMORY_OFF skip, explicit confirmation, retain status, related MEMORY_ON recall and error/empty cases. Current project has no frontend automation despite the stated stack.
7. **P2 — Persist/recover investigation run history in the UI.** A retrieval route exists, but the Command Center recent runs are session-only; load prior runs from API and provide an incident run list endpoint if needed.
8. **P3 — Connect recommendation feedback UI or defer the API.** Backend accepts feedback; no user-facing accept/reject/correct actions use it, so the feedback capability is inaccessible through the app.
9. **P3 — Remove stale defaults and update setup docs.** `.env.example` and README still document `incidentiq-demo`; code fallback values have the same old name. Ensure all config surfaces match the intended demo bank.
10. **P3 — Align local frontend port and docs.** Vite uses strict `5174`, while user-facing setup/active URL says `5173`; choose one and keep CORS and instructions aligned.

## 11. Recommended implementation plan

1. Establish the security boundary first: authenticated users, authorization policy, trusted engineer identity, and audit attribution. Keep local demo mode explicit and synthetic.
2. Resolve the single source of truth for Hindsight bank selection and display; update defaults, `.env.example`, README, and UI metadata coherently. Do not change `.env` during audit.
3. Add safe dependency readiness and diagnostics, then reproduce each reported integration error using non-production synthetic data and verify real provider status. Do not show secrets or raw provider payloads/errors.
4. Treat registered OpenAPI routes and schemas as source of truth; rewrite `project-docs/API.md` and document unsupported capabilities as deferred.
5. Complete or formally defer Postmortems; if implemented, generate drafts only from verified incident outcomes and retain review/status boundaries.
6. Add Playwright coverage for all six screens and the learning loop, including provider-failure and successful-empty recall behavior. Keep mock tests separate from live integration checks.
7. Recover durable investigation runs in the UI and either add recommendation feedback controls or defer that flow.
8. Align Vite port, CORS, and README instructions; then rerun backend tests/build and browser flows in a configured test environment.

## Audit limitations

No application data was created or changed and no external provider request was made. Hindsight and Groq are reported configured by the live health endpoint, but this does not establish they are reachable or authorized for the selected bank/model. The exact provider error behind the current user-visible messages remains unknown until an explicitly authorized non-production operation can be observed. The backend health endpoint did confirm the database connection. The audit did not inspect or print secret values.
