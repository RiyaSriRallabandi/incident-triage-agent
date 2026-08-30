import pytest

from triage.dataset import load_scenarios
from triage.tools.evidence import (
    ToolInputError,
    get_recent_deploys,
    query_metrics,
    search_logs,
)

SCENARIOS = {s.id: s for s in load_scenarios()}


@pytest.fixture
def scn_001():
    return SCENARIOS["scn_001"]


@pytest.fixture
def scn_002():
    return SCENARIOS["scn_002"]


# --- search_logs ---------------------------------------------------------- #


def test_search_logs_finds_signal_line(scn_001):
    result = search_logs(scn_001, "regex budget")
    assert result.total_matches == 1
    assert "rule 100417" in result.lines[0]
    assert result.lines[0].startswith("2026-05-12T13:42:45Z  waf-engine  ERROR")


def test_search_logs_all_terms_must_match(scn_001):
    assert search_logs(scn_001, "cpu saturated").total_matches >= 1
    assert search_logs(scn_001, "cpu unicorn").total_matches == 0


def test_search_logs_service_and_time_filters(scn_001):
    only_edge = search_logs(scn_001, "cpu", service="edge-proxy")
    assert only_edge.total_matches >= 1
    assert all("edge-proxy" in line for line in only_edge.lines)

    before_incident = search_logs(scn_001, "cpu", end="2026-05-12T13:42:00Z")
    assert before_incident.total_matches == 0


def test_search_logs_unknown_service_suggests_match(scn_001):
    with pytest.raises(ToolInputError, match="edge-proxy"):
        search_logs(scn_001, "anything", service="edge")


def test_search_logs_empty_query_rejected(scn_001):
    with pytest.raises(ToolInputError, match="search term"):
        search_logs(scn_001, "   ")


def test_search_logs_truncation(scn_002):
    capped = search_logs(scn_002, "checkout-api", limit=2)
    assert len(capped.lines) == 2
    assert capped.truncated is True
    assert capped.total_matches > 2


def test_search_logs_bad_timestamp(scn_001):
    with pytest.raises(ToolInputError, match="ISO 8601"):
        search_logs(scn_001, "cpu", start="yesterday")


# --- query_metrics ------------------------------------------------------- #


def test_query_metrics_reports_spike(scn_001):
    r = query_metrics(scn_001, "edge-proxy", "cpu_utilization_pct")
    assert r.unit == "percent"
    assert r.summary.maximum > 95
    assert r.summary.change_pct > 100  # roughly tripled
    assert len(r.points) > 20


def test_query_metrics_reports_drop(scn_002):
    # payments latency roughly quadruples
    r = query_metrics(scn_002, "payments-api", "p95_latency_ms")
    assert r.summary.change_pct > 200


def test_query_metrics_unknown_metric_lists_available(scn_001):
    with pytest.raises(ToolInputError, match="cpu_utilization_pct"):
        query_metrics(scn_001, "edge-proxy", "cpu")


def test_query_metrics_service_without_metrics(scn_001):
    with pytest.raises(ToolInputError, match="Services with metrics"):
        query_metrics(scn_001, "orders-api", "anything")


# --- get_recent_deploys ------------------------------------------------- #


def test_get_recent_deploys_returns_the_deploy(scn_001):
    r = get_recent_deploys(scn_001)
    assert r.count == 1
    assert "7f3a9c1" in r.deploys[0]
    assert r.deploys[0].startswith("2026-05-12T13:42:00Z  edge-proxy")


def test_get_recent_deploys_empty_is_not_an_error(scn_002):
    r = get_recent_deploys(scn_002)
    assert r.count == 0
    assert r.deploys == []


def test_get_recent_deploys_service_filter(scn_001):
    assert get_recent_deploys(scn_001, service="api-gateway").count == 0
    assert get_recent_deploys(scn_001, service="edge-proxy").count == 1


def test_get_recent_deploys_unknown_service(scn_001):
    with pytest.raises(ToolInputError, match="no service named"):
        get_recent_deploys(scn_001, service="edgeproxy")
