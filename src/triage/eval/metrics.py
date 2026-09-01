"""Programmatic (no-LLM) metrics: citation grounding, efficiency, escalation calls."""

from __future__ import annotations

from pydantic import BaseModel

from triage.eval.runner import CachedRun
from triage.grounding import GROUNDING_THRESHOLD, grounding_score
from triage.schema import Scenario

__all__ = ["GROUNDING_THRESHOLD", "RunMetrics", "grounding_score", "run_metrics"]


class RunMetrics(BaseModel):
    scenario_id: str
    run_index: int
    crashed: bool
    outcome: str  # "diagnosis" | "escalate" | "crashed"
    confidence: float | None
    tool_calls_used: int
    hit_budget_cap: bool
    error_steps: int  # tool calls that returned an error
    n_citations: int  # citations the agent generated (before post-hoc verification)
    n_grounded: int  # of those, how many trace back to retrieved evidence
    n_delivered: int  # citations that survive verification (grounded by construction)
    ungrounded_citations: list[str]
    escalation_decision_correct: bool  # did it make the right call about whether to escalate


def _generated_citations(result) -> list[str]:
    """The citations the agent produced, before post-hoc verification removed any."""
    delivered = []
    if result.outcome == "diagnosis" and result.diagnosis:
        delivered = list(result.diagnosis.evidence)
    elif result.outcome == "escalate" and result.escalation:
        delivered = list(result.escalation.evidence_gathered)
    if result.citation_report is not None:
        return delivered + list(result.citation_report.dropped)
    return delivered


def run_metrics(cached: CachedRun, scenario: Scenario) -> RunMetrics:
    if cached.result is None:
        return RunMetrics(
            scenario_id=cached.scenario_id,
            run_index=cached.run_index,
            crashed=True,
            outcome="crashed",
            confidence=None,
            tool_calls_used=0,
            hit_budget_cap=False,
            error_steps=0,
            n_citations=0,
            n_grounded=0,
            n_delivered=0,
            ungrounded_citations=[],
            escalation_decision_correct=False,
        )

    r = cached.result
    evidence_texts = [e.result for e in r.evidence]
    citations = _generated_citations(r)
    grounded = [c for c in citations if grounding_score(c, evidence_texts) >= GROUNDING_THRESHOLD]
    ungrounded = [c for c in citations if c not in grounded]

    should_escalate = scenario.ground_truth.should_escalate
    did_escalate = r.outcome == "escalate"

    return RunMetrics(
        scenario_id=cached.scenario_id,
        run_index=cached.run_index,
        crashed=False,
        outcome=r.outcome,
        confidence=r.diagnosis.confidence if r.diagnosis else None,
        tool_calls_used=r.tool_calls_used,
        hit_budget_cap=r.hit_budget_cap,
        error_steps=sum(1 for e in r.evidence if e.error),
        n_citations=len(citations),
        n_grounded=len(grounded),
        n_delivered=len(grounded),  # verification drops exactly the ungrounded ones
        ungrounded_citations=ungrounded,
        escalation_decision_correct=(should_escalate == did_escalate),
    )
