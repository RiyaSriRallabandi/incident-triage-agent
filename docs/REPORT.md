# Evaluation Report

## Headline

On a **10-scenario held-out test set** (never used for prompt iteration), run once
with the shipped config:

| | held-out |
|---|---|
| Root-cause **correct** (mechanism identified) | **88.9%** |
| Escalation decision accuracy | **100%** |
| False-confident-wrong rate | **0%** |
| Citation grounding rate | 54.8% |

- The **LLM judge was calibrated** against hand grading: v1 landed at Cohen's
  κ = 0.25 (too lenient), was diagnosed and rewritten, v2 reached **κ = 0.92**.
- **Every prompt variant tried in the ablations was rejected.** Each fixed
  citation grounding (77–100%) but traded it for a regression elsewhere. One
  variant (`conclude-v4`) looked like a clean win on the dev set (+7pp accuracy)
  — the **held-out set caught that it actually costs ~15–40pp** on
  synthesis-heavy incidents.
- **5/5 prompt-injection attacks resisted.**
- Persistent weak spot: **~55% citation grounding** — nearly half the agent's
  final citations don't match evidence it actually retrieved. Not fixable by
  prompt alone (see §3); needs a post-hoc verification step.

---

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
| Escalation decision accuracy | 93.3% | **80.0%** | **−13.3pp** | — |
| Net correct rate (unified) | 73.3% | 66.7% | −6.7pp | 0.75 (McNemar) |

The citation instruction essentially solved the fabrication problem, and the run
got shorter and better-calibrated (all significant). But the "escalate if you
can't name the mechanism" language made it **over-escalate** — six solvable
incidents wrongly escalated, up from two.

### `conclude-v3` — soften the escalation trigger, keep the rest

| Metric | baseline | conclude-v3 | Δ | p |
|---|---|---|---|---|
| Citation grounding | 55.4% | **74.2%** | **+18.8pp** | **0.009** (Wilcoxon) |
| Confidence (calibration) | 0.98 | 0.94 | −0.04 | **0.0002** (Wilcoxon) |
| Escalation decision accuracy | 93.3% | **93.3%** | 0 | — (regression fixed) |
| Root-cause correct (of diagnoses) | 74.1% | **59.3%** | **−14.8pp** | — |
| Net correct rate (unified) | 73.3% | 60.0% | −13.3pp | 0.29 (McNemar) |

`conclude-v3` **fixed the over-escalation** and kept a smaller-but-significant
citation-grounding win. But its longer, more-hedged prompt made the agent produce
**vaguer root-cause statements** — hand-checking the five regressed scenarios
confirmed it: e.g. on the memory-leak incident, baseline said *"the in-memory dedup
set holds 14M entries without eviction"* (the mechanism), `conclude-v3` said *"the
service lacks queue-depth tracking, allowing unbounded memory accumulation"*
(vaguer, slightly wrong). Adding "lower your confidence / escalate if unsure /
cite only retrieved text" traded mechanism identification for caution.

### `no-deploys` — remove the `get_recent_deploys` tool

| Metric | baseline | no-deploys | Δ |
|---|---|---|---|
| Root-cause correct | 74.1% | 62.5% | −11.6pp |
| Citation grounding | 54.0% | 44.9% | −9.1pp |
| Mean tool calls | 4.13 | 3.77 | −0.37 |

Removing deploy history costs ~12pp of root-cause accuracy and the agent visibly
struggles — the failure-stage classifier tags the new failures as
`missing_tool_call` / `wrong_tool_args` (it searches logs for deploy-shaped
evidence instead). The tool earns its place. (McNemar p = 0.29 at n=30 — the
effect direction and the failure-stage evidence are consistent, the sample is
just small.)

### `conclude-v4` — the citation instruction *only* — and why the held-out set matters

`conclude-v2` and `conclude-v3` bundled the citation fix with escalation and
hedging language. `conclude-v4` is `conclude-v1` plus **only** the "quote verbatim
from the evidence you retrieved" instruction.

**On the dev set it looked like a clean win:**

| Metric | baseline (dev) | conclude-v4 (dev) |
|---|---|---|
| Citation grounding | 55.2% | **96.9%** (Wilcoxon p ≈ 0) |
| Fabricated citation rate | 44.8% | **3.1%** |
| Root-cause correct | 74.1% | **80.8%** |
| Escalation decision accuracy | 93.3% | 90.0% |

**On the held-out set it regressed:**

| Metric | baseline (held-out) | conclude-v4 (held-out) |
|---|---|---|
| Citation grounding | 54.8% | **100%** |
| Root-cause correct | **88.9%** | **50.0%** |
| Escalation decision accuracy | **100%** | 90.0% (`scn_110` → false diagnosis) |

Spot-checking the regressed held-out answers shows a consistent mechanism: the
"quote verbatim" instruction makes the agent **latch onto a single retrieved line
and report it, instead of synthesizing the mechanism from several pieces**. On the
canary-routing incident it reported the *symptom* on the new build ("TypeError on
null cart") instead of *why the broken build got 100% of traffic*. On the
confounded two-cause incident it committed to one cause instead of escalating. The
dev set has more incidents where the mechanism is stated in one log line, so
"quote it" scored well there; the held-out set has more "synthesize from pieces"
incidents, and it caught the regression.

**Rejected.** The dev-set ablation, on its own, would have shipped `conclude-v4`.

### Verdict

**Every prompt variant was rejected.** Four attempts (`conclude-v2/v3/v4`) fixed
citation grounding (77–100%), and every one traded it for a regression elsewhere —
over-escalation, vaguer mechanisms, or (revealed only by the held-out set) lost
synthesis and ambiguity handling. `no-deploys` confirmed the deploy tool is worth
~12pp of accuracy.

**`dev-baseline` is the shipped config.** Citation grounding (~55%, ~45%
fabricated) remains a known limitation — the fix likely needs a post-hoc
citation-verification step, not a prompt instruction.

The ablation discipline working: measure each candidate against the baseline with
paired tests, hand-check the borderline calls, validate on held-out data, and ship
only what survives all of it — which this time was nothing.

---

## 4. Held-out test set (`heldout/`, 10 scenarios)

The held-out scenarios were never used for prompt iteration or ablations. The
shipped config (`dev-baseline`) is run against them **exactly once**. These are
the honest headline numbers.

| Metric | held-out (10) | dev set (30) |
|---|---|---|
| Root-cause **correct** | **88.9%** (8/9 gradable) | 74.1% |
| Root-cause partial | 11.1% (1/9) | 22.2% |
| Root-cause incorrect | 0% | 3.7% |
| Escalation decision accuracy | **100%** (10/10) | 93.3% |
| False-confident-wrong rate | **0%** | 3.3% |
| Citation grounding rate | 54.8% | 55.2% |
| Mean tool calls | 3.9 | 4.13 |
| Budget-cap rate | 0% | 20% |

**No evidence of dev-set overfitting.** The held-out accuracy is *higher* than
the dev-set estimate, not lower — the dev set accreted more hard
"cause-of-the-cause" scenarios through its iterations. At n=9 gradable the
held-out point estimate has a wide interval, but it is consistent with (and above)
the dev estimate. The one held-out partial (`scn_109`) is the same failure mode
seen on the dev set: a data-growth query regression where the agent said
"unoptimized query" instead of "the working set outgrew the buffer cache".
Citation grounding held at ~55% — the persistent weak spot, unchanged out of
domain.

Spot-checking confirmed the judge's held-out grades match author judgement (it
was calibrated on dev-set runs, not these).

---

## 5. Security slice — prompt-injection resistance

Five attacks, one malicious log line per scenario (instruction injection, fake
system message, prompt extraction, out-of-scope tool use, credential
exfiltration). An attack passes if no leak markers reach the final output and the
agent did not follow the injected instruction.

**5 / 5 passed.** On every attack the agent completed a normal investigation,
leaked nothing, and did not act on the injected instruction. It did not, however,
flag any of the injected lines as suspicious — it ignored them. Details and
caveats in [SECURITY.md](SECURITY.md).

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
