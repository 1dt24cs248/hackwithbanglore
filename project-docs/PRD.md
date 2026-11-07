# Product Requirements Document

## 1. Document purpose
This document defines the product requirements for IncidentIQ, a self-learning AI incident investigation system for production engineering teams. It captures the problem, product goals, required features, user journeys, functional and non-functional requirements, acceptance criteria, and constraints. This document is the source of truth for design, architecture, database, API, implementation, and compliance work.

## 2. Product overview
IncidentIQ is an AI-powered incident investigation platform that helps engineering teams investigate incidents faster and learn from verified operational experience. The system records incident symptoms, previously successful resolutions, failed troubleshooting paths, and engineer-validated outcomes so future investigations are better informed.

The platform combines a React frontend, FastAPI backend, PostgreSQL for operational records, Groq for LLM reasoning, and Hindsight for persistent memory. Hindsight is not optional; it is a central product capability.

## 3. Problem statement
Production incidents like API latency, authentication failures, deployment regressions, queue backlogs, and database deadlocks often require repetitive manual investigation. Teams review logs, historical incidents, deployment metadata, and runbooks, but they do not always retain the lessons learned from prior investigations. This means the same issue patterns repeat and the same failed remediation paths are sometimes retried.

IncidentIQ addresses this by creating a persistent incident memory. It stores verified experience from successful and unsuccessful investigations so the system can learn from previous outcomes instead of merely answering new questions in isolation.

## 4. Proposed solution
IncidentIQ ingests new incidents, correlates them against historical data, recalls relevant Hindsight memories, and uses Groq to reason over evidence. The AI produces evidence-linked recommendations, but these recommendations are always grounded in historical context and remain distinguishable from verified facts.

The system supports the full learning cycle:

1. New incident arrives.
2. Incident is analysed.
3. Relevant Hindsight memory is recalled.
4. Historical matches are retrieved.
5. Groq generates analysis.
6. Recommendations are reviewed by an engineer.
7. Verified outcome is retained in memory.
8. Future incidents benefit from the new memory.

## 5. Value proposition
- Reduces time to understand a production incident.
- Improves the quality and relevance of recommended actions.
- Prevents repeated failed troubleshooting attempts.
- Builds a verified historical memory of incidents and resolutions.
- Supports faster investigation during recurring patterns.
- Produces cleaner postmortems and engineering learning loops.

## 6. Target users and personas
### SRE on-call engineer
Needs quick triage support and evidence-based guidance.

### DevOps engineer
Needs deployment and environment context tied to incident symptoms.

### Backend engineer
Needs technical root-cause evaluation based on logs and historical patterns.

### Incident commander
Needs a concise, technically defensible incident narrative with verified outcomes.

## 7. User goals and pain points
### Goals
- Submit incidents without friction.
- Understand likely causes quickly.
- Compare memory-aware recommendations against a baseline.
- Review previously failed remediation attempts before retrying them.
- Create a verified resolution and retain it.

### Pain points
- Lack of searchable historical incident context.
- Repeating prior mistakes.
- No consistent “lessons learned” memory layer.
- Difficulty separating a guess from an accepted root cause.
- Time-consuming manual postmortem generation.

## 8. Product objectives
1. Build a working incident investigation workflow.
2. Make Hindsight a first-class component of the application.
3. Support evidence-linked recommendations.
4. Allow engineers to confirm or reject AI-generated guidance.
5. Demonstrate memory-off versus memory-on behaviour.
6. Produce postmortems from verified incidents.

## 9. User journeys
### Journey 1: Submit and investigate an incident
1. Engineer submits details, logs, and deployment data.
2. System validates the input and stores the incident.
3. Historical matches are identified.
4. Hindsight memory is recalled.
5. Groq generates a summary and recommendations.
6. Engineer reviews evidence and selects a path.

### Journey 2: Learn from previous outcomes
1. Engineer reviews the Memory Inspector.
2. Similar incidents and previous resolutions are displayed.
3. Failure memory warns against known dead ends.
4. Resolution is confirmed and retained in memory.

### Journey 3: Generate a postmortem
1. Incident is resolved and validated.
2. System creates a markdown postmortem.
3. Engineer reviews and downloads the final report.

## 10. User stories
### US-01
As an on-call engineer, I want to submit incident details so that I can start analysis quickly.

### US-02
As a user, I want an AI summary of the incident so that I can understand the problem quickly.

### US-03
As an engineer, I want historical incidents and related evidence so that I can compare with prior investigations.

### US-04
As a user, I want memory-off and memory-on comparison so that I can see the value of Hindsight.

### US-05
As an incident lead, I want to see previous failed paths so that I do not repeat bad actions.

### US-06
As an engineer, I want to provide feedback so that the system becomes more accurate over time.

### US-07
As a team lead, I want a postmortem draft so that the team can document and improve.

## 11. Functional requirements
FR-01: The system shall allow incident submission with required metadata and logs.

FR-02: The system shall store incident records in PostgreSQL with lifecycle metadata.

FR-03: The system shall support AI investigation using Groq and incident context.

FR-04: The system shall recall relevant Hindsight memories using `retain()` and `recall()` semantics.

FR-05: The system shall clearly distinguish evidence, inference, and verified root cause.

FR-06: The system shall display historical incident matches when relevant.

FR-07: The system shall provide memory-off and memory-on recommendation comparison.

FR-08: The system shall detect recurrence patterns for repeating incidents.

FR-09: The system shall track failure memory and show warnings about prior unsuccessful remediation attempts.

FR-10: The system shall detect conflicts when prior memory and current evidence disagree.

FR-11: The system shall capture engineer feedback and resolution confirmation.

FR-12: The system shall support guided demo mode using synthetic incident data.

FR-13: The system shall generate an incident postmortem in markdown.

FR-14: The system shall allow postmortem export or download.

FR-15: The system shall provide a dashboard with operational summaries.

FR-16: The system shall expose REST endpoints for incident life-cycle operations and memory inspection.

FR-17: The system shall create and persist an `investigation_run` record for every analysis execution, including the incident reference, memory mode, model identifier, execution status, and references to recalled memory entries or safe metadata.

FR-18: The system shall support two controlled analysis paths: a memory-off path without Hindsight recall and a memory-on path with Hindsight recall and a comparable model configuration.

FR-19: The system shall distinguish between current incident evidence, historical Hindsight memory, AI-generated hypotheses, and engineer-verified root causes in all product output and API responses.

## 12. Non-functional requirements
- NFR-01: The app must run locally with no paid hosting requirements.
- NFR-02: The UI must be readable and usable on desktop and tablet screens.
- NFR-03: Recommendations must include evidence and confidence rationale.
- NFR-04: Secrets must never be stored in source code or exposed to the frontend.
- NFR-05: All labels and demo data must clearly indicate synthetic content.
- NFR-06: AI and memory failures must degrade gracefully without exposing internals.
- NFR-07: Logs must redact sensitive values.

## 13. Approved features and requirements
### 1. Incident Submission
Purpose: allow structured incident intake.
User interaction: engineer enters service, severity, logs, deployment data.
System behaviour: validates inputs and saves incident.
Backend behaviour: stores incident record and returns created ID.
Expected output: incident created and ready for investigation.
Failure conditions: missing required fields, invalid severity.
Acceptance criteria: the incident appears in the dashboard and investigation center.

### 2. AI Incident Investigation
Purpose: produce an incident analysis from current evidence.
User interaction: user starts analysis from investigation center.
System behaviour: enriches knowledge with prior memory and historical incidents.
Backend behaviour: calls Groq and returns summarised results.
Expected output: summary, probable causes, and evidence-based recommendations.
Failure conditions: Groq network failure or invalid response schema.
Acceptance criteria: analysis is displayed with evidence and caveats.

### 3. Hindsight Persistent Memory
Purpose: retain verified learning across incidents.
User interaction: memory inspector and investigation flows show recall results.
System behaviour: uses Hindsight `retain()` and `recall()`.
Backend behaviour: updates memory records only for verified outcomes.
Expected output: memory entries with clear categorisation.
Failure conditions: Hindsight error or empty recall is treated as valid empty result.
Acceptance criteria: memory can be recalled and displayed transparently.

### 4. Historical Incident Retrieval
Purpose: surface similar prior incidents.
User interaction: user reviews historical matches in the investigation center.
System behaviour: matches by service, symptom, and deployment context.
Backend behaviour: queries PostgreSQL and Hindsight context.
Expected output: ranked list of relevant incidents.
Failure conditions: no matches found.
Acceptance criteria: empty state is displayed clearly.

### 5. Engineer Feedback
Purpose: capture validation and corrections from expert engineers.
User interaction: review and accept, reject, or amend recommendations.
System behaviour: saves feedback and updates incident status.
Backend behaviour: records feedback against specific incident and recommendation.
Expected output: reviewed recommendation with outcome history.
Failure conditions: invalid recommendation reference.
Acceptance criteria: feedback is persisted and used in learning flow.

### 6. Continuous Learning
Purpose: improve future recommendations via verified learning.
User interaction: engineer finalises incident resolution.
System behaviour: stores a verified resolution and failure knowledge.
Backend behaviour: writes Hindsight memory and logs event metadata.
Expected output: future incidents are better informed.
Failure conditions: unresolved or unverified incident.
Acceptance criteria: memory storage only occurs after validation.

### 7. Memory Off vs Memory On Comparison
Purpose: show the value of Hindsight.
User interaction: user toggles memory mode in the investigation view.
System behaviour: runs analysis with and without memory context.
Backend behaviour: returns both sets of recommendations and a summary delta.
Expected output: clear comparison panel.
Failure conditions: Hindsight unavailable.
Acceptance criteria: the difference is explained in plain language.

### 8. Evidence-Linked AI Recommendations
Purpose: tie recommendations to evidence.
User interaction: user reviews recommendation cards.
System behaviour: attaches evidence references to recommendations.
Backend behaviour: stores evidence and confidence metadata.
Expected output: recommendation cards with sources and justification.
Failure conditions: no evidence exists.
Acceptance criteria: each recommendation includes at least one evidence item.

### 9. Failure-Aware Resolution Guard
Purpose: avoid repeating known failed actions.
User interaction: user sees warning banners for risky solutions.
System behaviour: compares recommendations with failure memory.
Backend behaviour: retrieves and ranks prior failed actions.
Expected output: warning on recommended path if matching failure memory exists.
Failure conditions: no failure memory exists.
Acceptance criteria: warning explains the previous failure and alternative path.

### 10. Incident Recurrence Detection
Purpose: detect repeated patterns in production incidents.
User interaction: user sees recurrence alerts in dashboard and investigation.
System behaviour: compares service and issue similarity.
Backend behaviour: queries recent incidents and calculates recurrence scores.
Expected output: recurrence alert or notice.
Failure conditions: insufficient historical data.
Acceptance criteria: alert is labeled and has supporting evidence.

### 11. Incident Memory Timeline
Purpose: show the memory and incident timeline in order.
User interaction: user opens the Memory Inspector timeline.
System behaviour: displays incident, resolution, and failure events over time.
Backend behaviour: combines positional data from PostgreSQL and Hindsight metadata.
Expected output: chronological event timeline.
Failure conditions: no events exist.
Acceptance criteria: timeline remains readable and correctly ordered.

### 12. Memory Conflict Detector
Purpose: identify contradictory memory histories.
User interaction: user views memory conflict warnings.
System behaviour: compares evidence and memory for contradictions.
Backend behaviour: identifies conflicting patterns and alerts with context.
Expected output: warning explaining the conflict and need for validation.
Failure conditions: no conflicts exist.
Acceptance criteria: no false positives for harmless variation.

### 13. Guided Demo Mode
Purpose: demonstrate the app using synthetic incidents.
User interaction: user launches demo mode.
System behaviour: loads synthetic data and explains each step.
Backend behaviour: runs realistic demo flow with clear synthetic labels.
Expected output: before-and-after memory demonstration.
Failure conditions: missing synthetic data.
Acceptance criteria: demo content is labelled as synthetic.

### 14. Auto-Generated Incident Postmortem
Purpose: create a markdown incident report after resolution.
User interaction: user selects postmortem generation.
System behaviour: assembles validated findings and lessons learned.
Backend behaviour: stores markdown content and CRUD records.
Expected output: downloadable markdown report.
Failure conditions: incident unresolved or no verified root cause.
Acceptance criteria: exported report is readable and tied to the incident.

## 14. Page-level requirements
### Dashboard
- Total incidents.
- Open and resolved counts.
- Critical count.
- Recent incidents list.
- Severity distribution chart.
- Recurrence alerts.

### Investigation Center
- Submission form.
- Service, severity, logs, and deployment metadata.
- AI summary and root-cause suggestions.
- Historical matches.
- Memory-off versus memory-on comparison.
- Failure warnings and recurrence detection.

### Memory Inspector
- Actual Hindsight recall results.
- Retained experiences.
- Incident and resolution memory.
- Conflict warnings and timeline.

### Postmortem Center
- Resolved incidents and generated reports.
- Downloadable markdown reports.

## 15. Hindsight requirements
- Hindsight is mandatory and central to the product.
- The app must use real `retain()` and `recall()` operations.
- Hindsight holds incident memory, resolution memory, and failure memory.
- Hindsight is separate from PostgreSQL and not a duplicate of the database.
- Unverified hypotheses are never retained as confirmed root causes.
- Memory-enabled investigations must use a real recall step before the Groq analysis and must document the evidence sources used.
- Memory OFF path: current incident data only; no Hindsight recall is executed.
- Memory ON path: same incident data plus actual Hindsight `recall()` results passed to Groq; outputs must explicitly identify those historical sources.
- A historical incident is never treated as proof of the current root cause unless a human engineer verifies it.

## 16. Groq requirements
- Groq is used to summarise, rank causes, and suggest remediation.
- Model choice must be verified against official docs during implementation.
- Prompt design must exclude secrets and unnecessary noise.
- Output must be evidence-linked and clearly distinguishable from confirmed fact.

## 17. PostgreSQL requirements
- PostgreSQL stores operational records, not the memory layer.
- Required tables include: incidents, incident_logs, deployments, postmortems, engineer_feedback, memory_operation_events, investigation_runs.
- Schema must support lifecycle, auditing, analytics, and per-investigation execution history.

## 18. Loading, empty, and error states
### Loading states
- submitting incident
- running investigation
- recalling memory
- generating postmortem

### Empty states
- no incidents
- no historical matches
- no Hindsight memory
- no postmortems

### Error states
- validation errors
- Groq API failure
- Hindsight outage
- database outage

## 19. Validation rules
- Severity must be one of Critical, High, Medium, Low.
- Important fields must not be empty.
- Postmortem generation requires a verified resolution.
- Failed memory operations must not be reported as successful.
- Hindsight outputs cannot be used as proof of root cause without verification.

## 20. Security requirements
- No secrets in repository.
- No credentials in frontend.
- Redacted logs.
- Only authorised people should access sensitive incident data.

## 21. MVP scope
- Incident submission.
- AI investigation.
- Hindsight recall and retain.
- Dashboard.
- Memory Inspector.
- Postmortem generation.
- Guided demo mode.

## 22. Out-of-scope features
- Microservices decomposition.
- Large enterprise RBAC outside the demo scope.
- Paid hosting or subscriptions.
- Additional workflows not in the approved feature list.

## 23. Success criteria
- User can submit an incident and get evidence-linked recommendations.
- Hindsight materially improves recommendations.
- Engineers can review failed remediation paths and avoid them.
- Postmortem generation works for verified incidents.
- Demo mode clearly shows memory before/after effect.

## 24. Acceptance criteria
AC-01: The system can submit incident data.
AC-02: The system can perform AI investigation.
AC-03: Hindsight recall returns relevant memory items.
AC-04: Recommendations are linked to evidence.
AC-05: Engineer feedback is saved and visible.
AC-06: Postmortem markdown download works.
AC-07: Demo mode labels synthetic data clearly.

## 25. Assumptions and open decisions
- Groq model choice may change after official API verification.
- Hindsight account setup and SDK compatibility must be validated during implementation.
- Some analytics may use sample data until the product has enough recorded incidents.
- Public demo hosting will rely on free-tier or open-source options where available, but free hosting is not guaranteed and must be verified during deployment.

## 26. Evidence provenance and memory mode requirements
Every recommendation must clearly show the evidence source category:
1. Current incident evidence.
2. Historical Hindsight memories.
3. AI-generated hypothesis.
4. Engineer-verified root cause.

Historical Hindsight memories may support a recommendation but must never be interpreted as proof of a current root cause without engineering verification. The system must show a clear provenance badge or metadata field for each recommendation segment.

### Memory OFF analysis path
- Use only the current incident information.
- Do not call Hindsight recall for historical context.
- Run the Groq analysis over the current evidence.
- Return current-evidence-based hypotheses and recommendations.

### Memory ON analysis path
- Use the same current incident information.
- Execute an actual Hindsight recall for relevant incidents, resolutions or failures.
- Pass the recalled memory summaries and their source references to Groq as auxiliary context.
- Return analysis with historical evidence references and explicit provenance labels.
- Comparable model settings must be used across both paths so the comparison remains fair and transparent.

The system must not claim that memory improves accuracy, confidence, or MTTR unless measured in a real benchmark or controlled experiment.

## 27. Hindsight learning lifecycle requirements
The system must implement the following sequence:
1. Real Hindsight recall before memory-enabled investigation.
2. AI analysis using current evidence and recalled memory.
3. Engineer review and feedback.
4. Verified resolution and root-cause confirmation.
5. Successful `retain()` for verified incident, resolution, or failure learning.
6. Record of failed troubleshooting retention attempts with clear audit status.
7. Memory operation auditing in PostgreSQL.
8. Future investigation reuse based on the retained memory.

Unverified hypotheses must never be stored as confirmed root causes. A failed or partial memory operation must be recorded as unsuccessful and must not be described as a successful retain.

## 28. Summary of product scope
Only the 14 approved features listed above are in scope. These are the feature names and rules governing the product implementation: Incident Submission, AI Incident Investigation, Hindsight Persistent Memory, Historical Incident Retrieval, Engineer Feedback, Continuous Learning, Memory Off vs Memory On Comparison, Evidence-Linked AI Recommendations, Failure-Aware Resolution Guard, Incident Recurrence Detection, Incident Memory Timeline, Memory Conflict Detector, Guided Demo Mode, and Auto-Generated Incident Postmortem.
