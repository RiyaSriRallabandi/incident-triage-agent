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
- **Ground truth drafted by a stronger reasoning model (Claude Sonnet)** than
  the free-tier models used inside the harness, from public postmortems,
  reviewed by the author, and checked by an automated rubric reviewer.
- **30 scenarios** across 7 failure categories. Small for statistics: paired
  ablation tests run at n=30, so p-values are supporting evidence, not verdicts,
  and effect sizes are reported alongside.
- **The dev set was tuned against.** Prompts were iterated against these 30
  scenarios, so their accuracy is an in-domain (optimistic) estimate. The
  sealed 10-scenario held-out set addresses this: it was run once, with the
  frozen config, and its numbers are the report's headline (held-out accuracy
  came out above the dev estimate, not below).
- **Judge calibration is a two-tier model design.** Running a top-tier reasoning
  model as the production judge across the full evaluation volume isn't
  compatible with a $0 budget, so the harness's judge is a smaller free-tier
  model, validated via Cohen's kappa against a stronger reference: a manual
  review by Claude Sonnet applying the same rubric to a 30-run calibration
  sample. The judge-v2 prompt contains worked examples drawn from a few of
  those same scenarios, so some anchoring between the two is possible.

## Model / infrastructure

- **Free-tier models only**, which caps throughput: Groq OSS models (`gpt-oss-20b`
  ~200K tokens/day) and Gemini (`gemini-3.5-flash-lite` ~500 requests/day). The
  full ablation matrix does not fit in one day's quota, so runs are spread over
  several days. Structured output on the Groq OSS models is occasionally malformed
  and is retried.
- **No live deployment integration**; the agent reads scenario files.

## Security slice

- The prompt-injection suite is **5 attacks**, one payload per scenario, scored by
  a conservative keyword/behaviour heuristic (not an LLM judge). It shows the
  agent's resistance to a representative set of attack shapes, not a guarantee.
