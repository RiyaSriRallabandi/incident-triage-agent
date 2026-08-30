"""The rule-based branches of the judge - no LLM should be touched."""

import pytest

from triage.agent.state import AgentResult, Diagnosis, Escalation, EvidenceItem
from triage.dataset import load_scenarios
from triage.eval.judge import judge_run
from triage.eval.runner import CachedRun

SC = {s.id: s for s in load_scenarios()}


class _NoModel:
    def with_structured_output(self, *a, **k):
        raise AssertionError("judge called the model on a rule-only branch")


def _cached(result: AgentResult, sid: str) -> CachedRun:
    return CachedRun(tag="t", scenario_id=sid, run_index=1, budget=6, result=result)


def _ev() -> list[EvidenceItem]:
    return [EvidenceItem(step=1, plan_reasoning="r", tool="search_logs", args={}, result="x")]


def test_correct_escalation_on_ambiguous_scenario():
    result = AgentResult(
        scenario_id="scn_004",
        outcome="escalate",
        escalation=Escalation(reason="thin", evidence_gathered=[], suggested_next_steps=[]),
        evidence=_ev(),
        tool_calls_used=3,
        hit_budget_cap=False,
    )
    j = judge_run(_cached(result, "scn_004"), SC["scn_004"], model=_NoModel())
    assert j.escalation_call == "correct"
    assert j.root_cause_grade == "n/a"
    assert j.false_confident_wrong is False


def test_false_diagnosis_on_ambiguous_scenario_is_false_confident_wrong():
    result = AgentResult(
        scenario_id="scn_004",
        outcome="diagnosis",
        diagnosis=Diagnosis(
            root_cause="retry storm", confidence=0.7, evidence=[], recommended_fix="x"
        ),
        evidence=_ev(),
        tool_calls_used=6,
        hit_budget_cap=True,
    )
    j = judge_run(
        _cached(result, "scn_004"), SC["scn_004"], model=_NoModel(), classify_failures=False
    )
    assert j.escalation_call == "false_diagnosis"
    assert j.root_cause_grade == "incorrect"
    assert j.false_confident_wrong is True


def test_missed_escalation_on_solvable_scenario():
    result = AgentResult(
        scenario_id="scn_001",
        outcome="escalate",
        escalation=Escalation(reason="unsure", evidence_gathered=[], suggested_next_steps=[]),
        evidence=_ev(),
        tool_calls_used=6,
        hit_budget_cap=True,
    )
    j = judge_run(
        _cached(result, "scn_001"), SC["scn_001"], model=_NoModel(), classify_failures=False
    )
    assert j.escalation_call == "missed_escalation"
    assert j.unified_label() == "incorrect"


def test_crashed_run_is_na():
    j = judge_run(
        CachedRun(tag="t", scenario_id="scn_002", run_index=1, budget=6, error="boom"),
        SC["scn_002"],
        model=_NoModel(),
    )
    assert j.agent_outcome == "crashed"
    assert j.root_cause_grade == "n/a"


def test_unified_label_mapping():
    from triage.eval.judge import Judgement

    def _j(**kw) -> Judgement:
        base = dict(
            scenario_id="scn_001",
            run_index=1,
            reasoning="",
            false_confident_wrong=False,
            failure_stage=None,
        )
        return Judgement(**{**base, **kw})

    # diagnosis on a solvable scenario -> the root-cause grade carries through
    assert (
        _j(agent_outcome="diagnosis", root_cause_grade="partial", escalation_call="correct")
        .unified_label()
        == "partial"
    )
    # escalated a solvable scenario -> incorrect
    assert (
        _j(agent_outcome="escalate", root_cause_grade="n/a", escalation_call="missed_escalation")
        .unified_label()
        == "incorrect"
    )
    # correctly escalated an ambiguous scenario -> correct
    assert (
        _j(agent_outcome="escalate", root_cause_grade="n/a", escalation_call="correct")
        .unified_label()
        == "correct"
    )
    # confident diagnosis on an ambiguous scenario -> incorrect
    false_dx = _j(
        agent_outcome="diagnosis",
        root_cause_grade="incorrect",
        escalation_call="false_diagnosis",
    )
    assert false_dx.unified_label() == "incorrect"


@pytest.mark.parametrize("sid", ["scn_001", "scn_002", "scn_003"])
def test_no_model_call_for_solvable_escalation_when_not_classifying(sid):
    result = AgentResult(
        scenario_id=sid,
        outcome="escalate",
        escalation=Escalation(reason="x", evidence_gathered=[], suggested_next_steps=[]),
        evidence=_ev(),
        tool_calls_used=6,
        hit_budget_cap=True,
    )
    judge_run(_cached(result, sid), SC[sid], model=_NoModel(), classify_failures=False)
