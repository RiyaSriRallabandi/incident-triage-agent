# Memory growth and out-of-memory kills

## Symptoms

Memory use climbs steadily over minutes or hours rather than tracking load.
Eventually instances are killed and restarted (OOM), latency rises from garbage
collection pressure before the kill, and the pattern repeats on a sawtooth as
instances cycle.

## Likely causes

- A leak: objects retained in a cache, list, or map that is never bounded or
  evicted; listeners or connections never closed.
- An unbounded in-memory buffer or queue that grows when a consumer falls behind.
- A recent change increasing per-request allocation, or a larger working set from
  a data or traffic change.
- Heap or container memory limit set too low for the real working set.

## How to confirm

- Plot memory over time: a steady upward slope independent of request rate points
  to a leak; a step change points to a config or workload change.
- Check restart and OOM-kill counts for the service.
- Capture a heap dump and compare object counts over time, or watch which pool or
  cache grows without bound.

## Mitigation

Restart to buy time, then fix the retention: bound and evict caches, close
resources in finally blocks, add backpressure to queues. Right-size the memory
limit only after the leak is ruled out.

## References

- Google SRE Book, "Managing Critical State" and "Addressing Cascading Failures":
  https://sre.google/books/
