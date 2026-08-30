# DNS and network resolution failures

## Symptoms

Intermittent or total failure to reach a dependency, with errors about name
resolution, no route to host, connection timeouts, or TLS handshake failures.
The dependency itself is healthy when reached by other clients. Failures may
cluster by client region, availability zone, or resolver.

## Likely causes

- A DNS change: a record updated, deleted, or with a TTL that caused stale
  resolution; a misconfigured split-horizon or private zone.
- Resolver overload or a failing upstream resolver.
- A network path change: a security-group or firewall rule, a routing update, a
  peering or VPN failure.
- Connection or DNS caches holding a now-invalid answer.

## How to confirm

- Resolve the name manually from an affected host and from a healthy host; compare
  answers and response times.
- Test raw connectivity to the dependency's address, bypassing DNS.
- Check for recent DNS record changes and network or firewall changes in the
  window.
- Look at whether failures correlate with a specific zone, subnet, or resolver.

## Mitigation

Roll back the DNS or network change. Flush caches where a stale answer is stuck.
Add health-checked failover for critical names and monitor resolution success
rate as a first-class signal.

## References

- Google SRE Book, "Load Balancing at the Frontend": https://sre.google/books/
