"""LangSmith tracing setup.

LangChain / LangGraph emit trace events on their own when the right environment
variables are present. ``configure_tracing`` copies the resolved settings (which
may come from .env) into ``os.environ`` so that happens; ``trace_config`` adds
per-run metadata and tags so the LangSmith dashboard is filterable.

Tracing is a no-op when no API key is configured, so CI and offline tests are
unaffected.
"""

from __future__ import annotations

import os

from triage.config import Settings, get_settings
from triage.schema import Scenario

# LangChain reads the legacy LANGCHAIN_* names; recent versions also read
# LANGSMITH_*. Set both from our single resolved config.
_ENV_ALIASES = {
    "tracing": ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"),
    "api_key": ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"),
    "project": ("LANGCHAIN_PROJECT", "LANGSMITH_PROJECT"),
}


def tracing_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.langchain_tracing_v2 and settings.langchain_api_key)


def configure_tracing(settings: Settings | None = None) -> bool:
    """Push tracing config into os.environ. Returns True if tracing is on."""
    settings = settings or get_settings()
    if not tracing_enabled(settings):
        return False

    values = {
        "tracing": "true",
        "api_key": settings.langchain_api_key,
        "project": settings.langchain_project,
    }
    for key, names in _ENV_ALIASES.items():
        for name in names:
            os.environ[name] = values[key]
    return True


def trace_config(scenario: Scenario, budget: int) -> dict:
    """RunnableConfig fragment: a run name, filter tags, and metadata."""
    return {
        "run_name": f"triage-{scenario.id}",
        "tags": ["triage-agent", scenario.category.value, scenario.difficulty.value],
        "metadata": {
            "scenario_id": scenario.id,
            "category": scenario.category.value,
            "difficulty": scenario.difficulty.value,
            "tool_call_budget": budget,
            "ground_truth_should_escalate": scenario.ground_truth.should_escalate,
        },
    }
