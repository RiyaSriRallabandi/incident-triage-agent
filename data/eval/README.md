# Golden evaluation set

Each scenario is one synthetic incident: an incident report, a bundle of
synthetic evidence (logs, metrics, deploys), and a hand-verified ground-truth
answer (root cause, evidence path, fix, and whether the agent should escalate
instead of guessing).

## How a scenario is built

1. A real, public postmortem is chosen for its **failure pattern** (e.g. a bad
   deploy that saturates CPU, a retry storm that exhausts a connection pool).
2. A short spec is hand-written in `specs/scn_###.spec.json`: the paraphrased
   incident report, the ground truth, the handful of real "signal" log lines, the
   deploys, and the shape of each metric. **This spec is the human-reviewed
   artifact.**
3. `scripts/generate_evidence.py` expands the spec into `scenarios/scn_###.json`,
   inserting the signal lines at their real offsets among distractor log lines
   from unrelated services and generating realistic metric time series. Generation
   is deterministic (RNG seeded from the scenario id), so the committed scenario
   file is always exactly what the spec produces — a test enforces this.

Nothing is copied from the source postmortems. Incident text, service names, log
lines, metrics, timestamps, and commit hashes are all fabricated for evaluation;
only the failure pattern and root-cause shape come from the cited source, noted
per scenario in `source_note`.

## Regenerating

```bash
uv run python scripts/generate_evidence.py --all
```

## Automated review

```bash
uv run python scripts/review_scenarios.py            # needs GROQ_API_KEY
```

Runs each spec through an eight-check SRE rubric (report realism, signal→cause,
deploy presence, metric/narrative consistency, root-cause correctness, evidence
support, fix, escalation flag) using the Groq judge model. It flags; a human
confirms. The same rubric seeds the Task 8 LLM-judge.


## Current set (30 scenarios)

7 failure categories · 4 easy / 13 medium / 13 hard · 3 escalate-by-design.

| id | category | diff | esc? | modeled on |
|----|----------|------|------|------------|
| scn_001 | bad_deploy | med | no | Cloudflare 2019-07-02 (WAF regex → CPU) |
| scn_002 | resource_exhaustion | hard | no | AWS Builders' Library retry-storm |
| scn_003 | dependency_failure | med | no | AWS S3 2017-02-28 (over-removed capacity) |
| scn_004 | ambiguous | hard | **yes** | "Gray Failure" (MS Research) |
| scn_005 | network_dns | med | no | Facebook 2021-10-04 (DNS routes withdrawn) |
| scn_006 | network_dns | med | no | security-group change removes egress |
| scn_007 | cert_config_expiry | easy | no | MS Teams 2020-02-03 (expired TLS cert) |
| scn_008 | cert_config_expiry | hard | no | mTLS CA rotation, trust-bundle skew |
| scn_009 | database_issue | med | no | GitLab 2017 (blocking index migration) |
| scn_010 | database_issue | hard | no | Stripe 2019 (backfill → replica lag) |
| scn_011 | bad_deploy | hard | no | Knight Capital 2012 (repurposed flag) |
| scn_012 | ambiguous | hard | **yes** | two unconfirmable candidate causes |
| scn_013 | bad_deploy | med | no | Reddit 2023 Pi-Day (ingress upgrade) |
| scn_014 | bad_deploy | easy | no | refactor drops a cache → DB load 12x |
| scn_015 | bad_deploy | med | no | non-backwards-compatible column rename |
| scn_016 | resource_exhaustion | hard | no | unbounded dedup set → OOM loop |
| scn_017 | resource_exhaustion | med | no | debug logging left on → disk full |
| scn_018 | resource_exhaustion | hard | no | fd leak on an error path → EMFILE |
| scn_019 | resource_exhaustion | med | no | decompression-bomb image pins CPU |
| scn_020 | dependency_failure | easy | no | third-party tax API outage |
| scn_021 | dependency_failure | hard | no | Roblox 2021-style cache-cluster failure |
| scn_022 | dependency_failure | med | no | Dyn 2016 (managed DNS provider DDoS) |
| scn_023 | dependency_failure | med | no | service-discovery returns empty catalog |
| scn_024 | dependency_failure | easy | no | CDN regional POP degradation (EU) |
| scn_025 | network_dns | hard | no | LB health check on a warming readiness path |
| scn_026 | network_dns | hard | no | firewall failover → asymmetric routing |
| scn_027 | ambiguous | hard | **yes** | periodic error spikes, no correlating signal |
| scn_028 | cert_config_expiry | hard | no | OAuth secret rotation, stale pods |
| scn_029 | database_issue | med | no | fleet growth → DB max_connections |
| scn_030 | database_issue | med | no | plan regression after ANALYZE → seq scan |

`scn_004`, `scn_012`, and `scn_027` have no single correct root cause by design:
they test whether the agent escalates rather than fabricating one.

## Held-out test set (`heldout/`, 10 scenarios)

`scn_101`–`scn_110`, one or two per failure category plus one escalate case. These
were **not used for prompt iteration or ablations** — the dev set (above) was. The
agent is run against the held-out set exactly once, with the frozen final config,
to produce the report's headline numbers. Built and generated the same way; run
`uv run python scripts/generate_evidence.py --heldout`.
