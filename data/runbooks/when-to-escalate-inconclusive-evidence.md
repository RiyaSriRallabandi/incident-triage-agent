# When to escalate instead of concluding

## Purpose

Not every investigation reaches a confident root cause with the evidence at hand.
Declaring a cause that is not supported is worse than escalating, because it sends
responders down the wrong path. This runbook describes when to stop and escalate.

## Escalate when

- The error or latency change is modest and intermittent, spread across most
  hosts, with no single host or shard dominating.
- No deploy, config change, or operator action correlates with the onset.
- Downstream dependencies and shared infrastructure all report healthy.
- Resource signals are flat: CPU, memory, connection pools, and queues are within
  normal range.
- The incident partially self-recovers without any action taken.
- Two or more plausible causes fit the evidence equally well and cannot be
  distinguished without data you do not have.

## What a good escalation contains

- The symptom, precisely stated, with the time range.
- The evidence gathered and what each source showed, including the negatives
  ("no deploys in the window", "downstream nominal").
- The hypotheses considered and why each could not be confirmed or ruled out.
- The specific additional data or access needed to make progress: per-host
  breakdowns over a longer window, client-side changes from major callers,
  platform events such as host migrations or noisy neighbours.

## References

- Microsoft Research, "Gray Failure: The Achilles' Heel of Cloud-Scale Systems":
  https://www.microsoft.com/en-us/research/publication/gray-failure-the-achilles-heel-of-cloud-scale-systems/
- Google SRE Book, "Effective Troubleshooting": https://sre.google/books/
