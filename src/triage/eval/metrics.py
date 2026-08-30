"""Programmatic (no-LLM) metrics: citation grounding, efficiency, escalation calls."""

from __future__ import annotations

import re

from pydantic import BaseModel

from triage.eval.runner import CachedRun
from triage.schema import Scenario

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "at",
    "for",
    "is",
    "was",
    "as",
    "by",
    "with",
    "that",
    "this",
    "it",
    "its",
    "from",
    "into",
    "then",
    "than",
    "due",
    "caused",
    "cause",
    "root",
    "error",
    "errors",
    "issue",
    "service",
    "during",
}


def _content_words(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9._:-]*", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def grounding_score(citation: str, evidence_texts: list[str]) -> float:
    """Best fraction of the citation's content words found in any single evidence item."""
    words = _content_words(citation)
    if not words:
        return 0.0
    best = 0.0
    for text in evidence_texts:
        hay = set(_content_words(text))
        best = max(best, sum(w in hay for w in words) / len(words))
    return best


GROUNDING_THRESHOLD = 0.6


class RunMetrics(BaseModel):
    scenario_id: str
    run_index: int
    crashed: bool
    outcome: str  # "diagnosis" | "escalate" | "crashed"
    confidence: float | None
    tool_calls_used: int
    hit_budget_cap: bool
    error_steps: int  # tool calls that returned an error
    n_citations: int
    n_grounded: int
    ungrounded_citations: list[str]
    escalation_decision_correct: bool  # did it make the right call about whether to escalate


def _citations(result) -> list[str]:
    if result.outcome == "diagnosis" and result.diagnosis:
        return list(result.diagnosis.evidence)
    if result.outcome == "escalate" and result.escalation:
        return list(result.escalation.evidence_gathered)
    return []


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
            ungrounded_citations=[],
            escalation_decision_correct=False,
        )

    r = cached.result
    evidence_texts = [e.result for e in r.evidence]
    citations = _citations(r)
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
        ungrounded_citations=ungrounded,
        escalation_decision_correct=(should_escalate == did_escalate),
    )
