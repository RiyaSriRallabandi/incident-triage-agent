# Deploy-correlated latency or error regression

## Symptoms

A step change in latency, error rate, or resource use that begins within minutes
of a code or configuration rollout. The change is often sharp rather than gradual,
and it may be limited to the service that was deployed or to a subset of hosts if
the rollout is still in progress.

## Likely causes

- A regression in the new build: an inefficient code path, a bad query, a tight
  loop, or a dropped cache.
- A configuration or rule change shipped with the build (feature flags, routing
  rules, security or WAF rules) that behaves badly on production traffic.
- A schema or dependency version bump that changed behaviour under load.

## How to confirm

- Line up the incident start against deploy history for the affected service.
  A deploy whose timestamp precedes the first symptom by 1 to 10 minutes is a
  strong lead.
- Check whether hosts on the new build differ from hosts still on the old build.
- Look for errors that name a specific new rule, flag, or code path.

## Mitigation

Roll back to the previous known-good build first; diagnose afterwards. If the
rollout is partial, halt it. Once stable, reproduce in staging and add a
regression test or a pre-deploy check for the specific failure mode.

## References

- Google SRE Book, "Postmortem Culture" and "Release Engineering" chapters:
  https://sre.google/books/
