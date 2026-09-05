# IncidentTriage Agent

A multi-step AI agent that automates the **investigation** phase of an on-call
incident — not the fix. Given an incident report, it iteratively queries evidence
sources, reasons about what to check next, and produces a **cited root-cause
hypothesis** (with a confidence score and a recommended fix) — or **cleanly
escalates** when the evidence doesn't localize a cause.

The point of the project is not the agent — a plan/act/conclude loop is a known
pattern. The point is **building the agent *and* a rigorous evaluation of it**:
step-level metrics, a calibrated LLM judge, controlled ablations with paired
significance testing, a sealed held-out test set, and an adversarial slice.

**Live demo** (recorded traces, no live LLM calls):
https://incident-triage-agent-fkni.onrender.com

## What it does

```
   INCIDENT REPORT  ──►  ┌──────────────────────────────┐  ──►  DIAGNOSIS
   "checkout 503s since        plan  ─►  act  ─►  plan  ─►  ...        root cause + confidence
    ~09:23, no deploys,      (LLM)     (tool)   (LLM)              + cited evidence + fix
    payments looks slow"          └── conclude (LLM) ──┘        OR  ESCALATE
                                                                    reason + next steps
```

- **`plan`** (LLM): given the report + evidence so far, pick the next tool call, or conclude.
- **`act`** (deterministic): run the chosen tool, append the result to the evidence trace.
- **`conclude`** (LLM): produce the diagnosis contract, or escalate.
- A tool-call budget (default 6) bounds the loop.

Runtime and evaluation-harness diagrams: [docs/architecture.md](docs/architecture.md).

**Tools:** `search_logs`, `query_metrics`, `get_recent_deploys` (over one
scenario's synthetic evidence), and `retrieve_runbook` (RAG over a hand-written
runbook corpus). Also exposed as an [MCP](https://modelcontextprotocol.io) server.

## Results

Evaluated on a **30-scenario dev set** (used for prompt iteration + ablations)
and a **10-scenario sealed held-out set** (used once). Every scenario is derived
from a real public postmortem; ground truth is hand-verified.

**Held-out test set (10 scenarios, run once with the shipped config):**

| | |
|---|---|
| Root-cause correct (mechanism identified) | **88.9%** |
| Escalation decision accuracy | **100%** |
| False-confident-wrong rate | **0%** |
| Citation grounding | 54.8% |

- **Judge calibration:** the harness's free-tier judge is validated with
  Cohen's **κ** against a stronger reference model (Claude Sonnet) on a
  30-run sample — v1 scored **κ = 0.25** (too lenient), diagnosed and
  rewrote, **κ = 0.92**.
- **Ablations rejected every prompt variant.** Four `conclude`-prompt variants
  each fixed citation grounding (up to 55% → 97%, Wilcoxon p ≈ 0) but traded it
  for a regression. One looked like a clean win on the dev set — **the held-out
  set caught that it cost ~15–40pp of accuracy** on synthesis-heavy incidents.
- **5/5 prompt-injection attacks resisted** ([SECURITY.md](docs/SECURITY.md)).
- The agent generates ~57% grounded citations; a **deterministic post-hoc
  verification step** drops the rest, so **100% of delivered citations are
  grounded** and the fabrication rate is logged.

Full numbers, the ablation table, and the calibration story: [docs/REPORT.md](docs/REPORT.md).

## Stack

| | |
|---|---|
| Agent orchestration | **LangGraph** (explicit state machine) |
| LLMs | **Groq** (`gpt-oss-20b/120b`) + **Gemini** (`gemini-3.5-flash-lite`), free tiers only |
| Runbook RAG | **Chroma** + `sentence-transformers` (`all-MiniLM-L6-v2`, local) |
| Tracing | **LangSmith** free tier — per-step traces, tagged and filterable |
| Eval | custom harness · LLM-as-judge · `scikit-learn` (Cohen's κ) · `scipy` (McNemar, Wilcoxon) |
| Tooling | `uv` · `ruff` · `pytest` (250+ tests) · GitHub Actions CI |

Target cost: **$0**.

## Setup

```bash
uv sync --dev
cp .env.example .env                        # fill in GROQ_API_KEY, GEMINI_API_KEY, LANGCHAIN_API_KEY
uv run python scripts/build_runbook_index.py   # downloads the embedding model (~80 MB) once
```

Run the agent on a scenario:

```python
from triage.dataset import load_scenarios
from triage.agent.run import investigate

scenarios = {s.id: s for s in load_scenarios()}
result = investigate(scenarios["scn_001"])
print(result.outcome, result.diagnosis or result.escalation)
```

Reproduce the evaluation:

```bash
uv run python scripts/run_eval.py --variant dev-baseline   # baseline (uses cache)
uv run python scripts/run_ablations.py                     # variants + significance tests
uv run python scripts/run_security.py --provider groq      # prompt-injection slice
```

## MCP server

```bash
uv run triage-mcp        # stdio transport; 5 tools
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "incident-triage": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/incident-triage-agent", "triage-mcp"]
    }
  }
}
```

## Tracing

With `LANGCHAIN_API_KEY` + `LANGCHAIN_TRACING_V2=true` in `.env`, every run is
captured to the `incident-triage-agent` LangSmith project, tagged by scenario id,
category, and difficulty. No key → silent no-op.

## Deployment

A thin FastAPI layer ([src/triage/api.py](src/triage/api.py)) serves the cached
evaluation runs for the shipped config — each scenario's incident report, the
agent's plan/act/conclude trace, the diagnosis or escalation, the post-hoc
citation report, and the LLM judge's verdict.

```bash
uv sync --extra serve
uv run uvicorn triage.api:app --reload      # http://127.0.0.1:8000
```

It does **not** run the agent per request — investigation is slow and spends
free-tier LLM quota. `POST /investigate` runs a live investigation only when
`ALLOW_LIVE_RUNS=true`; the deployed instance leaves it off.

Live: **https://incident-triage-agent-fkni.onrender.com** (Render free tier via
[render.yaml](render.yaml); first request after idle cold-starts in ~50s). All
incident data is synthetic, so the public instance exposes nothing.

## Honesty

Synthetic data, small n, free-tier-limited throughput, prompts tuned against the
dev set. The gaps are documented in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).
