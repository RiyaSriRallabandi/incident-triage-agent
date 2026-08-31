"""MCP server exposing the incident-triage evidence tools.

Any MCP client (Claude Desktop, another agent) can list the synthetic incident
scenarios and query each one's logs, metrics, and deploys, plus search the shared
runbook corpus. The scenario-scoped tools take a ``scenario_id``; ``list_scenarios``
enumerates the choices.

Run:  uv run python -m triage.mcp_server        # stdio transport
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from triage.dataset import load_scenarios
from triage.tools import evidence
from triage.tools.runbook import retrieve_runbook

_SCENARIOS = {s.id: s for s in load_scenarios()}


def _scenario(scenario_id: str):
    scenario = _SCENARIOS.get(scenario_id)
    if scenario is None:
        raise ValueError(f"unknown scenario_id {scenario_id!r}. Options: {sorted(_SCENARIOS)}")
    return scenario


# --- tool implementations (plain functions, directly testable) --------------- #


def list_scenarios() -> list[dict]:
    """List the synthetic incident scenarios available for investigation."""
    return [
        {
            "id": s.id,
            "category": s.category.value,
            "difficulty": s.difficulty.value,
            "title": s.title,
            "incident_report": s.incident_report,
        }
        for s in _SCENARIOS.values()
    ]


def tool_search_logs(
    scenario_id: str,
    query: str,
    service: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Search a scenario's logs for lines containing every whitespace-separated term.

    Matching is case-insensitive against service, level, and message. ``start`` /
    ``end`` are optional ISO-8601 bounds. The result is capped; narrow the query if so.
    """
    r = evidence.search_logs(_scenario(scenario_id), query, service=service, start=start, end=end)
    return r.model_dump()


def tool_query_metrics(
    scenario_id: str,
    service: str,
    metric: str,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Return one metric time series for a service in the scenario, with a summary.

    On a miss, the error lists the metrics that do exist for the service.
    """
    r = evidence.query_metrics(_scenario(scenario_id), service, metric, start=start, end=end)
    return r.model_dump(mode="json")


def tool_get_recent_deploys(
    scenario_id: str,
    service: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """List deploys in the scenario. An empty list means nothing shipped."""
    r = evidence.get_recent_deploys(_scenario(scenario_id), service=service, start=start, end=end)
    return r.model_dump()


def tool_retrieve_runbook(query: str, k: int = 5) -> list[dict]:
    """Semantic search over the shared runbook corpus for troubleshooting guidance."""
    return [hit.model_dump() for hit in retrieve_runbook(query, k=k)]


def build_server() -> MCPServer:
    server = MCPServer("incident-triage")
    server.tool(name="list_scenarios")(list_scenarios)
    server.tool(name="search_logs")(tool_search_logs)
    server.tool(name="query_metrics")(tool_query_metrics)
    server.tool(name="get_recent_deploys")(tool_get_recent_deploys)
    server.tool(name="retrieve_runbook")(tool_retrieve_runbook)
    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
