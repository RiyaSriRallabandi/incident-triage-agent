# Evaluation Report

## Baseline (`tag=baseline`)

- **12 runs** — 4 scenarios × 3 repeats, 0 crashed
- **Agent model:** `gemini-3.5-flash-lite` (Groq `gpt-oss-20b` fallback). Groq's
  free tier caps at 200K tokens/day, which the agent's multi-turn runs exhaust in
  ~3 runs, so the eval uses Gemini.
- **Judge model:** Groq `gpt-oss-120b`, prompt `judge_root_cause_v2`
- **Tool-call budget:** 6

### Outcome metrics

| Metric | Value | Notes |
|---|---|---|
| Root-cause accuracy (correct) | **22.2%** | over 9 gradable runs (scn_004 escalates, not graded on cause) |
| Root-cause partial | 77.8% | right service + symptom chain, mechanism missing or wrong |
| Root-cause incorrect | 0% | |
| Escalation decision accuracy | **100%** | scn_004 correctly escalated 3/3; no solvable scenario wrongly escalated |
| False-confident-wrong rate | **0%** | no confident diagnosis was wrong |

### Step-level metrics

| Metric | Value | Notes |
|---|---|---|
| Citation grounding rate | **54.3%** | fraction of final citations that match retrieved evidence |
| Fabricated citation rate | 45.7% | citations with no support in the run's tool results |
| Mean tool calls | 5.0 | |
| Budget-cap rate | **41.7%** | runs that hit the 6-call limit before concluding |
| Mean error steps / run | 0.0 | no failed tool calls |

### Judge calibration

`judge_root_cause_v2` vs. the author's hand grading of all 12 runs:

- **Cohen's κ = 1.00**, raw agreement 100% (n = 12)
- `judge_root_cause_v1` was rejected: κ = 0.25, systematically lenient — it scored
  answers "correct" when they named the right service and symptom chain but not
  the mechanism a fix must address (e.g. "payments latency exhausted the pool"
  for a scenario whose cause is un-budgeted retry amplification).

**Caveats:** the calibration set is small (12 runs), and `v2` contains worked
examples drawn from scn_001/scn_002 patterns, so some anchoring is possible. It
generalised correctly to scn_003 (not in the examples). Re-calibrate when the
golden set expands.

## Reading the baseline

The agent **reliably localises the incident** — right service, right chain of
symptoms, correct decision to escalate when the evidence is genuinely thin — but
**names the underlying mechanism only ~22% of the time**. It tends to stop at
"service X was slow / erroring and that broke Y" without identifying *why*
(retry amplification, a pathological regex, quorum loss).

Nearly half of its citations are not grounded in what it actually retrieved, and
it hits the tool-call budget ~40% of the time.

### Targets for Task 9

1. Mechanism identification (22% → higher) — likely a `conclude` prompt change.
2. Citation grounding (54% → higher) — constrain citations to retrieved text.
3. Budget efficiency (42% cap rate) — better planning, or a larger budget (ablation).

## Reproducing

```bash
uv run python scripts/run_eval.py --tag baseline        # uses cached runs + judgements
uv run python scripts/run_eval.py --tag baseline --force # re-run the agent (slow, uses quota)
```

Cached runs: `data/eval/runs/baseline__*.json`. Hand labels:
`data/eval/hand_labels.json`. Summary: `data/eval/summary__baseline.json`.
