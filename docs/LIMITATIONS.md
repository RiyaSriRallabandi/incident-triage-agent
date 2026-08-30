# Limitations

This project demonstrates and evaluates an incident-investigation agent on a
synthetic benchmark. It is not a production incident-response tool. The gaps
below are deliberate scope choices, recorded honestly.

## Scope

- **Investigation only, no actions.** The agent produces a hypothesis or an
  escalation. It does not roll back, scale, failover, or test a fix.
- **Frozen evidence.** Each scenario is a static snapshot. The agent cannot run
  new queries against a live system, tail logs in real time, add instrumentation,
  or wait and re-check.
- **Four tools.** `search_logs`, `query_metrics`, `get_recent_deploys`,
  `retrieve_runbook`. Real on-call work also uses tracing/APM, profilers,
  `kubectl`, database consoles, cloud status pages, config diffs, feature-flag
  systems, and teammates. Scenarios are chosen to be solvable with these four.
- **No collaboration.** The agent works alone; the escalation output is the only
  channel to a human.

## Data

- **Synthetic.** Incident reports, logs, metrics, and deploys are fabricated.
  Only the failure pattern and root-cause shape come from the cited public
  postmortems. Real logs are messier (gaps, inconsistent formats, clock skew).
- **Small.** The golden set is a handful of scenarios during development; it
  expands later. Measured performance reflects these constructed scenarios, not
  real-world incidents.
- **Mostly singular ground truth.** Real incidents are sometimes never fully
  root-caused or are several overlapping problems. One scenario (`scn_004`) tests
  the "no clean answer, escalate" case.

## Model / infrastructure

- Free-tier models only (Groq OSS, Gemini). Structured output on the Groq OSS
  models is occasionally malformed and is retried.
- No live deployment integration; the agent reads scenario files.
