"""The three evidence tools: search_logs, query_metrics, get_recent_deploys.

Each operates on a single :class:`Scenario`. They are plain, fully-testable
functions here; :mod:`triage.tools.toolset` wraps them for the agent.

On bad input (unknown service, missing metric, unparseable timestamp) they raise
:class:`ToolInputError` with a message the caller can act on - never a bare
crash. An empty result (no matching logs, no deploys) is a valid answer, not an
error.
"""

from __future__ import annotations

import difflib
from datetime import UTC, datetime

from pydantic import BaseModel

from triage.schema import Scenario

MAX_LOG_RESULTS = 40


class ToolInputError(ValueError):
    """The tool was called with arguments it cannot use; message explains how to fix it."""


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #


def _validate_service(scenario: Scenario, service: str | None) -> None:
    if service is None:
        return
    known = scenario.services()
    if service in known:
        return
    close = difflib.get_close_matches(service, sorted(known), n=1, cutoff=0.5)
    hint = f" Did you mean {close[0]!r}?" if close else f" Known services: {sorted(known)}."
    raise ToolInputError(f"no service named {service!r}.{hint}")


def _parse_ts(value: str | None, *, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolInputError(
            f"could not parse {field}={value!r}; use ISO 8601, e.g. 2026-05-12T13:40:00Z"
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _time_bounds(start: str | None, end: str | None) -> tuple[datetime | None, datetime | None]:
    start_dt = _parse_ts(start, field="start")
    end_dt = _parse_ts(end, field="end")
    if start_dt and end_dt and start_dt > end_dt:
        raise ToolInputError(f"start ({start}) is after end ({end})")
    return start_dt, end_dt


def _in_window(ts: datetime, start: datetime | None, end: datetime | None) -> bool:
    return (start is None or ts >= start) and (end is None or ts <= end)


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# search_logs
# --------------------------------------------------------------------------- #


class LogSearchResult(BaseModel):
    lines: list[str]  # "2026-05-12T13:42:45Z  waf-engine  ERROR  <msg>"
    total_matches: int
    truncated: bool


def search_logs(
    scenario: Scenario,
    query: str,
    *,
    service: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> LogSearchResult:
    """Return log lines matching every whitespace-separated term in ``query``.

    Matching is case-insensitive against the service, level, and message.
    ``limit`` may lower the result cap but not raise it above MAX_LOG_RESULTS.
    """
    terms = query.lower().split()
    if not terms:
        raise ToolInputError("query must contain at least one search term")
    _validate_service(scenario, service)
    start_dt, end_dt = _time_bounds(start, end)

    cap = MAX_LOG_RESULTS if limit is None else max(1, min(limit, MAX_LOG_RESULTS))

    matches = [
        log
        for log in scenario.synthetic_logs
        if (service is None or log.service == service)
        and _in_window(log.ts, start_dt, end_dt)
        and all(term in f"{log.service} {log.level} {log.msg}".lower() for term in terms)
    ]
    matches.sort(key=lambda log: log.ts)

    shown = matches[:cap]
    return LogSearchResult(
        lines=[f"{_iso(log.ts)}  {log.service}  {log.level}  {log.msg}" for log in shown],
        total_matches=len(matches),
        truncated=len(matches) > len(shown),
    )


# --------------------------------------------------------------------------- #
# query_metrics
# --------------------------------------------------------------------------- #


class MetricSummary(BaseModel):
    first: float
    last: float
    minimum: float
    maximum: float
    change_pct: float | None  # from first value to the most extreme value; None if first ~ 0


class MetricQueryResult(BaseModel):
    service: str
    metric: str
    unit: str
    summary: MetricSummary
    points: list[tuple[datetime, float]]


def query_metrics(
    scenario: Scenario,
    service: str,
    metric: str,
    *,
    start: str | None = None,
    end: str | None = None,
) -> MetricQueryResult:
    """Return one metric time series for ``service`` plus a computed summary."""
    _validate_service(scenario, service)
    start_dt, end_dt = _time_bounds(start, end)

    series = next(
        (m for m in scenario.synthetic_metrics if m.service == service and m.name == metric),
        None,
    )
    if series is None:
        available = sorted(m.name for m in scenario.synthetic_metrics if m.service == service)
        if not available:
            with_metrics = sorted({m.service for m in scenario.synthetic_metrics})
            raise ToolInputError(
                f"no metrics recorded for service {service!r}. "
                f"Services with metrics: {with_metrics}"
            )
        raise ToolInputError(f"no metric named {metric!r} for {service!r}. Available: {available}")

    points = [(ts, val) for ts, val in series.points if _in_window(ts, start_dt, end_dt)]
    if not points:
        raise ToolInputError(
            f"no {metric!r} samples for {service!r} in the given window; "
            f"the series spans {_iso(series.points[0][0])} to {_iso(series.points[-1][0])}"
        )

    values = [v for _, v in points]
    first = values[0]
    high, low = max(values), min(values)
    extreme = high if (high - first) >= (first - low) else low
    change_pct = None if abs(first) < 1e-9 else round((extreme - first) / abs(first) * 100, 1)

    return MetricQueryResult(
        service=service,
        metric=metric,
        unit=series.unit,
        summary=MetricSummary(
            first=round(first, 4),
            last=round(values[-1], 4),
            minimum=round(low, 4),
            maximum=round(high, 4),
            change_pct=change_pct,
        ),
        points=points,
    )


# --------------------------------------------------------------------------- #
# get_recent_deploys
# --------------------------------------------------------------------------- #


class DeploysResult(BaseModel):
    deploys: list[str]  # "2026-05-12T13:42:00Z  edge-proxy  7f3a9c1  <summary>"
    count: int


def get_recent_deploys(
    scenario: Scenario,
    *,
    service: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> DeploysResult:
    """Return deploys in scope, chronologically. An empty list means nothing shipped."""
    _validate_service(scenario, service)
    start_dt, end_dt = _time_bounds(start, end)

    hits = [
        d
        for d in scenario.synthetic_deploys
        if (service is None or d.service == service) and _in_window(d.ts, start_dt, end_dt)
    ]
    hits.sort(key=lambda d: d.ts)

    return DeploysResult(
        deploys=[f"{_iso(d.ts)}  {d.service}  {d.commit}  {d.summary}" for d in hits],
        count=len(hits),
    )
