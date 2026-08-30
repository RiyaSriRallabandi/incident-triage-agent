"""Graph mechanics: routing, budget, state accumulation, error handling.

All offline - the planner and concluder are scripted, no LLM calls.
"""

import pytest

from triage.agent.run import _metric_catalog, investigate
from triage.agent.state import ConcludeResult, PlanDecision
from triage.dataset import load_scenarios

SC = {s.id: s for s in load_scenarios()}
NO_INDEX = "/nonexistent/runbook_index"  # tests here never touch the runbook tool


def scripted_planner(*decisions: PlanDecision):
    seq = iter(decisions)
    prompts: list[str] = []

    def planner(prompt: str) -> PlanDecision:
        prompts.append(prompt)
        return next(seq, PlanDecision(reasoning="fallback", action="conclude"))

    planner.prompts = prompts  # type: ignore[attr-defined]
    return planner


def scripted_concluder(result: ConcludeResult):
    prompts: list[str] = []

    def concluder(prompt: str) -> ConcludeResult:
        prompts.append(prompt)
        return result

    concluder.prompts = prompts  # type: ignore[attr-defined]
    return concluder


def call(tool: str, **args_pairs) -> PlanDecision:
    import json

    return PlanDecision(
        reasoning=f"call {tool}",
        action="call_tool",
        tool=tool,
        tool_args_json=json.dumps(args_pairs),
    )


CONCLUDE = PlanDecision(reasoning="enough", action="conclude")
DIAGNOSIS = ConcludeResult(
    outcome="diagnosis",
    root_cause="bad WAF rule",
    confidence=0.8,
    evidence=["deploy 7f3a9c1", "cpu spike"],
    recommended_fix="roll back",
)


def _run(scenario_id, planner, concluder=None, budget=6):
    return investigate(
        SC[scenario_id],
        budget=budget,
        planner=planner,
        concluder=concluder or scripted_concluder(DIAGNOSIS),
        runbook_index_dir=NO_INDEX,
    )


def test_happy_path_accumulates_evidence_then_concludes():
    planner = scripted_planner(
        call("search_logs", query="502"),
        call("get_recent_deploys"),
        CONCLUDE,
    )
    result = _run("scn_001", planner)

    assert result.outcome == "diagnosis"
    assert result.tool_calls_used == 2
    assert result.hit_budget_cap is False
    assert [e.tool for e in result.evidence] == ["search_logs", "get_recent_deploys"]
    assert "returning 502" in result.evidence[0].result
    assert "7f3a9c1" in result.evidence[1].result
    assert result.diagnosis is not None and result.escalation is None


def test_conclude_immediately_uses_no_tools():
    result = _run("scn_001", scripted_planner(CONCLUDE))
    assert result.tool_calls_used == 0
    assert result.evidence == []


def test_budget_cap_forces_conclude():
    planner = scripted_planner(*[call("search_logs", query="cpu") for _ in range(10)])
    concluder = scripted_concluder(DIAGNOSIS)
    result = _run("scn_001", planner, concluder=concluder, budget=3)

    assert result.tool_calls_used == 3
    assert result.hit_budget_cap is True
    assert len(result.evidence) == 3
    assert len(planner.prompts) == 3  # planner not called a 4th time
    assert "budget was exhausted" in concluder.prompts[0]  # conclude prompt notes it


def test_unknown_tool_is_recorded_as_error():
    planner = scripted_planner(call("frobnicate"), CONCLUDE)
    result = _run("scn_001", planner)

    assert result.tool_calls_used == 1
    assert result.evidence[0].error is True
    assert "unknown tool" in result.evidence[0].result


def test_bad_json_args_is_recorded_as_error():
    planner = scripted_planner(
        PlanDecision(
            reasoning="oops", action="call_tool", tool="search_logs", tool_args_json="{not json"
        ),
        CONCLUDE,
    )
    result = _run("scn_001", planner)
    assert result.evidence[0].error is True
    assert "could not parse" in result.evidence[0].result


def test_tool_exception_is_recorded_as_error():
    planner = scripted_planner(call("query_metrics", service="edge-proxy", metric="cpu"), CONCLUDE)
    result = _run("scn_001", planner)

    assert result.evidence[0].error is True
    assert "tool error" in result.evidence[0].result
    assert "no metric named 'cpu'" in result.evidence[0].result


def test_escalation_outcome_is_mapped():
    concluder = scripted_concluder(
        ConcludeResult(
            outcome="escalate",
            escalation_reason="evidence too thin",
            evidence=["no deploys in window"],
            suggested_next_steps=["per-host error breakdown"],
        )
    )
    result = _run("scn_004", scripted_planner(CONCLUDE), concluder=concluder)

    assert result.outcome == "escalate"
    assert result.diagnosis is None
    assert result.escalation is not None
    assert result.escalation.reason == "evidence too thin"
    assert result.escalation.suggested_next_steps == ["per-host error breakdown"]


def test_plan_prompt_carries_the_start_context():
    planner = scripted_planner(CONCLUDE)
    _run("scn_001", planner)
    prompt = planner.prompts[0]

    assert "edge tier is serving a high rate of 502s" in prompt
    assert "edge-proxy" in prompt and "waf-engine" in prompt
    assert "cpu_utilization_pct" in prompt  # metric catalog
    assert "search_logs(" in prompt  # tool specs


def test_metric_catalog_shape():
    catalog = _metric_catalog(SC["scn_002"])
    assert catalog["payments-api"] == ["p95_latency_ms"]
    assert "error_rate" in catalog["checkout-api"]
    assert catalog["orders-worker"] == []  # a service with logs but no metrics


@pytest.mark.parametrize("scenario_id", list(SC))
def test_runs_on_every_scenario_with_scripted_model(scenario_id):
    planner = scripted_planner(call("get_recent_deploys"), CONCLUDE)
    result = _run(scenario_id, planner)
    assert result.outcome == "diagnosis"
    assert result.evidence[0].tool == "get_recent_deploys"
