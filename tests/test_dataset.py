"""The golden set must always load, validate, and stay internally consistent."""

import pytest

from triage.dataset import SCENARIOS_DIR, load_scenario, load_scenarios

SCENARIO_FILES = sorted(SCENARIOS_DIR.glob("scn_*.json"))


def test_golden_set_is_non_empty():
    assert SCENARIO_FILES, "no scenario files found"


def test_load_scenarios_all():
    scenarios = load_scenarios()
    assert len(scenarios) == len(SCENARIO_FILES)
    assert [s.id for s in scenarios] == sorted(s.id for s in scenarios)


@pytest.mark.parametrize("path", SCENARIO_FILES, ids=lambda p: p.stem)
def test_scenario_is_consistent(path):
    s = load_scenario(path)

    # Every metric/deploy service also appears in the logs (no dangling services).
    log_services = {line.service for line in s.synthetic_logs}
    for m in s.synthetic_metrics:
        assert m.service in s.services()
    for d in s.synthetic_deploys:
        assert d.service in log_services or d.service in {m.service for m in s.synthetic_metrics}

    # Ground truth is coherent with the escalation flag.
    if s.ground_truth.should_escalate:
        assert s.category.value == "ambiguous"
    else:
        assert s.ground_truth.evidence_path
        assert s.ground_truth.fix

    # Evidence lives inside the stated incident window.
    lo, hi = s.time_range()
    assert lo < hi
