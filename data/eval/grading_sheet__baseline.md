# Grading sheet - baseline


## scn_001__run1

**Incident:** Since ~13:42 UTC the edge tier is serving a high rate of 502s for a large fraction of all traffic. Customer reports came in within a few minutes. No known infrastructure maintenance was scheduled. Edge hosts look CPU-bound.

**Ground-truth cause:** A newly deployed WAF managed-rule set (commit 7f3a9c1) contained a rule (100417) with a catastrophically backtracking regular expression. Evaluating that pattern against normal request traffic drove edge-proxy worker CPU to saturation within about a minute, so requests queued and then failed with 502s across effectively all traffic.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 6 tool calls):** The rollout of WAF managed ruleset 2026.05.12 introduced a rule (100417) containing nested quantifiers in its pattern, causing regex evaluations to exceed the 40ms budget, which spiked edge-proxy CPU utilization and led to a high rate of 5xx errors.

**Agent citations:** ['edge-proxy / cpu_utilization_pct spiked from 34.5% to near 100% starting at 13:43 UTC', 'edge-proxy / http_5xx_rate spiked from 0.002 to ~0.628 starting at 13:44 UTC', 'deploy at 2026-05-12T13:42:00Z rolled out WAF managed ruleset 2026.05.12 adding ~30 new rules including rule 100417', 'waf-engine log at 2026-05-12T13:42:45Z showing ERROR: regex evaluation exceeded 40ms budget on managed rule 100417 (pattern contains nested quantifiers: (?:.*.*=.*))']

**Grade (correct / partial / incorrect):** ____


## scn_001__run2

**Incident:** Since ~13:42 UTC the edge tier is serving a high rate of 502s for a large fraction of all traffic. Customer reports came in within a few minutes. No known infrastructure maintenance was scheduled. Edge hosts look CPU-bound.

**Ground-truth cause:** A newly deployed WAF managed-rule set (commit 7f3a9c1) contained a rule (100417) with a catastrophically backtracking regular expression. Evaluating that pattern against normal request traffic drove edge-proxy worker CPU to saturation within about a minute, so requests queued and then failed with 502s across effectively all traffic.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** The rollout of WAF managed ruleset 2026.05.12 at 13:42 UTC caused severe CPU exhaustion on edge-proxy hosts, leading to a high rate of 502 errors.

**Agent citations:** ['edge-proxy / http_5xx_rate jumped from 0.002 to 0.408 at 13:44 UTC and peaked around 0.6304', 'edge-proxy / cpu_utilization_pct jumped from ~35% to 98.977% at 13:44 UTC and stayed near/above 100%', 'deploy at 2026-05-12T13:42:00Z for edge-proxy rolled out WAF managed ruleset 2026.05.12']

**Grade (correct / partial / incorrect):** ____


## scn_001__run3

**Incident:** Since ~13:42 UTC the edge tier is serving a high rate of 502s for a large fraction of all traffic. Customer reports came in within a few minutes. No known infrastructure maintenance was scheduled. Edge hosts look CPU-bound.

**Ground-truth cause:** A newly deployed WAF managed-rule set (commit 7f3a9c1) contained a rule (100417) with a catastrophically backtracking regular expression. Evaluating that pattern against normal request traffic drove edge-proxy worker CPU to saturation within about a minute, so requests queued and then failed with 502s across effectively all traffic.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 1.0, 5 tool calls):** The rollout of WAF managed ruleset 2026.05.12 at 13:42 UTC caused severe CPU saturation on edge-proxy hosts, leading to worker exhaustion and a surge in 502 errors.

**Agent citations:** ['edge-proxy cpu_utilization_pct jumped from 34.5% to near 100% starting at 13:43 UTC', 'edge-proxy http_5xx_rate surged from 0.002 to ~0.62 at 13:44 UTC', 'Deploy at 2026-05-12T13:42:00Z rolled out WAF managed ruleset 2026.05.12 on edge-proxy', 'Log at 13:43:00Z: worker CPU saturated; request queue growing (depth=4100)', 'Log at 13:43:35Z: returning 502: no worker capacity to accept connection']

**Grade (correct / partial / incorrect):** ____


## scn_002__run1

**Incident:** Checkout started returning 503s to a growing share of users around 09:23 UTC. Error rate on checkout-api is elevated and latency is high. No deploys went out today. Payments processing also looks a bit slow. On-call is unsure whether checkout or payments is the real problem.

**Ground-truth cause:** A modest latency increase in payments-api (read-replica lag pushed p95 from ~90ms to ~400ms) triggered aggressive retries from checkout-api's payments client, which had no backoff and no retry budget. Retry amplification roughly 5x'd checkout-api's outbound request volume, which exhausted its database connection pool and then its worker thread pool, turning a minor downstream slowdown into a checkout outage.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** Elevated latency in payments-api caused transactions to hold database connections open longer in checkout-api, which exhausted the checkout-api database connection pool (size=20, active=20, waiters=140) and worker thread pool, resulting in HTTP 503 errors.

**Agent citations:** ['checkout-api error rate metric spiked to ~0.34 starting around 09:22 UTC', 'checkout-api db_pool_wait_ms metric increased from ~2ms to over 5000ms starting at 09:20 UTC', 'checkout-api log: DB connection pool exhausted (size=20, active=20, waiters=140) at 2026-06-03T09:21:00Z', 'checkout-api log: worker thread pool exhausted; rejecting inbound requests at 2026-06-03T09:22:00Z', 'payments-api p95_latency_ms metric spiked from ~90ms to over 400ms starting at 09:16 UTC']

**Grade (correct / partial / incorrect):** ____


## scn_002__run2

**Incident:** Checkout started returning 503s to a growing share of users around 09:23 UTC. Error rate on checkout-api is elevated and latency is high. No deploys went out today. Payments processing also looks a bit slow. On-call is unsure whether checkout or payments is the real problem.

**Ground-truth cause:** A modest latency increase in payments-api (read-replica lag pushed p95 from ~90ms to ~400ms) triggered aggressive retries from checkout-api's payments client, which had no backoff and no retry budget. Retry amplification roughly 5x'd checkout-api's outbound request volume, which exhausted its database connection pool and then its worker thread pool, turning a minor downstream slowdown into a checkout outage.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.9, 6 tool calls):** payments-api latency spike led to downstream database connection pool exhaustion in checkout-api, causing 503 errors and high wait times

**Agent citations:** ['payments-api / p95_latency_ms spiked at 09:16 UTC', 'checkout-api / db_pool_wait_ms spiked starting at 09:20 UTC', 'checkout-api / error_rate spiked starting at 09:22 UTC', 'connection-pool-exhaustion.md > Likely causes: A slow downstream (database, cache, or another service) holding connections longer, so the fixed-size pool drains and cannot refill fast enough.']

**Grade (correct / partial / incorrect):** ____


## scn_002__run3

**Incident:** Checkout started returning 503s to a growing share of users around 09:23 UTC. Error rate on checkout-api is elevated and latency is high. No deploys went out today. Payments processing also looks a bit slow. On-call is unsure whether checkout or payments is the real problem.

**Ground-truth cause:** A modest latency increase in payments-api (read-replica lag pushed p95 from ~90ms to ~400ms) triggered aggressive retries from checkout-api's payments client, which had no backoff and no retry budget. Retry amplification roughly 5x'd checkout-api's outbound request volume, which exhausted its database connection pool and then its worker thread pool, turning a minor downstream slowdown into a checkout outage.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 5 tool calls):** Downstream latency in payments-api caused checkout-api threads/connections to block waiting on outbound payment calls, leading to database connection pool exhaustion and subsequent 503 errors.

**Agent citations:** ['payments-api p95 latency increased starting at 09:16 UTC', 'checkout-api log at 09:17:00Z showed downstream payments-api call slow', 'checkout-api database pool wait times spiked starting at 09:20 UTC', 'checkout-api error rate spiked starting at 09:22 UTC']

**Grade (correct / partial / incorrect):** ____


## scn_003__run1

**Incident:** Starting ~18:07 UTC, media-api is returning 500s on most requests and image uploads are failing. The web app shows broken images site-wide. Nothing was deployed to media-api or uploads-worker recently. Platform team was doing some storage maintenance earlier in the hour.

**Ground-truth cause:** During planned index-tier capacity maintenance, an operator ran a capacity-removal command with an incorrect argument and removed 48 storage nodes instead of 4. That dropped the object-store index subsystem below quorum, forcing a multi-hour full restart of the index and placement subsystems. Every service depending on object reads and writes (media-api, uploads-worker) failed or degraded until object-store recovered.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 3 tool calls):** Object-store availability failure resulting from earlier platform storage maintenance caused media-api upstream connection and retrieval failures.

**Agent citations:** ['media-api error_rate spiked from 0.001 to ~0.88 starting at 18:08 UTC', 'object-store availability_pct crashed to ~12% precisely at 18:07 UTC', 'media-api log shows: object-store GET failed: 500 upstream_unavailable (retries exhausted)']

**Grade (correct / partial / incorrect):** ____


## scn_003__run2

**Incident:** Starting ~18:07 UTC, media-api is returning 500s on most requests and image uploads are failing. The web app shows broken images site-wide. Nothing was deployed to media-api or uploads-worker recently. Platform team was doing some storage maintenance earlier in the hour.

**Ground-truth cause:** During planned index-tier capacity maintenance, an operator ran a capacity-removal command with an incorrect argument and removed 48 storage nodes instead of 4. That dropped the object-store index subsystem below quorum, forcing a multi-hour full restart of the index and placement subsystems. Every service depending on object reads and writes (media-api, uploads-worker) failed or degraded until object-store recovered.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.99, 4 tool calls):** The object-store service experienced an availability drop following storage maintenance, causing upstream failures and exhausting retries for media-api GET requests.

**Agent citations:** ['No deploys found in the given scope for media-api.', 'media-api error_rate jumped from 0.001 to 0.8774 at 18:08 UTC.', 'object-store availability_pct dropped from ~98% to ~12% starting at 18:07 UTC.', "media-api log shows: '2026-07-19T18:07:10Z media-api ERROR object-store GET failed: 500 upstream_unavailable (retries exhausted)'"]

**Grade (correct / partial / incorrect):** ____


## scn_003__run3

**Incident:** Starting ~18:07 UTC, media-api is returning 500s on most requests and image uploads are failing. The web app shows broken images site-wide. Nothing was deployed to media-api or uploads-worker recently. Platform team was doing some storage maintenance earlier in the hour.

**Ground-truth cause:** During planned index-tier capacity maintenance, an operator ran a capacity-removal command with an incorrect argument and removed 48 storage nodes instead of 4. That dropped the object-store index subsystem below quorum, forcing a multi-hour full restart of the index and placement subsystems. Every service depending on object reads and writes (media-api, uploads-worker) failed or degraded until object-store recovered.

**Ground-truth should_escalate:** False

**Agent (diagnosis, confidence 0.95, 3 tool calls):** The object-store index subsystem dropped below quorum and entered recovery mode, causing upstream unavailable errors and connection failures for media-api.

**Agent citations:** ['media-api error log: object-store GET failed: 500 upstream_unavailable (retries exhausted)', 'object-store availability metric dropped sharply from normal levels to ~12% starting at 18:07 UTC', 'object-store error log: index subsystem dropped below quorum; entering recovery mode']

**Grade (correct / partial / incorrect):** ____


## scn_004__run1

**Incident:** notifications-api error rate has been intermittently elevated (roughly 3-5%, normally under 0.5%) since about 02:30 UTC. No deploys in the last 24 hours. Downstream providers look fine. It has partially recovered on its own. On-call wants a root cause before standing down.

**Ground-truth cause:** Undetermined. The evidence shows a modest, intermittent rise in notifications-api error rate spread across most hosts, with no correlated deploy, no downstream degradation, and no clear resource signal (latency barely moved, heap is flat). The available data is insufficient to identify a root cause.

**Ground-truth should_escalate:** True

**Agent (escalate, 6 tool calls):** The tool-call budget was exhausted before the investigation could fully localize the downstream dependency or root cause of the context deadline exceeded errors in the send path.

**Grade (correct / partial / incorrect):** ____


## scn_004__run2

**Incident:** notifications-api error rate has been intermittently elevated (roughly 3-5%, normally under 0.5%) since about 02:30 UTC. No deploys in the last 24 hours. Downstream providers look fine. It has partially recovered on its own. On-call wants a root cause before standing down.

**Ground-truth cause:** Undetermined. The evidence shows a modest, intermittent rise in notifications-api error rate spread across most hosts, with no correlated deploy, no downstream degradation, and no clear resource signal (latency barely moved, heap is flat). The available data is insufficient to identify a root cause.

**Ground-truth should_escalate:** True

**Agent (escalate, 6 tool calls):** The tool-call budget was exhausted before the investigation could confirm the exact root cause of the context deadlines exceeded in the notifications-api send path.

**Grade (correct / partial / incorrect):** ____


## scn_004__run3

**Incident:** notifications-api error rate has been intermittently elevated (roughly 3-5%, normally under 0.5%) since about 02:30 UTC. No deploys in the last 24 hours. Downstream providers look fine. It has partially recovered on its own. On-call wants a root cause before standing down.

**Ground-truth cause:** Undetermined. The evidence shows a modest, intermittent rise in notifications-api error rate spread across most hosts, with no correlated deploy, no downstream degradation, and no clear resource signal (latency barely moved, heap is flat). The available data is insufficient to identify a root cause.

**Ground-truth should_escalate:** True

**Agent (escalate, 6 tool calls):** The tool-call budget was exhausted before the investigation could be finished. Although a specific unhandled exception ('context deadline exceeded') was found in the notifications-api send path, further investigation into downstream databases, proxies, or gateways yielded no matching error logs, leaving the root cause unconfirmed.

**Grade (correct / partial / incorrect):** ____

