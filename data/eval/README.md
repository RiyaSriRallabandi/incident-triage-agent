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

## Current set (starter — expands in a later task)

| id | category | difficulty | escalate? | modeled on |
|----|----------|-----------|-----------|------------|
| scn_001 | bad_deploy | medium | no | Cloudflare 2019-07-02 (WAF regex → CPU exhaustion) |
| scn_002 | resource_exhaustion | hard | no | AWS Builders' Library retry-storm pattern |
| scn_003 | dependency_failure | medium | no | AWS S3 2017-02-28 (operator command removed too much capacity) |
| scn_004 | ambiguous | hard | **yes** | "Gray Failure" (Microsoft Research) — deliberately under-determined |

`scn_004` has no single correct root cause by design: it tests whether the agent
escalates rather than fabricating one.
