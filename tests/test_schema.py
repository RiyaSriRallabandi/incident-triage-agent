from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from triage.schema import GroundTruth, LogLevel, LogLine, MetricSeries, Scenario

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _log(offset: int = 0, **kw) -> dict:
    return {
        "ts": T0 + timedelta(seconds=offset),
        "service": kw.get("service", "svc"),
        "level": kw.get("level", LogLevel.INFO),
        "msg": kw.get("msg", "m"),
    }


def test_logline_rejects_blank_fields():
    with pytest.raises(ValidationError):
        LogLine(**_log(service=""))


def test_metric_series_requires_chronological_points():
    with pytest.raises(ValidationError, match="chronological"):
        MetricSeries(
            name="cpu",
            unit="percent",
            service="svc",
            points=[(T0 + timedelta(seconds=60), 1.0), (T0, 2.0)],
        )


def test_ground_truth_requires_evidence_path_unless_escalating():
    with pytest.raises(ValidationError, match="evidence_path"):
        GroundTruth(root_cause="x", fix="y", should_escalate=False, evidence_path=[])

    gt = GroundTruth(root_cause="x", fix="y", should_escalate=True, evidence_path=[])
    assert gt.should_escalate is True


def test_scenario_id_must_match_pattern():
    with pytest.raises(ValidationError):
        _make_scenario(id="scenario-1")


def test_scenario_logs_must_be_sorted():
    with pytest.raises(ValidationError, match="chronological"):
        _make_scenario(synthetic_logs=[_log(60), _log(0)])


def _make_scenario(**overrides) -> Scenario:
    data = {
        "id": "scn_001",
        "category": "bad_deploy",
        "title": "t",
        "source_url": "https://example.com",
        "source_note": "note",
        "incident_report": "r",
        "synthetic_logs": [_log(0), _log(60)],
        "synthetic_metrics": [],
        "synthetic_deploys": [],
        "ground_truth": {"root_cause": "c", "fix": "f", "evidence_path": ["e"]},
    }
    data.update(overrides)
    return Scenario.model_validate(data)


def test_make_scenario_helpers_and_accessors():
    s = _make_scenario()
    assert s.services() == {"svc"}
    lo, hi = s.time_range()
    assert lo == T0 and hi == T0 + timedelta(seconds=60)
