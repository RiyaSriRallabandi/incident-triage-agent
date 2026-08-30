"""Package the four evidence tools for the agent.

``build_toolset(scenario)`` returns LangChain ``StructuredTool``s whose data is
bound to one scenario. Each wrapper turns a structured result into a compact,
readable string for the model, and converts a :class:`ToolInputError` into a
``ToolException`` so the agent sees a recoverable message instead of a crash.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool, ToolException

from triage.schema import Scenario
from triage.tools import evidence
from triage.tools.runbook import INDEX_DIR, retrieve_runbook

TOOL_NAMES = ("search_logs", "query_metrics", "get_recent_deploys", "retrieve_runbook")


def _format_logs(r: evidence.LogSearchResult) -> str:
    if not r.lines:
        return "No matching log lines."
    header = f"{len(r.lines)} of {r.total_matches} matching log lines"
    if r.truncated:
        header += " (result capped; add search terms or a time range to narrow)"
    return header + ":\n" + "\n".join(r.lines)


def _format_metrics(r: evidence.MetricQueryResult) -> str:
    s = r.summary
    change = "n/a" if s.change_pct is None else f"{s.change_pct:+}%"
    pts = ", ".join(f"{ts:%H:%M}={val:g}" for ts, val in r.points)
    return (
        f"{r.service} / {r.metric} ({r.unit})\n"
        f"summary: first={s.first}, last={s.last}, min={s.minimum}, max={s.maximum}, "
        f"change {change} (first value -> most extreme value)\n"
        f"points: {pts}"
    )


def _format_deploys(r: evidence.DeploysResult) -> str:
    if not r.deploys:
        return "No deploys found in the given scope."
    return f"{r.count} deploy(s):\n" + "\n".join(r.deploys)


def _format_runbook(hits: list) -> str:
    if not hits:
        return "No runbook sections found."
    blocks = [f"[{i}] {h.citation()} (score {h.score})\n{h.text}" for i, h in enumerate(hits, 1)]
    return f"{len(hits)} runbook section(s):\n\n" + "\n\n".join(blocks)


def build_toolset(
    scenario: Scenario,
    *,
    runbook_index_dir: Path = INDEX_DIR,
) -> list[StructuredTool]:
    def search_logs(
        query: str,
        service: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> str:
        """Search this incident's logs for lines containing every term in the query.

        Args:
            query: Whitespace-separated search terms; a line must contain all of them
                (case-insensitive, matched against service, level, and message).
            service: Optional exact service name to restrict the search to.
            start: Optional ISO-8601 lower bound on timestamp, e.g. 2026-05-12T13:40:00Z.
            end: Optional ISO-8601 upper bound on timestamp.
        """
        try:
            return _format_logs(
                evidence.search_logs(scenario, query, service=service, start=start, end=end)
            )
        except evidence.ToolInputError as exc:
            raise ToolException(str(exc)) from exc

    def query_metrics(
        service: str,
        metric: str,
        start: str | None = None,
        end: str | None = None,
    ) -> str:
        """Get one metric time series for a service in this incident, with a summary.

        Args:
            service: Service name, e.g. edge-proxy.
            metric: Metric name, e.g. cpu_utilization_pct. On a miss, the available
                metric names for the service are returned.
            start: Optional ISO-8601 lower bound on timestamp.
            end: Optional ISO-8601 upper bound on timestamp.
        """
        try:
            return _format_metrics(
                evidence.query_metrics(scenario, service, metric, start=start, end=end)
            )
        except evidence.ToolInputError as exc:
            raise ToolException(str(exc)) from exc

    def get_recent_deploys(
        service: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> str:
        """List deploys for this incident. An empty result means nothing shipped.

        Args:
            service: Optional service name to filter by.
            start: Optional ISO-8601 lower bound on timestamp.
            end: Optional ISO-8601 upper bound on timestamp.
        """
        try:
            return _format_deploys(
                evidence.get_recent_deploys(scenario, service=service, start=start, end=end)
            )
        except evidence.ToolInputError as exc:
            raise ToolException(str(exc)) from exc

    def runbook_search(query: str) -> str:
        """Search the runbook library for troubleshooting guidance on a failure pattern.

        Args:
            query: A description of the symptom or pattern, e.g.
                "connection pool exhausted, slow downstream".
        """
        try:
            hits = retrieve_runbook(query, index_dir=runbook_index_dir)
        except (ValueError, FileNotFoundError) as exc:
            raise ToolException(str(exc)) from exc
        return _format_runbook(hits)

    # No handle_tool_error: a ToolException propagates to the agent's act node,
    # which records it as a failed evidence step (error=True) the planner can see.
    return [
        StructuredTool.from_function(search_logs, name="search_logs", parse_docstring=True),
        StructuredTool.from_function(query_metrics, name="query_metrics", parse_docstring=True),
        StructuredTool.from_function(
            get_recent_deploys, name="get_recent_deploys", parse_docstring=True
        ),
        StructuredTool.from_function(runbook_search, name="retrieve_runbook", parse_docstring=True),
    ]
