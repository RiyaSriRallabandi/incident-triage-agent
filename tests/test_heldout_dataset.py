"""The held-out test set must load, validate, and stay disjoint from the dev set."""

from triage.dataset import REPO_ROOT, load_scenario, load_scenarios

HELDOUT_DIR = REPO_ROOT / "data" / "eval" / "heldout" / "scenarios"
HELDOUT_FILES = sorted(HELDOUT_DIR.glob("scn_*.json"))


def test_heldout_set_is_present_and_valid():
    assert len(HELDOUT_FILES) == 10
    scenarios = load_scenarios(HELDOUT_DIR)
    assert len(scenarios) == 10
    for s in scenarios:
        if s.ground_truth.should_escalate:
            assert s.category.value == "ambiguous"
        else:
            assert s.ground_truth.evidence_path


def test_heldout_covers_every_category_and_has_an_escalate_case():
    scenarios = load_scenarios(HELDOUT_DIR)
    categories = {s.category.value for s in scenarios}
    assert categories == {
        "bad_deploy",
        "resource_exhaustion",
        "dependency_failure",
        "network_dns",
        "cert_config_expiry",
        "database_issue",
        "ambiguous",
    }
    assert sum(s.ground_truth.should_escalate for s in scenarios) == 1


def test_heldout_ids_are_disjoint_from_the_dev_set():
    dev = {s.id for s in load_scenarios()}
    held = {s.id for s in load_scenarios(HELDOUT_DIR)}
    assert dev.isdisjoint(held)
    assert held == {f"scn_1{n:02d}" for n in range(1, 11)}


def test_each_heldout_scenario_regenerates_from_its_spec():
    import json

    from triage.ingest.evidence import ScenarioSpec, generate_scenario

    for scenario_path in HELDOUT_FILES:
        spec_path = (
            REPO_ROOT / "data" / "eval" / "heldout" / "specs" / f"{scenario_path.stem}.spec.json"
        )
        spec = ScenarioSpec.model_validate_json(spec_path.read_text())
        regenerated = json.loads(generate_scenario(spec).model_dump_json())
        committed = json.loads(scenario_path.read_text())
        assert committed == regenerated, f"{scenario_path.name} is stale"
        # sanity: loader accepts it
        load_scenario(scenario_path)
