# Downstream dependency failure

## Symptoms

A service returns errors on the operations that call a particular dependency,
while operations that do not touch that dependency stay healthy. Error messages
point outward: upstream unavailable, connection refused, timeouts, or 5xx from a
named backend. Multiple unrelated services degrade at once if they share the
dependency.

## Likely causes

- The dependency itself is down or degraded (its own deploy, resource exhaustion,
  data-store failure, or capacity change).
- A network partition or DNS failure between the caller and the dependency.
- The dependency is rate-limiting or shedding load and returning errors by design.
- Credentials or certificates for the dependency expired.

## How to confirm

- Identify which code paths fail and which succeed; the common factor is usually a
  single dependency.
- Check the dependency's own health signals and incident channel before assuming
  the caller is at fault.
- Distinguish "dependency is down" from "cannot reach dependency" by testing
  connectivity and name resolution directly.

## Mitigation

The fix belongs with the dependency; the caller's job is to contain the blast
radius. Serve stale or cached data where possible, fail soft for non-critical
paths, open a circuit breaker, and queue writes for later. Escalate to the team
that owns the dependency.

## References

- Amazon S3 service disruption, US-EAST-1, February 28, 2017:
  https://aws.amazon.com/message/41926/
- Google SRE Book, "Addressing Cascading Failures": https://sre.google/books/
