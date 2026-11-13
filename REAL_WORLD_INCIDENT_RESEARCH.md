# IncidentIQ: Real World Incident Research

**Prepared:** 2026-11-13
**Scope:** Primary-source research and data preparation only. No application code, database schema, or existing records were changed.
**Evidence rule:** Company reports and official status pages are treated as evidence. Inferences and demo-only reconstructions are identified separately.

> **Implementation update:** This was the earlier research-only artifact. Its sample Cloudflare submission description includes published root-cause details, so it is not a blind-investigation payload. The later library implementation withholds the confirmed root cause from the investigation request; use the current `real_incident_demo.json`, `REAL_INCIDENT_DATASET.md`, and `INCIDENT_LIBRARY_IMPLEMENTATION_REPORT.md` for the implemented workflow.

## 1. Executive summary

Five documented production incidents were compared: Cloudflare's June 2022 routing outage, Google Cloud's June 2019 network congestion incident, GitHub's October 2018 database failover incident, AWS S3's February 2017 US-EAST-1 disruption, and Atlassian's April 2022 site deletion incident. Each has an official company postmortem or incident report, measurable impact, and disclosed response or prevention work.

**Recommended final demo incident: Cloudflare, June 21, 2022.** The primary report ties a network policy reorder to route withdrawal and overloaded smaller clusters; it gives a 19 data center footprint, 4% of locations carrying 50% of global requests, exact rollout/recovery times, and explicit prevention items. This fits IncidentIQ's description, severity, environment, error, and metric fields well. No real deployment ID, original customer error string, or host-level telemetry was published, so those fields must remain blank or be labeled as illustrative outside the documented-evidence section. [Cloudflare postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

## 2. Existing IncidentIQ form, API, and workflow

### Form and POST `/api/incidents`

The React submission form in `frontend/src/App.jsx` contains the listed controls: Incident title, Affected service, Description, Severity, Environment, Error message, Deployment ID, and System metrics JSON. It sends `title`, `description`, `service_name`, `environment`, `severity`, `error_messages` (a one-element array if populated, otherwise empty), and `system_metrics`; it adds `deployment: {deployment_id}` only when that field is nonempty. Thus the visible form does **not** expose log entries, deployment version/change summary, owner, or source.

The backend `IncidentSubmission` schema at `backend/app/schemas/investigation.py` accepts exactly these top-level fields: `title` (1–255 chars), `description` (1–20,000), `severity` (`critical|high|medium|low`), `service_name` (1–150), `environment` (1–50), optional `owner`, `source` (defaults to `api`), `error_messages` (up to 100 strings), `logs` (up to 100 structured log objects), optional `deployment`, and `system_metrics` (up to 100 scalar-valued key/value entries). Nested log keys are `log_type` (`error|warning|deployment|note`, default `note`), `log_text`, optional `source_system`, and optional `author`. Nested deployment keys are `deployment_id`, `version`, `deployed_by`, `deployed_at`, and `change_summary`. Both nested models forbid unknown properties. Metrics are stored as JSON text in an `IncidentLog` with `source_system=system_metrics`; submitted error messages and logs are stored as `IncidentLog` rows; deployment data is stored as a `Deployment` row. Incident title, description, service, environment, severity, owner, source, and status are incident fields.

The form parses metrics as a JSON object and rejects arrays or invalid JSON. The backend schema further constrains each metric value to string, number, boolean, or null. Use only documented numbers/strings as metrics. Since there is no real per-request sample or log from these reports, don't encode calculated or invented error rates in that field.

### Investigation and memory

The UI posts to `/api/incidents/{id}/investigate` with `memory_mode: MEMORY_OFF` or `MEMORY_ON`; the backend accepts these names (also normalized `off`/`on`). Both modes load the incident's current context and send it to the AI analysis service. `MEMORY_OFF` skips Hindsight recall. `MEMORY_ON` first asks Hindsight for relevant historical memories and includes returned memories as historical context. A memory-on failure prevents analysis rather than silently pretending recall succeeded. Findings retain provenance distinctions between current incident evidence, historical Hindsight memory, AI-generated hypotheses, and engineer-verified root cause.

Incident observations may be retained as observations, without asserting root cause. A verified resolution is retained only through the resolution workflow after a human submits a root cause and resolution and explicitly confirms verification. It is tagged as verified resolution; failed approaches are a separate memory type. The app does not automatically turn an AI hypothesis into verified memory. A typed verifier name and confirmation are workflow inputs, not authenticated identity. The repository notes that the app has no API authentication; keep this demo local and do not treat it as a production incident intake system. See `README.md` and `backend/app/services/hindsight_service.py`.

**Submission boundary:** The recommended payload below includes only supported POST fields. Do not put the investigation `memory_mode`, business impact, source URLs, or expected hypotheses into the incident submission payload; these are report metadata, not incident fields.

## 3. Incident comparison

| Company / date | System and primary failure | Duration disclosed | Publicly documented impact | Fit for IncidentIQ |
|---|---|---:|---|---|
| Cloudflare — 2022-06-21 | BGP prefix policy reordered; critical site-local prefixes withdrawn; internal load balancing disrupted | 06:27 to last revert 07:42 UTC (75 min); incident closed 08:00 UTC | 19 data centers; 4% of network locations carried 50% of requests | **Best:** clear change, network symptoms, impact metrics, and response path |
| Google Cloud — 2019-06-02 | Maintenance automation descheduled network control-plane jobs across locations due to combined configuration and software bug | Region-dependent 3h19–4h25; full service resumed 16:10 PDT | Six regions and many services; packet loss and several published API/error rates | Excellent metrics and complexity; root cause has multiple interacting contributors |
| GitHub — 2018-10-21/22 | 43-second network partition triggered MySQL orchestrator failover and inconsistent cross-site writes/replicas | 24h11 service degradation | Stale/inconsistent metadata; webhooks and Pages paused; >5m hook events and 80k Pages builds queued | Excellent database/failover demonstration, but telemetry values are sparse |
| AWS S3 — 2017-02-28 | Incorrect operational command removed too many servers; index and placement subsystems needed full restart | S3 normal at 13:54 PST; start 09:37 PST = 4h17 | S3 APIs and dependent AWS services disrupted in US-EAST-1; customer count and request failure rate not disclosed | Clear operational error and recovery, but limited customer-level metrics |
| Atlassian — 2022-04-05 | Deletion script passed site IDs where app IDs were expected; API lacked safeguards | Up to 14 days for some affected customers; all restored April 18 | 883 sites / 775 customers affected; >99.6% of customers/users remained unaffected; no customer lost >5 min data | Exceptional business-impact evidence, though a destructive data operation rather than service degradation |

All five incidents were established production events. Each report or incident page is linked in its detailed section below. “Request failure percentage” is only included where the company published one; no values have been reverse-engineered from figures or charts.

## 4. Detailed incident evidence and impact

### 4.1 Cloudflare — outage on June 21, 2022

**Official sources:** [postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/); [Cloudflare system status](https://www.cloudflarestatus.com/). The postmortem is the primary source; the general status-page URL is supplied as the official status portal, as the report did not expose a stable incident-specific status URL in the material reviewed.

**Date and duration.** June 21, 2022. The change reached MCP locations at 06:27 UTC; the last revert completed at 07:42 UTC, and the incident was closed at 08:00 UTC. Therefore, 75 minutes elapsed to the last revert and 93 minutes to incident closure. The report notes sporadic reappearance during reverts as engineers' changes overlapped. [Postmortem timeline](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Affected services and customer symptoms.** Traffic was affected in 19 data centers using the Multi-Colo PoP architecture. Customers relying on Cloudflare in impacted locations could not reach websites and services using Cloudflare; other locations continued to operate. The route withdrawal prevented access to customer origins and Cloudflare's affected locations, while the loss of internal forwarding caused smaller compute clusters to receive the same traffic as the largest and overload. [Postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Technical cause and recovery.** A prefix-advertisement policy change reordered terms so `REJECT-THE-REST` preceded the site-local advertisement terms. The policy withdrew critical site-local prefixes. Multimog then could not forward between MCP servers. Engineers used backup procedures to regain control of sites, identified the cause, and reverted the configuration. The first affected site returned at 06:58 UTC; the final revert was complete at 07:42 UTC. [Technical account and timeline](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Business impact and published measures.** The 19 MCP data centers were 4% of Cloudflare's network locations but handled 50% of global requests. Customer counts, failed-request percentage, revenue impact, and SLA credits/violations are **Not disclosed in the official incident report.** Inference: customers whose traffic depended on these locations experienced loss of reachability and service availability, while users routed through unaffected locations could continue operating. [Postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Prevention.** Cloudflare said its change procedures and automation needed MCP-specific testing and rollout procedures; it planned to redesign the policy statement to prevent incorrect ordering and improve rollout staggering and automated commit-confirm rollback. [Remediation section](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

### 4.2 Google Cloud — networking incident #19009, June 2, 2019

**Official sources:** [official incident report / status page](https://status.cloud.google.com/incident/cloud-networking/19009); [Google Cloud follow-up](https://cloud.google.com/blog/topics/inside-google-cloud/an-update-on-sundays-service-disruption).

**Date and duration.** June 2, 2019. Google reports impact durations varying between 3h19 and 4h25 by region; the incident began 11:45 PDT and full service resumed at 16:10 PDT. [Incident report](https://status.cloud.google.com/incident/cloud-networking/19009)

**Affected products and symptoms.** Google Cloud networking, Compute Engine, App Engine, Cloud Endpoints, Cloud Interconnect, Cloud VPN, Cloud Console, Stackdriver, Pub/Sub, BigQuery, regional Spanner, and Cloud Storage were affected, as were some G Suite/Google services. Symptoms included packet loss, increased latency, timeouts, errors, unavailable instances and regional services, and configuration push failures. Google identifies affected regions as us-central1, us-east1, us-east4, us-west2, northamerica-northeast1, and southamerica-east1. [Incident report](https://status.cloud.google.com/incident/cloud-networking/19009)

**Technical cause and recovery.** Two normally benign job/configuration conditions combined with a cluster-management software bug that allowed a maintenance event to deschedule network control-plane jobs in multiple physical locations. BGP routes were withdrawn after the network's fail-static period. Engineers halted the automation, rebuilt and redistributed lost network configuration, rescheduled the control plane, and directed service traffic away from affected regions during recovery. [Root cause and remediation](https://status.cloud.google.com/incident/cloud-networking/19009)

**Business impact and published measures.** App Engine in four regions was unavailable; us-central1 App Engine saw a 23.2% RPS drop. Cloud Endpoints error rate peaked at 4.4%; 50% of service configuration push workflows failed through June 4. Pub/Sub had a 27% global drop in successful publish/subscribe requests. BigQuery average error rate was 0.7%, with jobs.insert peaking at 27%. Cloud Storage average error rates included 96.2% in us-west2 and 62.4% in us-east4. User/organization counts, monetary impact, and whether a particular customer's SLA credit was granted are **Not disclosed in the official incident report**; Google documented the process for requesting SLA review. [Detailed impact](https://status.cloud.google.com/incident/cloud-networking/19009)

**Prevention.** Google halted the implicated automation pending safeguards; planned to reject cross-location descheduling requests, harden cluster management, persist network control-plane configuration, extend fail-static duration, improve emergency response tooling, and expand disaster-recovery testing. [Incident report](https://status.cloud.google.com/incident/cloud-networking/19009)

### 4.3 GitHub — October 21 post-incident analysis, 2018

**Official sources:** [post-incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/); [initial incident report](https://github.blog/news-insights/company-news/october21-incident-report/); [GitHub status portal](https://www.githubstatus.com/). The status portal is not a stable incident-specific snapshot in the reviewed source set.

**Date and duration.** October 21–22, 2018; 24h11 of service degradation. A routine replacement of failing 100G optical equipment caused a network partition at 22:52 UTC; connectivity returned in 43 seconds, but database failover/recovery consequences persisted. [Post-incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)

**Affected products and symptoms.** GitHub web metadata could be stale or inconsistent; users could not rely on issues, pull requests, and other non-Git metadata. Webhook events and GitHub Pages builds were paused for most of the event. Git repository data remained available and GitHub stated no user data was lost, though several seconds of writes required manual reconciliation. [Initial report and analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)

**Technical cause and recovery.** Orchestrator's Raft leadership change triggered MySQL failover writes to West Coast primaries while some East Coast writes were not replicated, preventing a safe simple failback. East Coast applications then incurred cross-country latency. Engineers failed forward, restored backups, synchronized replicas, established a stable topology, and processed queued jobs. More than five million hook events and 80,000 Pages builds queued; about 200,000 webhook payloads exceeded TTL and were dropped before GitHub increased TTL. [Timeline and recovery](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)

**Business impact and published measures.** The report states service degradation lasted 24h11 and some features were unavailable or inconsistent. A busy cluster had 954 writes in the affected window requiring analysis for reconciliation. Number of customers/users affected, percent of requests failing, financial loss, and SLA credits are **Not disclosed in the official incident report.** Inference: delayed webhooks and builds interrupted customer development and deployment workflows; the source confirms these events were queued and later processed, with some webhook payloads dropped. [Postmortem](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)

**Prevention.** Immediate recovery prioritized data integrity, with deliberate pausing of downstream writers and jobs. GitHub rebuilt replicas, added capacity to reduce replica utilization, extended webhook TTL when payloads expired, and described follow-up reconciliation and reliability work. The analysis discusses ensuring topology and application expectations align. [Postmortem](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)

### 4.4 AWS — S3 US-EAST-1 service disruption, February 28, 2017

**Official sources:** [AWS service disruption summary](https://aws.amazon.com/message/41926/); [AWS Service Health Dashboard](https://health.aws.amazon.com/health/status). AWS report is the primary source; the status dashboard URL is the general official status page.

**Date and duration.** February 28, 2017. A command ran at 09:37 PST; S3 was operating normally by 13:54 PST, a 4h17 interval. Some dependent services had backlogs and recovered later, with exact durations varying by service. [AWS summary](https://aws.amazon.com/message/41926/)

**Affected products and symptoms.** S3 requests in US-EAST-1 could not be served during subsystem restarts. AWS identifies the S3 console, new EC2 instance launches, EBS volumes restoring from S3 snapshots, and Lambda as dependent services affected. Individual user/organization counts and request failure percentages are **Not disclosed in the official incident report.**

**Technical cause and recovery.** An operator entered an incorrect input in an established command intended to remove a small number of servers from a billing subsystem; it removed a larger set, including capacity for S3 index and placement subsystems. Because those systems had not been fully restarted in large regions for years, restarting and metadata safety checks took longer than anticipated. Index requests resumed in stages; placement completed recovery at 13:54 PST. [AWS summary](https://aws.amazon.com/message/41926/)

**Business impact.** S3 supports customers' storage and applications and dependent AWS services were affected. Revenue, customer counts, failed transactions, and individual SLA outcomes are **Not disclosed in the official incident report.** Inference: customers relying on US-EAST-1 S3 for object access or as a dependency for compute/storage workflows could not complete some operations during the event. [AWS summary](https://aws.amazon.com/message/41926/)

**Prevention.** AWS slowed capacity removal, added minimum-capacity safeguards, audited other operational tools, expedited S3 cell partitioning, and changed its Service Health Dashboard console to run across multiple regions after its S3 dependency prevented service-specific updates. [AWS summary](https://aws.amazon.com/message/41926/)

### 4.5 Atlassian — April 2022 site deletion incident

**Official sources:** [Atlassian post-incident review](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage); [Atlassian status history](https://status.atlassian.com/history); [customer updates](https://community.atlassian.com/forums/discussion/2000572/updates-and-q-a-on-active-incident-affecting-atlassian-products). The PIR provides the authoritative details; the official status history URL is the status hub.

**Date and duration.** April 5, 2022, beginning 07:38 UTC. 883 sites representing 775 customers were deleted in a 23-minute script run. Restoration began April 8; all customers were restored by April 18. The outage lasted up to 14 days for a subset. [PIR](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)

**Affected products and symptoms.** Jira family products, Confluence, Atlassian Access, Opsgenie, and Statuspage were unavailable for affected customers. Some customer contact information was deleted, complicating support contact. [PIR](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)

**Technical cause and recovery.** A script intended to delete a legacy Insight app used whole cloud-site IDs. The API accepted both site and app identifiers without a warning or type check, so it deleted customer sites. A cross-team communication gap and inadequate safeguard allowed the wrong IDs to be used. Atlassian's cross-functional teams restored and validated affected customer sites, first beginning April 8 and completing by April 18. [PIR](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)

**Business impact and published measures.** 775 customers and 883 sites affected; up to 14 days of outage for a subset. Atlassian said over 99.6% of its customers/users continued using cloud products without disruption and no customer lost more than five minutes of data. Revenue and SLA credits actually paid are **Not disclosed in the official incident report.** Atlassian referred to published SLAs and a credit request process in its report, but that does not establish which customers received credits. [PIR](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)

**Prevention.** Atlassian blocked bulk site deletes pending safeguards; committed to universal soft deletes, staged rollout and tested rollback, expanded multi-site disaster recovery automation and drills, improved large-incident coordination, and stronger communication and customer-contact backups. [PIR](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)

## 5. Recommended incident — ready-to-enter data

### INCIDENT DATA — READY TO ENTER

**Incident title:** Cloudflare network outage after BGP prefix policy change (June 21, 2022)

**Affected service:** Cloudflare network

**Description:** On June 21, 2022 at 06:27 UTC, a network configuration rollout reached Cloudflare data centers using the Multi-Colo PoP architecture. The change reordered terms in a BGP prefix advertisement policy so the `REJECT-THE-REST` rule preceded site-local prefix advertisements. This withdrew critical site-local prefixes, disrupting access to affected Cloudflare locations and customer origins. The internal Multimog load balancer could no longer forward requests between MCP servers, overloading smaller compute clusters. Nineteen data centers were affected; the last configuration revert completed at 07:42 UTC and the incident was closed at 08:00 UTC. [Cloudflare postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Severity:** `critical` — IncidentIQ's allowed values include `critical`, `high`, `medium`, and `low`. This is a recommended demo classification based on broad traffic impact: 19 locations that carried 50% of Cloudflare's global requests were affected. This is our classification, not a severity value published by Cloudflare. [Postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)

**Environment:** `production` — the report describes real Cloudflare customer traffic and infrastructure.

**Error message:** Leave blank. Cloudflare documented route withdrawal, origin reachability and load-balancing failures but did not publish an exact customer-facing HTTP error string. If a visual error is needed for a separate demo-only log, label it **illustrative; not a Cloudflare log** (for example, `Illustrative only: upstream connection unavailable during network reachability incident`).

**Deployment ID:** Leave blank. No public deployment identifier was reported.

**System metrics — JSON:**

```json
{
  "affected_data_centers": 19,
  "affected_locations_share_of_network_percent": 4,
  "affected_locations_share_of_global_requests_percent": 50,
  "minutes_from_start_to_last_revert": 75,
  "minutes_from_start_to_incident_close": 93
}
```

All values above are directly calculated from or explicitly stated in the official timeline (the two duration values are arithmetic from published timestamps). These are incident-level documented facts, not per-host telemetry. The backend accepts scalar metric values. The calculated durations are transparent arithmetic, not a new company measurement.

**Supported POST payload for the form/API:**

```json
{
  "title": "Cloudflare network outage after BGP prefix policy change (June 21, 2022)",
  "description": "On June 21, 2022 at 06:27 UTC, a network configuration rollout reached Cloudflare data centers using the Multi-Colo PoP architecture. The change reordered terms in a BGP prefix advertisement policy so the REJECT-THE-REST rule preceded site-local prefix advertisements. This withdrew critical site-local prefixes, disrupting access to affected Cloudflare locations and customer origins. The internal Multimog load balancer could no longer forward requests between MCP servers, overloading smaller compute clusters. Nineteen data centers were affected; the last configuration revert completed at 07:42 UTC and the incident was closed at 08:00 UTC.",
  "service_name": "Cloudflare network",
  "environment": "production",
  "severity": "critical",
  "error_messages": [],
  "system_metrics": {
    "affected_data_centers": 19,
    "affected_locations_share_of_network_percent": 4,
    "affected_locations_share_of_global_requests_percent": 50,
    "minutes_from_start_to_last_revert": 75,
    "minutes_from_start_to_incident_close": 93
  }
}
```

This deliberately omits `deployment`, since there is no public ID, and `logs`, since the form does not submit logs and no original Cloudflare log was published. The exact API permits additional fields described in section 2, but they are not needed here.

## 6. Documented evidence versus reconstructed demo evidence

### A. Publicly documented evidence

- 19 data centers affected; these represented 4% of network locations and 50% of global requests.
- Change rollout reached MCP locations at 06:27 UTC; first data center restored at 06:58; last revert at 07:42; incident closed 08:00.
- BGP policy term reordering put `REJECT-THE-REST` ahead of site-local prefix terms; critical prefixes were withdrawn.
- Internal Multimog could no longer forward between MCP servers; smaller clusters overloaded.
- Cloudflare identified process, policy design, rollout stagger, and automated commit-confirm rollback improvements.

These facts are in the [official Cloudflare postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/). No original log lines, host CPU/memory, per-request error samples, or Cloudflare deployment ID were published in the report reviewed.

### B. Reconstructed demo evidence

**None is included in the recommended incident submission payload.** If desired for a separate simulation, create unmistakably illustrative evidence such as a synthetic route withdrawal event, synthetic 5xx symptom, or synthetic route availability metric. Do not copy such evidence into the documented-facts section or represent it as Cloudflare telemetry. Since IncidentIQ's visible form has no log-entry control, any reconstructed logs would need to be entered only via an explicitly labeled supported API `logs` item or described verbally; do not claim they came from Cloudflare.

## 7. Ground truth and expected IncidentIQ investigation

### Confirmed ground truth

- **Root cause:** a network configuration change reordered BGP policy terms, causing `REJECT-THE-REST` to precede site-local advertisement rules and withdraw critical prefixes.
- **Customer/system impact:** 19 MCP data centers were impacted; they represented 4% of locations but 50% of global requests. Affected users could not reach websites/services dependent on Cloudflare in those locations. Internal balancing failure caused smaller clusters to overload.
- **Recovery:** Cloudflare engineers used backup procedures to take control of affected sites, identified and reverted the bad policy. Last revert was complete at 07:42 UTC; incident closed at 08:00 UTC.
- **Preventive work:** MCP-specific change procedure and testing, policy redesign to prevent unintended term ordering, stronger rollout staggering, automated commit-confirm rollback.
- **Evidence:** [Cloudflare postmortem](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/) (timeline, technical configuration detail, measured impact, remediation).

### Expected IncidentIQ findings (hypotheses, not confirmed company findings)

The IncidentIQ model's output must be described as its analysis of submitted evidence. The known postmortem ground truth should be checked independently after each run.

1. **Hypothesis: Network routing/prefix advertisement changed immediately before reachability loss.** Evidence: submitted description has BGP policy reordering and critical prefix withdrawal. Investigation: compare config versions and rollout timestamps; inspect route advertisements and withdrawals by site; correlate with reachability probes.
2. **Hypothesis: Internal load balancing amplified the initial routing issue.** Evidence: documented Multimog inability to forward and overload in smaller clusters. Investigation: inspect inter-server forwarding, cluster-level request distribution, saturation and health around 06:27–07:42 UTC.
3. **Hypothesis: The issue is geographically concentrated in MCP data centers.** Evidence: incident affected 19 MCP sites; other locations continued to operate. Investigation: compare probes and request outcomes by site/region and architecture cohort.
4. **Recommended corrective actions:** freeze further rollout, verify actual route state, revert the implicated policy safely, restore site access via documented failover/control procedures, balance traffic after reachability returns, then add MCP-specific staged rollout tests and commit-confirm rollback.

**Unsupported/incorrect findings:** claiming a database, memory, CPU, or deployment binary caused the incident; asserting an exact HTTP error or request failure rate; assigning a deployment ID; claiming all Cloudflare sites or customers were down; claiming revenue loss or a specific user/customer count; presenting the submitted incident narrative as Cloudflare's original logs; or calling an AI hypothesis the verified cause before comparing it with the cited postmortem.

## 8. MEMORY_OFF vs MEMORY_ON demonstration plan

Use a clearly marked **simulated follow-up incident**, not a claim that Cloudflare experienced a second real event. Store the historic Cloudflare incident as a research fixture with source citations. A possible follow-up can simulate a later BGP policy rollout with a different configuration regression; label every added symptom and metric as illustrative.

1. Submit and investigate the documented Cloudflare incident in `MEMORY_OFF`; save the exact run output and mode. This analysis uses only current incident evidence.
2. Compare the output against the official postmortem. An engineer enters the confirmed root cause and actual recovery as the reviewed resolution, with explicit confirmation. Do not merely approve the model's answer.
3. Retain through the verified-resolution workflow. Verify the app reports successful/duplicate-skipped Hindsight retention; a failed/missing retention is not learning.
4. Create a second, clearly labeled **synthetic** related routing incident. Include only synthetic evidence for that follow-up and keep its status distinct from the real historical record.
5. Run that follow-up in `MEMORY_OFF`; save hypotheses, recommendations, limitations, and evidence references.
6. Run the same follow-up evidence in `MEMORY_ON`; inspect recalled memory text and provenance. Confirm it is marked historical/verified-resolution and not current proof.
7. Compare returned hypotheses and recommendations side by side. Report differences without claiming increased accuracy, confidence, or lower MTTR unless an independently designed evaluation demonstrates that result.

The Hindsight service supports `incident` observations, engineer-verified `verified_resolution`, and `failed_approach` memories as separate types. `MEMORY_OFF` skips recall; `MEMORY_ON` recalls relevant memories before analysis. Historical memory is contextual evidence, not proof of the next root cause. Do not automatically retain AI-generated hypotheses. See `backend/app/services/hindsight_service.py`, `backend/app/services/investigation_service.py`, and the UI demo flow in `frontend/src/App.jsx`.

## 9. Limitations and data gaps

- Public postmortems do not provide raw customer logs or consistent request-level metrics. No original logs are supplied here.
- Cloudflare did not disclose customer count, a numeric HTTP error rate, revenue loss, real deployment ID, or exact customer error text in the postmortem reviewed.
- Percent of global requests is a reported share of traffic handled by affected locations, **not** the percentage of all requests that failed.
- The application has a metrics JSON field, but its incident table stores arbitrary scalar values without evidence provenance on each metric. Keep the source report alongside the record and mark the selected metrics as incident-level facts in the description.
- An incident in Hindsight's persistent bank may interact with other retained memories. Use an isolated demo bank as indicated in `README.md`, and inspect recall output. Do not clear or overwrite existing project memory or database records as part of this research task.
- Severity choice is a demo classification; company incident-severity labels may differ or be absent.
- IncidentIQ has no API authentication per repository documentation. Do not expose it publicly or submit sensitive production incidents.

## 10. Recommendation

Use **Cloudflare June 21, 2022** for the final-round project demonstration. It combines an understandable but nontrivial chain—configuration rollout, BGP route withdrawal, origin/reachability loss, and load-balancer overload—with an official postmortem, exact timeline, 19-location scope, and a particularly useful business statistic: locations representing 4% of the network handled 50% of requests. It maps directly to the current form's affected service, description, severity, environment, and JSON metrics. It also creates a natural basis for a separately labeled synthetic follow-up when showing Hindsight.

Google Cloud offers richer error percentages and broader failure complexity, making it a strong alternative for a metrics-heavy investigation. GitHub is the best database/failover example and has queue/backlog counts but fewer directly usable operational metrics. Atlassian offers the strongest disclosed customer count and business recovery story, but the event centers on accidental deletion rather than performance signals. AWS offers a clear capacity-removal failure, but less published business measurement. Cloudflare is the best balance of causal clarity, operational complexity, customer relevance, documented quantitative evidence, and fit to IncidentIQ's existing fields.

## 11. References

- [Cloudflare: outage on June 21, 2022](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/)
- [Cloudflare status](https://www.cloudflarestatus.com/)
- [Google Cloud Networking Incident #19009](https://status.cloud.google.com/incident/cloud-networking/19009)
- [Google Cloud follow-up on June 2 disruption](https://cloud.google.com/blog/topics/inside-google-cloud/an-update-on-sundays-service-disruption)
- [GitHub: October 21 post-incident analysis](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)
- [GitHub: October 21 incident report](https://github.blog/news-insights/company-news/october21-incident-report/)
- [GitHub status](https://www.githubstatus.com/)
- [AWS: S3 US-EAST-1 service disruption summary](https://aws.amazon.com/message/41926/)
- [AWS Health Dashboard](https://health.aws.amazon.com/health/status)
- [Atlassian: April 2022 post-incident review](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage)
- [Atlassian status history](https://status.atlassian.com/history)
- [Atlassian customer updates](https://community.atlassian.com/forums/discussion/2000572/updates-and-q-a-on-active-incident-affecting-atlassian-products)
