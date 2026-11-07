# AGENTS.md

## 1. Project-document hierarchy
This project is governed by the following documents:
1. `PRD.md`
2. `DESIGN.md`
3. `ARCHITECTURE.md`
4. `DATABASE.md`
5. `API.md`
6. `IMPLEMENTATION_PLAN.md`
7. `HACKATHON_REQUIREMENTS.md`

Read the relevant document before implementing or changing code.

## 2. Requirement compliance
- follow PRD exactly
- do not add unapproved features
- keep terminology consistent across docs, code, and UI
- keep Hindsight central to the product
- do not treat PostgreSQL as a replacement for Hindsight memory

## 3. Existing-code inspection
Before changing code, inspect the existing workspace and relevant files. Preserve valid work and avoid unnecessary rewrites.

## 4. Naming conventions
- use consistent names for API routes, table names, and UI elements
- keep SDK and route names aligned with the architecture docs
- use clear, technical naming in code bases

## 5. Folder structure
Expected future structure:
```text
hackwithbanglore/
├── frontend/
├── backend/
├── project-docs/
├── README.md
├── .env.example
└── .gitignore
```

## 6. Component reuse
- reuse common UI cards, tables, and forms
- keep enterprise design consistency with `DESIGN.md`
- do not create one-off patterns when a shared component exists

## 7. Dependency management
- use the approved stack only
- do not add paid infrastructure for the MVP
- verify official documentation before assuming model or SDK availability

## 8. Type safety
- keep payload schemas explicit
- avoid vague `any` types in critical paths
- validate inputs and outputs at API boundaries

## 9. Error handling
- show user-friendly errors
- log failures without leaking secrets
- degrade gracefully when Groq or Hindsight is unavailable

## 10. Database rules
- PostgreSQL stores operational records
- Hindsight stores memory
- do not duplicate memory content into a second primary record store
- enforce timestamps and constraints
- `investigation_runs` is required for tracking repeated analyses of the same incident and for memory-mode audits
- `memory_operation_events` must store safe metadata and redacted errors, never raw secrets or raw memory payloads

## 11. API rules
- follow the documented endpoint names and payload structure
- keep responses consistent and typed
- never expose credentials or secrets to the frontend

## 12. Hindsight rules
- Hindsight is mandatory and must be used for real `retain()` and `recall()` operations
- never fake memory retrieval
- never fake successful retention
- never claim a root cause is verified without evidence
- do not invent undocumented Hindsight SDK methods, parameters, or result fields
- memory OFF must skip Hindsight recall completely; memory ON must include a real recall step before analysis
- record failed or partial memory operations as failed or partial and do not present them as successful retain events

## 13. Groq rules
- verify model availability and API contract against official docs
- never invent SDK methods or response fields
- avoid including sensitive strings in prompts or logs

## 14. Security and secrets
- never hardcode API keys
- never expose credentials in source code or UI
- keep secret values in environment variables only
- redact sensitive values before logging

## 15. Testing requirements
- add tests for important backend logic
- validate API endpoints and schemas
- validate the Hindsight integration behaviour when available
- test critical UI flows for investigation and postmortem generation
- include tests for memory OFF and memory ON execution paths
- validate that investigation runs are created and retrievable
- validate demo reset/replay behaviour without uncontrolled duplicate memory retention

## 16. Documentation requirements
- update relevant docs when implementation changes behaviour
- keep architecture, API, and schema docs aligned with code
- if something is uncertain, mark it as an open decision rather than inventing facts

## 17. Git discipline
- keep changes focused
- do not rewrite unrelated working code
- keep commit scope reviewable and purposeful

## 18. Change management
- if a feature is outside the approved scope, capture the decision explicitly instead of silently adding it
- maintain consistent terminology across the code and docs

## 19. Code review requirements
Review for:
- correctness
- security
- documentation alignment
- Hindsight and Groq contract compliance
- clear distinction between evidence, inference, and verified fact

## 20. Mandatory rules summary
- read relevant documentation before implementation
- never invent SDK methods
- verify external API documentation
- never fake memory retrieval
- never fake successful retention
- never hardcode API keys
- never expose credentials
- never treat unverified hypotheses as confirmed resolutions
- never execute destructive production commands
- never rewrite unrelated working code
- never add unapproved features
- write tests for important changes
- explain significant implementation decisions
