# Worker or thread pool exhaustion

## Symptoms

The service stops accepting new work: log lines about a full worker pool, a
rejected-execution error, or a saturated event loop. Inbound requests are queued
or dropped with 503 responses. Already-running requests may still complete slowly.

## Likely causes

- Downstream calls blocking worker threads for longer than usual, so all workers
  are tied up waiting.
- A retry storm or traffic surge exceeding the pool's capacity.
- Long-running or unbounded work (large exports, synchronous fan-out) occupying
  workers that are needed for normal traffic.
- Pool sized too small, or blocking I/O on an event loop that assumes
  non-blocking calls.

## How to confirm

- Check worker pool utilisation and queue depth: workers at the ceiling, queue
  growing, rejections rising.
- Determine what the busy workers are doing: a thread dump or active-span sample
  usually shows them all blocked on the same downstream call.
- Correlate onset with downstream latency, traffic, and deploys.

## Mitigation

Shed load at the edge so the service can drain. Add per-dependency timeouts so a
slow downstream cannot hold a worker indefinitely. Separate pools for slow work,
size for peak concurrency, and make fan-out asynchronous.

## References

- Google SRE Book, "Addressing Cascading Failures": https://sre.google/books/
