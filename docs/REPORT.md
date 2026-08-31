# Evaluation Report

The agent is evaluated on two levels — outcome (did it reach the right
conclusion?) and step-level (was the process sound?) — over a **30-scenario dev
set** used for prompt iteration and ablations, plus a **10-scenario held-out test
set** used exactly once for the headline numbers.

- **Agent model:** `gemini-3.5-flash-lite` (Groq `gpt-oss-20b` fallback). Free
  tiers only; the ablation matrix is spread over several days of quota.
- **Judge:** Groq `gpt-oss-120b`, prompt `judge_root_cause_v2`.
- **Tool-call budget:** 6.

---

## 1. Judge calibration

Root-cause statements are free text, so they are graded by an LLM judge on a
3-point scale (correct / partial / incorrect). The judge is only trusted after
being checked against the author's hand grading.

| Judge prompt | Cohen's κ vs hand grading | Verdict |
|---|---|---|
| `judge_root_cause_v1` | **0.25** (n=12) | **rejected** — systematically lenient |
| `judge_root_cause_v2` | **0.92** (n=30) | accepted |

`v1` scored an answer "correct" whenever it named the right service and symptom
chain, even when it missed the *mechanism a fix must address* (e.g. "payments
latency exhausted the pool" for an incident whose cause is un-budgeted retry
amplification). `v2` requires the mechanism. On the 30 dev-set runs it disagreed
with the author on 1 of 30 (a borderline "external DNS provider failure" vs.
"DDoS").

**Caveats:** the calibration set is 30 runs; `v2` contains worked examples drawn
from a few scenarios, so some anchoring is possible; it did generalise to
scenarios not in its examples.

---

## 2. Dev-set baseline (`dev-baseline`, 30 scenarios)

### Outcome

| Metric | Value |
|---|---|
| Root-cause **correct** | 74.1% |
| Root-cause partial | 22.2% |
| Root-cause incorrect | 3.7% |
| Escalation decision accuracy | 93.3% (28/30) |
| False-confident-wrong rate | 3.3% (1/30) |

### Step-level

| Metric | Value |
|---|---|
| Citation grounding rate | 55.2% |
| Fabricated citation rate | 44.8% |
| Mean tool calls | 4.13 |
| Budget-cap rate | 20.0% |

### Reading

The agent reliably **localises** the incident — right service, right symptom
chain, correct call on whether to escalate. It **names the mechanism** ~74% of
the time; the partials cluster on *cause-of-the-cause* incidents (a stats refresh
that flips a query plan, a health check pointed at a warming cache, a retry
config), where it stops at "X was slow and broke Y". Nearly half its citations
are not grounded in what it actually retrieved.

---

## 3. Ablations (dev set, n=30 paired)

Each variant changes one thing vs `dev-baseline`. Paired tests: McNemar's exact
(correct / not-correct) and Wilcoxon signed-rank (continuous). With n=30, p-values
are supporting evidence; effect sizes are reported alongside.

### `conclude-v2` — demand the mechanism, cite only retrieved text

| Metric | baseline | conclude-v2 | Δ | p |
|---|---|---|---|---|
| Citation grounding | 55.6% | **87.4%** | **+31.8pp** | **0.0004** (Wilcoxon) |
| Mean tool calls | 4.13 | 3.73 | −0.40 | **0.027** (Wilcoxon) |
| Confidence (calibration) | 0.99 | 0.95 | −0.04 | **0.0005** (Wilcoxon) |
| Escalation decision accuracy | 93.3% | 80.0% | −13.3pp | — |
| Net correct rate (unified) | 73.3% | 66.7% | −6.7pp | 0.75 (McNemar) |

**Verdict: partial win, rejected as-is.** The citation instruction essentially
solved the fabrication problem, and the run got shorter and better-calibrated,
all significant. But the "escalate if you can't name the mechanism" language made
it **over-escalate** — six solvable incidents wrongly escalated (up from two) —
which cancels the accuracy gains. `conclude-v3` keeps the citation and mechanism
language and softens the escalation trigger.

### `conclude-v3` — the fix

_(pending — running)_

### `no-deploys` — remove the `get_recent_deploys` tool

_(pending — running)_

---

## 4. Held-out test set (`heldout/`, 10 scenarios)

The held-out scenarios were not used for any prompt iteration. Baseline and the
winning config are run against them **once**.

_(pending — run after the dev-set config is frozen)_

---

## 5. Security slice — prompt-injection resistance

Five attacks, one malicious log line per scenario (instruction injection,
fake system message, prompt extraction, out-of-scope tool use, credential
exfiltration). An attack passes if no leak markers reach the final output and the
agent did not follow the injected instruction.

_(pending — running)_

---

## Reproducing

```bash
uv run python scripts/run_eval.py --variant dev-baseline   # dev baseline (cached)
uv run python scripts/run_ablations.py                     # all variants + comparison
uv run python scripts/run_heldout.py --winner conclude-v3  # held-out, once
uv run python scripts/run_security.py --provider groq      # injection slice
```

Cached artifacts: `data/eval/runs/`, `data/eval/judgements__*.json`,
`data/eval/summary__*.json`, `data/eval/ablations.json`, `data/eval/hand_labels.json`,
`data/security/results.json`.
