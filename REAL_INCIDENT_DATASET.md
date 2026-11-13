# Real Incident Dataset

> Research snapshot: 2026-11-13. This curated collection is not a statistically representative sample of global outages. Each verified record cites at least one official company source. Verified describes source provenance for the populated record, not access to company-internal telemetry or an independent re-performance of the company investigation.

## Collection overview

- **Verified incidents:** 35 across 9 companies.
- **Date range:** 2011-04-21 through 2026-03-25.
- **Records with source-published metrics:** 34.
- **Records with a published incident duration or impact window:** 34.
- The category field is one primary classification per incident. Category counts therefore sum to the catalog size; the taxonomy is not a multi-label count.
- Severity is IncidentIQ?s impact-based classification with a written basis. It is not a severity label assigned by the reporting company.
- Unavailable customer counts, transaction/request failure ratios, revenue, deployment IDs, original logs, and metrics remain unknown. No company telemetry was manufactured.

## Taxonomy coverage

| Primary incident category | Verified examples |
|---|---:|
| Database failures | 3 |
| Database connection exhaustion | 2 |
| API failures | 0 |
| HTTP 500 errors | 0 |
| HTTP 502 errors | 0 |
| HTTP 503 errors | 0 |
| Network outages | 7 |
| DNS failures | 1 |
| BGP routing failures | 2 |
| Cloud infrastructure failures | 5 |
| Authentication failures | 2 |
| Authorization failures | 0 |
| Deployment failures | 2 |
| Configuration errors | 1 |
| Cache failures | 0 |
| Redis failures | 0 |
| Message queue failures | 2 |
| Storage failures | 3 |
| Disk exhaustion | 0 |
| CPU exhaustion | 1 |
| Memory exhaustion | 0 |
| Kubernetes failures | 1 |
| Container failures | 0 |
| Load balancer failures | 0 |
| CDN failures | 1 |
| Payment processing failures | 0 |
| Third-party dependency failures | 0 |
| Data consistency problems | 1 |
| Data corruption incidents | 1 |
| Security incidents | 0 |
| Certificate and TLS failures | 0 |
| Service discovery failures | 0 |
| Monitoring and observability failures | 0 |
| Backup and recovery failures | 0 |
| Application-level bugs | 0 |

## Comparison table

| Company | Date | Incident | Service | Category | Severity | Duration / impact window | Published metrics | Primary source |
|---|---|---|---|---|---|---|---|---|
| Cloudflare | 2019-07-02 | Global HTTP 502 service disruption | Cloudflare CDN | CPU exhaustion | critical | About 30 minutes | traffic_drop_at_worst: **82 percent** (Cloudflare network traffic) | [Official source](https://blog.cloudflare.com/cloudflare-outage/) |
| Cloudflare | 2020-04-15 | Cloudflare Dashboard and API availability incident | Cloudflare Dashboard, Cloudflare API | Network outages | high | 4 hours 21 minutes to Dashboard/API recovery; full redundancy at 20:31 UTC | incident_duration: **261 minutes** (Dashboard/API) | [Official source](https://blog.cloudflare.com/cloudflare-dashboard-and-api-outage-on-april-15-2020/) |
| Cloudflare | 2022-06-21 | Cloudflare global network disruption affecting 19 data centers | Cloudflare Network, Cloudflare CDN | BGP routing failures | critical | 75 minutes to last revert; 93 minutes to incident closure | affected_data_centers: **19 data centers** (Cloudflare MCP network); affected_locations_share_network: **4 percent** (Cloudflare network locations); affected_share_requests: **50 percent** (Global requests) | [Official source](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/) |
| Cloudflare | 2023-01-24 | Cloudflare multi-service availability incident | Cloudflare Workers, Cloudflare Zero Trust, Cloudflare CDN control plane | Authentication failures | high | 121 minutes | duration: **121 minutes** (Several Cloudflare services) | [Official source](https://blog.cloudflare.com/cloudflare-incident-on-january-24th-2023) |
| Cloudflare | 2023-10-30 | Workers KV and dependent service disruption | Cloudflare Workers KV, Cloudflare services depending on KV | Deployment failures | high | 37 minutes | duration: **37 minutes** (Multiple Cloudflare services) | [Official source](https://blog.cloudflare.com/cloudflare-incident-on-october-30-2023/) |
| Cloudflare | 2023-11-02 | Cloudflare control-plane and analytics outage | Cloudflare control plane, Cloudflare analytics | Cloud infrastructure failures | high | 40 hours 41 minutes; most control plane restored after 6 hours 13 minutes | duration: **40.68 hours** (Control plane and analytics) | [Official source](https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/) |
| Cloudflare | 2025-02-06 | Cloudflare R2 service outage | Cloudflare R2, Cloudflare Stream, Cloudflare Images, Cache Reserve, Vectorize, Log Delivery | Storage failures | high | 59 minutes for primary R2 outage; secondary 23-minute window | r2_outage_duration: **59 minutes** (R2); durable_objects_error_increase: **0.09 percent** (North America Durable Objects, 09:13–09:36 UTC) | [Official source](https://blog.cloudflare.com/cloudflare-incident-on-february-6-2025/) |
| Cloudflare | 2025-08-21 | Cloudflare customer origin connectivity disruption | Cloudflare-to-AWS us-east-1 connectivity | Network outages | high | 3h11m to substantial reduction; 3h51m until intermittent latency ended | impact_start_to_substantial_reduction: **191 minutes** (Cloudflare/AWS us-east-1 path); impact_end: **231 minutes** (Cloudflare/AWS us-east-1 path) | [Official source](https://blog.cloudflare.com/cloudflare-incident-on-august-21-2025) |
| GitHub | 2018-10-21 | October 21 post-incident analysis | GitHub.com metadata services, Webhooks, GitHub Pages | Data consistency problems | high | 24 hours 11 minutes | degradation_duration: **24.18 hours** (GitHub services); queued_webhooks: **5000000 events minimum** (Webhook backlog); queued_pages_builds: **80000 builds** (GitHub Pages); dropped_webhook_payloads: **200000 approximate payloads** (Expired webhook backlog) | [Official source](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/) |
| GitHub | 2020-02-19 | February 19 database resource-contention incident | GitHub.com services on mysql1 | Database connection exhaustion | high | 52 minutes | duration: **52 minutes** (mysql1 dependent services) | [Official source](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/) |
| GitHub | 2020-02-20 | February 20 ProxySQL degradation during master promotion | GitHub.com services on mysql1 | Database failures | high | 47 minutes | duration: **47 minutes** (mysql1 dependent services) | [Official source](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/) |
| GitHub | 2020-02-25 | February 25 ProxySQL file-descriptor-limit incident | GitHub.com mysql1 writes | Database connection exhaustion | high | 2 hours 12 minutes | duration: **132 minutes** (mysql1 dependent services); configured_limit: **1073741824 file descriptors** (Intended LimitNOFILE); effective_limit: **65536 file descriptors** (ProxySQL process limit) | [Official source](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/) |
| GitHub | 2020-02-27 | February 27 database load incident | GitHub.com services dependent on mysql1 | Database failures | high | 4 hours 23 minutes | duration: **263 minutes** (mysql1 dependent services); post-incident_deployment_freeze: **3 days** (GitHub production deployments) | [Official source](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/) |
| GitHub | 2023-05-09 | May 9 Git database degradation after configuration change | GitHub Git databases, Git operations, Pull requests, Actions | Configuration errors | high | Just over one hour of primary downtime; some data recovery continued afterward | main_services_degraded: **8 of 10 services** (GitHub status portal) | [Official source](https://github.blog/news-insights/company-news/addressing-githubs-recent-availability-issues/) |
| Google Cloud | 2019-05-20 | Cloud Pub/Sub metadata hotspot incident | Cloud Pub/Sub, Cloud SQL, Cloud Filestore, App Engine Task Queues | Message queue failures | high | 3 hours 30 minutes | publish_error_rate: **1.2 percent** (Cloud Pub/Sub publish); publish_p99_latency_increase: **8.3 seconds** (Cloud Pub/Sub publish); publish_admin_error_rate: **8.3 percent** (Pub/Sub publish admin operations); subscribe_admin_error_rate: **3.2 percent** (Pub/Sub subscribe admin operations) | [Official source](https://status.cloud.google.com/incident/cloud-pubsub/19001) |
| Google Cloud | 2019-06-02 | Google Cloud Networking incident #19009 | Compute Engine, App Engine, Cloud Endpoints, Cloud Interconnect, Cloud VPN, Cloud Pub/Sub, BigQuery, Cloud Storage | Network outages | critical | 3h19–4h25 depending on region | pubsub_successful_requests_global_drop: **27 percent** (Global Pub/Sub publish/subscribe during incident); app_engine_us_central_rps_drop: **23.2 percent** (App Engine us-central1); endpoints_peak_error_rate: **4.4 percent** (Cloud Endpoints at onset); cloud_storage_us_west2_error_rate: **96.2 percent** (Cloud Storage bucket requests, us-west2 average) | [Official source](https://status.cloud.google.com/incident/cloud-networking/19009) |
| Google Cloud | 2019-10-22 | Google Cloud Networking incident #19020 | Compute Engine, Cloud Router, Cloud VPN, Memorystore, Kubernetes Engine, Cloud SQL, Bigtable | Network outages | critical | 2 hours 31 minutes | gce_instances_packet_loss_affected: **20 percent of instances** (us-west1-b); affected_instances_packet_loss: **100 percent** (Affected instances); cloud_router_affected: **20 percent** (us-west1 region); cloud_vpn_affected: **6 percent** (us-west1 region) | [Official source](https://status.cloud.google.com/incident/cloud-networking/19020) |
| Google Cloud | 2019-11-11 | Google Cloud regional service disruption involving Cloud KMS | Cloud IAM, Pub/Sub, Compute Engine, App Engine, Cloud Functions, Cloud Storage, Cloud Console | Cloud infrastructure failures | critical | 48 minutes core impact; some service tails longer | cloud_iam_us_east1_errors: **94.5 percent average** (Cloud IAM during incident); gcs_us_east1_errors: **99 percent average** (Cloud Storage buckets during incident); compute_engine_api_errors: **16 percent** (GCE API requests); pubsub_publish_errors: **15 percent average** (Cloud Pub/Sub publish operations) | [Official source](https://status.cloud.google.com/incident/cloud-datastore/19006) |
| Google Cloud | 2020-06-29 | Us-east1 data-center fuel delivery failure | Compute Engine, Persistent Disk, Cloud VPN, Network Load Balancing | Cloud infrastructure failures | critical | 1h30 for major GCE impact; some disks up to 28h | us_east1_c_instances_unavailable: **22.5 percent** (Compute Engine us-east1-c for 90 minutes); persistent_disk_devices_affected: **0.0267 percent** (PD devices us-east1-c); regional_packet_loss: **5 percent** (Public IP and Network Load Balancer traffic) | [Official source](https://status.cloud.google.com/incidents/Wb97fPsnE5VdLaKDcAeP) |
| Google Cloud | 2020-12-09 | Networking disruption in europe-west2-a | Google Cloud Networking, Memorystore, Cloud VPN, App Engine Flex | Network outages | high | 1h24 network; longer dependency recovery | network_disruption: **84 minutes** (europe-west2-a); memorystore_redis_instances_unhealthy: **1.5 percent** (europe-west2; lasted 2h24); classic_vpn_tunnels_unavailable: **4.5 percent** (europe-west2; lasted 8h10) | [Official source](https://status.cloud.google.com/incidents/qRpmq9arsrCV7xWdfftF) |
| AWS | 2011-04-21 | US East EBS and EC2 disruption | Amazon EBS, Amazon EC2, Amazon RDS | Storage failures | critical | Several days for residual volume restoration | affected_az_ebs_volumes_stuck: **13 percent** (Peak affected AZ); unrestorable_volumes: **0.07 percent** (Volumes in affected AZ); single_az_rds_stuck_io_peak: **45 percent** (RDS single-AZ instances in affected zone) | [Official source](https://aws.amazon.com/message/65648/) |
| AWS | 2017-02-28 | S3 service disruption in US-EAST-1 | Amazon S3, EC2, EBS, Lambda | Storage failures | high | 4 hours 17 minutes for S3 normal operations | s3_recovery_duration: **257 minutes** (S3 US-EAST-1) | [Official source](https://aws.amazon.com/message/41926/) |
| AWS | 2018-11-22 | EC2 DNS resolution issue in Seoul region | Amazon EC2 DNS resolver | DNS failures | high | 1 hour 24 minutes | duration: **84 minutes** (EC2 DNS in Seoul) | [Official source](https://aws.amazon.com/message/74876-2/) |
| AWS | 2019-08-23 | EC2 and EBS service disruption in Tokyo | Amazon EC2, Amazon EBS, RDS, ElastiCache | Cloud infrastructure failures | high | Majority recovered by 18:30 JST | cooling_restored_minutes: **165 minutes after event start** (Affected Tokyo AZ); majority_resource_recovery_minutes: **354 minutes after event start** (Affected Tokyo AZ) | [Official source](https://aws.amazon.com/message/56489/) |
| AWS | 2020-11-25 | Kinesis and dependent AWS services disruption in US-EAST-1 | Amazon Kinesis, CloudWatch, Lambda, EventBridge, ECS, EKS | Message queue failures | high | Varied by dependent service | kinesis_normal_recovery_time: **10:23 PM PST** (Kinesis Data Streams); cognito_normal_recovery_time: **2:18 PM PST** (Cognito User Pools and Identity Pools); lambda_invocation_error_mitigation_time: **10:36 AM PST** (Lambda invocation errors associated with metric-buffer memory contention); cloudwatch_metrics_alarm_recovery_time: **10:31 PM PST** (CloudWatch metrics and alarms) | [Official source](https://aws.amazon.com/message/11201/) |
| AWS | 2021-09-02 | Direct Connect packet loss in Tokyo | AWS Direct Connect, Tokyo VPC connectivity | Network outages | high | 6 hours 12 minutes | impact_to_full_recovery: **372 minutes** (Direct Connect Tokyo) | [Official source](https://aws.amazon.com/tw/message/17908/) |
| AWS | 2021-12-07 | US-EAST-1 internal network congestion event | EC2 APIs, RDS, EMR, WorkSpaces, Internal monitoring, Internal DNS | Network outages | high | Several hours; service recovery varied | ec2_api_recovery_start: **1:15 PM PST** (EC2 API improvements); new_ec2_launch_recovery: **2:40 PM PST** (new EC2 launches) | [Official source](https://aws.amazon.com/message/12721/) |
| Meta | 2021-10-04 | October 4 global backbone/DNS outage | Facebook, Instagram, WhatsApp, Meta internal tools | BGP routing failures | high | Not disclosed in the official incident report. | Not disclosed in the official incident report. | [Official source](https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/) |
| Fastly | 2021-06-08 | Global outage triggered by valid customer configuration | Fastly edge network, Customer websites | CDN failures | critical | 95% normal within 49 minutes; resolved 2h57 after onset | network_error_scope: **85 percent** (Fastly network); network_normal_after: **95 percent** (Fastly network) | [Official source](https://www.fastly.com/blog/summary-of-june-8-outage) |
| Dropbox | 2014-01-10 | Database outage during scheduled machine maintenance | Dropbox website, Photo sharing, Camera uploads, Some API features | Database failures | high | Most service ~3h; core restored Sunday 16:40 PT | most_functionality_recovery: **180 minutes** (Dropbox service) | [Official source](https://dropbox.tech/infrastructure/outage-post-mortem) |
| Atlassian | 2022-04-05 | April 2022 customer site deletion incident | Jira, Confluence, Atlassian Access, Opsgenie, Statuspage | Data corruption incidents | critical | Up to 14 days for subset; all restored Apr 18 | sites_deleted: **883 sites** (Atlassian sites); customers_affected: **775 customers** (Atlassian official customer definition); customers_unaffected: **99.6 percent minimum** (Customers/users); maximum_data_loss: **5 minutes** (Any affected customer) | [Official source](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage) |
| Discord | 2023-11-06 | Authentication outage caused by ScyllaDB overload | Discord authentication, Discord messaging | Authentication failures | critical | Approximately 50 minutes | http_200_availability: **25 percent** (Discord requests during outage) | [Official source](https://discord.com/blog/authentication-outage) |
| Discord | 2026-03-25 | Voice and video outage after session configuration update | Discord Voice, Discord Video | Kubernetes failures | critical | 3 hours 17 minutes | session_servers_lost: **17 percent** (Discord session service) | [Official source](https://discord.com/blog/behind-the-scenes-of-the-3-25-26-voice-outage) |
| Google Cloud | 2024-09-07 | Google Cloud asia-northeast1 multi-service incident | Cloud Build, Dataflow, Cloud Deploy, Cloud SQL, Compute Engine, GKE | Deployment failures | high | 1 hour 50 minutes | duration: **110 minutes** (asia-northeast1 products) | [Official source](https://status.cloud.google.com/incidents/XwnegjADrYy2GHJphG2V) |
| Google Cloud | 2024-10-29 | Google Cloud australia-southeast2 multi-service incident | Apigee, Batch, Filestore, Firestore, KMS, Cloud Run, BigQuery, Dataflow, Pub/Sub, Cloud SQL, GCS, Compute Engine, GKE, IAM | Cloud infrastructure failures | critical | 3h13 overall; longest impact 2h03 | overall_duration: **193 minutes** (Google Cloud australia-southeast2); longest_regional_impact: **123 minutes** (Affected services) | [Official source](https://status.cloud.google.com/incidents/Pvq1RGrACDwogEE8hcrm) |

## Incident evidence records

### 1. Cloudflare ? Global HTTP 502 service disruption

**ID / date / environment:** `cloudflare-2019-07-cpu-502` ? 2019-07-02 ? production
**Affected products/services:** Cloudflare CDN, Cloudflare-proxied websites / Cloudflare CDN
**Primary category / type:** CPU exhaustion / outage
**IncidentIQ severity:** critical ? Global 502 responses with an 82% worst-point traffic drop; classification is IncidentIQ's.

**Customer-facing symptoms:** HTTP 502 responses; CPU reached 100% worldwide

**Technical root cause:** A deployed regular expression caused CPU utilization to spike to 100% across machines worldwide; Cloudflare rolled back the deployment.

**Customer impact:** Visitors to Cloudflare-proxied sites received 502 errors; traffic fell by 82% at the worst point.

**Business impact:** Visitors to Cloudflare-proxied sites received 502 errors; traffic fell by 82% at the worst point.

**Duration:** About 30 minutes

**Source-published metrics:** traffic_drop_at_worst: **82 percent** (Cloudflare network traffic)

**Recovery actions:** Rolled back the bad software deployment; service returned to normal.

**Preventive actions:** Review the deployment and testing process; the short postmortem says a full review was underway.

**Data gaps:** Exact start/end recovery timestamps beyond the approximate duration are not recorded here.

**Primary source:** [postmortem ? 2019-07-02](https://blog.cloudflare.com/cloudflare-outage/). The official postmortem identifies 502 errors, 100% CPU and an 82% traffic drop, and attributes the event to a bad software deployment. It describes rollback. (record last reviewed 2026-11-13)

### 2. Cloudflare ? Cloudflare Dashboard and API availability incident

**ID / date / environment:** `cloudflare-2020-04-dashboard-api` ? 2020-04-15 ? production
**Affected products/services:** Cloudflare Dashboard, Cloudflare API, Cloudflare edge proxy, Cloudflare security services / Cloudflare Dashboard, Cloudflare API
**Primary category / type:** Network outages / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Dashboard login unavailable; API unavailable; Customers could not make configuration changes, purge cache, or access some analytics

**Technical root cause:** During planned cabinet retirement, technicians disconnected a patch panel providing external connectivity from a core data center; the patch panel was a physical single point of failure.

**Customer impact:** Dashboard and API unavailable 15:31–19:52 UTC. Core customer website proxying and several security products continued normally.

**Business impact:** Dashboard and API unavailable 15:31–19:52 UTC. Core customer website proxying and several security products continued normally.

**Duration:** 4 hours 21 minutes to Dashboard/API recovery; full redundancy at 20:31 UTC

**Source-published metrics:** incident_duration: **261 minutes** (Dashboard/API)

**Recovery actions:** Restored connectivity links; first backup link had 10 Gbps capacity; restored the Dashboard/API and then full redundant connectivity.

**Preventive actions:** Distribute connectivity across physical panels; label cables/panels; explicitly identify cabling that maintenance must not touch.

**Data gaps:** Customer count and financial/SLA impact are not disclosed.

**Primary source:** [postmortem ? 2020-04-16](https://blog.cloudflare.com/cloudflare-dashboard-and-api-outage-on-april-15-2020/). Official report states the maintenance task disconnected a patch panel; dashboard/API were unavailable 15:31–19:52 UTC, while edge proxy/security continued. A backup link was 10 Gbps. (record last reviewed 2026-11-13)

### 3. Cloudflare ? Cloudflare global network disruption affecting 19 data centers

**ID / date / environment:** `cloudflare-2022-06-bgp` ? 2022-06-21 ? production
**Affected products/services:** Cloudflare CDN, Cloudflare network / Cloudflare Network, Cloudflare CDN
**Primary category / type:** BGP routing failures / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Affected locations became unreachable; Internal Multimog forwarding between MCP servers stopped; Smaller clusters overloaded

**Technical root cause:** A BGP advertisement policy term reorder placed REJECT-THE-REST before site-local prefix advertisement terms, withdrawing critical site-local prefixes; Multimog could no longer forward between servers.

**Customer impact:** 19 data centers (4% of locations) handled 50% of global requests. Last revert completed at 07:42 UTC; incident closed at 08:00 UTC.

**Business impact:** 19 data centers (4% of locations) handled 50% of global requests. Last revert completed at 07:42 UTC; incident closed at 08:00 UTC.

**Duration:** 75 minutes to last revert; 93 minutes to incident closure

**Source-published metrics:** affected_data_centers: **19 data centers** (Cloudflare MCP network); affected_locations_share_network: **4 percent** (Cloudflare network locations); affected_share_requests: **50 percent** (Global requests)

**Recovery actions:** Engineers used backup procedures to access affected sites, found the routing-policy issue and reverted it.

**Preventive actions:** Add MCP-specific tests and rollout procedures; redesign policy to prevent term reordering; improve rollout staggering; add automated commit-confirm rollback.

**Data gaps:** Customer count, failed request percentage, revenue, SLA outcome, raw logs and deployment ID not disclosed.

**Primary source:** [postmortem ? 2022-06-21](https://blog.cloudflare.com/cloudflare-outage-on-june-21-2022/). The official postmortem gives the timeline, 19 data centers, 4%/50% traffic scope, policy ordering and recovery actions. (record last reviewed 2026-11-13)

### 4. Cloudflare ? Cloudflare multi-service availability incident

**ID / date / environment:** `cloudflare-2023-01-service-tokens` ? 2023-01-24 ? production
**Affected products/services:** Cloudflare Workers, Cloudflare Zero Trust, Cloudflare CDN / Cloudflare Workers, Cloudflare Zero Trust, Cloudflare CDN control plane
**Primary category / type:** Authentication failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Service-token-dependent services degraded; Workers and Zero Trust features unavailable; CDN control-plane functions degraded

**Technical root cause:** An error in the release of code managing service tokens disrupted token-based authentication.

**Customer impact:** Multiple products unavailable for 121 minutes; exact customer count and request error percentage not disclosed.

**Business impact:** Multiple products unavailable for 121 minutes; exact customer count and request error percentage not disclosed.

**Duration:** 121 minutes

**Source-published metrics:** duration: **121 minutes** (Several Cloudflare services)

**Recovery actions:** Cloudflare mitigated the faulty release and restored affected services.

**Preventive actions:** Postmortem describes release/validation and service dependency improvements; see source for detailed action list.

**Data gaps:** No customer count or revenue impact disclosed.

**Primary source:** [postmortem ? 2023-01-25](https://blog.cloudflare.com/cloudflare-incident-on-january-24th-2023). The official report states several services were unavailable for 121 minutes because of an error releasing service-token code. (record last reviewed 2026-11-13)

### 5. Cloudflare ? Workers KV and dependent service disruption

**ID / date / environment:** `cloudflare-2023-10-workers-kv` ? 2023-10-30 ? production
**Affected products/services:** Workers KV, Cloudflare services relying on KV / Cloudflare Workers KV, Cloudflare services depending on KV
**Primary category / type:** Deployment failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Workers KV-dependent services unavailable; Customer-facing data/control-plane features degraded

**Technical root cause:** A misconfiguration in a deployment tool used by Workers KV caused a service outage.

**Customer impact:** Multiple services unavailable for 37 minutes; customer count and request-failure percentage not disclosed.

**Business impact:** Multiple services unavailable for 37 minutes; customer count and request-failure percentage not disclosed.

**Duration:** 37 minutes

**Source-published metrics:** duration: **37 minutes** (Multiple Cloudflare services)

**Recovery actions:** Cloudflare corrected the Workers KV deployment-tool configuration and recovered services.

**Preventive actions:** Postmortem details deployment-tool safeguards and recovery improvements.

**Data gaps:** Exact user count and financial/SLA impact not disclosed.

**Primary source:** [postmortem ? 2023-11-01](https://blog.cloudflare.com/cloudflare-incident-on-october-30-2023/). Official postmortem names the deployment tool misconfiguration and 37-minute outage. (record last reviewed 2026-11-13)

### 6. Cloudflare ? Cloudflare control-plane and analytics outage

**ID / date / environment:** `cloudflare-2023-11-control-plane` ? 2023-11-02 ? production
**Affected products/services:** Cloudflare control plane, Cloudflare analytics, Cloudflare edge network / Cloudflare control plane, Cloudflare analytics
**Primary category / type:** Cloud infrastructure failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Dashboard/control plane unavailable; Analytics and raw logs unavailable for most customers; Network/security traffic continued operating

**Technical root cause:** Failure of a core data-center provider exposed non-obvious dependencies in Cloudflare's control plane and analytics recovery architecture.

**Customer impact:** Incident lasted 2023-11-02 11:44 UTC to 2023-11-04 04:25 UTC; most control plane restored at 17:57 UTC on Nov 2.

**Business impact:** Incident lasted 2023-11-02 11:44 UTC to 2023-11-04 04:25 UTC; most control plane restored at 17:57 UTC on Nov 2.

**Duration:** 40 hours 41 minutes; most control plane restored after 6 hours 13 minutes

**Source-published metrics:** duration: **40.68 hours** (Control plane and analytics)

**Recovery actions:** Restored most control-plane services at a disaster-recovery facility, then brought remaining services back.

**Preventive actions:** Postmortem describes dependency mapping, disaster-recovery and architecture changes.

**Data gaps:** Financial impact and customer count not disclosed.

**Primary source:** [postmortem ? 2023-11-04](https://blog.cloudflare.com/post-mortem-on-cloudflare-control-plane-and-analytics-outage/). Official postmortem gives incident interval, partial restore time, raw-log impact and states edge network/security services continued. (record last reviewed 2026-11-13)

### 7. Cloudflare ? Cloudflare R2 service outage

**ID / date / environment:** `cloudflare-2025-02-r2` ? 2025-02-06 ? production
**Affected products/services:** R2, Stream, Images, Cache Reserve, Vectorize, Log Delivery / Cloudflare R2, Cloudflare Stream, Cloudflare Images, Cache Reserve, Vectorize, Log Delivery
**Primary category / type:** Storage failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** R2 operations failed; Dependent storage-backed services degraded

**Technical root cause:** Human error and insufficient validation safeguards during abuse remediation disabled the production R2 Gateway responsible for the R2 API.

**Customer impact:** R2 unavailable for 59 minutes; a later reconnect backlog caused a 0.09% increase in errors for North America Durable Objects between 09:13 and 09:36 UTC.

**Business impact:** R2 unavailable for 59 minutes; a later reconnect backlog caused a 0.09% increase in errors for North America Durable Objects between 09:13 and 09:36 UTC.

**Duration:** 59 minutes for primary R2 outage; secondary 23-minute window

**Source-published metrics:** r2_outage_duration: **59 minutes** (R2); durable_objects_error_increase: **0.09 percent** (North America Durable Objects, 09:13–09:36 UTC)

**Recovery actions:** Restored the R2 gateway; managed reconnection backlog and isolated secondary metadata impact.

**Preventive actions:** Add validation safeguards to abuse-remediation action and improve service protections.

**Data gaps:** Customer count and monetary impact not disclosed.

**Primary source:** [postmortem ? 2025-02-07](https://blog.cloudflare.com/cloudflare-incident-on-february-6-2025/). Official report states duration, gateway disabled by remediation action and 0.09% secondary error increase. (record last reviewed 2026-11-13)

### 8. Cloudflare ? Cloudflare customer origin connectivity disruption

**ID / date / environment:** `cloudflare-2025-08-aws-east` ? 2025-08-21 ? production
**Affected products/services:** Cloudflare network, AWS us-east-1 origins / Cloudflare-to-AWS us-east-1 connectivity
**Primary category / type:** Network outages / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** High latency; Packet loss; Origin failures

**Technical root cause:** An unusual high-traffic event exposed insufficient network congestion management on links between Cloudflare and AWS us-east-1.

**Customer impact:** Impact began 16:27 UTC, substantially reduced by 19:38, with intermittent latency until 20:18 UTC.

**Business impact:** Impact began 16:27 UTC, substantially reduced by 19:38, with intermittent latency until 20:18 UTC.

**Duration:** 3h11m to substantial reduction; 3h51m until intermittent latency ended

**Source-published metrics:** impact_start_to_substantial_reduction: **191 minutes** (Cloudflare/AWS us-east-1 path); impact_end: **231 minutes** (Cloudflare/AWS us-east-1 path)

**Recovery actions:** Traffic impact reduced and links returned to service; Cloudflare continued investigation and mitigation.

**Preventive actions:** Postmortem documents congestion-management and capacity improvements.

**Data gaps:** Request percentage, customer count and revenue impact not disclosed.

**Primary source:** [postmortem ? 2025-08-22](https://blog.cloudflare.com/cloudflare-incident-on-august-21-2025). Official report states start/reduction/end timestamps and symptoms; root summary attributes it to insufficient congestion management. (record last reviewed 2026-11-13)

### 9. GitHub ? October 21 post-incident analysis

**ID / date / environment:** `github-2018-10-database-failover` ? 2018-10-21 ? production
**Affected products/services:** GitHub.com, GitHub Pages, Webhooks / GitHub.com metadata services, Webhooks, GitHub Pages
**Primary category / type:** Data consistency problems / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Stale or inconsistent website metadata; Webhooks and Pages builds paused; Slow cross-country database writes

**Technical root cause:** A 43-second loss of connectivity during optical equipment maintenance triggered Orchestrator failover and divergent cross-site writes; safe failback required reconciliation.

**Customer impact:** Service degradation lasted 24h11. Over five million hook events and 80,000 Pages builds queued; about 200,000 webhook payloads expired and were dropped.

**Business impact:** Service degradation lasted 24h11. Over five million hook events and 80,000 Pages builds queued; about 200,000 webhook payloads expired and were dropped.

**Duration:** 24 hours 11 minutes

**Source-published metrics:** degradation_duration: **24.18 hours** (GitHub services); queued_webhooks: **5000000 events minimum** (Webhook backlog); queued_pages_builds: **80000 builds** (GitHub Pages); dropped_webhook_payloads: **200000 approximate payloads** (Expired webhook backlog)

**Recovery actions:** Failed forward, restored database backups, synchronized replicas, returned to the original topology and drained queues; increased webhook TTL after discovering expired payloads.

**Preventive actions:** Improve database failover/reconciliation and recovery procedures; preserve data integrity while changing topology.

**Data gaps:** Customer count and request failure percentage not disclosed.; Manual reconciliation of a small number of writes was ongoing when the report published.

**Primary source:** [postmortem ? 2018-10-30](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/). Official analysis reports the network partition, database topology, incident duration, queue sizes, expired deliveries and no user data lost. (record last reviewed 2026-11-13)

### 10. GitHub ? February 19 database resource-contention incident

**ID / date / environment:** `github-2020-02-19-proxysql` ? 2020-02-19 ? production
**Affected products/services:** GitHub.com / GitHub.com services on mysql1
**Primary category / type:** Database connection exhaustion / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Queries inconsistently failed; Database operations stalled

**Technical root cause:** A query intended for read replicas was sent to the mysql1 master at high frequency, overloading ProxySQL and exhausting its ability to consistently perform queries.

**Customer impact:** 52-minute incident, 15:17 UTC start; exact customer count and failed request percent not disclosed.

**Business impact:** 52-minute incident, 15:17 UTC start; exact customer count and failed request percent not disclosed.

**Duration:** 52 minutes

**Source-published metrics:** duration: **52 minutes** (mysql1 dependent services)

**Recovery actions:** Applied remediation from the prior investigation to restore service.

**Preventive actions:** Improve query routing, ProxySQL operational readiness and realistic performance testing.

**Data gaps:** No per-customer or request-volume measures published.

**Primary source:** [postmortem ? 2020-03-26](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/). Official report's Feb 19 timeline identifies query misrouting, ProxySQL failure and 52-minute duration. (record last reviewed 2026-11-13)

### 11. GitHub ? February 20 ProxySQL degradation during master promotion

**ID / date / environment:** `github-2020-02-20-proxysql` ? 2020-02-20 ? production
**Affected products/services:** GitHub.com services on mysql1 / GitHub.com services on mysql1
**Primary category / type:** Database failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Service queries degraded during master promotion

**Technical root cause:** Unexpectedly high load during planned promotion of the database master triggered ProxySQL failure.

**Customer impact:** 47-minute degradation.

**Business impact:** 47-minute degradation.

**Duration:** 47 minutes

**Source-published metrics:** duration: **47 minutes** (mysql1 dependent services)

**Recovery actions:** Used remediation steps from the previous event; suspended similar maintenance while investigating.

**Preventive actions:** Improve ProxySQL operational readiness and test high-load master promotion scenarios.

**Data gaps:** Exact customer count and error percentages not published.

**Primary source:** [postmortem ? 2020-03-26](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/). Official postmortem identifies Feb 20 21:31 UTC event and 47-minute duration. (record last reviewed 2026-11-13)

### 12. GitHub ? February 25 ProxySQL file-descriptor-limit incident

**ID / date / environment:** `github-2020-02-25-proxysql` ? 2020-02-25 ? production
**Affected products/services:** GitHub.com mysql1 writes / GitHub.com mysql1 writes
**Primary category / type:** Database connection exhaustion / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Stalled writes on mysql1; ProxySQL degraded after remediation

**Technical root cause:** ProxySQL nodes had a lower file-descriptor limit than intended: a process manager silently reduced LimitNOFILE from 1,073,741,824 to 65,536; a race slowed correction.

**Customer impact:** Incident lasted 2h12.

**Business impact:** Incident lasted 2h12.

**Duration:** 2 hours 12 minutes

**Source-published metrics:** duration: **132 minutes** (mysql1 dependent services); configured_limit: **1073741824 file descriptors** (Intended LimitNOFILE); effective_limit: **65536 file descriptors** (ProxySQL process limit)

**Recovery actions:** Engineers remediated the limit and addressed the process-manager/configuration race.

**Preventive actions:** Improve ProxySQL limits, observability and integration testing at realistic scale.

**Data gaps:** No customer count or numerical request failure rate disclosed.

**Primary source:** [postmortem ? 2020-03-26](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/). Official timeline names the threshold, limit values and race; duration 2h12. (record last reviewed 2026-11-13)

### 13. GitHub ? February 27 database load incident

**ID / date / environment:** `github-2020-02-27-database-load` ? 2020-02-27 ? production
**Affected products/services:** GitHub.com services dependent on mysql1 / GitHub.com services dependent on mysql1
**Primary category / type:** Database failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Database load spike; Service availability degraded

**Technical root cause:** Application query-pattern changes increased master load beyond available headroom.

**Customer impact:** Incident lasted 4h23; GitHub froze production deployments for three days afterward.

**Business impact:** Incident lasted 4h23; GitHub froze production deployments for three days afterward.

**Duration:** 4 hours 23 minutes

**Source-published metrics:** duration: **263 minutes** (mysql1 dependent services); post-incident_deployment_freeze: **3 days** (GitHub production deployments)

**Recovery actions:** Stabilized traffic and froze production changes for three days.

**Preventive actions:** Partitioned key data, reduced master reads, required feature flags for code changes and improved realistic-scale performance tests.

**Data gaps:** Per-user outage counts and error percentages not published.

**Primary source:** [postmortem ? 2020-03-26](https://github.blog/news-insights/company-news/february-service-disruptions-post-incident-analysis/). Official postmortem names query-pattern change, 4h23 duration and three-day production deployment freeze. (record last reviewed 2026-11-13)

### 14. GitHub ? May 9 Git database degradation after configuration change

**ID / date / environment:** `github-2023-05-git-db` ? 2023-05-09 ? production
**Affected products/services:** GitHub Git databases, Git operations, Pull requests, Actions / GitHub Git databases, Git operations, Pull requests, Actions
**Primary category / type:** Configuration errors / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** 8 of 10 main services degraded; Git reads/writes failed or were delayed; Some pull request and push data had extended recovery

**Technical root cause:** A configuration change intended to prevent connection saturation triggered a database failover; the rollback then failed due to internal infrastructure error.

**Customer impact:** Most downtime lasted just over an hour; eight of ten status-portal services were impacted.

**Business impact:** Most downtime lasted just over an hour; eight of ten status-portal services were impacted.

**Duration:** Just over one hour of primary downtime; some data recovery continued afterward

**Source-published metrics:** main_services_degraded: **8 of 10 services** (GitHub status portal)

**Recovery actions:** Reverted the configuration where possible and restored Git database service; some data recovery continued afterward.

**Preventive actions:** Safer deployment process, better low-volume/high-cost query observability, and database failover fixes.

**Data gaps:** Exact error percentage, affected users and financial impact not disclosed.

**Primary source:** [postmortem ? 2023-05-15](https://github.blog/news-insights/company-news/addressing-githubs-recent-availability-issues/). Official GitHub analysis calls out May 9, 8/10 services, configuration trigger and rollback failure. (record last reviewed 2026-11-13)

### 15. Google Cloud ? Cloud Pub/Sub metadata hotspot incident

**ID / date / environment:** `google-2019-05-pubsub` ? 2019-05-20 ? production
**Affected products/services:** Cloud Pub/Sub, Cloud SQL, Cloud Filestore, App Engine Task Queues / Cloud Pub/Sub, Cloud SQL, Cloud Filestore, App Engine Task Queues
**Primary category / type:** Message queue failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Publish error rate 1.2%; p99 publish latency increased 8.3 seconds; DEADLINE_EXCEEDED errors

**Technical root cause:** A surge of publish requests did not cache as expected, hot-spotted metadata storage, and activated overload protection which rejected/delayed requests.

**Customer impact:** Incident lasted 3h30; publish/admin errors and downstream timeouts were reported.

**Business impact:** Incident lasted 3h30; publish/admin errors and downstream timeouts were reported.

**Duration:** 3 hours 30 minutes

**Source-published metrics:** publish_error_rate: **1.2 percent** (Cloud Pub/Sub publish); publish_p99_latency_increase: **8.3 seconds** (Cloud Pub/Sub publish); publish_admin_error_rate: **8.3 percent** (Pub/Sub publish admin operations); subscribe_admin_error_rate: **3.2 percent** (Pub/Sub subscribe admin operations)

**Recovery actions:** Rate-limited source traffic; disabled nonessential internal traffic; service auto-healed after request surge subsided.

**Preventive actions:** Add metadata caching, increase storage-server count, improve schema/load distribution and rate-limit/load-shed/hotspot playbooks.

**Data gaps:** Affected customer count and revenue impact not disclosed.

**Primary source:** [postmortem ? 2019-05-28](https://status.cloud.google.com/incident/cloud-pubsub/19001). Official status postmortem contains impact percentages, latency, error example, root cause and recovery. (record last reviewed 2026-11-13)

### 16. Google Cloud ? Google Cloud Networking incident #19009

**ID / date / environment:** `google-2019-06-network` ? 2019-06-02 ? production
**Affected products/services:** Google Cloud Platform, G Suite, YouTube / Compute Engine, App Engine, Cloud Endpoints, Cloud Interconnect, Cloud VPN, Cloud Pub/Sub, BigQuery, Cloud Storage
**Primary category / type:** Network outages / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Elevated latency; Intermittent errors/timeouts; Regional connectivity loss; Some requests returned HTTP 500

**Technical root cause:** Maintenance automation descheduled network-control-plane jobs across physical locations due to two configuration conditions and a cluster-management software bug; BGP routes were withdrawn after fail-static operation expired.

**Customer impact:** Region-dependent duration 3h19–4h25; App Engine unavailable in four regions; Pub/Sub saw a 27% global drop in successful publish/subscribe requests.

**Business impact:** Region-dependent duration 3h19–4h25; App Engine unavailable in four regions; Pub/Sub saw a 27% global drop in successful publish/subscribe requests.

**Duration:** 3h19–4h25 depending on region

**Source-published metrics:** pubsub_successful_requests_global_drop: **27 percent** (Global Pub/Sub publish/subscribe during incident); app_engine_us_central_rps_drop: **23.2 percent** (App Engine us-central1); endpoints_peak_error_rate: **4.4 percent** (Cloud Endpoints at onset); cloud_storage_us_west2_error_rate: **96.2 percent** (Cloud Storage bucket requests, us-west2 average)

**Recovery actions:** Halted automation, rebuilt/restarted control plane and configuration, and shifted service traffic away from affected regions.

**Preventive actions:** Harden maintenance automation and cluster-management safeguards; persist control-plane configuration; longer fail-static mode; expanded disaster-recovery testing.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2019-06-06](https://status.cloud.google.com/incident/cloud-networking/19009). Official report covers multi-region impact, root-cause chain, metrics, recovery and preventive actions. (record last reviewed 2026-11-13)

### 17. Google Cloud ? Google Cloud Networking incident #19020

**ID / date / environment:** `google-2019-10-network` ? 2019-10-22 ? production
**Affected products/services:** Compute Engine, Cloud Router, Cloud VPN, Memorystore, Kubernetes Engine, Cloud SQL, Bigtable / Compute Engine, Cloud Router, Cloud VPN, Memorystore, Kubernetes Engine, Cloud SQL, Bigtable
**Primary category / type:** Network outages / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** 100% packet loss to/from about 20% of instances in us-west1-b; New instance creation failed; Cloud VPN/Router and Memorystore degraded

**Technical root cause:** Chubby leader-election churn stopped network programming; a race in leadership-change handling distributed invalid configurations to existing instances.

**Customer impact:** Network programming impact 2h31; 20% of Cloud Routers and 6% of VPN gateways experienced packet loss.

**Business impact:** Network programming impact 2h31; 20% of Cloud Routers and 6% of VPN gateways experienced packet loss.

**Duration:** 2 hours 31 minutes

**Source-published metrics:** gce_instances_packet_loss_affected: **20 percent of instances** (us-west1-b); affected_instances_packet_loss: **100 percent** (Affected instances); cloud_router_affected: **20 percent** (us-west1 region); cloud_vpn_affected: **6 percent** (us-west1 region)

**Recovery actions:** Rate-limited, forced leader elections and redirected traffic until control plane recovered.

**Preventive actions:** Fix election race, reject invalid configurations and improve failure-specific response tooling.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2019-10-30](https://status.cloud.google.com/incident/cloud-networking/19020). Official status report details packet loss, affected fractions, root cause and mitigations. (record last reviewed 2026-11-13)

### 18. Google Cloud ? Google Cloud regional service disruption involving Cloud KMS

**ID / date / environment:** `google-2019-11-kms` ? 2019-11-11 ? production
**Affected products/services:** Cloud IAM, Pub/Sub, Compute Engine, App Engine, Cloud Functions, Cloud Storage, Cloud Console / Cloud IAM, Pub/Sub, Compute Engine, App Engine, Cloud Functions, Cloud Storage, Cloud Console
**Primary category / type:** Cloud infrastructure failures / degradation
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** High API error rates; Control-plane operations failed; HTTP errors on storage and cloud services

**Technical root cause:** A new KMS binary introduced a feature incompatible with older related components; KMS is a common dependency for cryptographic operations.

**Customer impact:** Core KMS impact 02:39–03:27 PST; some service impact lasted longer; Cloud IAM error rates reached 94.5% in us-east1 and GCS averaged 99% errors there.

**Business impact:** Core KMS impact 02:39–03:27 PST; some service impact lasted longer; Cloud IAM error rates reached 94.5% in us-east1 and GCS averaged 99% errors there.

**Duration:** 48 minutes core impact; some service tails longer

**Source-published metrics:** cloud_iam_us_east1_errors: **94.5 percent average** (Cloud IAM during incident); gcs_us_east1_errors: **99 percent average** (Cloud Storage buckets during incident); compute_engine_api_errors: **16 percent** (GCE API requests); pubsub_publish_errors: **15 percent average** (Cloud Pub/Sub publish operations)

**Recovery actions:** Stopped/adjusted rollout and recovered KMS and affected dependent services.

**Preventive actions:** Improve compatibility and rollout safeguards for shared KMS components; see follow-up section in status report.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? publication date not disclosed](https://status.cloud.google.com/incident/cloud-datastore/19006). Official report identifies new-version incompatibility and detailed product error rates. (record last reviewed 2026-11-13)

### 19. Google Cloud ? Us-east1 data-center fuel delivery failure

**ID / date / environment:** `google-2020-06-power` ? 2020-06-29 ? production
**Affected products/services:** Compute Engine, Persistent Disk, Cloud VPN, Network Load Balancing / Compute Engine, Persistent Disk, Cloud VPN, Network Load Balancing
**Primary category / type:** Cloud infrastructure failures / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** 22.5% of us-east1-c instances unavailable for 90 minutes; 5% regional packet loss for ten minutes; Some disks unavailable up to 28 hours

**Technical root cause:** During scheduled utility substation maintenance, generator fuel delivery system failures caused generators to run out of fuel despite fuel being present in storage tanks.

**Customer impact:** 22.5% of us-east1-c VMs unavailable for 1h30; 0.0267% of PD devices unavailable up to 28h.

**Business impact:** 22.5% of us-east1-c VMs unavailable for 1h30; 0.0267% of PD devices unavailable up to 28h.

**Duration:** 1h30 for major GCE impact; some disks up to 28h

**Source-published metrics:** us_east1_c_instances_unavailable: **22.5 percent** (Compute Engine us-east1-c for 90 minutes); persistent_disk_devices_affected: **0.0267 percent** (PD devices us-east1-c); regional_packet_loss: **5 percent** (Public IP and Network Load Balancer traffic)

**Recovery actions:** Datacenter operators mitigated fuel-supply problem, utility power returned and cluster recovery completed.

**Preventive actions:** Improve generator fuel safeguards/maintenance and monitoring; see official incident prevention details.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? publication date not disclosed](https://status.cloud.google.com/incidents/Wb97fPsnE5VdLaKDcAeP). Official incident report provides root cause and affected instance/disk/packet-loss shares. (record last reviewed 2026-11-13)

### 20. Google Cloud ? Networking disruption in europe-west2-a

**ID / date / environment:** `google-2020-12-network` ? 2020-12-09 ? production
**Affected products/services:** Google Cloud Networking, Memorystore, Cloud VPN, App Engine Flex / Google Cloud Networking, Memorystore, Cloud VPN, App Engine Flex
**Primary category / type:** Network outages / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Some resources unreachable; 1.5% Memorystore Redis instances unhealthy; 4.5% Classic VPN tunnels unavailable

**Technical root cause:** A network-control-plane ACL change removed permissions required by leader-election tasks to read configuration from the lock service. Production ACL state differed from staging/canary; when leader election failed, BGP routes were withdrawn and europe-west2-a became isolated.

**Customer impact:** Network disruption 1h24; Redis impact 2h24; some VPN tunnels remained down 8h10; App Engine Flex deployment errors 1h45.

**Business impact:** Network disruption 1h24; Redis impact 2h24; some VPN tunnels remained down 8h10; App Engine Flex deployment errors 1h45.

**Duration:** 1h24 network; longer dependency recovery

**Source-published metrics:** network_disruption: **84 minutes** (europe-west2-a); memorystore_redis_instances_unhealthy: **1.5 percent** (europe-west2; lasted 2h24); classic_vpn_tunnels_unavailable: **4.5 percent** (europe-west2; lasted 8h10)

**Recovery actions:** Google restored networking and then recovered affected dependent services.

**Preventive actions:** Status report describes network control-plane resiliency work.

**Data gaps:** Details of customer/revenue/SLA impact not disclosed.

**Primary source:** [postmortem ? publication date not disclosed](https://status.cloud.google.com/incidents/qRpmq9arsrCV7xWdfftF). Official status report states network duration and measured Redis/VPN impact. (record last reviewed 2026-11-13)

### 21. AWS ? US East EBS and EC2 disruption

**ID / date / environment:** `aws-2011-04-ebs` ? 2011-04-21 ? production
**Affected products/services:** EC2, EBS, RDS / Amazon EBS, Amazon EC2, Amazon RDS
**Primary category / type:** Storage failures / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** EBS reads/writes stuck; EC2 instances using affected volumes stalled; EBS API latency/errors across region

**Technical root cause:** Traffic was shifted from primary to a lower-capacity redundant network; node isolation triggered a re-mirroring storm, cluster-capacity exhaustion and EBS control-plane thread starvation.

**Customer impact:** About 13% of affected-AZ volumes stuck at peak; 0.07% could not be restored consistently; up to 45% of single-AZ RDS instances in affected AZ had stuck I/O; 10-day service credit offered to qualifying customers.

**Business impact:** About 13% of affected-AZ volumes stuck at peak; 0.07% could not be restored consistently; up to 45% of single-AZ RDS instances in affected AZ had stuck I/O; 10-day service credit offered to qualifying customers.

**Duration:** Several days for residual volume restoration

**Source-published metrics:** affected_az_ebs_volumes_stuck: **13 percent** (Peak affected AZ); unrestorable_volumes: **0.07 percent** (Volumes in affected AZ); single_az_rds_stuck_io_peak: **45 percent** (RDS single-AZ instances in affected zone)

**Recovery actions:** Disabled/isolated degraded cluster control APIs, throttled/remediated replication storm, snapshotted recoverable volumes and restored most data; manually handled remaining volumes.

**Preventive actions:** Improve network change safety, backoff and capacity protection, control-plane isolation, recovery tooling and multi-AZ guidance.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2011-04-29](https://aws.amazon.com/message/65648/). AWS postmortem documents root-cause chain, 13% stuck volume, 0.07% unrestorable and RDS impact; it states 10-day credit. (record last reviewed 2026-11-13)

### 22. AWS ? S3 service disruption in US-EAST-1

**ID / date / environment:** `aws-2017-02-s3` ? 2017-02-28 ? production
**Affected products/services:** Amazon S3, EC2, EBS, Lambda / Amazon S3, EC2, EBS, Lambda
**Primary category / type:** Storage failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** GET/LIST/PUT/DELETE requests unavailable in stages; S3 console and some dependent workflows impaired

**Technical root cause:** An incorrect input to an operational command removed a larger set of servers than intended, removing capacity from S3 index and placement subsystems.

**Customer impact:** S3 normal at 13:54 PST from 09:37 PST start (4h17); downstream service backlogs recovered separately.

**Business impact:** S3 normal at 13:54 PST from 09:37 PST start (4h17); downstream service backlogs recovered separately.

**Duration:** 4 hours 17 minutes for S3 normal operations

**Source-published metrics:** s3_recovery_duration: **257 minutes** (S3 US-EAST-1)

**Recovery actions:** Restarted and safety-checked index and placement systems; recovered GET/LIST/DELETE before PUT; dependent services drained backlogs.

**Preventive actions:** Rate-limit capacity removal; enforce minimum-capacity guardrails; partition services into cells; run status admin console across regions.

**Data gaps:** Customer count, request failure percentages and revenue impact not disclosed.

**Primary source:** [postmortem ? publication date not disclosed](https://aws.amazon.com/message/41926/). AWS report gives command error, affected subsystems, recovery timestamps, dependencies and preventive actions. (record last reviewed 2026-11-13)

### 23. AWS ? EC2 DNS resolution issue in Seoul region

**ID / date / environment:** `aws-2018-11-seoul-dns` ? 2018-11-22 ? production
**Affected products/services:** Amazon EC2 DNS resolver / Amazon EC2 DNS resolver
**Primary category / type:** DNS failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** DNS queries from within EC2 instances failed

**Technical root cause:** A configuration update removed the resolver fleet's minimum healthy-host setting; a low default led to too few healthy hosts remaining in service.

**Customer impact:** DNS impact 08:19–09:43 KST (84 minutes); exact customer count not disclosed.

**Business impact:** DNS impact 08:19–09:43 KST (84 minutes); exact customer count not disclosed.

**Duration:** 1 hour 24 minutes

**Source-published metrics:** duration: **84 minutes** (EC2 DNS in Seoul)

**Recovery actions:** Prevented further host removal and restored resolver fleet capacity.

**Preventive actions:** Validate minimum capacity in config updates and throttle hourly removal of healthy capacity.

**Data gaps:** Customer count/error rate not disclosed.

**Primary source:** [postmortem ? 2018-11-27](https://aws.amazon.com/message/74876-2/). Official AWS report states timing, configuration omission, recovery and semantic validation measures. (record last reviewed 2026-11-13)

### 24. AWS ? EC2 and EBS service disruption in Tokyo

**ID / date / environment:** `aws-2019-08-tokyo-cooling` ? 2019-08-23 ? production
**Affected products/services:** Amazon EC2, Amazon EBS, RDS, ElastiCache / Amazon EC2, Amazon EBS, RDS, ElastiCache
**Primary category / type:** Cloud infrastructure failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Instances shut down; EBS volume performance degraded; RunInstances and Auto Scaling launches failed for a period

**Technical root cause:** A data-center control-system failover malfunction caused redundant cooling systems to fail; excessive heat shut down servers.

**Customer impact:** Cooling restored at 15:21 JST; most instances/volumes recovered by 18:30 JST. A small number required retirement.

**Business impact:** Cooling restored at 15:21 JST; most instances/volumes recovered by 18:30 JST. A small number required retirement.

**Duration:** Majority recovered by 18:30 JST

**Source-published metrics:** cooling_restored_minutes: **165 minutes after event start** (Affected Tokyo AZ); majority_resource_recovery_minutes: **354 minutes after event start** (Affected Tokyo AZ)

**Recovery actions:** Restored cooling, temperatures and power; recovered instances/volumes; repaired launch API and Auto Scaling impact.

**Preventive actions:** Change control path to allow purge mode to bypass PLCs; train operators to recognize/control failure.

**Data gaps:** Customer counts and revenue impact not disclosed.

**Primary source:** [postmortem ? 2019-08-29](https://aws.amazon.com/message/56489/). Official AWS report links overheating to cooling control failure and records recovery milestones. (record last reviewed 2026-11-13)

### 25. AWS ? Kinesis and dependent AWS services disruption in US-EAST-1

**ID / date / environment:** `aws-2020-11-kinesis` ? 2020-11-25 ? production
**Affected products/services:** Amazon Kinesis, CloudWatch, Lambda, EventBridge, ECS, EKS / Amazon Kinesis, CloudWatch, Lambda, EventBridge, ECS, EKS
**Primary category / type:** Message queue failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** CloudWatch Events/EventBridge API errors and delivery delays; Lambda invocation errors increased; Auto Scaling metrics delayed

**Technical root cause:** Adding capacity to the Kinesis front-end fleet caused existing servers to establish per-server communication threads with new servers. Fleet growth pushed thread counts above the operating-system limit; shard-map cache construction then failed, leaving front-end servers unable to route requests to backend clusters. AWS explicitly ruled out the initially suspected memory-pressure explanation as the Kinesis root cause.

**Customer impact:** Kinesis errors affected dependent services. Cognito users experienced elevated API failures and could be unable to authenticate or obtain temporary credentials; CloudWatch metric/log APIs had errors and latency with gaps in persisted telemetry; Lambda invocation errors increased from local metric-buffer memory contention; EventBridge, ECS/EKS provisioning and scaling workflows were delayed.

**Business impact:** AWS customers experienced impaired streaming, authentication/credential, monitoring, serverless invocation, and container orchestration workflows. AWS did not publish a customer count or revenue loss.

**Duration:** Varied by dependent service

**Source-published metrics:** kinesis_normal_recovery_time: **10:23 PM PST** (Kinesis Data Streams); cognito_normal_recovery_time: **2:18 PM PST** (Cognito User Pools and Identity Pools); lambda_invocation_error_mitigation_time: **10:36 AM PST** (Lambda invocation errors associated with metric-buffer memory contention); cloudwatch_metrics_alarm_recovery_time: **10:31 PM PST** (CloudWatch metrics and alarms)

**Recovery actions:** Removed the capacity addition, then restarted Kinesis front-end servers gradually to rebuild shard-map caches and restore traffic; Kinesis returned to normal at 10:23 PM PST.; Deployed a Cognito change to reduce dependency on Kinesis; Cognito returned to normal by 2:18 PM PST.; Mitigated Lambda invocation errors caused by local metric-buffer memory contention at 10:36 AM PST.

**Preventive actions:** Move to larger CPU/memory servers and reduce fleet thread demand.; Add fine-grained thread-consumption alarms and test a higher OS thread limit.; Improve cold starts and move shard-map cache to a dedicated fleet.; Partition front-end fleets for large dependent AWS services and accelerate cellularization.; Change Cognito so Kinesis errors do not exhaust its buffers.; Persist three hours of metric data locally in CloudWatch; change completed in us-east-1 at publication time.

**Data gaps:** Affected customer and organization counts were not disclosed.; AWS did not quantify revenue or financial loss.; Kinesis front-end fleet size is described only as many thousands of servers.

**Primary source:** [postmortem ? publication date not disclosed](https://aws.amazon.com/message/11201/). AWS post-event summary states capacity addition, OS thread limit exhaustion, failed shard-map construction, dependent Cognito/CloudWatch/Lambda/EventBridge impacts, recovery timelines, and preventive measures; AWS specifically says Kinesis root cause was not memory pressure. (record last reviewed 2026-11-13)

### 26. AWS ? Direct Connect packet loss in Tokyo

**ID / date / environment:** `aws-2021-09-direct-connect` ? 2021-09-02 ? production
**Affected products/services:** AWS Direct Connect, Tokyo VPC connectivity / AWS Direct Connect, Tokyo VPC connectivity
**Primary category / type:** Network outages / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Intermittent connectivity; Elevated packet loss

**Technical root cause:** A latent network-device OS/protocol bug caused devices in one network layer to stop forwarding some customer packets; automation detected unusually high device failures.

**Customer impact:** Impact began 07:30 JST; recovery started 12:30 and fully resolved at 13:42 JST.

**Business impact:** Impact began 07:30 JST; recovery started 12:30 and fully resolved at 13:42 JST.

**Duration:** 6 hours 12 minutes

**Source-published metrics:** impact_to_full_recovery: **372 minutes** (Direct Connect Tokyo)

**Recovery actions:** Removed failing devices from service and disabled the new protocol in Tokyo.

**Preventive actions:** Developed enhanced detection/remediation before applying protocol changes elsewhere.

**Data gaps:** Exact packet-loss percent and customer counts not disclosed.

**Primary source:** [postmortem ? 2021-09-13](https://aws.amazon.com/tw/message/17908/). Official AWS report gives path, packet loss/connectivity symptoms, times, protocol bug, rollback and preventive detection. (record last reviewed 2026-11-13)

### 27. AWS ? US-EAST-1 internal network congestion event

**ID / date / environment:** `aws-2021-12-internal-network` ? 2021-12-07 ? production
**Affected products/services:** EC2 APIs, RDS, EMR, WorkSpaces, Internal monitoring, Internal DNS / EC2 APIs, RDS, EMR, WorkSpaces, Internal monitoring, Internal DNS
**Primary category / type:** Network outages / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** EC2 API errors and latency; New resource launches failed; Monitoring telemetry unavailable/delayed

**Technical root cause:** Automated service scaling triggered a large connection surge/retry storm between AWS internal and main networks, overwhelming networking devices; monitoring data sharing that path was impaired.

**Customer impact:** Running EC2 instances were unaffected; EC2 APIs began improving at 13:15 PST and new launches recovered by 14:40 PST.

**Business impact:** Running EC2 instances were unaffected; EC2 APIs began improving at 13:15 PST and new launches recovered by 14:40 PST.

**Duration:** Several hours; service recovery varied

**Source-published metrics:** ec2_api_recovery_start: **1:15 PM PST** (EC2 API improvements); new_ec2_launch_recovery: **2:40 PM PST** (new EC2 launches)

**Recovery actions:** Reduced congestion and mitigated connection/retry behavior; relied on logs while monitoring telemetry degraded.

**Preventive actions:** Post-event report describes client/network resilience and monitoring improvements.

**Data gaps:** No global customer count or exact request error rates published.

**Primary source:** [postmortem ? 2021-12-10](https://aws.amazon.com/message/12721/). AWS report states control-plane impact and makes clear running customer workloads were not directly affected. (record last reviewed 2026-11-13)

### 28. Meta ? October 4 global backbone/DNS outage

**ID / date / environment:** `meta-2021-10-backbone` ? 2021-10-04 ? production
**Affected products/services:** Facebook, Instagram, WhatsApp, Meta backbone / Facebook, Instagram, WhatsApp, Meta internal tools
**Primary category / type:** BGP routing failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Facebook/Instagram/WhatsApp unavailable; Authoritative DNS unreachable; Internal diagnostic tools inaccessible

**Technical root cause:** A maintenance command intended to assess backbone capacity disconnected all backbone connections; a bug in the command-audit tool failed to block it. DNS health automation withdrew BGP advertisements when facilities could not reach datacenters.

**Customer impact:** Global platform outage; exact per-customer request rate and duration are not quantified in the engineering report.

**Business impact:** Global platform outage; exact per-customer request rate and duration are not quantified in the engineering report.

**Duration:** Not disclosed in the official incident report.

**Source-published metrics:** Not disclosed in the official incident report.

**Recovery actions:** Onsite engineers used secure out-of-band access to restore backbone connectivity; services recovered as backbone returned.

**Preventive actions:** Improve command auditing and network resilience; review DNS/BGP dependency and operational access procedures.

**Data gaps:** Exact incident start/end, customer count and per-service error rates not quantified in this engineering article.

**Primary source:** [postmortem ? 2021-10-05](https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/). Official Meta engineering report details command/audit bug, DNS BGP withdrawals, and recovery obstacles. (record last reviewed 2026-11-13)

### 29. Fastly ? Global outage triggered by valid customer configuration

**ID / date / environment:** `fastly-2021-06-config-bug` ? 2021-06-08 ? production
**Affected products/services:** Fastly edge network, Customer websites / Fastly edge network, Customer websites
**Primary category / type:** CDN failures / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** 85% of network returned errors; Customer websites using Fastly failed

**Technical root cause:** A May 12 software deployment introduced an undiscovered bug triggered by a valid customer configuration change.

**Customer impact:** Within 49 minutes, 95% of network was operating normally; incident was resolved 12:44 UTC.

**Business impact:** Within 49 minutes, 95% of network was operating normally; incident was resolved 12:44 UTC.

**Duration:** 95% normal within 49 minutes; resolved 2h57 after onset

**Source-published metrics:** network_error_scope: **85 percent** (Fastly network); network_normal_after: **95 percent** (Fastly network)

**Recovery actions:** Identified and isolated cause within minutes, disabled configuration, then deployed permanent bug fix.

**Preventive actions:** Improve QA/testing to detect bug, speed mitigation, and use WebAssembly/Compute@Edge isolation.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2021-06-08](https://www.fastly.com/blog/summary-of-june-8-outage). Fastly official postmortem provides 85% error scope, recovery timeline and deployment-trigger chain. (record last reviewed 2026-11-13)

### 30. Dropbox ? Database outage during scheduled machine maintenance

**ID / date / environment:** `dropbox-2014-01-maintenance` ? 2014-01-10 ? production
**Affected products/services:** Dropbox website, Photo sharing, Camera uploads, Some API features / Dropbox website, Photo sharing, Camera uploads, Some API features
**Primary category / type:** Database failures / outage
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Dropbox site and features unavailable; File contents were not at risk because affected DBs stored metadata/features

**Technical root cause:** A remote production-state verification script failed to detect that a handful of machines were serving production, so planned OS upgrade affected live database master/replica pairs.

**Customer impact:** Most functionality restored within about three hours; core service fully restored Sunday at 16:40 PT.

**Business impact:** Most functionality restored within about three hours; core service fully restored Sunday at 16:40 PT.

**Duration:** Most service ~3h; core restored Sunday 16:40 PT

**Source-published metrics:** most_functionality_recovery: **180 minutes** (Dropbox service)

**Recovery actions:** Recovered from backups; later developed parallel binary-log replay to improve large database recovery.

**Preventive actions:** Add local machine state checks before destructive commands; speed backup recovery by parallelizing binlog replay.

**Data gaps:** Date of the Friday event is stated indirectly; estimated from Jan 12 article and day-of-week; verify exact event date before asserting.

**Primary source:** [postmortem ? 2014-01-12](https://dropbox.tech/infrastructure/outage-post-mortem). Official Dropbox postmortem dates article and details maintenance script, database effects and recovery improvements. (record last reviewed 2026-11-13)

### 31. Atlassian ? April 2022 customer site deletion incident

**ID / date / environment:** `atlassian-2022-04-site-deletion` ? 2022-04-05 ? production
**Affected products/services:** Jira, Confluence, Atlassian Access, Opsgenie, Statuspage / Jira, Confluence, Atlassian Access, Opsgenie, Statuspage
**Primary category / type:** Data corruption incidents / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Jira-family products and Confluence unavailable for affected sites; Some deleted customer contact information complicated support

**Technical root cause:** The deletion script received whole-site IDs instead of app IDs; the API accepted both identifier types without validation or a warning.

**Customer impact:** 883 sites / 775 customers; some affected up to 14 days; over 99.6% of customers/users continued unaffected; no customer lost over five minutes of data.

**Business impact:** 775 customers lost access to products; subset outage lasted up to 14 days. More than 99.6% of customers/users remained unaffected, and no customer lost more than five minutes of data.

**Duration:** Up to 14 days for subset; all restored Apr 18

**Source-published metrics:** sites_deleted: **883 sites** (Atlassian sites); customers_affected: **775 customers** (Atlassian official customer definition); customers_unaffected: **99.6 percent minimum** (Customers/users); maximum_data_loss: **5 minutes** (Any affected customer)

**Recovery actions:** Cross-functional team restored and validated sites from April 8 through April 18.

**Preventive actions:** Universal soft delete, staged rollout and tested rollback, larger-scale DR exercises, improved incident coordination and communications.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2022-04-29](https://www.atlassian.com/blog/how-we-build/post-incident-review-april-2022-outage). Atlassian PIR states script ran 07:38–08:01, deleted 883 sites/775 customers, no >5 min data loss, 99.6%+ unaffected and restore dates. (record last reviewed 2026-11-13)

### 32. Discord ? Authentication outage caused by ScyllaDB overload

**ID / date / environment:** `discord-2023-11-auth` ? 2023-11-06 ? production
**Affected products/services:** Discord authentication, Discord messaging / Discord authentication, Discord messaging
**Primary category / type:** Authentication failures / outage
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Authentication unavailable; HTTP 200 response availability fell to approximately 25%

**Technical root cause:** Operating-system upgrade took one ScyllaDB zone offline while a degraded disk in another zone reduced capacity, overloading an underprovisioned authentication cluster.

**Customer impact:** Approximately 50 minutes from 10:52 PST; availability fell to about 25%.

**Business impact:** Approximately 50 minutes from 10:52 PST; availability fell to about 25%.

**Duration:** Approximately 50 minutes

**Source-published metrics:** http_200_availability: **25 percent** (Discord requests during outage)

**Recovery actions:** Engineers restored the impacted zone/cluster and recovered authentication service.

**Preventive actions:** Improve authentication-cluster architecture, provisioning and OS upgrade procedure.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2023-11-15](https://discord.com/blog/authentication-outage). Discord engineering report states outage, duration, auth symptoms, ScyllaDB upgrade/degraded disk chain and 25% availability. (record last reviewed 2026-11-13)

### 33. Discord ? Voice and video outage after session configuration update

**ID / date / environment:** `discord-2026-03-voice` ? 2026-03-25 ? production
**Affected products/services:** Discord Voice, Discord Video / Discord Voice, Discord Video
**Primary category / type:** Kubernetes failures / degradation
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Voice/video calls unavailable for most users; Awaiting Endpoint status; Session servers disconnected

**Technical root cause:** A routine configuration update during Kubernetes migration shut down a large portion of session-management servers; downstream connection supervisors and voice routing were overwhelmed by reconnect/spawn load.

**Customer impact:** Major degradation from 12:13 to 15:30 PDT (3h17); 17% of sessions were lost at once.

**Business impact:** Major degradation from 12:13 to 15:30 PDT (3h17); 17% of sessions were lost at once.

**Duration:** 3 hours 17 minutes

**Source-published metrics:** session_servers_lost: **17 percent** (Discord session service)

**Recovery actions:** Reduced downstream pressure and recovered voice/video services; one targeted supervisor restart was tried and did not help.

**Preventive actions:** Add validating Kubernetes admission webhook and graceful drain requirements; increase voice-system parallelism and monitoring; plan regional control-plane scaling.

**Data gaps:** No additional gap entered; fields not disclosed remain blank or explicitly marked.

**Primary source:** [postmortem ? 2026-04-29](https://discord.com/blog/behind-the-scenes-of-the-3-25-26-voice-outage). Discord engineering article gives timeline, 17% sessions lost, symptoms and preventative changes. (record last reviewed 2026-11-13)

### 34. Google Cloud ? Google Cloud asia-northeast1 multi-service incident

**ID / date / environment:** `google-2024-09-asia` ? 2024-09-07 ? production
**Affected products/services:** Cloud Build, Dataflow, Cloud Deploy, Cloud SQL, Compute Engine, GKE / Cloud Build, Dataflow, Cloud Deploy, Cloud SQL, Compute Engine, GKE
**Primary category / type:** Deployment failures / degradation
**IncidentIQ severity:** high ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** VM operations failed; Cloud Build jobs did not execute; Dataflow jobs failed at startup/autoscaling disrupted; Cloud Deploy tasks stalled

**Technical root cause:** A metadata-store software update handled a rare resource-contention corner case poorly, causing GCE internal DNS writes to fail. A secondary automated-failover issue left the regional metadata store unavailable despite healthy replicas.

**Customer impact:** Reported duration 1h50; issue later marked resolved.

**Business impact:** Reported duration 1h50; issue later marked resolved.

**Duration:** 1 hour 50 minutes

**Source-published metrics:** duration: **110 minutes** (asia-northeast1 products)

**Recovery actions:** Engineers manually initiated failover of metadata storage operations to healthy zones; service mitigated at 06:10 US/Pacific.

**Preventive actions:** Improve automated metadata-store failover logic.; Improve testing for resource-contention corner cases.; Improve response processes and documentation.

**Data gaps:** Per-product customer counts and financial impact were not disclosed.

**Primary source:** [status_report ? publication date not disclosed](https://status.cloud.google.com/incidents/XwnegjADrYy2GHJphG2V). Final Google incident report documents the metadata store update, resource-contention corner case, failover failure, 1h50 duration, and corrective actions. (record last reviewed 2026-11-13)

### 35. Google Cloud ? Google Cloud australia-southeast2 multi-service incident

**ID / date / environment:** `google-2024-10-australia` ? 2024-10-29 ? production
**Affected products/services:** Apigee, Batch, Filestore, Firestore, KMS, Cloud Run, BigQuery, Dataflow, Pub/Sub, Cloud SQL, GCS, Compute Engine, GKE, IAM / Apigee, Batch, Filestore, Firestore, KMS, Cloud Run, BigQuery, Dataflow, Pub/Sub, Cloud SQL, GCS, Compute Engine, GKE, IAM
**Primary category / type:** Cloud infrastructure failures / degradation
**IncidentIQ severity:** critical ? IncidentIQ demo classification based on the documented production availability impact; this is not the company's severity label.

**Customer-facing symptoms:** Apigee 5XX errors and latency; Batch jobs remained SCHEDULED; Filestore operations failed; Cloud products unavailable/degraded

**Technical root cause:** Two nearby fiber failures reduced available inter-region capacity; then a voltage swell at a network PoP hosting 50% of regional network capacity rebooted networking devices. Equipment rectifiers shut down because a UPS voltage regulator pushed voltage above the equipment tolerance.

**Customer impact:** Incident 16:21–19:34 PDT; longest regional impact 2h03.

**Business impact:** Incident 16:21–19:34 PDT; longest regional impact 2h03.

**Duration:** 3h13 overall; longest impact 2h03

**Source-published metrics:** overall_duration: **193 minutes** (Google Cloud australia-southeast2); longest_regional_impact: **123 minutes** (Affected services)

**Recovery actions:** Impacted network paths recovered after devices rebooted; all affected zones regained full connectivity by 16:43 US/Pacific. Some services required manual recovery actions.

**Preventive actions:** Review regional power distribution and add protections against voltage swells/sags.; Reconfigure UPS voltage regulator and institute monthly reviews.; Deploy double-conversion UPS.; Change network-device configuration to reduce recovery time.; Review other sites for the same risk.

**Data gaps:** Customer counts and financial impact were not disclosed.

**Primary source:** [postmortem ? publication date not disclosed](https://status.cloud.google.com/incidents/Pvq1RGrACDwogEE8hcrm). Final Google report updated 4 Dec 2024 documents two fiber failures, voltage swell, 50% capacity PoP, device reboot, 21-minute multi-product loss, up to 15% latency/error-rate increase, root cause, and prevention. (record last reviewed 2026-11-13)
