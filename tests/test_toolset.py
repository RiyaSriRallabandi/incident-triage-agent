from triage.dataset import load_scenarios
from triage.tools.toolset import TOOL_NAMES, build_toolset

SCENARIOS = {s.id: s for s in load_scenarios()}


def _toolset(scenario_id: str, **kw):
    tools = build_toolset(SCENARIOS[scenario_id], **kw)
    return {t.name: t for t in tools}


def test_toolset_exposes_all_four_tools_with_schemas():
    tools = build_toolset(SCENARIOS["scn_001"])
    assert [t.name for t in tools] == list(TOOL_NAMES)
    for t in tools:
        assert t.description.strip()
        assert t.args_schema is not None
    # arg descriptions were parsed from the docstrings
    assert "query" in tools[0].args
    assert tools[0].args["query"]["description"]


def test_search_logs_tool_returns_readable_string():
    out = _toolset("scn_001")["search_logs"].invoke({"query": "502"})
    assert "returning 502" in out
    assert "2026-05-12T13:43:35Z" in out


def test_deploys_tool_reports_nothing_shipped_for_scn_002():
    out = _toolset("scn_002")["get_recent_deploys"].invoke({})
    assert out == "No deploys found in the given scope."


def test_metrics_tool_bad_input_returns_message_not_exception():
    out = _toolset("scn_001")["query_metrics"].invoke({"service": "edge-proxy", "metric": "cpu"})
    assert "no metric named 'cpu'" in out
    assert "cpu_utilization_pct" in out


def test_runbook_tool_present_and_retrieves(runbook_index):
    tools = _toolset("scn_001", runbook_index_dir=runbook_index)
    out = tools["retrieve_runbook"].invoke({"query": "cpu pinned at 100 percent after a deploy"})
    assert "runbook section" in out
    assert ".md >" in out


def test_runbook_tool_missing_index_returns_message(tmp_path):
    tools = _toolset("scn_001", runbook_index_dir=tmp_path / "nope")
    out = tools["retrieve_runbook"].invoke({"query": "anything"})
    assert "build_runbook_index" in out
