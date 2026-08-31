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

**Tools:** `search_logs`, `query_metrics`, `get_recent_deploys` (over one
scenario's synthetic evidence), and `retrieve_runbook` (RAG over a hand-written
runbook corpus). Also exposed as an [MCP](https://modelcontextprotocol.io) server.

## Results

Evaluated on a **30-scenario dev set** (used for prompt iteration + ablations)
and a **10-scenario sealed held-out set** (used once). Every scenario is derived
from a real public postmortem; ground truth is hand-verified.

_See [docs/REPORT.md](docs/REPORT.md) for the full numbers, the ablation table,
and the judge-calibration story. Headline figures land here once the held-out run
completes._

Highlights so far:

- **Judge calibration:** v1 of the LLM judge came out at Cohen's **κ = 0.25**
  (too lenient); diagnosed the bias, rewrote it, **κ = 0.92** (n=30).
- **Ablation:** a `conclude` prompt that constrains citations to retrieved text
  raised citation grounding **55% → 87%** (Wilcoxon p = 0.0004) — but over-escalated
  (93% → 80%), caught by the paired test; the next iteration fixes it.

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

The agent is packaged as a library plus scripts; a thin FastAPI wrapper and a
Render/Fly deploy config are planned (see [docs/REPORT.md](docs/REPORT.md) for
status). All incident data is synthetic, so a deployed instance exposes no
production data.

## Honesty

Synthetic data, small n, free-tier-limited throughput, prompts tuned against the
dev set. The gaps are documented in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).
