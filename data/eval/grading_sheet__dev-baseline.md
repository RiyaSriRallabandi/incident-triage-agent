# Grading sheet - dev-baseline


## scn_001__run1

**Incident:** Since ~13:42 UTC the edge tier is serving a high rate of 502s for a large fraction of all traffic. Customer reports came in within a few minutes. No known infrastructure maintenance was scheduled. Edge hosts look CPU-bound.

**Ground-truth cause:** A newly deployed WAF managed-rule set (commit 7f3a9c1) contained a rule (100417) with a catastrophically backtracking regular expression. Evaluating that pattern against normal request traffic drove edge-proxy worker CPU to saturation within about a minute, so requests queued and then failed with 502s across effectively all traffic.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 6 tool calls):** The rollout of the WAF managed ruleset 2026.05.12 introduced CPU saturation and subsequent 502 errors on edge-proxy hosts.

**Agent citations:** ['deploy: 2026-05-12T13:42:00Z edge-proxy 7f3a9c1 roll out WAF managed ruleset 2026.05.12', 'metric edge-proxy / cpu_utilization_pct: spiked from ~34% to 98-101% starting at 13:43 UTC', 'metric edge-proxy / http_5xx_rate: surged from 0.002 to ~0.62 starting at 13:44 UTC', 'runbook cpu-saturation.md > Mitigation: Roll back the change that introduced the hot path.']

**Grade (correct / partial / incorrect):** ____


## scn_002__run1

**Incident:** Checkout started returning 503s to a growing share of users around 09:23 UTC. Error rate on checkout-api is elevated and latency is high. No deploys went out today. Payments processing also looks a bit slow. On-call is unsure whether checkout or payments is the real problem.

**Ground-truth cause:** A modest latency increase in payments-api (read-replica lag pushed p95 from ~90ms to ~400ms) triggered aggressive retries from checkout-api's payments client, which had no backoff and no retry budget. Retry amplification roughly 5x'd checkout-api's outbound request volume, which exhausted its database connection pool and then its worker thread pool, turning a minor downstream slowdown into a checkout outage.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 6 tool calls):** Downstream payments-api latency increase starting at 09:16 UTC led to thread and database connection pool exhaustion in checkout-api, causing server capacity errors and 503 responses.

**Agent citations:** ['payments-api / p95_latency_ms spiked at 09:16 UTC from ~90ms to over 400ms', 'checkout-api / outbound_requests_per_s surged starting around 09:18 UTC', 'checkout-api / db_pool_wait_ms spiked at 09:20 UTC to over 5000ms', 'checkout-api ERROR log at 09:21:00Z: DB connection pool exhausted (size=20, active=20, waiters=140)', 'checkout-api ERROR log at 09:22:00Z: worker thread pool exhausted; rejecting inbound requests', 'checkout-api ERROR log at 09:23:00Z: HTTP 503: server at capacity']

**Grade (correct / partial / incorrect):** ____


## scn_003__run1

**Incident:** Starting ~18:07 UTC, media-api is returning 500s on most requests and image uploads are failing. The web app shows broken images site-wide. Nothing was deployed to media-api or uploads-worker recently. Platform team was doing some storage maintenance earlier in the hour.

**Ground-truth cause:** During planned index-tier capacity maintenance, an operator ran a capacity-removal command with an incorrect argument and removed 48 storage nodes instead of 4. That dropped the object-store index subsystem below quorum, forcing a multi-hour full restart of the index and placement subsystems. Every service depending on object reads and writes (media-api, uploads-worker) failed or degraded until object-store recovered.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 3 tool calls):** The object-store index subsystem dropped below quorum and entered recovery mode during platform team storage maintenance, causing upstream unavailability and exhausting retries for the media-api.

**Agent citations:** ['2026-07-19T18:07:10Z  media-api  ERROR  object-store GET failed: 500 upstream_unavailable (retries exhausted)', 'object-store / availability_pct dropped sharply from ~99% to ~12% starting at 18:07 UTC', '2026-07-19T18:06:00Z  object-store  ERROR  index subsystem dropped below quorum; entering recovery mode']

**Grade (correct / partial / incorrect):** ____


## scn_004__run1

**Incident:** notifications-api error rate has been intermittently elevated (roughly 3-5%, normally under 0.5%) since about 02:30 UTC. No deploys in the last 24 hours. Downstream providers look fine. It has partially recovered on its own. On-call wants a root cause before standing down.

**Ground-truth cause:** Undetermined. The evidence shows a modest, intermittent rise in notifications-api error rate spread across most hosts, with no correlated deploy, no downstream degradation, and no clear resource signal (latency barely moved, heap is flat). The available data is insufficient to identify a root cause.

**Ground-truth should_escalate:** True

**Agent (escalate, 6 tool calls):** The tool-call budget was exhausted before the investigation finished. Although unhandled exceptions with 'context deadline exceeded' were found in notifications-api, the exact downstream service or root bottleneck causing the timeouts could not be pinpointed within the budget.

**Grade (correct / partial / incorrect):** ____


## scn_005__run1

**Incident:** Since ~15:42 UTC the site is returning 503s for essentially all traffic. Edge load balancers report they cannot reach any backends. No application deploys today. The network team ran a scheduled backbone capacity audit earlier.

**Ground-truth cause:** A backbone network config push withdrew the route advertisements for the subnet hosting the authoritative DNS servers (dns-auth, 10.2.0.0/16). With the nameservers unreachable, DNS resolution failed globally, so every service that has to resolve a hostname (api-gateway, edge-lb) failed and the edge served 503s for all traffic. Recovery required manually re-advertising the withdrawn prefixes.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 6 tool calls):** A scheduled backbone capacity audit on core routers caused authoritative nameservers to become unreachable from the edge, resulting in a collapse of DNS resolution and leaving edge load balancers unable to reach backends.

**Agent citations:** ['edge-lb / http_5xx_rate metric spiked from 0.003 to 0.9591 at 15:43 UTC', 'dns-auth / dns_resolution_success_rate metric dropped sharply from ~1.0 to 0.0204 at 15:42 UTC', 'dns-auth log: authoritative nameservers unreachable from edge; health checks failing at 15:41 UTC', 'network-automation log: scheduled backbone capacity audit starting on core routers at 15:30 UTC']

**Grade (correct / partial / incorrect):** ____


## scn_006__run1

**Incident:** Since ~11:07 UTC all card payments are failing at checkout with 'try again later'. Non-payment traffic is fine. No application deploys. Cloud infra team pushed a security-group change this morning.

**Ground-truth cause:** A security-group change (CR-4821) intended to tighten egress rules removed the rule permitting payments-gateway to reach the external payment processor's IP range. DNS still resolved, but TCP connections to the processor could no longer be established, so every payment authorization timed out. Non-payment traffic was unaffected. Recovery required rolling back the change.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 3 tool calls):** Cloud infra team security-group change blocked outbound connections from payments-gateway to processor.acme-pay.com

**Agent citations:** ['payments-gateway / outbound_connect_errors_per_s surged from 0.2 to over 45 errors per second starting at 11:08 UTC', '2026-09-22T11:07:00Z payments-gateway WARN outbound connection to processor.acme-pay.com timing out (connect timeout 10s)', '2026-09-22T11:11:00Z payments-gateway INFO DNS resolves processor.acme-pay.com fine; TCP connect never completes', 'Cloud infra team pushed a security-group change this morning']

**Grade (correct / partial / incorrect):** ____


## scn_007__run1

**Incident:** At exactly 00:00 UTC login success rate dropped to zero across the product. Clients are getting TLS errors when their browser or app connects to the login service. No deploys in the last week. Nothing changed at midnight that anyone knows of.

**Ground-truth cause:** The TLS certificate for auth-service's token endpoint reached its expiry (notAfter = 2026-10-01T00:00:00Z) and was not renewed. Starting exactly at that wall-clock time, clients rejected the expired certificate during the TLS handshake, so every login and token-issuance request failed. There was no deploy or config change - the trigger was the calendar. Recovery required installing and reloading the renewed certificate.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 2 tool calls):** The auth-service TLS certificate expired at 2026-10-01T00:00:00Z, causing a massive spike in TLS handshake failures and dropping login success rate to zero.

**Agent citations:** ['auth-service / tls_handshake_errors_per_s spiked from ~0.1 to over 384 at 00:01 UTC', '2026-10-01T00:00:00Z auth-service ERROR TLS handshake failures from clients: certificate expired (notAfter=2026-10-01T00:00:00Z)']

**Grade (correct / partial / incorrect):** ____


## scn_008__run1

**Incident:** Since ~09:33 UTC about a third of internal service-to-service calls are failing with certificate errors. Customer-facing error rate is elevated but not total. No application deploys. The platform team ran a scheduled internal CA rotation this morning.

**Ground-truth cause:** A scheduled rotation of the internal mTLS certificate authority distributed a new root, but roughly 30% of service-mesh pods failed to pick up the new trust bundle. Calls between pods on the new root and pods still on the old root failed certificate validation ('signed by unknown authority'), producing a partial (~35%) error rate on internal calls that matches the fraction of stale pods. Recovery required forcing a trust-bundle refresh on the lagging pods.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 6 tool calls):** The scheduled internal CA rotation completed by mesh-control resulted in lagging pods failing to pick up the new trust bundle, causing a spike in mTLS validation errors across the service mesh until a forced trust-bundle refresh was applied.

**Agent citations:** ['mesh-control log: 2026-10-08T09:30:00Z mesh-control INFO scheduled internal CA rotation complete; new root distributed to service mesh', 'internal-api-mesh / mtls_validation_error_rate metric starting to rise sharply at 09:34 UTC, reaching ~0.35', 'mesh-control log: 2026-10-08T10:00:00Z mesh-control INFO forced trust-bundle refresh on lagging pods; error rate falling']

**Grade (correct / partial / incorrect):** ____


## scn_009__run1

**Incident:** Since ~20:11 UTC signups and profile updates are failing with timeouts. Reads look fine. Login mostly works but is slow. A migration deploy went out to users-service just before it started.

**Ground-truth cause:** A schema migration deployed with commit d4e5f6a created an index on users.last_seen_at as a blocking operation on an ~80M-row table. The CREATE INDEX held an AccessExclusiveLock on the users table for its duration, blocking all writes. Every operation that writes to users - signups, profile updates, the last_seen_at touch on login - stalled and hit the 5s statement timeout. Reads were unaffected. Recovery required cancelling the migration to release the lock.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 3 tool calls):** Database migration adding an index on users.last_seen_at caused a surge in database lock wait sessions, leading to write timeouts for signups and profile updates.

**Agent citations:** ['users-service deploy at 2026-10-15T20:09:00Z: add index on users.last_seen_at (migration 20261015)', 'users-service write_error_rate spiked from 0.001 to ~0.60 starting around 20:14 UTC', 'users-db db_lock_wait_sessions jumped from ~1 to over 55 sessions starting at 20:12 UTC following the migration']

**Grade (correct / partial / incorrect):** ____


## scn_010__run1

**Incident:** Since ~13:13 UTC analytics and reporting endpoints are failing or returning errors. The main checkout path is fine. Data platform started a large backfill job earlier in the afternoon. No deploys.

**Ground-truth cause:** A one-off backfill job ('recompute_ltv', ~120M row updates on the orders table) generated write volume far above normal, so the read replicas fell behind - replication lag climbed from under 1s to over 300s. When lag crossed the 300s safety cutoff, analytics-api's fail-safe stopped serving from replicas and failed reads by design; routing that read load onto the primary then raised the primary's latency. The trigger is the un-throttled backfill. Recovery required throttling it so replicas could catch up.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 3 tool calls):** High database replication lag on orders-db-replica exceeded the 300s cutoff due to a large backfill job, causing analytics-api to fail reads rather than serve stale data.

**Agent citations:** ['analytics-api read_error_rate spiked from 0.002 to ~0.50 starting at 13:14 UTC', "analytics-api log: 'lag exceeded 300s cutoff; failing reads rather than serve stale (fail-safe)' at 13:13:00Z", 'orders-db-replica replication_lag_s metric climbed past the 300s threshold beginning around 13:10 UTC, peaking at over 346 seconds']

**Grade (correct / partial / incorrect):** ____


## scn_011__run1

**Incident:** Since ~14:32 UTC a fraction of orders are being submitted twice or with wrong quantities. Total order volume looks normal. A rollout of order-router started a few minutes before. Trading ops are seeing bad orders reach the exchange.

**Ground-truth cause:** Deploy 9a8b7c6 repurposed the ROUTE_MODE feature flag. During the partial rollout (6 of 8 hosts), the two hosts still on the previous build (h7, h8) interpreted the same flag value as 'use the deprecated routing path', which contained a known bug that produced duplicate and malformed order submissions. About 12% of order flow - the share handled by the two stale hosts - went through the buggy legacy path. The trigger is deploying a semantic change to a shared flag without a coordinated cutover. Recovery required rolling back and disabling the legacy path.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 4 tool calls):** The fleet rollout of order-router with repurposed flag ROUTE_MODE caused hosts h7 and h8 on a previous build to interpret the flag as the legacy routing path, resulting in duplicate order submissions.

**Agent citations:** ['2026-10-28T14:30:00Z order-router 9a8b7c6 repurpose flag ROUTE_MODE; fleet rollout in progress', 'order-router / erroneous_order_rate spiked starting at 14:32 (0.0169) and 14:33 (0.0591), reaching ~0.12', '2026-10-28T14:32:00Z order-router WARN hosts h7,h8 on previous build: ROUTE_MODE flag interpreted as the legacy routing path', '2026-10-28T14:34:00Z order-router ERROR duplicate order submissions detected from the legacy routing path (h7,h8): 220 affected orders']

**Grade (correct / partial / incorrect):** ____


## scn_012__run1

**Incident:** search-api p99 latency roughly doubled (about 300ms to 620ms) starting around 04:00 UTC. p50 is unchanged. No error spike, no resource alarm. The team wants a root cause before closing the incident.

**Ground-truth cause:** Undetermined. search-api p99 latency roughly doubled at ~04:00 while p50, error rate, and resource use stayed essentially flat. Two candidate causes are present but neither fits: the last deploy (ranking model v7) was ~5.5 hours before onset with no corresponding event at 04:00, and organic query growth (+24% week-over-week) plus index growth are gradual, not a step change. The available evidence does not localize a cause.

**Ground-truth should_escalate:** True

**Agent (diagnosis, confidence 0.9, 5 tool calls):** The search-api deployment (bump ranking model to v7; minor query-parser refactor) introduced a regression that caused the p99 latency to roughly double starting around 04:00 UTC.

**Agent citations:** ['search-api / p99_latency_ms changed from ~299ms to ~615ms (+110.8%)', 'search-api deploy at 2026-11-03T22:30:00Z: bump ranking model to v7; minor query-parser refactor', 'search-api cpu_utilization_pct remained flat between 44.2% and 48.9%']

**Grade (correct / partial / incorrect):** ____


## scn_013__run1

**Incident:** Since ~16:03 UTC roughly 40% of services are returning 503s. The rest are fine. No application deploys. The platform team did some infrastructure work this afternoon.

**Ground-truth cause:** The ingress-controller was upgraded from 3.x to 4.x (deploy b1c2d3e). Version 4.x changed how a routing annotation is interpreted and silently ignored the legacy 'route.class' annotation still used by ~40% of services. Those services' route rules stopped matching any backend, so the ingress returned 503 (no route) for them. Services already on the new annotation form were unaffected. Recovery required rolling back the ingress-controller.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** Infrastructure upgrade caused ingress-controller to ignore legacy annotation 'route.class' in version 4.x, rendering 42 route rules inactive and causing 40% of services to return 503 errors.

**Agent citations:** ['edge-ingress / http_5xx_rate metric spiked at 16:03 UTC from 0.004 to over 0.40', 'ingress-controller / active_route_rules dropped from ~105 to ~62 at 16:03 UTC', "ingress-controller log at 16:02 UTC: 42 route rules did not match any backend after upgrade (legacy annotation 'route.class' ignored in 4.x)", 'ingress-controller log at 16:05 UTC: 40% of configured routes inactive; affected services returning 503']

**Grade (correct / partial / incorrect):** ____


## scn_014__run1

**Incident:** Since ~10:23 UTC product pages are very slow and some are timing out. A refactor of product-api went out around 10:20. Database team says product-api read load is way up.

**Ground-truth cause:** Deploy e4f5a6b refactored the product-detail assembly path and removed the caching decorator around the per-product lookup. Requests that previously served from cache (94% hit rate) now made a fresh database query per product, raising product-api's database read volume ~12x. The database could not keep up, so p95 latency climbed to ~3.2s and ~4% of requests timed out. Recovery on rollback.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 2 tool calls):** The product-api refactor deployed at 10:20 caused cache hit rate to drop by 96.9%, leading to a massive spike in read load on products-db and causing product pages to time out.

**Agent citations:** ['1 deploy(s): 2026-11-13T10:20:00Z product-api e4f5a6b refactor product detail assembly', 'product-api / cache_hit_rate change -96.9% dropping from ~0.94 to 0.0295 following the deploy at 10:20', 'Database team reports product-api read load is way up']

**Grade (correct / partial / incorrect):** ____


## scn_015__run1

**Incident:** Since ~22:01 UTC about half of invoice-creation requests are failing. A billing-api deploy with a database migration started at 22:00 and is still rolling out. Reads seem fine.

**Ground-truth cause:** Deploy a7b8c9d renamed the invoices.amount column to amount_cents in a single step - the migration and the code change shipped together. During the rolling deploy, instances still on the old code queried invoices.amount, which no longer existed, so ~50% of invoice writes (the fraction on old instances) failed with 'column does not exist'. This is an expand/contract violation: the rename was not backwards-compatible with the in-flight old version. Errors cleared once every instance was on the new code.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 4 tool calls):** The billing-api deployment performed a breaking database schema migration (renaming invoices.amount to amount_cents) combined with code in a single release, causing old instances running during the rollout to fail invoice writes because the 'amount' column no longer exists.

**Agent citations:** ['2026-11-17T22:00:00Z billing-api a7b8c9d rename invoices.amount -> amount_cents (migration + code in one release)', 'billing-api / schema_errors_per_s spiked from ~0 to ~30 starting at 22:02 UTC', '2026-11-17T22:01:00Z billing-api ERROR old instances: column invoices.amount does not exist (SQLSTATE 42703); invoice writes failing']

**Grade (correct / partial / incorrect):** ____


## scn_016__run1

**Incident:** notification-worker has been restarting repeatedly since around 05:00 UTC and the notification queue is falling behind. No deploys today; the last one was 3 days ago. Latency on the rest of the platform is normal.

**Ground-truth cause:** notification-worker has a memory leak: an in-memory de-duplication set that is never bounded or evicted (observed holding 14M entries). As notification volume grew, the set's footprint climbed until the container hit its memory limit and was OOM-killed, restarting on a sawtooth. During each growth phase, GC pressure slowed processing and the work queue backed up. The leak predates today - the last deploy was 3 days ago - and only became visible now as volume crossed the threshold. Recovery required bounding the set with a size cap and TTL.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 4 tool calls):** The in-memory dedup set holds 14 million entries without eviction, leading to a memory leak and subsequent OOMKilled container restarts.

**Agent citations:** ['notification-worker / oom_restarts_total metric shows a sharp increase starting at 05:00 UTC', 'notification-worker / heap_used_pct metric climbs up to 96.78%', 'Log line: 2026-11-20T05:40:00Z notification-worker ERROR OOMKilled; restart #4; in-memory dedup set holds 14M entries and never evicts', 'Runbook section memory-leak-and-oom.md matches symptoms of steadily climbing memory use ending in OOM kills']

**Grade (correct / partial / incorrect):** ____


## scn_017__run1

**Incident:** Since ~14:03 UTC api-server is throwing 5xx on a growing share of requests. It looks host-specific - some hosts are fine. No deploys. There was a troubleshooting session on this service about an hour ago.

**Ground-truth cause:** DEBUG-level logging was enabled on the api-server host pool during an earlier troubleshooting session (~1 hour before) and never reverted. The elevated log volume filled the /var/log disk to 100%. With the disk full, api-server could not write its request log or create temp files ('No space left on device'), so a growing fraction of requests failed - tracking exactly the hosts that hit 100% disk. Recovery required reverting the log level and rotating the accumulated debug logs.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 3 tool calls):** Disk exhaustion on /var/log due to accumulated debug logs, preventing the api-server from writing request logs and causing 5xx errors on affected hosts.

**Agent citations:** ['2026-11-24T14:00:00Z  api-server  WARN  disk usage on /var/log at 92%', '2026-11-24T14:03:00Z  api-server  ERROR  disk full: cannot write request log; /var/log at 100%', '2026-11-24T14:07:00Z  api-server  WARN  5xx rate 22%; errors correlate with hosts at 100%', 'api-server / disk_used_pct metric showing values peaking at ~101.8% starting around 14:04 UTC']

**Grade (correct / partial / incorrect):** ____


## scn_018__run1

**Incident:** Since ~08:30 UTC proxy-service is returning 5xx on about a third of requests and the rate is climbing. No deploys today. inventory-api had a spell of errors earlier this morning.

**Ground-truth cause:** proxy-service leaks file descriptors on one error path: connections opened to inventory-api during a request are not closed when that request hits a specific downstream error, so the socket and its fd stay open indefinitely. An earlier spell of inventory-api errors accelerated the leak; open fds climbed from ~8k toward the 40k limit. Once the limit was hit, proxy-service could not accept new connections or open upstream ones ('too many open files'), so ~30% of requests failed. A restart resets the fd count but the leak remains until the error-path code is fixed.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 4 tool calls):** file descriptor exhaustion due to socket/file descriptor leak, leading to EMFILE errors and inability to accept new connections or open upstream connections

**Agent citations:** ['proxy-service / error_rate summary: first=0.002, last=0.3004, max=0.3058, change +15190.0%', 'proxy-service ERROR accept() failing: too many open files (EMFILE)', 'proxy-service ERROR cannot open new upstream connections; 5xx rate 30%', 'proxy-service / open_fds summary: first=7960.5352, last=39645.0476, max=40784.4371']

**Grade (correct / partial / incorrect):** ____


## scn_019__run1

**Incident:** Since ~19:32 UTC image resizing is extremely slow platform-wide and the resize queue is huge. No deploys. CPU on the resize fleet is pinned.

**Ground-truth cause:** A user uploaded a decompression-bomb image: a ~40KB file that declares 48000x48000 pixel dimensions. image-resizer attempted to fully decode it, consuming enormous CPU and holding a worker for tens of seconds per attempt. The client retried the same asset ~140 times, so many workers were simultaneously stuck on oversized-decode jobs, CPU saturated, and the resize queue backed up for all users. There was no deploy - the trigger was the crafted input plus the absence of a decoded-size guard. Recovery required adding a max-decoded-dimension check and blocklisting the asset.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 5 tool calls):** CPU exhaustion on the image-resizer fleet caused by decoding an excessively large declared image dimension (48000x48000 px from a 40KB file) for asset a91f, amplified by 140 client retries.

**Agent citations:** ['image-resizer / cpu_utilization_pct jumped to ~100% starting at 19:32 UTC', '2026-12-01T19:32:00Z image-resizer ERROR decode job for asset a91f exceeded 60s; image declares 48000x48000 px from a 40KB file', '2026-12-01T19:37:00Z image-resizer WARN asset a91f resubmitted 140 times (client retry)']

**Grade (correct / partial / incorrect):** ____


## scn_020__run1

**Incident:** Since ~13:15 UTC a large share of checkouts are failing. Payments and inventory look fine. The error seems to be at the tax calculation step. No deploys today.

**Ground-truth cause:** The external tax-calculation provider (api.taxly.io) had a major outage starting ~13:12 UTC, confirmed on its status page. checkout-api calls the provider for a tax quote on every checkout; those calls returned 503 and then timed out, so up to ~60% of checkout attempts failed at the tax step. The failure is isolated to the tax-calc integration - payments and inventory calls stayed healthy - and there were no deploys. The fix belongs to the provider; the mitigation was to fall back to cached tax rates.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 2 tool calls):** The external tax calculation provider api.taxly.io is experiencing a major outage and timing out, causing checkout-api tax calculation failures.

**Agent citations:** ['checkout-api / tax_calc_success_rate metric drops sharply starting at 13:16 UTC down to ~0.10', 'log line 2026-12-04T13:15:00Z: tax-calc provider api.taxly.io returning 503; ~12% of checkouts affected', 'log line 2026-12-04T13:18:00Z: tax-calc calls timing out; ~60% of checkout attempts failing at the tax step', 'log line 2026-12-04T13:20:00Z: taxly.io status page reports a major outage since 13:12 UTC; ETA unknown']

**Grade (correct / partial / incorrect):** ____


## scn_021__run1

**Incident:** Since ~07:42 UTC multiple services are slow or erroring - auth, profiles, feed. Databases report very high load. No deploys. Someone mentioned the cache cluster had a node problem.

**Ground-truth cause:** The shared Redis cluster used for sessions and hot caches lost its primary node (redis-01), and automatic failover to redis-02 stalled on a split-brain guard, so the cache was unavailable cluster-wide. Every read that would have been a cache hit fell through to the origin databases. That cache-miss stampede pushed users-db to its connection limit (480/500), so query latency climbed and dependent services (profile-api, web-frontend auth) timed out - a thundering herd triggered by the cache outage, not by any change on the services themselves. Recovery required manually promoting redis-02 and letting the cache warm.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 3 tool calls):** The primary session-store cache node (redis-01) became unresponsive, causing automatic failover to fail due to a split-brain guard. This resulted in cache availability dropping to zero and triggered cascading high connection utilization on the users database.

**Agent citations:** ['session-store / cache_availability dropped from ~1.0 to near 0 starting at 07:41 UTC', 'users-db / db_connection_utilization spiked to nearly 99% starting at 07:43 UTC', '2026-12-08T07:40:00Z session-store ERROR primary node redis-01 unresponsive; automatic failover to redis-02 did not complete (split-brain guard)']

**Grade (correct / partial / incorrect):** ____


## scn_022__run1

**Incident:** Since ~12:00 UTC many users cannot reach the site at all, and some outbound API calls are failing intermittently. Our servers look healthy. Reports say a DNS provider is having problems.

**Ground-truth cause:** The managed DNS provider hosting the company's public DNS zones was hit by a large DDoS starting ~11:58 UTC (confirmed by the provider). External resolution of the company's own domains - and of some third-party endpoints on the same provider - became unreliable, dropping to ~55% success from multiple regions, so users could not reliably reach the site and ~20% of outbound third-party calls failed at DNS resolution. Internal DNS and the origin servers were healthy; the failure was entirely at the external authoritative DNS layer, which the company does not operate. The mitigation was to activate a secondary DNS provider for critical zones.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** External DNS provider failure causing name resolution failures and intermittent outbound API call failures starting around 12:01 UTC

**Agent citations:** ['edge-monitor external_dns_success_rate dropped sharply starting at 12:01 UTC down to ~0.54', 'edge-monitor synthetic_checkout_success_rate dropped starting at 12:04 UTC down to ~0.63', 'dns-and-network-failures.md > Symptoms describes intermittent or total failure to reach a dependency with name resolution errors']

**Grade (correct / partial / incorrect):** ____


## scn_023__run1

**Incident:** Since ~10:03 UTC several services report 'no healthy instances' for dependencies that are actually up. Errors are widespread. No application deploys. The platform team applied a service-discovery config change this morning.

**Ground-truth cause:** A config reload on the service-discovery cluster corrupted its health-check subsystem, which then returned empty or partial backend lists for ~30% of services. Clients querying discovery (orders-api and others) saw '0 healthy instances' for dependencies like payments-api that were actually healthy, and stopped routing to them, so those calls all failed. Nothing was wrong with the backend services - the platform's service catalog was stale. Recovery required rolling back the config reload and re-syncing the catalog from a healthy replica.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 4 tool calls):** The service-discovery config change applied this morning triggered a config reload that caused the health-check subsystem to return empty results for 30% of services, resulting in widespread 'no healthy instances' errors.

**Agent citations:** ['service-discovery / discovery_catalog_completeness dropped from 1.0188 down to a minimum of 0.3922 starting around 10:02 UTC', '2026-12-15T10:00:00Z service-discovery WARN config reload applied; catalog re-sync in progress', '2026-12-15T10:01:00Z service-discovery ERROR health-check subsystem returning empty results for 30% of services after the reload', '2026-12-15T10:20:00Z service-discovery INFO rolled back the config reload; catalog re-synced from a healthy replica; backends restored']

**Grade (correct / partial / incorrect):** ____


## scn_024__run1

**Incident:** Since ~16:20 UTC EU users report the site looks broken - images and styles not loading. US and APAC are fine. API calls work. No deploys.

**Ground-truth cause:** The CDN provider serving static assets had degraded performance at its Frankfurt and Amsterdam edge locations starting ~16:15 UTC (confirmed on the provider's status page). EU users experienced slow or failed asset loads - error rate up to ~35%, p95 latency ~4s - so pages rendered broken for them. The origin asset servers and all API endpoints were healthy; the problem was confined to the CDN edge in EU. Recovery came when the provider shifted EU traffic to alternate POPs.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** CDN-edge failure in the EU region causing asset serving errors and high latency for static assets while origin and API endpoints remain unaffected

**Agent citations:** ['EU users report site looks broken - images and styles not loading starting around 16:20 UTC', 'static-assets / asset_error_rate_eu spiked from 0.0051 to 0.1204 at 16:21 UTC and reached ~0.35', 'static-assets / asset_p95_latency_ms_eu jumped from ~120ms to over 4000ms starting at 16:22 UTC', '2026-12-18T16:26:00Z static-assets INFO origin asset serving is healthy; API endpoints unaffected; issue is CDN-edge only, EU only']

**Grade (correct / partial / incorrect):** ____


## scn_025__run1

**Incident:** Since ~03:03 UTC the app is throwing 503s for most users. The load balancer shows most instances as unhealthy, but the instances themselves look fine. No application deploys. A load-balancer config change went in overnight.

**Ground-truth cause:** A config change (CR-9012) pointed the load balancer's health check at /ready, which returns 503 until a background cache is warm. When the nightly cache flush and rebuild ran, 18 of 24 app-server instances failed that health check - even though they could serve traffic - and the load balancer removed them from rotation. The remaining 6 instances overloaded (95% CPU) and started returning 503s. The instances were never unhealthy; the health check was testing readiness of a warming cache, not liveness. Recovery required reverting the health check to a liveness-only path.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 4 tool calls):** An overnight load-balancer configuration change caused most instances to be marked unhealthy, removing them from rotation and overloading the remaining instances.

**Agent citations:** ['A load-balancer config change went in overnight.', 'app-lb / lb_healthy_instances dropped by 75.3% around 03:04 UTC.', 'app-lb / http_5xx_rate spiked significantly starting at 03:06 UTC.', 'app-lb log line at 03:05:00Z: ERROR only 6 instances in rotation; each at 95% CPU; 503 rate climbing']

**Grade (correct / partial / incorrect):** ____


## scn_026__run1

**Incident:** Since ~09:19 UTC large file uploads and streaming responses are failing about 40% of the time with connection resets. Small quick requests mostly work. No deploys. Network team did a planned firewall failover this morning.

**Ground-truth cause:** A planned failover of the edge firewall pair to the secondary unit created an asymmetric network path: outbound traffic went through the secondary firewall while return traffic still routed through the primary. Each stateful firewall only saw one direction of a connection, so it dropped the 'unexpected' return packets. Connections needing many round-trips (large uploads, streaming responses) failed with mid-transfer TCP resets at ~40%, while short request/response pairs usually completed before hitting the problem. The trigger is the failover leaving routing asymmetric. Recovery required correcting the return route to match the outbound path.

**Ground-truth should_escalate:** False

**Agent (escalate, 4 tool calls):** Although metrics, logs, and the incident report confirm that large file uploads and streaming responses are failing with TCP resets on the region-gateway starting at ~09:19 UTC following a network firewall failover, the retrieved runbooks only cover connection-pool exhaustion and do not provide specific guidance or mitigation steps for network firewall failover-induced TCP resets on long-lived connections.

**Grade (correct / partial / incorrect):** ____


## scn_027__run1

**Incident:** orders-api error rate has been spiking to about 6% for roughly 8 minutes at a time, about every 90-120 minutes, since ~02:00 UTC. It recovers on its own each time. No deploys. On-call wants to know what is causing it.

**Ground-truth cause:** Undetermined. orders-api error rate spikes to ~6% for ~8 minutes on a rough 90-120 minute cadence starting ~02:00, while latency and resource use stay essentially flat and downstream dependencies are healthy during the spikes. No deploy, config change, traffic change, or visible scheduled job correlates with the cadence, and the errors are spread across all hosts. The periodic shape suggests something scheduled - a batch job on shared infrastructure, a noisy neighbour, or a client - but the available evidence does not identify it.

**Ground-truth should_escalate:** True

**Agent (escalate, 6 tool calls):** The tool-call budget was exhausted before the investigation could fully localize the root cause of the periodic error spikes, which exhibit intermittent behavior with no correlated deploys or resource saturation.

**Grade (correct / partial / incorrect):** ____


## scn_028__run1

**Incident:** Since ~14:02 UTC about 30% of partner API calls are failing authentication. The rest succeed. No application deploys. The identity team did a scheduled secret rotation at 14:00.

**Ground-truth cause:** The OAuth client secret that partner-api-gateway uses to authenticate to the internal identity provider was rotated on schedule and the old secret was revoked. The new secret was in place at the identity provider, but a subset of partner-api-gateway pods - those that autoscaled up after ~13:40 from a stale config map - came up holding the pre-rotation secret. Those pods' token requests returned '401 invalid_client', failing ~30% of partner API calls. The rotation itself was fine; the failure is a config-propagation gap that left some pods on the revoked secret. Recovery required rolling the deployment to force fresh config onto all pods.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 4 tool calls):** Config map version skew caused newer partner-api-gateway pods started after 13:40 to hold the pre-rotation client secret following the identity team's scheduled secret rotation at 14:00.

**Agent citations:** ['INCIDENT REPORT: The identity team did a scheduled secret rotation at 14:00.', 'auth_failure_rate metric on partner-api-gateway spiked to ~0.30 starting at 14:03 UTC.', 'partner-api-gateway log: ~30% of partner API calls failing auth; affected pods started after 13:40 with a stale config', 'partner-api-gateway log: config map version skew: newer pods hold the pre-rotation client secret']

**Grade (correct / partial / incorrect):** ____


## scn_029__run1

**Incident:** Since ~11:30 UTC orders-service is intermittently failing with database connection errors - about 15% of requests. No deploys. The fleet was scaled up this morning for load.

**Ground-truth cause:** The database's server-side connection limit (max_connections = 500) was reached. Each orders-service instance holds a static pool of 10 connections; the fleet had grown over the week and an autoscale from 40 to 52 instances that morning brought total pool demand to 52 x 10 = 520, exceeding 500. The database began refusing new connections ('too many clients already'), so ~15% of requests failed to acquire a connection. There was no code deploy - the cause is cumulative connection demand crossing the fixed limit, tipped over by the morning's scale-up. Recovery required lowering the per-instance pool size and raising max_connections.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 3 tool calls):** The fleet scale-up in the morning caused the total number of client connections from orders-service to exceed the database connection limit on orders-db, resulting in connection acquire failures ("FATAL: sorry, too many clients already").

**Agent citations:** ['orders-service connection_acquire_error_rate metric spiked starting at 11:33 UTC from 0.001 to ~0.15', 'orders-db db_active_connections metric increased up to ~505 starting around 11:31 UTC', 'orders-service logs show: FATAL: sorry, too many clients already; ~15% of requests failing to acquire a DB connection']

**Grade (correct / partial / incorrect):** ____


## scn_030__run1

**Incident:** Since ~08:00 UTC the dashboards are timing out and anything sharing the reporting database is slow. Database CPU is near 100%. No deploys. There was a large data import into the reporting database earlier.

**Ground-truth cause:** A routine auto-analyze, triggered after a ~30M-row bulk import into the events table, updated the table statistics, and the query planner then switched a frequently-run dashboard query (q_dashboard_summary) from an index scan to a sequential scan on the 200M-row events table. That query's latency jumped from ~40ms to over 8s, and the repeated sequential scans drove database CPU to 96%, slowing every other query sharing the database. There was no deploy - the trigger was the statistics refresh changing the plan. Recovery required pinning the good (index) plan for that query.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 4 tool calls):** A large data import into the reporting database caused database CPU utilization to spike to near 100%, leading to severe query p95 latency and dashboard timeouts.

**Agent citations:** ['reporting-db / db_cpu_utilization_pct spiked from ~34.6% to max 97.6% starting at 08:02 UTC', 'reporting-db / query_p95_latency_ms spiked from ~39.9ms to max 12220.8ms starting at 08:02 UTC', 'dashboard-api ERROR log at 2027-01-20T08:03:00Z: dashboard requests timing out; DB CPU 96%']

**Grade (correct / partial / incorrect):** ____

