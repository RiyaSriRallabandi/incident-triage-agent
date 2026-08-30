# CPU saturation

## Symptoms

Processor utilisation pinned at or near 100% across most or all instances of a
service. Request latency climbs, work queues grow, and the service eventually
returns 5xx errors or times out because there is no spare capacity to accept new
work. Recovery is immediate once the CPU cost is removed.

## Likely causes

- A pathological code path introduced by a recent change: a catastrophically
  backtracking regular expression, an accidental O(n^2) loop, unbounded JSON
  parsing, or serialization of a large object on every request.
- A cache that stopped working, forcing expensive recomputation per request.
- A retry storm or traffic surge pushing the service past its capacity.
- Garbage collection thrashing due to memory pressure.

## How to confirm

- Confirm the spike is CPU specifically, not memory or I/O wait.
- Correlate the onset with deploy history and with any change in request mix.
- Capture a CPU profile or flame graph if the service is still up; look for a
  single dominant frame.
- Check for log lines naming a slow rule, slow query, or evaluation-budget
  exceeded.

## Mitigation

Roll back the change that introduced the hot path. If it is load-driven, shed
load or scale out. Add a CPU budget or timeout around the expensive operation and
a pre-deploy complexity check where possible.

## References

- Google SRE Book, "Handling Overload": https://sre.google/books/
- Cloudflare, "Details of the Cloudflare outage on July 2, 2019":
  https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/
