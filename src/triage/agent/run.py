"""``investigate(scenario)`` - the single entry point to run the agent."""

from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel

from triage.agent.graph import build_graph
from triage.agent.nodes import Concluder, Planner
from triage.agent.prompts import CONCLUDE_PROMPT, PLAN_PROMPT
from triage.agent.state import (
    AgentResult,
    ConcludeResult,
    Diagnosis,
    Escalation,
    PlanDecision,
    TriageState,
)
from triage.config import get_settings
from triage.llm import (
    Provider,
    get_chat_model,
    invoke_with_backoff,
    with_structured_output,
)
from triage.rag.index import INDEX_DIR
from triage.schema import Scenario
from triage.tools.toolset import build_toolset
from triage.tracing import configure_tracing, trace_config

DEFAULT_BUDGET = 6
DEFAULT_PROVIDER: Provider = "groq"


def _evidence_window(scenario: Scenario) -> str:
    lo, hi = scenario.time_range()
    return f"{lo:%Y-%m-%dT%H:%M:%SZ} to {hi:%Y-%m-%dT%H:%M:%SZ}"


def _metric_catalog(scenario: Scenario) -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {svc: [] for svc in scenario.services()}
    for series in scenario.synthetic_metrics:
        catalog.setdefault(series.service, []).append(series.name)
    return {svc: sorted(names) for svc, names in catalog.items()}


_OTHER: dict[Provider, Provider] = {"groq": "gemini", "gemini": "groq"}


def _structured_runnable(schema, provider: Provider, model: str | None):
    """Primary provider with the other as a fallback when its key is present."""
    settings = get_settings()
    runnable = with_structured_output(
        get_chat_model(provider, model=model), schema, provider=provider
    )

    other = _OTHER[provider]
    other_key = settings.groq_api_key if other == "groq" else settings.gemini_api_key
    if other_key:
        fb = with_structured_output(get_chat_model(other), schema, provider=other)
        runnable = runnable.with_fallbacks([fb])
    return runnable


def _llm_planner(
    provider: Provider, model: str | None = None, override: BaseChatModel | None = None
) -> Planner:
    structured = (
        with_structured_output(override, PlanDecision)
        if override is not None
        else _structured_runnable(PlanDecision, provider, model)
    )
    return lambda prompt: invoke_with_backoff(structured, prompt)


def _llm_concluder(
    provider: Provider, model: str | None = None, override: BaseChatModel | None = None
) -> Concluder:
    structured = (
        with_structured_output(override, ConcludeResult)
        if override is not None
        else _structured_runnable(ConcludeResult, provider, model)
    )
    return lambda prompt: invoke_with_backoff(structured, prompt)


def _to_result(scenario_id: str, state: TriageState) -> AgentResult:
    result = state["result"]
    if result is None:  # graph always sets this; guard for type-checkers
        raise RuntimeError("agent finished without producing a conclusion")

    diagnosis = escalation = None
    if result.outcome == "diagnosis":
        diagnosis = Diagnosis(
            root_cause=result.root_cause,
            confidence=result.confidence,
            evidence=result.evidence,
            recommended_fix=result.recommended_fix,
        )
    else:
        escalation = Escalation(
            reason=result.escalation_reason,
            evidence_gathered=result.evidence,
            suggested_next_steps=result.suggested_next_steps,
        )

    return AgentResult(
        scenario_id=scenario_id,
        outcome=result.outcome,
        diagnosis=diagnosis,
        escalation=escalation,
        evidence=state["evidence"],
        tool_calls_used=state["tool_calls_used"],
        hit_budget_cap=state["hit_budget_cap"],
    )


def investigate(
    scenario: Scenario,
    *,
    budget: int = DEFAULT_BUDGET,
    provider: Provider = DEFAULT_PROVIDER,
    model: str | None = None,
    plan_prompt: str = PLAN_PROMPT,
    conclude_prompt: str = CONCLUDE_PROMPT,
    tools: tuple[str, ...] | None = None,
    planner: Planner | None = None,
    concluder: Concluder | None = None,
    runbook_index_dir: Path = INDEX_DIR,
) -> AgentResult:
    """Run the triage agent on one scenario and return its assessment.

    ``provider`` / ``model`` select the model backing the default planner and
    concluder (the other provider is a fallback). ``plan_prompt`` /
    ``conclude_prompt`` select prompt versions; ``tools`` restricts the toolset
    (None = all four). Tests pass scripted callables instead.
    """
    configure_tracing()
    toolset = {t.name: t for t in build_toolset(scenario, runbook_index_dir=runbook_index_dir)}
    if tools is not None:
        toolset = {name: t for name, t in toolset.items() if name in tools}
    planner = planner or _llm_planner(provider, model)
    concluder = concluder or _llm_concluder(provider, model)

    graph = build_graph(
        toolset, planner, concluder, plan_prompt=plan_prompt, conclude_prompt=conclude_prompt
    )
    initial: TriageState = {
        "incident_report": scenario.incident_report,
        "evidence_window": _evidence_window(scenario),
        "service_inventory": sorted(scenario.services()),
        "metric_catalog": _metric_catalog(scenario),
        "evidence": [],
        "tool_calls_used": 0,
        "tool_call_budget": budget,
        "hit_budget_cap": False,
        "pending_plan": None,
        "result": None,
    }
    config = {"recursion_limit": budget * 2 + 5, **trace_config(scenario, budget)}
    final = graph.invoke(initial, config)
    return _to_result(scenario.id, final)
