# Connection pool exhaustion

## Symptoms

Errors or log lines stating that a connection pool is exhausted, that all
connections are in use, or that acquisition timed out with many waiters queued.
Pool wait time rises sharply. Throughput collapses while CPU and memory may look
normal, because requests are blocked waiting for a connection rather than doing
work.

## Likely causes

- A slow downstream (database, cache, or another service) holding connections
  longer, so the fixed-size pool drains and cannot refill fast enough.
- Retry amplification increasing concurrent outbound calls beyond the pool size.
- A connection leak: connections checked out and never returned due to a missing
  release in an error path.
- Pool sized too small for current traffic, or a single pool shared between fast
  local work and slow remote calls.

## How to confirm

- Check pool metrics: active connections at the ceiling, waiters greater than
  zero, rising acquisition wait time.
- Correlate with downstream latency and with the caller's outbound request rate.
- If downstream latency is normal, suspect a leak; look for steadily falling idle
  connections over time.

## Mitigation

Relieve the downstream slowdown or cut the offending traffic. Then isolate pools
per dependency, size them for peak concurrency, add acquisition timeouts, and fix
any code path that fails to release a connection.

## References

- AWS Builders' Library, "Using load shedding to avoid overload":
  https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/
