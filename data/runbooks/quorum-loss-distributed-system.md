# Quorum loss in a distributed system

## Symptoms

A stateful system (database cluster, coordination service, object store index,
message broker) reports that it is below quorum, has lost its leader, is
read-only, or has entered a recovery or safe mode. Reads may partially succeed
from cache or replicas; writes fail. Recovery is often slow because the system
must rebuild or re-replicate state.

## Likely causes

- Too many nodes lost at once: a bad capacity change, a coordinated restart, a
  rack or availability-zone outage, or an aggressive rollout.
- Network partition splitting the cluster so no side has a majority.
- Disk or data corruption taking replicas out of service.
- Misconfiguration of the cluster size or voting membership.

## How to confirm

- Check cluster membership: how many nodes are healthy versus the configured
  total, and whether that count is below the majority threshold.
- Look for a recent event that removed capacity: an operator command, an
  autoscaling action, an infrastructure maintenance.
- Confirm whether a leader or primary currently exists.

## Mitigation

Restore the missing nodes rather than forcing the cluster past its safety checks;
forcing quorum can cause data loss. Once membership is healthy, let it
re-replicate. Add guardrails to capacity tooling: cap nodes removed per action,
require confirmation, and refuse changes that would break quorum.

## References

- Amazon S3 service disruption, US-EAST-1, February 28, 2017:
  https://aws.amazon.com/message/41926/
