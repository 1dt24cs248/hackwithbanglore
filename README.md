# IncidentIQ

IncidentIQ is an AI-assisted production incident investigation system. It combines current incident evidence with relevant historical operational memory to help engineers investigate recurring problems. AI findings are hypotheses and recommendations; engineers remain responsible for confirming outcomes.

## The problem

Engineering teams repeatedly investigate similar incidents, often without a reliable way to reuse lessons from verified resolutions or unsuccessful troubleshooting. IncidentIQ records operational incident data and uses persistent memory to surface prior experience during later investigations.

## Architecture

```text
React + Vite browser app
          |
          v
FastAPI REST API
   |       |       |
   v       v       v
PostgreSQL Hindsight Groq API
```

- **Frontend:** React, Vite, and Lucide icons.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, and Alembic.
- **Operational database:** PostgreSQL stores incidents, logs, deployments, investigation runs, findings, feedback, and memory-operation metadata.
- **Memory:** Hindsight stores and recalls contextual incident experience.
- **Reasoning:** Groq provides structured AI investigation analysis.

The backend is organized as a modular monolith. PostgreSQL is the operational record; Hindsight is the contextual memory layer.

## How Hindsight memory works

An investigation can run with memory turned off or on. Memory-off skips recall. Memory-on asks Hindsight for relevant historical memories before analysis. The backend keeps current evidence, historical memories, AI-generated hypotheses, and engineer-verified findings distinct.

Reported incident experience and unsuccessful troubleshooting may be retained as separate memory types. A resolution is retained as verified only through the resolution workflow after explicit human confirmation. Hindsight memory is not proof that a historical cause is the current cause. No demo data is automatically seeded.

The optional `backend/test_hindsight.py` smoke test recalls synthetic test context. It writes a synthetic memory only when `HINDSIGHT_SMOKE_TEST_RETAIN=true`; use a test memory bank when enabling that option.

## Groq integration

The backend sends structured incident evidence and, when enabled, historical memory to Groq. It checks that the configured model is available and validates the returned analysis against application schemas. Generated causes remain hypotheses; recommendations are for engineer review and do not execute production actions.

Live provider behavior depends on valid credentials, network access, and provider availability. The automated test suite uses test doubles and does not establish that external Groq or Hindsight services are reachable.

## Prerequisites

- Python with support for the versions required by the pinned backend packages.
- Node.js and npm.
- PostgreSQL for persistent application data.
- Hindsight and Groq credentials for provider-backed investigation workflows.

## Environment configuration

From the repository root, copy `backend/.env.example` to `backend/.env` and replace the example values locally. Do not commit `.env` files or put provider secrets in frontend variables; variables prefixed with `VITE_` are bundled for the browser.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URL used by the API and migrations. |
| `HINDSIGHT_API_KEY` | Server-side Hindsight API credential. |
| `HINDSIGHT_BASE_URL` | Hindsight API base URL. |
| `HINDSIGHT_BANK_ID` | Server-side memory bank; defaults to `incidentiq-hackathon-demo`. Set a dedicated test/demo bank before retaining demo data. |
| `GROQ_API_KEY` | Server-side Groq API credential. |
| `GROQ_MODEL` | Groq model identifier; defaults to `openai/gpt-oss-20b`. |
| `HINDSIGHT_SMOKE_TEST_RETAIN` | Opt-in switch for retaining synthetic memory from the smoke test; defaults to `false`. |

Database-backed API routes require a configured database. Memory-on investigations require a working Hindsight integration, and AI analysis requires a working Groq integration.

## Backend setup

In PowerShell from the repository root:

```powershell
Set-Location backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `backend/.env` with local PostgreSQL connection details and provider credentials. If the file already exists, preserve it and edit it locally rather than overwriting it. Start PostgreSQL, then apply migrations from the `backend` directory:

```powershell
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The API is available at `http://127.0.0.1:8001`; interactive API documentation is at `/docs`.

## Frontend setup

In a second terminal from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The Vite development server listens on `http://127.0.0.1:5174`. The frontend defaults to the API at `http://127.0.0.1:8001/api`. For a different backend URL, set `VITE_API_BASE_URL` before starting Vite. Do not put secrets in `VITE_*` variables.

## Tests and production build

Run backend tests from the `backend` directory with the environment activated:

```powershell
python -m pytest -q
python -m compileall -q app migrations scripts test_hindsight.py
```

Run the frontend production build from `frontend`:

```powershell
npm ci
npm test
npm run build
```

The backend `/health` response performs a read-only Hindsight recall and a lightweight Groq model-list request. It reports safe provider status categories and the configured Hindsight bank ID; it never returns provider credentials or raw exception details.

## Security limitations

**This application is not safe to expose to the public internet or use with sensitive production incidents.** The current incident and investigation API has no authentication or authorization. A caller can access incident data and invoke write operations. In particular, the resolution endpoint accepts client-supplied `confirmed` and `verified_by` fields; these fields do not authenticate an engineer, and CORS is not an access-control boundary. Run locally on loopback only until authentication and authorization are implemented.

AI hypotheses are stored as unverified findings by the investigation workflow. However, without authenticated authorization, the API cannot establish who confirmed a resolution. Do not treat a request's confirmation flag or verifier name as trustworthy.

The minimum viable production integration is an established OIDC identity provider: validate signed access tokens server-side (issuer, audience, expiry and signing keys), enforce authorization on every incident and investigation endpoint, derive verifier identity from the validated principal rather than request data, preserve explicit human confirmation, and serve the app only over HTTPS. Configure CORS to the actual trusted frontend origin as defense in depth. Do not substitute a shared browser-embedded API key or a caller-supplied username for user authentication.

## Guided demo walkthrough

1. Open **Investigations** and select **Create / load historical sample**. The app creates or reuses only an exact incident marked `source=synthetic_demo`; no records are seeded at startup, overwritten, or deleted.
2. Run that incident with **MEMORY_OFF**. The result states that historical recall was skipped.
3. In **Engineer review**, enter a root cause and resolution that you actually verified in the simulated scenario, enter a display name, and explicitly check the confirmation box. A typed name is not authentication. The backend then calls the existing verified-resolution workflow and displays its Hindsight retain status.
4. After the MEMORY_OFF run and a successful or duplicate-skipped retain, select **Create & investigate related sample**. This creates or reuses the related synthetic incident and runs it with **MEMORY_ON** through the backend's real recall path.
5. Review the actual returned Hindsight memories and provenance. Empty recall is shown as empty; historical information is not proof of the new incident's cause. Failed approaches are warnings only when Hindsight returns the corresponding tagged memory.

The browser stores only the IDs and retain state of the demo fixtures to avoid accidental repeats, and also checks exact server-side fixture records before creating a new sample. Provider connectivity is still dependent on local configuration; automated tests use mocks and do not verify live Hindsight or Groq operations. Do not use this unauthenticated app with real production incidents or expose it publicly.

## Synthetic demonstration data

Any synthetic incidents, memories, or AI output used for a demonstration must be clearly labeled as synthetic and must not be presented as production evidence. The browser-QA mock server is intentionally excluded from the application staging set; do not use mocked responses to claim that live Groq or Hindsight integrations work.
