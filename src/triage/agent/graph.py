"""Assemble the triage agent as an explicit LangGraph state machine.

START -> plan --(call_tool)--> act --(budget left)--> plan
             \\--(conclude)--> conclude -> END          \\--(budget spent)--> conclude
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from triage.agent.nodes import (
    Concluder,
    Planner,
    Toolset,
    act_node,
    conclude_node,
    plan_node,
    route_after_act,
    route_after_plan,
)
from triage.agent.state import TriageState


def build_graph(tools: Toolset, planner: Planner, concluder: Concluder):
    graph = StateGraph(TriageState)

    graph.add_node("plan", partial(plan_node, planner=planner, tools=tools))
    graph.add_node("act", partial(act_node, tools=tools))
    graph.add_node("conclude", partial(conclude_node, concluder=concluder))

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", route_after_plan, {"act": "act", "conclude": "conclude"})
    graph.add_conditional_edges("act", route_after_act, {"plan": "plan", "conclude": "conclude"})
    graph.add_edge("conclude", END)

    return graph.compile()
