"""The three graph nodes (plan, act, conclude) and the routing functions.

``plan`` and ``conclude`` are LLM calls, injected as ``planner`` / ``concluder``
callables so tests can script them. ``act`` is pure Python: it dispatches the
tool the plan chose, records the result, and never reasons.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from langchain_core.tools import StructuredTool

from triage.agent.prompts import CONCLUDE_PROMPT, PLAN_PROMPT, render
from triage.agent.state import ConcludeResult, EvidenceItem, PlanDecision, TriageState

Planner = Callable[[str], PlanDecision]
Concluder = Callable[[str], ConcludeResult]

Toolset = dict[str, StructuredTool]

_MAX_RESULT_CHARS = 1500


# --------------------------------------------------------------------------- #
# prompt rendering
# --------------------------------------------------------------------------- #


def _render_evidence(items: list[EvidenceItem]) -> str:
    if not items:
        return "(none yet)"
    blocks = []
    for it in items:
        result = it.result
        if len(result) > _MAX_RESULT_CHARS:
            result = result[:_MAX_RESULT_CHARS] + " ...[truncated]"
        tag = " [error]" if it.error else ""
        blocks.append(
            f"[{it.step}]{tag} reasoning: {it.plan_reasoning}\n"
            f"    call: {it.tool}({json.dumps(it.args)})\n"
            f"    result: {result}"
        )
    return "\n\n".join(blocks)


def _render_tool_specs(tools: Toolset) -> str:
    lines = []
    for tool in tools.values():
        arg_names = ", ".join(tool.args.keys())
        first_line = (tool.description or "").strip().splitlines()[0]
        lines.append(f"- {tool.name}({arg_names}): {first_line}")
    return "\n".join(lines)


def _render_catalog(catalog: dict[str, list[str]]) -> str:
    return "\n".join(
        f"- {service}: {', '.join(metrics) if metrics else '(none)'}"
        for service, metrics in sorted(catalog.items())
    )


def build_plan_prompt(state: TriageState, tools: Toolset) -> str:
    return render(
        PLAN_PROMPT,
        incident_report=state["incident_report"],
        evidence_window=state["evidence_window"],
        service_inventory=", ".join(state["service_inventory"]),
        metric_catalog=_render_catalog(state["metric_catalog"]),
        tool_specs=_render_tool_specs(tools),
        evidence=_render_evidence(state["evidence"]),
        tool_calls_used=str(state["tool_calls_used"]),
        tool_call_budget=str(state["tool_call_budget"]),
    )


def build_conclude_prompt(state: TriageState) -> str:
    budget_note = ""
    if state["hit_budget_cap"]:
        budget_note = (
            "\nNote: the tool-call budget was exhausted before the investigation finished.\n"
        )
    return render(
        CONCLUDE_PROMPT,
        incident_report=state["incident_report"],
        evidence=_render_evidence(state["evidence"]),
        budget_note=budget_note,
    )


# --------------------------------------------------------------------------- #
# nodes
# --------------------------------------------------------------------------- #


def plan_node(state: TriageState, *, planner: Planner, tools: Toolset) -> dict:
    decision = planner(build_plan_prompt(state, tools))
    return {"pending_plan": decision}


def act_node(state: TriageState, *, tools: Toolset) -> dict:
    decision = state["pending_plan"]
    assert decision is not None  # routing guarantees this
    step = state["tool_calls_used"] + 1
    budget = state["tool_call_budget"]

    def done(result: str, *, args: dict, error: bool) -> dict:
        item = EvidenceItem(
            step=step,
            plan_reasoning=decision.reasoning,
            tool=decision.tool or "(none)",
            args=args,
            result=result,
            error=error,
        )
        return {
            "evidence": [item],
            "tool_calls_used": step,
            "hit_budget_cap": step >= budget,
            "pending_plan": None,
        }

    tool = tools.get(decision.tool)
    if tool is None:
        return done(
            f"unknown tool {decision.tool!r}. Available tools: {sorted(tools)}",
            args={},
            error=True,
        )

    try:
        args = json.loads(decision.tool_args_json or "{}")
        if not isinstance(args, dict):
            raise ValueError("tool_args_json must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        return done(f"could not parse tool_args_json: {exc}", args={}, error=True)

    try:
        result = str(tool.invoke(args))
        error = False
    except Exception as exc:  # noqa: BLE001 - any tool failure becomes an observation
        result = f"tool error: {exc}"
        error = True

    return done(result, args=args, error=error)


def conclude_node(state: TriageState, *, concluder: Concluder) -> dict:
    return {"result": concluder(build_conclude_prompt(state))}


# --------------------------------------------------------------------------- #
# routing
# --------------------------------------------------------------------------- #


def route_after_plan(state: TriageState) -> str:
    decision = state["pending_plan"]
    if decision is None or decision.action == "conclude":
        return "conclude"
    return "act"


def route_after_act(state: TriageState) -> str:
    if state["tool_calls_used"] >= state["tool_call_budget"]:
        return "conclude"
    return "plan"
