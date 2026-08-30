"""State and result types for the triage agent graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """One completed tool call, kept as the investigation trace."""

    step: int
    plan_reasoning: str
    tool: str
    args: dict[str, Any]
    result: str
    error: bool = False


class PlanDecision(BaseModel):
    """What the plan node decides to do next."""

    reasoning: str = Field(description="One or two sentences: what is known and why this is next.")
    action: Literal["call_tool", "conclude"]
    tool: str = Field(default="", description="Tool name; required when action is call_tool.")
    tool_args_json: str = Field(
        default="{}",
        description='JSON object of tool arguments, e.g. {"query": "502 capacity"}.',
    )


class ConcludeResult(BaseModel):
    """The conclude node's structured output; mapped to Diagnosis or Escalation."""

    outcome: Literal["diagnosis", "escalate"]
    root_cause: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    recommended_fix: str = ""
    escalation_reason: str = ""
    suggested_next_steps: list[str] = Field(default_factory=list)


class Diagnosis(BaseModel):
    root_cause: str
    confidence: float
    evidence: list[str]
    recommended_fix: str


class Escalation(BaseModel):
    reason: str
    evidence_gathered: list[str]
    suggested_next_steps: list[str]


class AgentResult(BaseModel):
    scenario_id: str
    outcome: Literal["diagnosis", "escalate"]
    diagnosis: Diagnosis | None = None
    escalation: Escalation | None = None
    evidence: list[EvidenceItem]
    tool_calls_used: int
    hit_budget_cap: bool


class TriageState(TypedDict):
    incident_report: str
    evidence_window: str  # ISO span that all available evidence falls within
    service_inventory: list[str]
    metric_catalog: dict[str, list[str]]
    evidence: Annotated[list[EvidenceItem], operator.add]
    tool_calls_used: int
    tool_call_budget: int
    hit_budget_cap: bool
    pending_plan: PlanDecision | None
    result: ConcludeResult | None
