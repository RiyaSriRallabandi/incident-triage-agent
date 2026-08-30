"""Aggregate per-run metrics and judgements into one eval summary."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from triage.eval.calibration import Calibration
from triage.eval.judge import Judgement
from triage.eval.metrics import RunMetrics


def _rate(numer: int, denom: int) -> float | None:
    return round(numer / denom, 3) if denom else None


class ScenarioBreakdown(BaseModel):
    scenario_id: str
    n_runs: int
    root_cause_grades: dict[str, int]
    escalation_calls: dict[str, int]
    mean_tool_calls: float
    grounded_citation_rate: float | None


class EvalSummary(BaseModel):
    tag: str
    n_runs: int
    n_crashed: int

    # outcome
    root_cause_accuracy: float | None  # correct / (gradable runs)
    root_cause_partial_rate: float | None
    escalation_decision_accuracy: float | None
    false_confident_wrong_rate: float | None

    # step-level
    mean_tool_calls: float
    budget_cap_rate: float
    mean_error_steps: float
    citation_grounding_rate: float | None
    fabricated_citation_rate: float | None

    failure_stages: dict[str, int]
    per_scenario: list[ScenarioBreakdown]
    calibration: Calibration | None = None


def summarize(
    tag: str,
    metrics: list[RunMetrics],
    judgements: list[Judgement],
    *,
    calibration: Calibration | None = None,
) -> EvalSummary:
    n = len(metrics)
    crashed = [m for m in metrics if m.crashed]

    gradable = [j for j in judgements if j.root_cause_grade in ("correct", "partial", "incorrect")]
    n_correct = sum(j.root_cause_grade == "correct" for j in gradable)
    n_partial = sum(j.root_cause_grade == "partial" for j in gradable)

    esc_calls = [j.escalation_call for j in judgements if j.escalation_call is not None]
    n_esc_correct = sum(c == "correct" for c in esc_calls)

    total_citations = sum(m.n_citations for m in metrics)
    total_grounded = sum(m.n_grounded for m in metrics)

    stages = Counter(j.failure_stage for j in judgements if j.failure_stage is not None)

    per_scenario: list[ScenarioBreakdown] = []
    for sid in sorted({m.scenario_id for m in metrics}):
        s_metrics = [m for m in metrics if m.scenario_id == sid]
        s_judge = [j for j in judgements if j.scenario_id == sid]
        s_citations = sum(m.n_citations for m in s_metrics)
        per_scenario.append(
            ScenarioBreakdown(
                scenario_id=sid,
                n_runs=len(s_metrics),
                root_cause_grades=dict(Counter(j.root_cause_grade for j in s_judge)),
                escalation_calls=dict(
                    Counter(j.escalation_call for j in s_judge if j.escalation_call)
                ),
                mean_tool_calls=round(
                    sum(m.tool_calls_used for m in s_metrics) / len(s_metrics), 2
                ),
                grounded_citation_rate=_rate(sum(m.n_grounded for m in s_metrics), s_citations),
            )
        )

    return EvalSummary(
        tag=tag,
        n_runs=n,
        n_crashed=len(crashed),
        root_cause_accuracy=_rate(n_correct, len(gradable)),
        root_cause_partial_rate=_rate(n_partial, len(gradable)),
        escalation_decision_accuracy=_rate(n_esc_correct, len(esc_calls)),
        false_confident_wrong_rate=_rate(sum(j.false_confident_wrong for j in judgements), n),
        mean_tool_calls=round(sum(m.tool_calls_used for m in metrics) / n, 2) if n else 0.0,
        budget_cap_rate=_rate(sum(m.hit_budget_cap for m in metrics), n) or 0.0,
        mean_error_steps=round(sum(m.error_steps for m in metrics) / n, 2) if n else 0.0,
        citation_grounding_rate=_rate(total_grounded, total_citations),
        fabricated_citation_rate=_rate(total_citations - total_grounded, total_citations),
        failure_stages=dict(stages),
        per_scenario=per_scenario,
        calibration=calibration,
    )
