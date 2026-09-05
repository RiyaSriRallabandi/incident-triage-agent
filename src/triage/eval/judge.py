"""LLM-as-judge: root-cause grading and failure-stage classification.

Only genuinely ambiguous cases go to the model. The escalation calls are decided
by rule (comparing the agent's outcome to ``ground_truth.should_escalate``).
"""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from triage.agent.prompts import render
from triage.agent.state import AgentResult
from triage.eval.runner import CachedRun
from triage.llm import get_judge_model, with_structured_output
from triage.schema import Scenario

JUDGE_ROOT_CAUSE_PROMPT = "judge_root_cause_v2"  # v1 kept: skewed lenient vs the manual review
JUDGE_FAILURE_STAGE_PROMPT = "judge_failure_stage_v1"

RootCauseGrade = Literal["correct", "partial", "incorrect", "n/a"]
EscalationCall = Literal["correct", "missed_escalation", "false_diagnosis"]
FailureStage = Literal[
    "missing_tool_call",
    "wrong_tool_args",
    "misread_evidence",
    "wrong_synthesis",
    "premature_conclusion",
    "other",
]


class _RootCauseVerdict(BaseModel):
    reasoning: str
    grade: Literal["correct", "partial", "incorrect"]


class _FailureVerdict(BaseModel):
    reasoning: str
    stage: FailureStage


class Judgement(BaseModel):
    scenario_id: str
    run_index: int
    agent_outcome: str  # "diagnosis" | "escalate" | "crashed"
    root_cause_grade: RootCauseGrade
    escalation_call: EscalationCall | None
    false_confident_wrong: bool
    failure_stage: FailureStage | None
    reasoning: str

    @property
    def key(self) -> str:
        return f"{self.scenario_id}__run{self.run_index}"

    def unified_label(self) -> Literal["correct", "partial", "incorrect"]:
        """Collapse the outcome to a 3-way label for judge/human calibration."""
        if self.agent_outcome == "crashed":
            return "incorrect"
        if self.agent_outcome == "escalate":
            return "correct" if self.escalation_call == "correct" else "incorrect"
        if self.escalation_call == "false_diagnosis":
            return "incorrect"
        return self.root_cause_grade  # type: ignore[return-value]


def _render_trace(result: AgentResult) -> str:
    if not result.evidence:
        return "(the agent gathered no evidence)"
    return "\n\n".join(
        f"[{e.step}] reasoning: {e.plan_reasoning}\n"
        f"    call: {e.tool}({e.args}){'  [error]' if e.error else ''}\n"
        f"    result: {e.result[:800]}"
        for e in result.evidence
    )


def _conclusion_text(result: AgentResult) -> str:
    if result.diagnosis:
        d = result.diagnosis
        return f"diagnosis (confidence {d.confidence}): {d.root_cause}"
    if result.escalation:
        return f"escalation: {result.escalation.reason}"
    return "(no conclusion)"


def _grade_root_cause(
    scenario: Scenario, agent_cause: str, model: BaseChatModel
) -> _RootCauseVerdict:
    prompt = render(
        JUDGE_ROOT_CAUSE_PROMPT,
        incident_report=scenario.incident_report,
        ground_truth_cause=scenario.ground_truth.root_cause,
        ground_truth_path="\n".join(f"- {s}" for s in scenario.ground_truth.evidence_path)
        or "(none)",
        agent_cause=agent_cause,
    )
    return with_structured_output(model, _RootCauseVerdict).invoke(prompt)


def _classify_failure(
    scenario: Scenario, result: AgentResult, model: BaseChatModel
) -> _FailureVerdict:
    prompt = render(
        JUDGE_FAILURE_STAGE_PROMPT,
        incident_report=scenario.incident_report,
        ground_truth_cause=scenario.ground_truth.root_cause,
        ground_truth_path="\n".join(f"- {s}" for s in scenario.ground_truth.evidence_path)
        or "(none)",
        trace=_render_trace(result),
        conclusion=_conclusion_text(result),
    )
    return with_structured_output(model, _FailureVerdict).invoke(prompt)


def judge_run(
    cached: CachedRun,
    scenario: Scenario,
    *,
    model: BaseChatModel | None = None,
    classify_failures: bool = True,
) -> Judgement:
    model = model or get_judge_model()
    should_escalate = scenario.ground_truth.should_escalate

    if cached.result is None:
        return Judgement(
            scenario_id=cached.scenario_id,
            run_index=cached.run_index,
            agent_outcome="crashed",
            root_cause_grade="n/a",
            escalation_call=None,
            false_confident_wrong=False,
            failure_stage=None,
            reasoning="run crashed",
        )

    result = cached.result

    # Agent escalated -----------------------------------------------------
    if result.outcome == "escalate":
        call: EscalationCall = "correct" if should_escalate else "missed_escalation"
        stage = None
        reasoning = (
            "correctly escalated an under-determined incident"
            if should_escalate
            else "escalated a solvable incident"
        )
        if call == "missed_escalation" and classify_failures:
            fv = _classify_failure(scenario, result, model)
            stage, reasoning = fv.stage, fv.reasoning
        return Judgement(
            scenario_id=cached.scenario_id,
            run_index=cached.run_index,
            agent_outcome="escalate",
            root_cause_grade="n/a",
            escalation_call=call,
            false_confident_wrong=False,
            failure_stage=stage,
            reasoning=reasoning,
        )

    # Agent produced a diagnosis ----------------------------------------
    confidence = result.diagnosis.confidence if result.diagnosis else 0.0

    if should_escalate:
        stage = None
        reasoning = "produced a confident diagnosis for an incident with no determinable cause"
        if classify_failures:
            fv = _classify_failure(scenario, result, model)
            stage, reasoning = fv.stage, fv.reasoning
        return Judgement(
            scenario_id=cached.scenario_id,
            run_index=cached.run_index,
            agent_outcome="diagnosis",
            root_cause_grade="incorrect",
            escalation_call="false_diagnosis",
            false_confident_wrong=True,
            failure_stage=stage,
            reasoning=reasoning,
        )

    verdict = _grade_root_cause(scenario, result.diagnosis.root_cause, model)
    fcw = verdict.grade == "incorrect" and confidence >= 0.5
    stage = None
    if verdict.grade == "incorrect" and classify_failures:
        stage = _classify_failure(scenario, result, model).stage

    return Judgement(
        scenario_id=cached.scenario_id,
        run_index=cached.run_index,
        agent_outcome="diagnosis",
        root_cause_grade=verdict.grade,
        escalation_call="correct",
        false_confident_wrong=fcw,
        failure_stage=stage,
        reasoning=verdict.reasoning,
    )
