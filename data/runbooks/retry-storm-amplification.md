# Retry storm and load amplification

## Symptoms

A small latency increase in a downstream dependency is followed by a
disproportionately large spike in traffic to that dependency and in resource use
on the caller. Outbound request rate from the caller rises well above its inbound
request rate. The caller degrades or fails even though the downstream problem was
minor.

## Likely causes

- Client retries with no backoff, no jitter, and no retry budget. Every slow call
  becomes several calls, multiplying load by the retry count.
- Retries stacked at multiple layers (library, service mesh, gateway) so the
  amplification compounds.
- Timeouts set longer than the caller's own deadline, so retries pile up while the
  original request is still waiting.

## How to confirm

- Compare the caller's outbound request rate to its inbound request rate. A ratio
  well above 1 during the incident indicates amplification.
- Look for log lines showing repeated attempts against the same dependency.
- Check the retry configuration: fixed-interval or immediate retries, and absence
  of a circuit breaker, are the tell.

## Mitigation

Reduce or disable the retry budget to break the storm, then restore capacity.
Fix the client to use exponential backoff with jitter, a bounded retry budget,
and a circuit breaker. Ensure only one layer retries.

## References

- AWS Builders' Library, "Timeouts, retries, and backoff with jitter":
  https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
