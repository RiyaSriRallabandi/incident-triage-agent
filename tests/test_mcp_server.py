import pytest

from triage.mcp_server import (
    build_server,
    list_scenarios,
    tool_get_recent_deploys,
    tool_query_metrics,
    tool_retrieve_runbook,
    tool_search_logs,
)


def test_list_scenarios_returns_the_golden_set():
    rows = list_scenarios()
    assert len(rows) == 30
    row = next(r for r in rows if r["id"] == "scn_001")
    assert row["category"] == "bad_deploy"
    assert row["incident_report"]


def test_search_logs_tool_over_mcp():
    out = tool_search_logs("scn_001", "502")
    assert out["total_matches"] >= 1
    assert any("returning 502" in line for line in out["lines"])


def test_query_metrics_tool_over_mcp():
    out = tool_query_metrics("scn_001", "edge-proxy", "cpu_utilization_pct")
    assert out["unit"] == "percent"
    assert out["summary"]["maximum"] > 95


def test_get_recent_deploys_tool_over_mcp():
    assert tool_get_recent_deploys("scn_002")["count"] == 0
    assert "7f3a9c1" in tool_get_recent_deploys("scn_001")["deploys"][0]


def test_unknown_scenario_id_is_rejected():
    with pytest.raises(ValueError, match="unknown scenario_id"):
        tool_search_logs("scn_999", "x")


def test_retrieve_runbook_tool_over_mcp(runbook_index, monkeypatch):
    import triage.mcp_server as mod
    from triage.tools.runbook import retrieve_runbook as real_retrieve

    monkeypatch.setattr(
        mod, "retrieve_runbook", lambda q, k=5: real_retrieve(q, k=k, index_dir=runbook_index)
    )
    hits = tool_retrieve_runbook("connection pool exhausted, slow downstream", k=3)
    assert len(hits) == 3
    assert hits[0]["source"] == "connection-pool-exhaustion.md"


def test_server_registers_five_tools():
    server = build_server()
    names = {t.name for t in server._tool_manager.list_tools()}  # noqa: SLF001
    assert names == {
        "list_scenarios",
        "search_logs",
        "query_metrics",
        "get_recent_deploys",
        "retrieve_runbook",
    }
