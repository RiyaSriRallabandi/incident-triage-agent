# IncidentTriage Agent

A multi-step AI agent that automates the *investigation* phase of an on-call
incident — not the fix. Given an incident report, it iteratively queries evidence
sources (logs, metrics, deploy history, and a runbook knowledge base), reasons
about what to check next, and produces a cited root-cause hypothesis with a
confidence score and recommended fix — or cleanly escalates to a human when the
evidence is insufficient.

The goal is to demonstrate agent design and orchestration with in-demand tooling:
LangGraph for the agent state machine, tool-use over structured evidence sources,
retrieval for the runbook corpus, and step-level evaluation with tracing.

## Status

Early development.

## Stack

- **Orchestration:** LangGraph (explicit state machine)
- **LLM calls:** Groq and Google AI Studio (Gemini) — free tiers only
- **Runbook retrieval:** Chroma + sentence-transformers embeddings
- **Tracing / eval:** LangSmith free tier
- **Serving:** FastAPI + uvicorn
- **CI:** GitHub Actions
- **Deployment:** Render or Fly.io free tier

Everything runs on free tiers. Target cost: $0.

## Setup

```bash
uv sync --dev
cp .env.example .env   # then fill in API keys
```

Verify LLM access once keys are set:

```bash
uv run python scripts/smoke_llm.py
```

Build the runbook retrieval index (downloads the embedding model on first run):

```bash
uv run python scripts/build_runbook_index.py
```

## Data

All incident data is synthetic or derived from public postmortems. No production
data is used.
