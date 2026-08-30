from triage.agent.state import AgentResult, Diagnosis, Escalation, EvidenceItem
from triage.dataset import load_scenarios
from triage.eval.metrics import GROUNDING_THRESHOLD, grounding_score, run_metrics
from triage.eval.runner import CachedRun

SC = {s.id: s for s in load_scenarios()}


def _evidence(*results: str) -> list[EvidenceItem]:
    return [
        EvidenceItem(step=i, plan_reasoning="r", tool="search_logs", args={}, result=text)
        for i, text in enumerate(results, 1)
    ]


def test_grounding_score_matches_supporting_evidence():
    ev = ["2026-05-12T13:42:00Z edge-proxy deploy 7f3a9c1 roll out WAF ruleset"]
    assert grounding_score("deploy 7f3a9c1 rolled out a new WAF ruleset", ev) >= GROUNDING_THRESHOLD


def test_grounding_score_flags_fabricated_citation():
    ev = ["2026-05-12T13:42:00Z edge-proxy cpu usage 78 percent rising"]
    assert grounding_score("payments-api replica lag caused 500 errors", ev) < GROUNDING_THRESHOLD


def _cached(result: AgentResult, scenario_id: str) -> CachedRun:
    return CachedRun(tag="t", scenario_id=scenario_id, run_index=1, budget=6, result=result)


def test_run_metrics_counts_grounded_and_fabricated_citations():
    result = AgentResult(
        scenario_id="scn_001",
        outcome="diagnosis",
        diagnosis=Diagnosis(
            root_cause="bad WAF rule",
            confidence=0.8,
            evidence=[
                "edge-proxy cpu rose to 100 percent",  # grounded
                "a database migration locked the users table",  # fabricated
            ],
            recommended_fix="roll back",
        ),
        evidence=_evidence(
            "edge-proxy cpu usage climbed to 100 percent and stayed pinned",
            "waf-engine regex evaluation exceeded budget",
        ),
        tool_calls_used=2,
        hit_budget_cap=False,
    )
    m = run_metrics(_cached(result, "scn_001"), SC["scn_001"])

    assert m.n_citations == 2
    assert m.n_grounded == 1
    assert m.ungrounded_citations == ["a database migration locked the users table"]
    assert m.escalation_decision_correct is True  # scn_001 is solvable, agent diagnosed


def test_run_metrics_escalation_decision_for_ambiguous_scenario():
    escalated = AgentResult(
        scenario_id="scn_004",
        outcome="escalate",
        escalation=Escalation(
            reason="thin evidence", evidence_gathered=[], suggested_next_steps=[]
        ),
        evidence=_evidence("notifications-api error rate 3 percent, no deploys"),
        tool_calls_used=4,
        hit_budget_cap=False,
    )
    assert run_metrics(_cached(escalated, "scn_004"), SC["scn_004"]).escalation_decision_correct

    diagnosed = escalated.model_copy(
        update={
            "outcome": "diagnosis",
            "escalation": None,
            "diagnosis": Diagnosis(
                root_cause="retry storm", confidence=0.7, evidence=[], recommended_fix="x"
            ),
        }
    )
    assert not run_metrics(_cached(diagnosed, "scn_004"), SC["scn_004"]).escalation_decision_correct


def test_run_metrics_handles_crashed_run():
    m = run_metrics(
        CachedRun(tag="t", scenario_id="scn_002", run_index=1, budget=6, error="boom"),
        SC["scn_002"],
    )
    assert m.crashed is True
    assert m.outcome == "crashed"
