import pytest
from fastapi.testclient import TestClient

from triage.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_scenarios_lists_dev_and_heldout(client):
    rows = client.get("/scenarios").json()
    groups = {r["group"] for r in rows}
    assert groups == {"dev", "heldout"}
    assert len(rows) == 40
    assert all(r["id"].startswith("scn_") for r in rows)


def test_index_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "IncidentTriage Agent" in r.text
    assert "/scenarios/scn_001" in r.text


def test_scenario_detail_shows_trace_and_verdict(client):
    r = client.get("/scenarios/scn_001")
    assert r.status_code == 200
    assert "Investigation trace" in r.text
    assert "Citation verification" in r.text
    assert "Judge verdict" in r.text


def test_unknown_scenario_is_404(client):
    r = client.get("/scenarios/scn_999")
    assert r.status_code == 404


def test_live_investigation_disabled_by_default(client):
    r = client.post("/investigate", json={"scenario_id": "scn_001"})
    assert r.status_code == 503
    assert "disabled" in r.json()["detail"].lower()
