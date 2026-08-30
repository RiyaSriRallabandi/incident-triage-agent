"""``investigate(scenario)`` - the single entry point to run the agent."""

from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel

from triage.agent.graph import build_graph
from triage.agent.nodes import Concluder, Planner
from triage.agent.state import (
    AgentResult,
    ConcludeResult,
    Diagnosis,
    Escalation,
    PlanDecision,
    TriageState,
)
from triage.config import get_settings
from triage.llm import get_chat_model, with_structured_output
from triage.rag.index import INDEX_DIR
from triage.schema import Scenario
from triage.tools.toolset import build_toolset
from triage.tracing import configure_tracing, trace_config

DEFAULT_BUDGET = 6


def _evidence_window(scenario: Scenario) -> str:
    lo, hi = scenario.time_range()
    return f"{lo:%Y-%m-%dT%H:%M:%SZ} to {hi:%Y-%m-%dT%H:%M:%SZ}"


def _metric_catalog(scenario: Scenario) -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {svc: [] for svc in scenario.services()}
    for series in scenario.synthetic_metrics:
        catalog.setdefault(series.service, []).append(series.name)
    return {svc: sorted(names) for svc, names in catalog.items()}


def _structured_runnable(schema):
    """Groq (json-schema, with retry) and, if a Gemini key is set, a Gemini fallback."""
    runnable = with_structured_output(get_chat_model("groq"), schema)
    if get_settings().gemini_api_key:
        gemini = with_structured_output(get_chat_model("gemini"), schema, provider="gemini")
        runnable = runnable.with_fallbacks([gemini])
    return runnable


def _llm_planner(model: BaseChatModel | None = None) -> Planner:
    structured = (
        with_structured_output(model, PlanDecision)
        if model is not None
        else _structured_runnable(PlanDecision)
    )
    return lambda prompt: structured.invoke(prompt)


def _llm_concluder(model: BaseChatModel | None = None) -> Concluder:
    structured = (
        with_structured_output(model, ConcludeResult)
        if model is not None
        else _structured_runnable(ConcludeResult)
    )
    return lambda prompt: structured.invoke(prompt)


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
    planner: Planner | None = None,
    concluder: Concluder | None = None,
    runbook_index_dir: Path = INDEX_DIR,
) -> AgentResult:
    """Run the triage agent on one scenario and return its assessment.

    ``planner`` / ``concluder`` default to Groq-backed LLM callables; tests pass
    scripted ones.
    """
    configure_tracing()
    tools = {t.name: t for t in build_toolset(scenario, runbook_index_dir=runbook_index_dir)}
    planner = planner or _llm_planner()
    concluder = concluder or _llm_concluder()

    graph = build_graph(tools, planner, concluder)
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
