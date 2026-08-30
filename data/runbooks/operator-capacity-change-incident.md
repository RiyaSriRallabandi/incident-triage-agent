# Operator-induced capacity change incident

## Symptoms

An outage that begins during planned maintenance or a manual operation, not during
a deploy. Logs show an operator session and a command that changed capacity,
scaled a group, drained nodes, or altered routing, often with a parameter larger
than intended. Impact appears seconds to minutes after the command.

## Likely causes

- A command run with the wrong argument, wrong target, or wrong environment: a
  fat-finger, a copied value, or a script bug.
- Automation acting on stale or incorrect input.
- An operation whose blast radius was underestimated: removing more capacity than
  the system could tolerate.

## How to confirm

- Search logs and audit trails for operator sessions and capacity or routing
  commands in the window before the first symptom.
- Compare the parameter that was used against the parameter that was intended
  (requested versus applied).
- Check whether the change took a system below a safety threshold such as quorum
  or minimum healthy count.

## Mitigation

Reverse the change or restore the removed capacity. Do not improvise around
safety checks. Afterwards, add guardrails: bound the magnitude of a single
action, require a second operator or a confirmation for large changes, and make
tooling refuse changes that violate a documented safety invariant.

## References

- Amazon S3 service disruption, US-EAST-1, February 28, 2017:
  https://aws.amazon.com/message/41926/
- GitLab.com database incident, January 31, 2017:
  https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/
