# Database degradation

## Symptoms

Queries slow down or time out, error rates rise on database-backed endpoints, and
the caller may then show connection pool exhaustion as a secondary effect.
Replica lag increases, or the primary shows high load, lock waits, or rejected
connections.

## Likely causes

- A missing or dropped index, or a query-plan change after a statistics update or
  version upgrade, making a common query expensive.
- A long-running transaction or migration holding locks.
- Replica lag from a write spike, a large backfill, or replication falling behind,
  so reads served from replicas are slow or stale.
- Connection limit reached on the database side.
- Vacuum, compaction, or checkpoint activity competing with live traffic.

## How to confirm

- Identify the slow queries and inspect their execution plans; compare against a
  known-good baseline.
- Check replica lag, active connection count against the limit, and lock waits.
- Correlate with deploys, schema migrations, and large batch jobs.

## Mitigation

Kill or pause the offending query, transaction, or batch job. Add the missing
index or pin the plan. Route reads away from lagging replicas. Raise connection
limits only as a stopgap. Schedule heavy maintenance away from peak.

## References

- GitLab.com database incident, January 31, 2017:
  https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/
